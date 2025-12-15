import os
import platform
import subprocess
import sys

import shutil

def create_icns(png_path, icon_name="icon"):
    """
    Generate .icns from a .png file on macOS using sips and iconutil.
    """
    if not os.path.exists(png_path):
        return None

    iconset_name = f"{icon_name}.iconset"
    if os.path.exists(iconset_name):
        shutil.rmtree(iconset_name)
    os.makedirs(iconset_name)

    # Standard sizes for macOS icons
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    try:
        # Check source image size
        try:
            out = subprocess.check_output(["sips", "-g", "pixelHeight", png_path])
            height = int(out.decode().split(":")[-1].strip())
        except:
            height = 1024 # Assume large if check fails

        for size in sizes:
            # Normal resolution
            out_file = os.path.join(iconset_name, f"icon_{size}x{size}.png")
            try:
                subprocess.run(["sips", "-z", str(size), str(size), png_path, "--out", out_file], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                print(f"Warning: Failed to resize to {size}x{size}")

            # High resolution (Retina)
            if size <= 512:
                out_file_2x = os.path.join(iconset_name, f"icon_{size}x{size}@2x.png")
                try:
                    subprocess.run(["sips", "-z", str(size*2), str(size*2), png_path, "--out", out_file_2x], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    print(f"Warning: Failed to resize to {size*2}x{size*2}")

        # Generate .icns

        icns_path = f"{icon_name}.icns"
        subprocess.run(["iconutil", "-c", "icns", iconset_name, "-o", icns_path], check=True)
        
        # Cleanup
        shutil.rmtree(iconset_name)
        return icns_path

    except Exception as e:
        print(f"Error creating icns: {e}")
        if os.path.exists(iconset_name):
            shutil.rmtree(iconset_name)
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
