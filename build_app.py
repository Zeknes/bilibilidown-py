import os
import platform
import subprocess
import sys

def build():
    system = platform.system()
    sep = os.path.sep
    
    print(f"Detected system: {system}")
    
    # Common PyInstaller options
    # -F: One file
    # -w: No console window (GUI only)
    # --add-data: Add bili.png if exists
    # --name: Output name
    
    cmd = [
        "pyinstaller",
        "-F",
        "-w",
        "--name", "BiliDown",
        "--clean",
        "main.py"
    ]
    
    # Add icon if exists
    icon_path = "bili.png"
    if os.path.exists(icon_path):
        if system == "Windows":
            # On Windows, use icon for exe
            cmd.extend(["--icon", icon_path])
            cmd.extend(["--add-data", f"{icon_path};."])
        else:
            # On Mac/Linux, add data
            cmd.extend(["--add-data", f"{icon_path}:."])
            if system == "Darwin":
                 # On Mac, use icon for .app bundle (if .icns exists, otherwise PyInstaller handles png somewhat or ignore)
                 # For now, just adding data
                 pass
    
    print("Running command:", " ".join(cmd))
    
    try:
        subprocess.check_call(cmd)
        print("\nBuild successful!")
        print(f"Executable is in: {os.path.join(os.getcwd(), 'dist')}")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    build()
