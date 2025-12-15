# BiliDown-Py

> **特别致谢 / Special Thanks**: 本项目灵感来源于及部分参考了 [nICEnnnnnnnLee/BilibiliDown](https://github.com/nICEnnnnnnnLee/BilibiliDown/releases)。
>
> **Special Thanks**: This project is inspired by and partially references [nICEnnnnnnnLee/BilibiliDown](https://github.com/nICEnnnnnnnLee/BilibiliDown/releases).

[中文](#中文) | [English](#english)

---

<a id="中文"></a>
## 中文说明

基于 Python 和 **PySide6 (Qt)** 构建的跨平台 Bilibili 视频下载器。

### ✨ 功能特性

- **解析视频**: 支持 Bilibili 视频链接和 BVID。
- **视频信息**: 显示视频标题和缩略图。
- **下载选项**: 支持下载 MP4/FLV 或 DASH 视频流。
- **扫码登录**: 通过 Bilibili 手机 App 安全扫码登录。
- **跨平台**: 支持 macOS, Windows 和 Linux。

### 📥 下载与使用

**推荐普通用户直接下载可执行文件：**

请前往 [GitHub Releases](https://github.com/Zeknes/bilibilidown-py/releases) 页面下载最新版本的应用程序。

### 🛠️ 源码运行 (开发人员)

如果您希望从源码运行或参与开发：

1. **克隆仓库**:
   ```bash
   git clone https://github.com/Zeknes/bilibilidown-py.git
   cd bilibilidown-py
   ```

2. **安装依赖**:
   ```bash
   # 创建虚拟环境
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   # 安装依赖
   pip install -r requirements.txt
   ```

3. **运行**:
   ```bash
   python main.py
   # 或使用脚本 (macOS/Linux)
   ./run.sh
   ```

### ⚙️ 配置说明

- **Cookies**: 登录信息保存在本地 `cookies.pkl` 文件中。
- **下载路径**: 视频默认保存到当前目录或 `downloads/` 文件夹。

---

<a id="english"></a>
## English Description

A cross-platform Bilibili video downloader built with Python and **PySide6 (Qt)**.

### ✨ Features

- **Parse Video URLs:** Supports Bilibili video URLs and BVIDs.
- **Video Information:** Displays video title and thumbnail.
- **Download Options:** Supports downloading MP4/FLV or DASH video streams.
- **QR Code Login:** Secure login via Bilibili mobile app QR code.
- **Cross-Platform:** Works on macOS, Windows, and Linux.

### 📥 Download & Usage

**For end users, please download the executable directly:**

Go to the [GitHub Releases](https://github.com/Zeknes/bilibilidown-py/releases) page to download the latest version.

### 🛠️ Run from Source (Developers)

If you want to run from source or contribute:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Zeknes/bilibilidown-py.git
   cd bilibilidown-py
   ```

2. **Install dependencies:**
   ```bash
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

   # Install requirements
   pip install -r requirements.txt
   ```

3. **Run:**
   ```bash
   python main.py
   # Or use shell script (macOS/Linux)
   ./run.sh
   ```

### ⚙️ Configuration

- **Cookies:** Login information is stored locally in `cookies.pkl`.
- **Downloads:** Videos are saved to the current working directory or a specified `downloads/` folder.

---

## License

[MIT License](LICENSE)
