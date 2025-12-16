import os
import sys
import subprocess
import shutil
import platform
import multiprocessing
import datetime

# Application Metadata
APP_PKG_NAME = "bilibilidown"
APP_NAME = "BiliDown"
APP_VERSION = "1.1.0"
APP_RELEASE = "1"
APP_DESCRIPTION = "Bilibili Video Downloader with GUI"
APP_MAINTAINER = "BiliDown Team"
APP_EMAIL = "zeknes@163.com"
APP_LICENSE = "MIT"
APP_URL = "https://github.com/zeknes/bilibilidown-py"

def create_deb(source_dir, output_dir, version=APP_VERSION):
    """
    Create a .deb package for Linux distribution (supports both dpkg-deb and manual ar method)
    """
    print("\n=== Creating DEB Package ===")
    
    # Determine Architecture
    arch = platform.machine()
    if arch == "x86_64":
        deb_arch = "amd64"
    elif arch == "aarch64":
        deb_arch = "arm64"
    else:
        deb_arch = arch

    # Setup build directories
    build_root = os.path.join(output_dir, "deb_build")
    if os.path.exists(build_root):
        shutil.rmtree(build_root)
        
    deb_opt = os.path.join(build_root, "opt", APP_PKG_NAME)
    deb_bin = os.path.join(build_root, "usr", "bin")
    deb_desktop = os.path.join(build_root, "usr", "share", "applications")
    deb_icon = os.path.join(build_root, "usr", "share", "pixmaps")
    deb_debian = os.path.join(build_root, "DEBIAN")
    
    for d in [deb_opt, deb_bin, deb_desktop, deb_icon, deb_debian]:
        os.makedirs(d, exist_ok=True)
    
    # Copy application files
    print(f"   Copying application files from {source_dir}...")
    if os.path.isdir(source_dir):
        shutil.copytree(source_dir, deb_opt, dirs_exist_ok=True)
    else:
        shutil.copy2(source_dir, deb_opt)
        
    # Ensure executable permissions
    main_exec = os.path.join(deb_opt, "main")
    if os.path.exists(main_exec):
        os.chmod(main_exec, 0o755)
    
    # Create launcher script
    launcher_path = os.path.join(deb_bin, APP_PKG_NAME)
    with open(launcher_path, 'w') as f:
        f.write(f"""#!/bin/bash
cd /opt/{APP_PKG_NAME}
exec ./main "$@"
""")
    os.chmod(launcher_path, 0o755)

    # Create .desktop file
    with open(os.path.join(deb_desktop, f"{APP_PKG_NAME}.desktop"), "w") as f:
        f.write(f"""[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
GenericName=Bilibili Video Downloader
Comment={APP_DESCRIPTION}
Exec={APP_PKG_NAME}
Icon={APP_PKG_NAME}
Terminal=false
Categories=Network;AudioVideo;Qt;
Keywords=bilibili;video;download;
""")
        
    # Copy icon
    if os.path.exists("bili.png"):
        shutil.copy2("bili.png", os.path.join(deb_icon, f"{APP_PKG_NAME}.png"))
        
    # Calculate installed size
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(deb_opt):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if not os.path.islink(filepath):
                total_size += os.path.getsize(filepath)
    installed_size = total_size // 1024
    
    # Create control file
    with open(os.path.join(deb_debian, "control"), "w") as f:
        f.write(f"""Package: {APP_PKG_NAME}
Version: {version}-{APP_RELEASE}
Section: net
Priority: optional
Architecture: {deb_arch}
Installed-Size: {installed_size}
Maintainer: {APP_MAINTAINER} <{APP_EMAIL}>
Description: {APP_DESCRIPTION}
 BiliDown is a GUI application for downloading videos from Bilibili.
 It supports multiple video qualities and formats with a modern interface.
""")
        
    # Create postinst script
    postinst_path = os.path.join(deb_debian, "postinst")
    with open(postinst_path, "w") as f:
        f.write(f"""#!/bin/bash
set -e
chmod +x /opt/{APP_PKG_NAME}/main 2>/dev/null || true
exit 0
""")
    os.chmod(postinst_path, 0o755)

    deb_filename = f"{APP_PKG_NAME}_{version}-{APP_RELEASE}_{deb_arch}.deb"
    deb_path = os.path.join(output_dir, deb_filename)

    # Try dpkg-deb first
    if shutil.which("dpkg-deb"):
        try:
            subprocess.run(["dpkg-deb", "--build", build_root, deb_path], check=True)
            print(f"✅ DEB package created: {deb_path}")
            shutil.rmtree(build_root)
            return
        except subprocess.CalledProcessError:
            print("⚠️ dpkg-deb failed, trying manual method...")
    
    # Manual fallback using ar/tar
    print("   Using manual construction (ar + tar)...")
    try:
        # Create data.tar.gz
        data_tar = os.path.join(output_dir, "data.tar.gz")
        subprocess.run([
            "tar", "-czf", data_tar,
            "-C", build_root,
            "--exclude=DEBIAN", "."
        ], check=True)
        
        # Create control.tar.gz
        control_tar = os.path.join(output_dir, "control.tar.gz")
        subprocess.run([
            "tar", "-czf", control_tar,
            "-C", deb_debian, "."
        ], check=True)
        
        # Create debian-binary
        debian_binary = os.path.join(output_dir, "debian-binary")
        with open(debian_binary, 'w') as f:
            f.write("2.0\n")
            
        # Combine with ar
        if shutil.which("ar"):
            if os.path.exists(deb_path):
                os.remove(deb_path)
            subprocess.run([
                "ar", "r", deb_path,
                debian_binary, control_tar, data_tar
            ], check=True)
            print(f"✅ DEB package created (manual): {deb_path}")
        else:
            print("❌ 'ar' utility not found. Cannot create DEB package.")
            
        # Cleanup temp files
        for f in [data_tar, control_tar, debian_binary]:
            if os.path.exists(f):
                os.remove(f)
        shutil.rmtree(build_root)
            
    except Exception as e:
        print(f"❌ Failed to create DEB package: {e}")

def create_rpm(source_dir, output_dir, version=APP_VERSION):
    """
    Create a .rpm package for Linux distribution using rpmbuild
    """
    print("\n=== Creating RPM Package ===")
    
    if not shutil.which("rpmbuild"):
        print("⚠️ 'rpmbuild' not found. Skipping RPM creation.")
        return

    # RPM build structure
    rpm_root = os.path.join(output_dir, "rpm_build")
    if os.path.exists(rpm_root):
        shutil.rmtree(rpm_root)
        
    for d in ["BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"]:
        os.makedirs(os.path.join(rpm_root, d), exist_ok=True)
    
    spec_file = os.path.join(rpm_root, "SPECS", f"{APP_PKG_NAME}.spec")
    changelog_date = datetime.datetime.now().strftime("%a %b %d %Y")
    
    # Determine architecture
    arch = platform.machine()
    
    # We will simply copy the binaries in %install, no need for Source0 tarball
    # This is a binary repackaging
    
    with open(spec_file, 'w') as f:
        f.write(f"""Name:           {APP_PKG_NAME}
Version:        {version}
Release:        {APP_RELEASE}%{{?dist}}
Summary:        {APP_DESCRIPTION}
License:        {APP_LICENSE}
URL:            {APP_URL}
BuildArch:      {arch}
AutoReqProv:    no

%description
BiliDown is a GUI application for downloading videos from Bilibili.
It supports multiple video qualities and formats with a modern interface.

%prep
# No prep

%build
# No build

%install
rm -rf %{{buildroot}}
mkdir -p %{{buildroot}}/opt/{APP_PKG_NAME}
mkdir -p %{{buildroot}}/usr/bin
mkdir -p %{{buildroot}}/usr/share/applications
mkdir -p %{{buildroot}}/usr/share/pixmaps

# Copy application files
# We need to copy from the external source directory
cp -a {os.path.abspath(source_dir)}/* %{{buildroot}}/opt/{APP_PKG_NAME}/

# Ensure main is executable
chmod 755 %{{buildroot}}/opt/{APP_PKG_NAME}/main

# Create launcher
cat > %{{buildroot}}/usr/bin/{APP_PKG_NAME} << 'EOF'
#!/bin/bash
cd /opt/{APP_PKG_NAME}
exec ./main "$@"
EOF
chmod 755 %{{buildroot}}/usr/bin/{APP_PKG_NAME}

# Create desktop file
cat > %{{buildroot}}/usr/share/applications/{APP_PKG_NAME}.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name={APP_NAME}
GenericName=Bilibili Video Downloader
Comment={APP_DESCRIPTION}
Exec={APP_PKG_NAME}
Icon={APP_PKG_NAME}
Terminal=false
Categories=Network;AudioVideo;Qt;
Keywords=bilibili;video;download;
EOF

# Copy icon
if [ -f "{os.path.abspath('bili.png')}" ]; then
    cp "{os.path.abspath('bili.png')}" %{{buildroot}}/usr/share/pixmaps/{APP_PKG_NAME}.png
fi

%files
%defattr(-,root,root,-)
/opt/{APP_PKG_NAME}
/usr/bin/{APP_PKG_NAME}
/usr/share/applications/{APP_PKG_NAME}.desktop
/usr/share/pixmaps/{APP_PKG_NAME}.png

%changelog
* {changelog_date} {APP_MAINTAINER} <{APP_EMAIL}> - {version}-{APP_RELEASE}
- Automated build release
""")

    print(f"   Building RPM package using spec: {spec_file}")
    try:
        subprocess.check_call([
            "rpmbuild", 
            "--define", f"_topdir {os.path.abspath(rpm_root)}", 
            "-bb", spec_file
        ], stdout=subprocess.DEVNULL) # Suppress verbose output
        
        # Find and move RPM
        rpms_dir = os.path.join(rpm_root, "RPMS")
        found = False
        for root, dirs, files in os.walk(rpms_dir):
            for file in files:
                if file.endswith(".rpm"):
                    src = os.path.join(root, file)
                    dst = os.path.join(output_dir, file)
                    shutil.move(src, dst)
                    print(f"✅ RPM package created: {dst}")
                    found = True
        
        if not found:
            print("❌ RPM build finished but no .rpm file found.")
            
        # Cleanup
        shutil.rmtree(rpm_root)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create RPM package: {e}")

def create_dmg(app_path):
    """
    Create a DMG file for macOS distribution using create-dmg tool
    """
    if not os.path.exists(app_path):
        print("❌ App bundle not found, cannot create DMG.")
        return

    dmg_name = "BiliDown-Installer.dmg"
    dmg_path = os.path.join(os.path.dirname(app_path), dmg_name)
    
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
        
    print(f"📦 Creating DMG installer: {dmg_name}...")
    
    # Check if create-dmg is installed
    try:
        subprocess.check_call(["which", "create-dmg"], stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("⚠️ 'create-dmg' tool not found. Skipping DMG creation.")
        print("💡 Run 'brew install create-dmg' to enable this feature.")
        return

    cmd = [
        "create-dmg",
        "--volname", "BiliDown Installer",
        "--volicon", "bili.png",
        "--window-pos", "200", "120",
        "--window-size", "800", "400",
        "--icon-size", "100",
        "--icon", "BiliDown.app", "200", "190",
        "--hide-extension", "BiliDown.app",
        "--app-drop-link", "600", "185",
        dmg_path,
        app_path
    ]
    
    try:
        subprocess.check_call(cmd)
        print(f"✅ DMG created successfully: {dmg_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create DMG: {e}")

def build():
    print("🚀 Starting Nuitka build...")
    
    # Detect OS
    system_os = platform.system()
    print(f"💻 Detected OS: {system_os}")
    
    # Get CPU count for parallel compilation
    n_cores = multiprocessing.cpu_count()
    print(f"🔥 Using {n_cores} cores for compilation")

    # Base command
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",    # Smart dependency handling for PySide6
        "--show-progress",
        "--show-memory",
        f"--jobs={n_cores}",          # Enable parallel compilation
        "--output-dir=dist_nuitka",
        "--include-data-file=bili.png=bili.png",
        "--main=main.py",
    ]
    
    # OS-specific flags
    output_artifact = ""
    
    if system_os == "Darwin": # macOS
        cmd.extend([
            "--macos-create-app-bundle",
            "--macos-app-name=BiliDown",
            "--macos-app-icon=bili.png",
            "--disable-console",
        ])
        output_artifact = "BiliDown.app"
        
        # Nuitka 2.x sometimes names the app based on script name even with --macos-app-name
        # We'll check for both
        possible_artifacts = ["BiliDown.app", "main.app"]
        
    elif system_os == "Linux":
        # Linux specific flags
        # On Linux, standalone usually creates a folder with the binary inside
        # We can try to use --onefile if preferred, but standalone is safer for PySide6
        # Adding icon if supported by desktop environment integration
        cmd.extend([
            "--linux-icon=bili.png",
        ])
        output_artifact = "main.dist/main" # Nuitka default output name in standalone mode
        
    elif system_os == "Windows":
        cmd.extend([
            "--windows-icon-from-ico=bili.png", # Nuitka might auto-convert or need .ico
            "--disable-console",
        ])
        output_artifact = "main.dist\\main.exe"

    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ Build successful!")
        
        # Determine actual artifact path
        dist_dir = os.path.join(os.getcwd(), 'dist_nuitka')
        artifact_path = os.path.join(dist_dir, output_artifact)
        
        if system_os == "Darwin":
             # Check if Nuitka created main.app instead of BiliDown.app
            fallback_path = os.path.join(dist_dir, "main.app")
            if not os.path.exists(artifact_path) and os.path.exists(fallback_path):
                print(f"⚠️ Nuitka created 'main.app', renaming to '{output_artifact}'...")
                shutil.move(fallback_path, artifact_path)
                
        elif system_os == "Linux":
            # Check if Nuitka created main.bin instead of main
            # We need to ensure the binary is named 'main' because our .desktop files and scripts expect it
            dist_folder = os.path.join(dist_dir, "main.dist")
            binary_path = os.path.join(dist_folder, "main")
            binary_bin_path = os.path.join(dist_folder, "main.bin")
            
            if not os.path.exists(binary_path) and os.path.exists(binary_bin_path):
                 print("⚠️ Nuitka created 'main.bin', renaming to 'main'...")
                 shutil.move(binary_bin_path, binary_path)

        print(f"Artifact location: {artifact_path}")
        
        # Bundle ffmpeg
        print("🎥 Bundling ffmpeg...")
        ffmpeg_src = shutil.which("ffmpeg")
        if ffmpeg_src:
            if system_os == "Darwin":
                # For macOS .app, put in Contents/MacOS
                dest_dir = os.path.join(artifact_path, "Contents", "MacOS")
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(ffmpeg_src, os.path.join(dest_dir, "ffmpeg"))
            elif system_os == "Linux":
                # For Linux, put in main.dist
                dest_dir = os.path.dirname(artifact_path)
                shutil.copy2(ffmpeg_src, os.path.join(dest_dir, "ffmpeg"))
            elif system_os == "Windows":
                 # For Windows, put in main.dist
                 dest_dir = os.path.dirname(artifact_path)
                 shutil.copy2(ffmpeg_src, os.path.join(dest_dir, "ffmpeg.exe"))
            print(f"✅ ffmpeg bundled from {ffmpeg_src}")
        else:
            print("⚠️ ffmpeg not found in PATH. It will not be bundled.")

        # Create DMG for macOS
        if system_os == "Darwin" and output_artifact.endswith(".app"):
            create_dmg(artifact_path)
            
        # Create DEB and RPM for Linux
        if system_os == "Linux":
            # For Linux standalone, we package the whole 'main.dist' directory
            dist_folder = os.path.join(dist_dir, "main.dist")
            create_deb(dist_folder, dist_dir)
            create_rpm(dist_folder, dist_dir)
        
        # Open the output folder
        output_dir = dist_dir
        try:
            if system_os == "Darwin":
                subprocess.call(["open", output_dir])
            elif system_os == "Linux":
                subprocess.call(["xdg-open", output_dir])
            elif system_os == "Windows":
                os.startfile(output_dir)
        except Exception:
            pass # Ignore errors opening folder
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    # Clean previous build
    if os.path.exists("dist_nuitka"):
        shutil.rmtree("dist_nuitka")
    if os.path.exists("main.build"):
        shutil.rmtree("main.build")
        
    build()
