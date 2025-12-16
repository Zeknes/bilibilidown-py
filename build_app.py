import os
import sys
import subprocess
import shutil
import platform
import multiprocessing

def create_deb(source_dir, output_dir, version="1.0.0"):
    """
    Create a .deb package for Linux distribution
    """
    print("📦 Creating DEB package...")
    
    # Check if dpkg-deb is installed
    if not shutil.which("dpkg-deb"):
        print("⚠️ 'dpkg-deb' not found. Skipping DEB creation.")
        return

    arch = platform.machine()
    if arch == "x86_64":
        deb_arch = "amd64"
    elif arch == "aarch64":
        deb_arch = "arm64"
    else:
        deb_arch = arch

    package_name = "bilibilidown"
    build_root = os.path.join(output_dir, "deb_build")
    
    # Clean previous build dir
    if os.path.exists(build_root):
        shutil.rmtree(build_root)
        
    # Create directory structure
    # /opt/bilibilidown -> application files
    # /usr/share/applications -> desktop shortcut
    # /usr/share/icons -> icon
    
    opt_dir = os.path.join(build_root, "opt", package_name)
    os.makedirs(opt_dir)
    
    # Copy application files
    # source_dir is 'main.dist' which contains the binary and dependencies
    # We copy the content of source_dir to opt_dir
    if os.path.isdir(source_dir):
        shutil.copytree(source_dir, opt_dir, dirs_exist_ok=True)
    else:
        # If source is a single file (not likely with standalone, but just in case)
        shutil.copy2(source_dir, opt_dir)
        
    # Create control file
    debian_dir = os.path.join(build_root, "DEBIAN")
    os.makedirs(debian_dir)
    
    control_content = f"""Package: {package_name}
Version: {version}
Section: utils
Priority: optional
Architecture: {deb_arch}
Maintainer: BiliDown Developer <zeknes@163.com>
Description: Bilibili Video Downloader
 A desktop application to download videos from Bilibili.
"""
    with open(os.path.join(debian_dir, "control"), "w") as f:
        f.write(control_content)
        
    # Create postinst script to set permissions
    postinst_content = f"""#!/bin/sh
chmod +x /opt/{package_name}/main
"""
    postinst_path = os.path.join(debian_dir, "postinst")
    with open(postinst_path, "w") as f:
        f.write(postinst_content)
    os.chmod(postinst_path, 0o755)

    # Create .desktop file
    apps_dir = os.path.join(build_root, "usr", "share", "applications")
    os.makedirs(apps_dir)
    
    desktop_content = f"""[Desktop Entry]
Name=BiliDown
Comment=Download Bilibili Videos
Exec=/opt/{package_name}/main
Icon={package_name}
Terminal=false
Type=Application
Categories=Utility;Network;
"""
    with open(os.path.join(apps_dir, f"{package_name}.desktop"), "w") as f:
        f.write(desktop_content)
        
    # Copy icon
    # Assuming bili.png exists in current directory
    if os.path.exists("bili.png"):
        icon_dir = os.path.join(build_root, "usr", "share", "icons", "hicolor", "512x512", "apps")
        os.makedirs(icon_dir)
        shutil.copy2("bili.png", os.path.join(icon_dir, f"{package_name}.png"))
        
    # Build package
    deb_filename = f"{package_name}_{version}_{deb_arch}.deb"
    deb_path = os.path.join(output_dir, deb_filename)
    
    try:
        subprocess.check_call(["dpkg-deb", "--build", build_root, deb_path])
        print(f"✅ DEB package created: {deb_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create DEB package: {e}")
        
    # Cleanup build root
    # shutil.rmtree(build_root) 

def create_rpm(source_dir, output_dir, version="1.0.0"):
    """
    Create a .rpm package for Linux distribution using rpmbuild
    """
    print("📦 Creating RPM package...")
    
    if not shutil.which("rpmbuild"):
        print("⚠️ 'rpmbuild' not found. Skipping RPM creation.")
        return

    package_name = "bilibilidown"
    arch = platform.machine()
    
    # RPM build structure
    rpm_root = os.path.join(output_dir, "rpm_build")
    for d in ["BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS"]:
        os.makedirs(os.path.join(rpm_root, d), exist_ok=True)
        
    # We need to tar the source to put in SOURCES
    # But since we have a binary distribution, we can trick it or use a simpler spec
    # Let's try to copy files directly in %install without a source tarball if possible
    # But rpmbuild really wants a source.
    # We will create a fake tarball of the binary distribution
    
    print("   Preparing sources for RPM...")
    source_tar = f"{package_name}-{version}.tar.gz"
    tar_path = os.path.join(rpm_root, "SOURCES", source_tar)
    
    # Create tarball of the dist folder
    # We want the tarball to contain a folder named bilibilidown-1.0.0 containing the files
    temp_src = os.path.join(output_dir, f"{package_name}-{version}")
    if os.path.exists(temp_src):
        shutil.rmtree(temp_src)
    
    if os.path.isdir(source_dir):
        shutil.copytree(source_dir, temp_src)
    else:
        os.makedirs(temp_src)
        shutil.copy2(source_dir, temp_src)
        
    # Add icon to source
    if os.path.exists("bili.png"):
        shutil.copy2("bili.png", temp_src)
        
    # Create tar
    subprocess.check_call(["tar", "-czf", tar_path, "-C", output_dir, f"{package_name}-{version}"])
    
    # Cleanup temp src
    shutil.rmtree(temp_src)
    
    # Create SPEC file
    spec_content = f"""
Name:           {package_name}
Version:        {version}
Release:        1
Summary:        Bilibili Video Downloader
License:        MIT
URL:            https://github.com/Zeknes/bilibilidown-py
Source0:        %{{name}}-%{{version}}.tar.gz

%description
A GUI tool to download videos from Bilibili.

%prep
%setup -q

%build
# Nothing to build, we have binaries

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/opt/{package_name}
mkdir -p $RPM_BUILD_ROOT/usr/share/applications
mkdir -p $RPM_BUILD_ROOT/usr/share/icons/hicolor/512x512/apps

# Copy binary files
cp -r * $RPM_BUILD_ROOT/opt/{package_name}/

# Create desktop file
cat > $RPM_BUILD_ROOT/usr/share/applications/{package_name}.desktop <<EOF
[Desktop Entry]
Name=BiliDown
Comment=Download Bilibili Videos
Exec=/opt/{package_name}/main
Icon={package_name}
Terminal=false
Type=Application
Categories=Utility;Network;
EOF

# Install icon
if [ -f bili.png ]; then
    cp bili.png $RPM_BUILD_ROOT/usr/share/icons/hicolor/512x512/apps/{package_name}.png
fi

# Cleanup source files that shouldn't be in /opt
rm -f $RPM_BUILD_ROOT/opt/{package_name}/bili.png
rm -f $RPM_BUILD_ROOT/opt/{package_name}/{package_name}.desktop

%files
/opt/{package_name}
/usr/share/applications/{package_name}.desktop
/usr/share/icons/hicolor/512x512/apps/{package_name}.png

%changelog
* Mon Dec 16 2024 Developer <dev@example.com> - 1.0.0-1
- Initial release
"""

    spec_path = os.path.join(rpm_root, "SPECS", f"{package_name}.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)
        
    # Build RPM
    try:
        subprocess.check_call([
            "rpmbuild", 
            "--define", f"_topdir {rpm_root}", 
            "-bb", spec_path
        ])
        
        # Move RPM to output dir
        rpm_arch_dir = os.path.join(rpm_root, "RPMS", arch)
        if not os.path.exists(rpm_arch_dir):
             # Try x86_64 if machine is different
             rpm_arch_dir = os.path.join(rpm_root, "RPMS", "x86_64")
             
        if os.path.exists(rpm_arch_dir):
            for file in os.listdir(rpm_arch_dir):
                if file.endswith(".rpm"):
                    shutil.move(os.path.join(rpm_arch_dir, file), os.path.join(output_dir, file))
                    print(f"✅ RPM package created: {os.path.join(output_dir, file)}")
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
