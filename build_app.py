import os
import sys
import subprocess
import shutil

def build():
    print("🚀 Starting Nuitka build...")
    
    # Check if ccache is available (optional but recommended for speed)
    # subprocess.call(["brew", "install", "ccache"]) 

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--macos-create-app-bundle",  # Create .app bundle (best for macOS)
        "--enable-plugin=pyside6",    # Smart dependency handling for PySide6
        "--show-progress",
        "--show-memory",
        "--output-dir=dist_nuitka",
        "--macos-app-name=BiliDown",
        "--macos-app-icon=bili.png",  # Nuitka handles png to icns conversion automatically if capable
        "--include-data-file=bili.png=bili.png",
        "--main=main.py",
    ]
    
    # If you really want a single binary file (not .app bundle) on macOS, 
    # you can use --onefile, but .app is standard for GUI.
    # Nuitka's .app bundle startup is much faster than PyInstaller's onefile.
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ Build successful!")
        print(f"App is located at: {os.path.join(os.getcwd(), 'dist_nuitka', 'BiliDown.app')}")
        
        # Open the folder
        subprocess.call(["open", "dist_nuitka"])
        
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
