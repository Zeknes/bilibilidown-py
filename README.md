# BiliDown-Py

A cross-platform Bilibili video downloader built with Python and **PySide6 (Qt)**.

## Features

- **Parse Video URLs:** Supports Bilibili video URLs and BVIDs.
- **Video Information:** Displays video title and thumbnail.
- **Download Options:** Supports downloading MP4/FLV or DASH video streams.
- **QR Code Login:** Secure login via Bilibili mobile app QR code.
- **Cross-Platform:** Works on macOS, Windows, and Linux.

## Prerequisites

- Python 3.8+
- FFmpeg (Optional, for merging audio/video in future updates)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Zeknes/bilibilidown-py.git
   cd bilibilidown-py
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running from Source

You can run the application directly using Python:

```bash
python main.py
```

Or use the provided shell script (macOS/Linux):

```bash
./run.sh
```

### Building the Application

To create a standalone executable/app bundle:

1. Ensure you have installed the build requirements (included in `requirements.txt` or install `pyinstaller` manually).
2. Run the build script:

```bash
python build_app.py
```

The executable will be generated in the `dist/` directory.

## Configuration

- **Cookies:** Login information is stored locally in `cookies.pkl`. This file is ignored by git to protect your session.
- **Downloads:** Videos are saved to the current working directory or a specified `downloads/` folder (depending on implementation).

## License

[MIT License](LICENSE)
