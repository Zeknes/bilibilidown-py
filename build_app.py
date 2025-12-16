import os
import sys
import subprocess
import shutil
import platform
import multiprocessing

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

        print(f"Artifact location: {artifact_path}")
        
        # Create DMG for macOS
        if system_os == "Darwin" and output_artifact.endswith(".app"):
            create_dmg(artifact_path)
        
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
