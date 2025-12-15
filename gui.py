import sys
import os
import threading
import requests
from io import BytesIO
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QProgressBar, QMessageBox, 
                             QDialog, QComboBox, QScrollArea, QFrame, QGraphicsDropShadowEffect,
                             QGraphicsOpacityEffect, QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint
from PySide6.QtGui import QPixmap, QImage, QIcon, QFont, QColor, QPainter, QPainterPath

from core import BiliDownloader

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class WorkerThread(QThread):
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, target, *args):
        super().__init__()
        self.target = target
        self.args = args
        
    def run(self):
        try:
            result = self.target(*self.args)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class DownloadWorker(QThread):
    progress = Signal(float)
    status = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, downloader, url, filepath, is_dash=False, dash_info=None):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.filepath = filepath
        self.is_dash = is_dash
        self.dash_info = dash_info

    def run(self):
        try:
            if not self.is_dash:
                self.downloader.download_file(self.url, self.filepath, self._progress_callback)
                self.finished.emit(self.filepath)
            else:
                # DASH Logic
                video_url = self.dash_info['video_url']
                audio_url = self.dash_info['audio_url']
                v_path = self.dash_info['v_path']
                a_path = self.dash_info['a_path']
                out_path = self.filepath

                self.status.emit("Downloading Video...")
                self.downloader.download_file(video_url, v_path, self._progress_callback_factory(0, 50))
                
                self.status.emit("Downloading Audio...")
                self.downloader.download_file(audio_url, a_path, self._progress_callback_factory(50, 95))
                
                self.status.emit("Merging...")
                try:
                    self.downloader.merge_video_audio(v_path, a_path, out_path)
                    if os.path.exists(v_path): os.remove(v_path)
                    if os.path.exists(a_path): os.remove(a_path)
                    self.progress.emit(100)
                    self.finished.emit(out_path)
                except Exception as e:
                    self.error.emit(f"Merge failed: {str(e)}")

        except Exception as e:
            self.error.emit(str(e))

    def _progress_callback(self, current, total):
        if total > 0:
            p = (current / total) * 100
            self.progress.emit(p)
            self.status.emit(f"Downloading... {int(p)}%")

    def _progress_callback_factory(self, start, end):
        def callback(current, total):
            if total > 0:
                fraction = current / total
                p = start + (fraction * (end - start))
                self.progress.emit(p)
                self.status.emit(f"Downloading... {int(p)}%")
        return callback

class LoginDialog(QDialog):
    def __init__(self, authenticator, parent=None):
        super().__init__(parent)
        self.authenticator = authenticator
        self.setWindowTitle("Login to Bilibili")
        self.setFixedSize(360, 480)
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; }
            QLabel { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        """)
        self.setup_ui()
        self.start_login_process()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        title = QLabel("Scan QR Code")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #1D1D1F; letter-spacing: -0.5px;")
        layout.addWidget(title)
        
        self.lbl_info = QLabel("Open Bilibili App on your phone\nand scan the QR code to login.")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        self.lbl_info.setStyleSheet("color: #86868B; font-size: 14px; line-height: 1.4;")
        layout.addWidget(self.lbl_info)
        
        qr_container = QFrame()
        qr_container.setStyleSheet("""
            background-color: white; 
            border-radius: 20px; 
            border: 1px solid rgba(0,0,0,0.05);
        """)
        # Shadow for QR
        qr_shadow = QGraphicsDropShadowEffect(qr_container)
        qr_shadow.setBlurRadius(30)
        qr_shadow.setOffset(0, 8)
        qr_shadow.setColor(QColor(0,0,0,15))
        qr_container.setGraphicsEffect(qr_shadow)
        
        qr_layout = QVBoxLayout(qr_container)
        qr_layout.setContentsMargins(24, 24, 24, 24)
        
        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setFixedSize(180, 180)
        qr_layout.addWidget(self.lbl_qr, 0, Qt.AlignCenter)
        
        layout.addWidget(qr_container, 0, Qt.AlignCenter)
        
        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #007AFF; font-weight: 600; font-size: 14px;")
        layout.addWidget(self.lbl_status)

    def start_login_process(self):
        try:
            self.qr_url = self.authenticator.get_login_qrcode()
            img_data = self.authenticator.get_qrcode_image(self.qr_url)
            
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            self.lbl_qr.setPixmap(pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.poll_status)
            self.timer.start(2000)
            
        except Exception as e:
            self.lbl_status.setText(f"Error: {e}")

    def poll_status(self):
        try:
            code, msg = self.authenticator.poll_login_status()
            if code == 0:
                self.lbl_status.setText("Success!")
                self.timer.stop()
                self.accept()
            elif code == 86101:
                self.lbl_status.setText("Waiting for scan...")
            elif code == 86090:
                self.lbl_status.setText("Scanned, please confirm")
            else:
                self.lbl_status.setText(msg)
        except Exception as e:
            print(e)

class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        # No shadow on the frame itself to keep it clean, relying on border and background opacity
        # But a subtle shadow helps separation on dark bg
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

class SearchInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Paste Bilibili Video Link (URL / BV)")
        self.setFixedHeight(50)
        self.setTextMargins(20, 0, 20, 0)
        self.setObjectName("SearchInput")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BiliDown")
        self.resize(900, 700)
        
        icon_path = resource_path("bili.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.downloader = BiliDownloader()
        self.current_info = None
        self.is_logged_in = False
        
        self.setup_ui()
        self.apply_styles()
        
        self.check_login_status()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Background container (for full window content)
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(60, 60, 60, 50)
        content_layout.setSpacing(24) # Reduced spacing
        content_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        main_layout.addWidget(content_container)

        # --- Brand Watermark (Top Left absolute-ish look via layout) ---
        header_row = QHBoxLayout()
        
        brand_container = QFrame()
        brand_container.setObjectName("BrandWatermark")
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(20, 10, 20, 10) # Smaller margins
        brand_layout.setSpacing(8)
        
        self.lbl_title = QLabel("BiliDown")
        self.lbl_title.setObjectName("BrandText")
        brand_layout.addWidget(self.lbl_title)
        
        header_row.addWidget(brand_container)
        header_row.addStretch()
        
        # User Pill (Glass style)
        self.user_widget = QFrame()
        self.user_widget.setObjectName("UserPill")
        self.user_widget.setCursor(Qt.PointingHandCursor)
        user_layout = QHBoxLayout(self.user_widget)
        user_layout.setContentsMargins(6, 6, 16, 6)
        user_layout.setSpacing(12)
        
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setFixedSize(28, 28) # Smaller avatar
        self.lbl_avatar.setStyleSheet("border-radius: 14px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);")
        self.lbl_avatar.setScaledContents(True)
        user_layout.addWidget(self.lbl_avatar)
        
        self.lbl_username = QLabel("Guest")
        self.lbl_username.setObjectName("UserName")
        user_layout.addWidget(self.lbl_username)
        
        self.btn_action = QPushButton("LOGIN") # Uppercase default
        self.btn_action.setObjectName("AuthBtn")
        self.btn_action.setCursor(Qt.PointingHandCursor)
        self.btn_action.clicked.connect(self.handle_auth)
        user_layout.addWidget(self.btn_action)
        
        header_row.addWidget(self.user_widget)
        
        content_layout.addLayout(header_row)

        # --- Search Bar ---
        search_container = QWidget()
        # search_container.setFixedWidth(1000) # Removed fixed width
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(16)
        
        self.entry_url = SearchInput()
        search_layout.addWidget(self.entry_url)
        
        self.btn_analyze = QPushButton("ANALYZE")
        self.btn_analyze.setObjectName("PrimaryBtn")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setFixedWidth(120) # Smaller button
        self.btn_analyze.setFixedHeight(46) # Smaller height
        self.btn_analyze.clicked.connect(self.analyze_video)
        search_layout.addWidget(self.btn_analyze)
        
        content_layout.addWidget(search_container)
        content_layout.addSpacing(4) # Reduce spacing

        # --- Main Content Area ---
        self.content_area = QWidget()
        # self.content_area.setFixedWidth(1000) # Removed fixed width
        self.content_area.setVisible(False)
        
        # Initialize opacity for animation
        self.content_opacity = QGraphicsOpacityEffect(self.content_area)
        self.content_opacity.setOpacity(0)
        self.content_area.setGraphicsEffect(self.content_opacity)
        
        # Vertical Layout: Controls (Top) -> Media (Bottom)
        inner_content_layout = QVBoxLayout(self.content_area)
        inner_content_layout.setContentsMargins(0, 0, 0, 0)
        inner_content_layout.setSpacing(20)
        
        # 1. Controls Row (Progress | Quality | Download)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(16)
        
        # Progress Section (Status + Bar in VBox, expanding)
        progress_section = QVBoxLayout()
        progress_section.setSpacing(4)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("StatusText")
        progress_section.addWidget(self.lbl_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        progress_section.addWidget(self.progress_bar)
        
        controls_row.addLayout(progress_section, 1) # Stretch factor 1 (Take available space)

        # Quality (Wider)
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["1080P", "720P"])
        self.combo_quality.setFixedWidth(140) # Wider as requested
        controls_row.addWidget(self.combo_quality)
        
        # Download Button
        self.btn_download = QPushButton("DOWNLOAD")
        self.btn_download.setObjectName("DownloadBtn")
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.setFixedWidth(120)
        self.btn_download.setFixedHeight(40)
        self.btn_download.clicked.connect(self.start_download)
        controls_row.addWidget(self.btn_download)
        
        inner_content_layout.addLayout(controls_row)

        # 2. Media Row (Image Left | Text Right - Equal Height)
        media_row = QHBoxLayout()
        media_row.setSpacing(24)
        media_row.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Left: Image Container
        self.image_container = QFrame()
        self.image_container.setObjectName("ImageContainer")
        self.image_container.setFixedSize(320, 180) # 16:9 ratio
        
        img_layout = QVBoxLayout(self.image_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setScaledContents(True)
        img_layout.addWidget(self.lbl_thumb)
        
        media_row.addWidget(self.image_container)
        
        # Right: Info Area (Same Height as Image)
        self.info_container = QFrame()
        self.info_container.setFixedHeight(180) # Match image height
        
        info_layout = QVBoxLayout(self.info_container)
        info_layout.setContentsMargins(0, 4, 0, 4)
        info_layout.setSpacing(8)
        
        self.lbl_video_title = QLabel()
        self.lbl_video_title.setObjectName("VideoTitle")
        self.lbl_video_title.setWordWrap(True)
        self.lbl_video_title.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbl_video_title.setMaximumHeight(80) # Limit title height
        info_layout.addWidget(self.lbl_video_title)
        
        self.lbl_video_desc = QLabel()
        self.lbl_video_desc.setObjectName("VideoDesc")
        self.lbl_video_desc.setWordWrap(True)
        self.lbl_video_desc.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        info_layout.addWidget(self.lbl_video_desc)
        info_layout.addStretch()
        
        media_row.addWidget(self.info_container, 1) # Expand width
        
        inner_content_layout.addLayout(media_row)
        
        content_layout.addWidget(self.content_area)


        content_layout.addStretch()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F7; /* Apple System Gray 6 (Light) */
            }
            QWidget {
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
                color: #1D1D1F;
            }
            
            /* --- Brand Watermark --- */
            QFrame#BrandWatermark {
                background: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 12px;
            }
            QLabel#BrandText {
                font-size: 20px; /* Reduced from 24 */
                font-weight: 700;
                color: #1D1D1F;
                letter-spacing: -0.5px;
            }
            
            /* --- User Pill --- */
            QFrame#UserPill {
                background: rgba(255, 255, 255, 0.6);
                border-radius: 20px;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
            QLabel#UserName {
                font-size: 13px; /* Reduced from 14 */
                font-weight: 500;
                color: #1D1D1F;
            }
            QPushButton#AuthBtn {
                background-color: transparent;
                color: #007AFF;
                font-weight: 600;
                border: none;
                font-size: 12px; /* Reduced from 13 */
            }
            QPushButton#AuthBtn:hover {
                color: #0051A8;
            }

            /* --- Search Input --- */
            QLineEdit#SearchInput {
                background-color: #FFFFFF;
                border: 1px solid #D1D1D6; /* System Gray 4 */
                border-radius: 12px;
                color: #1D1D1F;
                font-size: 14px; /* Reduced from 16 */
                padding-left: 12px;
                selection-background-color: #B3D7FF;
            }
            QLineEdit#SearchInput:focus {
                border: 2px solid #007AFF; /* System Blue */
                background-color: #FFFFFF;
            }

            /* --- Buttons --- */
            QPushButton#PrimaryBtn {
                background-color: #007AFF;
                color: #FFFFFF;
                border-radius: 12px;
                font-size: 13px; /* Reduced from 14 */
                font-weight: 600;
                border: none;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #0051A8;
            }
            QPushButton#PrimaryBtn:pressed {
                background-color: #003E80;
            }
            QPushButton#PrimaryBtn:disabled {
                background-color: #99C7FF;
            }

            QPushButton#DownloadBtn {
                background-color: #34C759; /* System Green */
                color: #FFFFFF;
                border-radius: 20px; /* Slightly reduced radius */
                font-size: 13px; /* Reduced from 15 */
                font-weight: 600;
                border: none;
            }
            QPushButton#DownloadBtn:hover {
                background-color: #248A3D;
            }
            QPushButton#DownloadBtn:pressed {
                background-color: #1E7030;
            }
            QPushButton#DownloadBtn:disabled {
                background-color: #A1E3B1;
            }

            /* --- Image Container --- */
            QFrame#ImageContainer {
                border-radius: 12px; /* Reduced radius */
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
            QFrame#ImageContainer > QLabel {
                border-radius: 12px;
            }

            /* --- Subtitle Area (Glass Card) --- */
            QFrame#GlassCard {
                background-color: rgba(255, 255, 255, 0.7); /* Translucent White */
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.4);
            }

            /* --- Typography --- */
            QLabel#VideoTitle {
                font-size: 22px; /* Reduced from 28 */
                font-weight: 700;
                color: #1D1D1F;
                line-height: 1.2;
                letter-spacing: -0.5px;
            }
            QLabel#VideoDesc {
                font-size: 13px; /* Reduced from 15 */
                color: #86868B; /* System Gray */
                line-height: 1.4;
            }
            QLabel#StatusText {
                font-size: 12px; /* Reduced from 13 */
                color: #86868B;
                font-weight: 500;
            }

            /* --- Combo Box --- */
            QComboBox {
                border: 1px solid #D1D1D6;
                border-radius: 8px;
                padding: 4px 10px;
                background-color: #FFFFFF;
                color: #1D1D1F;
                font-size: 13px; /* Reduced from 14 */
            }
            QComboBox:hover {
                border: 1px solid #C7C7CC;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-top: 5px solid #86868B;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #1D1D1F;
                selection-background-color: #F2F2F7;
                border: 1px solid #E5E5E5;
            }

            /* --- Progress Bar --- */
            QProgressBar {
                background-color: #E5E5E5;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #007AFF;
                border-radius: 3px;
            }
        """)

    def animate_content_entry(self):
        self.content_area.setVisible(True)
        
        # Opacity Animation
        self.anim_opacity = QPropertyAnimation(self.content_opacity, b"opacity")
        self.anim_opacity.setDuration(600)
        self.anim_opacity.setStartValue(0)
        self.anim_opacity.setEndValue(1)
        self.anim_opacity.setEasingCurve(QEasingCurve.OutCubic)
        
        # Slide Up Animation (using geometry is tricky with layouts, so we rely on opacity + simple translation if possible, 
        # but layouts fight geometry changes. We'll stick to a smooth opacity fade for now, 
        # as it's cleaner than fighting the layout engine for a slide-up effect without a wrapper).
        # Alternatively, we can animate the maximumHeight, but that changes layout size. 
        # A pure fade is very "Apple".
        
        self.anim_opacity.start()

    def handle_auth(self):
        if self.is_logged_in:
            reply = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.downloader.logout()
                self.check_login_status()
        else:
            dialog = LoginDialog(self.downloader.authenticator, self)
            if dialog.exec() == QDialog.Accepted:
                self.downloader.save_cookies()
                self.check_login_status()
                QMessageBox.information(self, "Success", "Login successful!")

    def check_login_status(self):
        self.login_worker = WorkerThread(self.downloader.get_user_info)
        self.login_worker.finished.connect(self.on_login_check_finished)
        self.login_worker.start()

    def on_login_check_finished(self, user_info):
        if user_info:
            self.is_logged_in = True
            self.btn_action.setText("LOGOUT")
            self.btn_action.setStyleSheet("QPushButton#AuthBtn { color: #FF3B30; }")
            self.lbl_username.setText(user_info['uname'])
            self.avatar_worker = WorkerThread(self.load_image, user_info['face'])
            self.avatar_worker.finished.connect(self.on_avatar_loaded)
            self.avatar_worker.start()
        else:
            self.is_logged_in = False
            self.btn_action.setText("Login")
            self.btn_action.setStyleSheet("QPushButton#AuthBtn { color: #007AFF; }")
            self.lbl_username.setText("Guest")
            self.lbl_avatar.setStyleSheet("border-radius: 14px; background: #F0F0F0;")
            self.lbl_avatar.clear()

    def on_avatar_loaded(self, data):
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            size = 28
            rounded = QPixmap(size, size)
            rounded.fill(Qt.transparent)
            import PySide6.QtGui as QtGui
            from PySide6.QtGui import QPainter
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, size, size, pixmap)
            painter.end()
            self.lbl_avatar.setPixmap(rounded)

    def analyze_video(self):
        url = self.entry_url.text().strip()
        if not url:
            return
        
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("Analyzing...")
        
        self.worker = WorkerThread(self.downloader.get_video_info, url)
        self.worker.finished.connect(self.on_info_received)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_info_received(self, info):
        self.current_info = info
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Analyze")
        
        # Trigger animation instead of just setVisible
        self.animate_content_entry()
        
        self.lbl_video_title.setText(info['title'])
        self.lbl_video_desc.setText(info.get('desc', '')[:120] + '...')
        
        self.probe_worker = WorkerThread(self.downloader.get_play_url, info['bvid'], info['cid'], 120)
        self.probe_worker.finished.connect(self.on_capabilities_received)
        self.probe_worker.start()
        
        self.thumb_worker = WorkerThread(self.load_image, info['pic'])
        self.thumb_worker.finished.connect(self.on_thumb_loaded)
        self.thumb_worker.start()

    def on_capabilities_received(self, play_info):
        available_qns = set()
        if 'dash' in play_info and 'video' in play_info['dash']:
            for stream in play_info['dash']['video']:
                available_qns.add(stream['id'])
        
        if 'accept_quality' in play_info and 'accept_description' in play_info:
            qualities = play_info['accept_quality']
            descriptions = play_info['accept_description']
            
            self.combo_quality.clear()
            for qn, desc in zip(qualities, descriptions):
                if 'dash' not in play_info or qn in available_qns:
                    self.combo_quality.addItem(desc, qn)
            
            if self.combo_quality.count() > 0:
                self.combo_quality.setCurrentIndex(0)

    def load_image(self, url):
        try:
            resp = requests.get(url)
            return resp.content
        except:
            return None

    def on_thumb_loaded(self, data):
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.lbl_thumb.setPixmap(pixmap.scaled(self.lbl_thumb.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def on_error(self, err_msg):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Analyze")
        self.btn_download.setEnabled(True)
        self.btn_download.setText("Download")
        QMessageBox.critical(self, "Error", err_msg)

    def start_download(self):
        if not self.current_info:
            return
            
        self.btn_download.setEnabled(False)
        self.btn_download.setText("Starting...")
        
        qn = self.combo_quality.currentData()
        if qn is None: qn = 80
        
        self.play_worker = WorkerThread(self.downloader.get_play_url, self.current_info['bvid'], self.current_info['cid'], qn)
        self.play_worker.finished.connect(lambda info: self.on_play_url_received(info, qn))
        self.play_worker.error.connect(self.on_error)
        self.play_worker.start()

    def on_play_url_received(self, play_info, requested_qn):
        title = self.current_info['title']
        filename = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        if not filename: filename = self.current_info['bvid']
        
        downloads_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        
        base_filename = filename
        counter = 1
        while os.path.exists(os.path.join(downloads_dir, f"{filename}.mp4")):
            filename = f"{base_filename}({counter})"
            counter += 1
            
        is_dash = False
        dash_info = None
        download_url = None
        
        if 'dash' in play_info:
            is_dash = True
            video_streams = play_info['dash']['video']
            video_streams.sort(key=lambda x: x['id'], reverse=True)
            selected_video = video_streams[0]
            for stream in video_streams:
                if stream['id'] == requested_qn:
                    selected_video = stream
                    break
            if selected_video['id'] != requested_qn:
                for stream in video_streams:
                     if stream['id'] <= requested_qn:
                        selected_video = stream
                        break

            video_url = selected_video['base_url']
            audio_streams = play_info['dash']['audio']
            audio_streams.sort(key=lambda x: x['id'], reverse=True)
            audio_url = audio_streams[0]['base_url']

            dash_info = {
                'video_url': video_url,
                'audio_url': audio_url,
                'v_path': os.path.join(downloads_dir, f"{filename}_video.m4s"),
                'a_path': os.path.join(downloads_dir, f"{filename}_audio.m4s")
            }
            filepath = os.path.join(downloads_dir, f"{filename}.mp4")
            
        elif 'durl' in play_info:
            download_url = play_info['durl'][0]['url']
            filepath = os.path.join(downloads_dir, f"{filename}.mp4")
        else:
            self.on_error("No download URL found")
            return

        self.dl_worker = DownloadWorker(self.downloader, download_url, filepath, is_dash, dash_info)
        self.dl_worker.progress.connect(self.progress_bar.setValue)
        self.dl_worker.status.connect(self.lbl_status.setText)
        self.dl_worker.finished.connect(self.on_download_finished)
        self.dl_worker.error.connect(self.on_error)
        self.dl_worker.start()

    def on_download_finished(self, path):
        self.btn_download.setEnabled(True)
        self.btn_download.setText("Download")
        self.lbl_status.setText("Done")
        QMessageBox.information(self, "Success", f"Download completed!\nSaved to: {path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
