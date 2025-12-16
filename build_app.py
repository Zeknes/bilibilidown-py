import os
import sys
import subprocess
import shutil
import platform
import multiprocessing

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
        ])
        output_artifact = "BiliDown.app"
        
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
        
        artifact_path = os.path.join(os.getcwd(), 'dist_nuitka', output_artifact)
        print(f"Artifact location: {artifact_path}")
        
        # Open the output folder
        output_dir = os.path.join(os.getcwd(), 'dist_nuitka')
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
