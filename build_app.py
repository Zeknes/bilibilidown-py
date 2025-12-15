import os
import platform
import subprocess
import sys

import shutil
from PIL import Image

def create_icns(png_path, icon_name="icon"):
    """
    Generate .icns from a .png file using Pillow.
    """
    if not os.path.exists(png_path):
        return None

    icns_path = f"{icon_name}.icns"
    
    try:
        img = Image.open(png_path)
        img.save(icns_path, format='ICNS')
        return icns_path
    except Exception as e:
        print(f"Error creating icns with Pillow: {e}")
        return None

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
                 # Generate .icns for macOS .app bundle
                 icns_path = create_icns(icon_path, "BiliDown")
                 if icns_path and os.path.exists(icns_path):
                     print(f"Generated icon: {icns_path}")
                     cmd.extend(["--icon", icns_path])
                 else:
                     print("Failed to generate .icns, app icon might be missing.")

    
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
