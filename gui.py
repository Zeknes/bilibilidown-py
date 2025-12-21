import sys
import os
import threading
import requests
from io import BytesIO
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QProgressBar, QMessageBox, 
                             QDialog, QComboBox, QScrollArea, QFrame, QGraphicsDropShadowEffect,
                             QGraphicsOpacityEffect, QSizePolicy, QTextEdit)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, QPointF, QRectF
from PySide6.QtGui import QPixmap, QImage, QIcon, QFont, QColor, QPainter, QPainterPath, QFontMetrics, QTransform, QPolygonF

from core import BiliDownloader

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Toast(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close_toast)
        
        self.message = ""
        self.is_success = True
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        self.animation = None
        self.hide()

    def show_message(self, text, is_success=True, duration=1000):
        if self.animation:
            self.animation.stop()
            
        self.message = text
        self.is_success = is_success
        self.adjustSize()
        
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.bottom() - 100
            )
        
        self.show()
        self.raise_()
        
        self.opacity_effect.setOpacity(0)
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setDuration(200)
        self.animation.start()
        
        self.timer.start(duration)
        
    def close_toast(self):
        if self.animation:
            self.animation.stop()
            
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setStartValue(self.opacity_effect.opacity())
        self.animation.setEndValue(0)
        self.animation.setDuration(200)
        self.animation.finished.connect(self.hide)
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        # Green for success, Red for error
        bg_color = QColor("#34C759") if self.is_success else QColor("#FF3B30")
        
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        
        painter.setPen(Qt.white)
        font = self.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.message)
        
    def sizeHint(self):
        font = self.font()
        font.setPointSize(12)
        font.setBold(True)
        metrics = QFontMetrics(font)
        width = metrics.horizontalAdvance(self.message) + 40
        return QSize(max(120, width), 40)

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
        self.setup_ui()
        self.start_login_process()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        
        title = QLabel("Scan QR Code")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.lbl_info = QLabel("Open Bilibili App on your phone\nand scan the QR code to login.")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_info)
        
        qr_container = QFrame()
        
        qr_layout = QVBoxLayout(qr_container)
        qr_layout.setContentsMargins(24, 24, 24, 24)
        
        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setFixedSize(180, 180)
        qr_layout.addWidget(self.lbl_qr, 0, Qt.AlignCenter)
        
        layout.addWidget(qr_container, 0, Qt.AlignCenter)
        
        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
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

class SearchInput(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.placeholder_text = "Paste Bilibili Video Links (URL / BV) - One per line"
        self.setPlaceholderText(self.placeholder_text)
        self.setFixedHeight(120) 
        self.setObjectName("SearchInput")
        self.setStyleSheet("""
            QTextEdit {
                padding: 12px;
                font-size: 15px;
                line-height: 1.5;
                border: 1px solid #d1d1d1;
                border-radius: 12px;
                background-color: #FFFFFF;
                selection-background-color: #B3D7FF;
            }
            QTextEdit:focus {
                border: 2px solid #007AFF;
            }
        """)

    def focusInEvent(self, e):
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        # Re-apply placeholder if empty (Qt handles this natively usually but user reported issues)
        if not self.toPlainText():
             pass

class TrapezoidImageList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = [] # List of QPixmap
        self.setFixedHeight(220) # Height to accommodate cards
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_images(self, pixmaps):
        self.images = pixmaps
        self.update()

    def paintEvent(self, event):
        if not self.images:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Card settings
        card_w = 280 
        card_h = 158 # 16:9 approx
        
        # Calculate dynamic overlap/spacing
        # We have available width: self.width()
        # We need to fit n images.
        # total_width = start_x + (n-1)*step_x + card_w + padding_right
        
        n = len(self.images)
        start_x = 20
        padding_right = 20
        available_w = self.width()
        
        # Standard step (if space permits)
        # Standard overlap ~60px -> step = 220
        standard_step = 220
        
        if n <= 1:
            step_x = standard_step
        else:
            required_w_standard = start_x + (n - 1) * standard_step + card_w + padding_right
            
            if required_w_standard <= available_w:
                step_x = standard_step
            else:
                # Squeeze
                # available_w = start_x + (n-1)*step_x + card_w + padding_right
                # (n-1)*step_x = available_w - start_x - card_w - padding_right
                available_for_steps = available_w - start_x - card_w - padding_right
                step_x = available_for_steps / (n - 1)
                
                # Enforce minimum step to avoid total collapse
                min_step = 40
                if step_x < min_step:
                    step_x = min_step

        start_y = 20
        current_x = start_x
        
        for i, pixmap in enumerate(self.images):
            # Source Rect
            src_rect = QRectF(pixmap.rect())
            
            # Target Quad (Trapezoid)
            # Left side: normal height
            # Right side: reduced height (0.8)
            h_left = card_h
            h_right = card_h * 0.8
            diff = (h_left - h_right) / 2
            
            tl = QPointF(current_x, start_y)
            tr = QPointF(current_x + card_w, start_y + diff)
            br = QPointF(current_x + card_w, start_y + card_h - diff)
            bl = QPointF(current_x, start_y + card_h)
            
            quad = QPolygonF([tl, tr, br, bl])
            
            # Create Transform
            transform = QTransform()
            if QTransform.quadToQuad(QPolygonF(src_rect), quad, transform):
                painter.save()
                painter.setTransform(transform)
                painter.drawPixmap(pixmap.rect(), pixmap)
                painter.restore()
            
            # Advance
            current_x += step_x

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BiliDown")
        self.resize(900, 700)
        
        icon_path = resource_path("bili.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.downloader = BiliDownloader()
        self.video_queue = [] # List of URLs to process
        self.current_download_index = 0
        self.is_downloading = False
        self.is_logged_in = False
        
        self.setup_ui()
        self.apply_styles()
        
        self.check_login_status()
        
        self.toast = Toast(self)

    def show_toast(self, message, is_success=True):
        self.toast.show_message(message, is_success)

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

        # --- Search Bar & Buttons ---
        search_container = QWidget()
        search_layout = QVBoxLayout(search_container) # Changed to VBox
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(12)
        search_layout.setAlignment(Qt.AlignTop)
        
        self.entry_url = SearchInput()
        search_layout.addWidget(self.entry_url)
        
        self.btn_analyze = QPushButton("ANALYZE")
        self.btn_analyze.setObjectName("PrimaryBtn")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.setFixedWidth(120)
        self.btn_analyze.setFixedHeight(46)
        self.btn_analyze.clicked.connect(self.analyze_video)
        
        # Align button to right
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_stats = QLabel("")
        self.lbl_stats.setObjectName("StatsText")
        actions_layout.addWidget(self.lbl_stats)
        
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_analyze)
        
        search_layout.addLayout(actions_layout)
        
        content_layout.addWidget(search_container)
        content_layout.addSpacing(4)

        # --- Main Content Area ---
        self.content_area = QWidget()
        self.content_area.setVisible(False)
        
        # Initialize opacity for animation
        self.content_opacity = QGraphicsOpacityEffect(self.content_area)
        self.content_opacity.setOpacity(0)
        self.content_area.setGraphicsEffect(self.content_opacity)
        
        # Vertical Layout
        inner_content_layout = QVBoxLayout(self.content_area)
        inner_content_layout.setContentsMargins(0, 0, 0, 0)
        inner_content_layout.setSpacing(20)
        
        # 1. Info Row (Title | Quality | Download)
        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        
        self.lbl_video_title = QLabel()
        self.lbl_video_title.setObjectName("VideoTitle")
        self.lbl_video_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # We handle text elision manually or just let layout handle it?
        # QLabel doesn't auto-elide nicely in HBox without subclass.
        # But we can just let it be cut off if we set a size policy.
        self.lbl_video_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        info_row.addWidget(self.lbl_video_title)
        
        # Quality
        self.combo_quality = QComboBox()
        self.combo_quality.addItem("Highest", 999)
        self.combo_quality.addItem("8K", 127)
        self.combo_quality.addItem("4K", 120)
        self.combo_quality.addItem("1080P60", 116)
        self.combo_quality.addItem("1080P", 80)
        self.combo_quality.addItem("720P", 64)
        self.combo_quality.setFixedWidth(140)
        info_row.addWidget(self.combo_quality)
        
        # Download Button
        self.btn_download = QPushButton("DOWNLOAD")
        self.btn_download.setObjectName("DownloadBtn")
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.setFixedWidth(120)
        self.btn_download.setFixedHeight(40)
        self.btn_download.clicked.connect(self.start_download)
        info_row.addWidget(self.btn_download)
        
        inner_content_layout.addLayout(info_row)
        
        # 2. Progress Row
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        inner_content_layout.addWidget(self.progress_bar)
        
        # 3. Image List Row
        self.image_list = TrapezoidImageList()
        inner_content_layout.addWidget(self.image_list)
        
        content_layout.addWidget(self.content_area)


        content_layout.addStretch()

    def apply_styles(self):
        # Apply Main Window background color to self (the QMainWindow)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F7; /* Apple System Gray 6 (Light) */
            }
        """)

        # Apply specific widget styles ONLY to central widget contents.
        # This ensures that child windows (like LoginDialog or QMessageBox) do not inherit these styles,
        # keeping them fully native/system standard.
        if hasattr(self, 'centralWidget') and self.centralWidget():
            self.centralWidget().setStyleSheet("""
            /* Refined generic selector to avoid hitting QComboBox/QProgressBar unless targeted */
            QLabel, QLineEdit, QTextEdit, QPushButton {
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
            QLabel#StatsText {
                font-size: 13px;
                color: #86868B;
                font-weight: 500;
            }
            QLabel#StatusText {
                font-size: 12px; /* Reduced from 13 */
                color: #86868B;
                font-weight: 500;
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
            if self.show_simple_confirm("Logout", "Are you sure you want to logout?"):
                self.downloader.logout()
                self.check_login_status()
        else:
            dialog = LoginDialog(self.downloader.authenticator, self)
            if dialog.exec() == QDialog.Accepted:
                self.downloader.save_cookies()
                self.check_login_status()
                self.show_toast("Login successful!", is_success=True)

    def check_login_status(self):
        self.login_worker = WorkerThread(self.downloader.get_user_info)
        self.login_worker.finished.connect(self.on_login_check_finished)
        self.login_worker.start()

    def show_simple_alert(self, title, message):
        """Shows a minimal native-like alert without icons."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)
        msg_box.setIcon(QMessageBox.NoIcon) # Explicitly no icon
        # Ensure no style sheet interference
        msg_box.setStyleSheet("")
        msg_box.exec()

    def show_simple_confirm(self, title, message):
        """Shows a minimal native-like confirmation without icons."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.setIcon(QMessageBox.NoIcon)
        msg_box.setStyleSheet("")
        return msg_box.exec() == QMessageBox.Yes

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

    def load_image(self, url):
        try:
            resp = requests.get(url)
            return resp.content
        except:
            return None

    def on_avatar_loaded(self, data):
        if data:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            size = 28
            rounded = QPixmap(size, size)
            rounded.fill(Qt.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            
            # Use KeepAspectRatioByExpanding to fill the circle
            scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Draw centered
            x = (size - scaled.width()) // 2
            y = (size - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            
            self.lbl_avatar.setPixmap(rounded)
            # Remove border/background style when image is present to avoid square corners showing
            self.lbl_avatar.setStyleSheet("background: transparent; border: none;")

    def analyze_video(self):
        text = self.entry_url.toPlainText().strip()
        if not text:
            self.show_toast("Please enter a URL", is_success=False)
            return
            
        # Parse lines
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not raw_lines:
            return

        # Deduplicate while preserving order
        unique_lines = []
        seen_keys = set()
        
        for line in raw_lines:
            # Try to extract ID for smarter deduplication (e.g. BV123... and BV123.../ are same)
            key = self.downloader._extract_bvid(line)
            if not key:
                key = line # Fallback to raw string if no BVID found
            
            if key not in seen_keys:
                unique_lines.append(line)
                seen_keys.add(key)
        
        # Stats
        self.stats_total_input = len(raw_lines)
        self.stats_duplicates = len(raw_lines) - len(unique_lines)
        
        self.lbl_stats.setText(f"Analyzing {len(unique_lines)} URLs... (Input: {self.stats_total_input}, Duplicates: {self.stats_duplicates})")

        self.video_queue = unique_lines
        self.current_info_map = {} # Reset
        
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("Analyzing...")
        
        # Batch fetch all info
        self.worker = WorkerThread(self.fetch_batch_info, unique_lines)
        self.worker.finished.connect(self.on_batch_info_received)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def fetch_batch_info(self, urls):
        results = []
        for url in urls:
            try:
                info = self.downloader.get_video_info(url)
                results.append(info)
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                results.append(None)
        return results

    def on_batch_info_received(self, results):
        valid_infos = []
        for i, info in enumerate(results):
            if info:
                self.current_info_map[i] = info
                valid_infos.append(info)
        
        # Update Stats
        success_count = len(valid_infos)
        failed_count = len(results) - success_count
        self.lbl_stats.setText(f"Total: {self.stats_total_input} | Success: {success_count} | Failed: {failed_count} | Duplicates: {self.stats_duplicates}")

        if not valid_infos:
            self.on_error("Failed to fetch info for all videos")
            return

        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Analyze")
        
        self.animate_content_entry()
        
        # Update UI with first valid info
        first_info = valid_infos[0]
        title = first_info['title']
        count = len(valid_infos)
        if count > 1:
            title = f"[{count} Videos] {title}"
        
        # Truncate title to avoid stretching window
        max_len = 30
        if len(title) > max_len:
            title = title[:max_len] + "..."

        # Set title (elide handled by layout/size policy)
        self.lbl_video_title.setText(title)
        self.lbl_video_title.setToolTip(first_info['title'])
        
        if count > 1:
            self.btn_download.setText(f"Download All ({count})")
        else:
            self.btn_download.setText("Download")
            
        # Start fetching images
        img_urls = [info['pic'] for info in valid_infos]
        self.thumb_worker = WorkerThread(self.fetch_batch_images, img_urls)
        self.thumb_worker.finished.connect(self.on_batch_images_loaded)
        self.thumb_worker.start()

    def fetch_batch_images(self, urls):
        pixmaps = []
        for url in urls:
            try:
                content = requests.get(url).content
                pixmap = QPixmap()
                if pixmap.loadFromData(content):
                    pixmaps.append(pixmap)
            except:
                pass
        return pixmaps

    def on_batch_images_loaded(self, pixmaps):
        self.image_list.set_images(pixmaps)

    def on_capabilities_received(self, play_info):
        # Deprecated logic as combo box is fixed now
        pass

    def on_error(self, err_msg):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Analyze")
        self.btn_download.setEnabled(True)
        self.btn_download.setText("Download")
        self.show_toast(err_msg, is_success=False)

    def start_download(self):
        if not self.video_queue:
            return
            
        self.btn_download.setEnabled(False)
        self.btn_download.setText("Initializing...")
        
        self.current_download_index = 0
        self.is_downloading = True
        
        self.process_next_download()

    def process_next_download(self):
        if self.current_download_index >= len(self.video_queue):
            self.is_downloading = False
            self.btn_download.setEnabled(True)
            self.btn_download.setText("Download")
            self.show_toast("All downloads completed!", is_success=True)
            # Clear input and reset state
            self.entry_url.clear()
            self.video_queue = []
            self.current_info_map = {}
            # Reset UI to initial state if desired, or just keep last preview.
            # Keeping preview is fine, but clearing input implies reset.
            return
            
        url = self.video_queue[self.current_download_index]
        
        # We need to get info first if we don't have it (we only have it for the first one usually)
        if self.current_download_index in self.current_info_map:
            self.process_download_for_info(self.current_info_map[self.current_download_index])
        else:
            # Fetch info
            self.info_worker = WorkerThread(self.downloader.get_video_info, url)
            self.info_worker.finished.connect(self.on_download_info_received)
            self.info_worker.error.connect(self.on_download_error)
            self.info_worker.start()

    def on_download_info_received(self, info):
        self.current_info_map[self.current_download_index] = info
        self.process_download_for_info(info)

    def process_download_for_info(self, info):
        target_qn = self.combo_quality.currentData()
        if target_qn is None: target_qn = 127 # Default to highest possible check if not set
        
        # We request highest possible quality metadata to check what's available
        # 127 is 8K, asking for it usually returns all available DASH formats
        self.play_worker = WorkerThread(self.downloader.get_play_url, info['bvid'], info['cid'], 127)
        self.play_worker.finished.connect(lambda play_info: self.on_play_url_received(play_info, info, target_qn))
        self.play_worker.error.connect(self.on_download_error)
        self.play_worker.start()

    def on_download_error(self, err_msg):
        print(f"Error downloading {self.current_download_index}: {err_msg}")
        # Skip to next
        self.current_download_index += 1
        self.process_next_download()

    def on_play_url_received(self, play_info, info, target_qn):
        title = info['title']
        filename = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        if not filename: filename = info['bvid']
        
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
            # Sort by ID descending (Highest quality first)
            video_streams.sort(key=lambda x: x['id'], reverse=True)
            
            selected_video = None
            
            if target_qn == 999: # Highest
                selected_video = video_streams[0]
            else:
                # Find exact match or fallback to lower
                for stream in video_streams:
                    if stream['id'] <= target_qn:
                        selected_video = stream
                        break
                
                # If nothing found (e.g. target is lower than lowest available? unlikely but possible), pick lowest
                if not selected_video:
                    selected_video = video_streams[-1]

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
            self.on_download_error("No download URL found")
            return

        self.dl_worker = DownloadWorker(self.downloader, download_url, filepath, is_dash, dash_info)
        self.dl_worker.progress.connect(self.progress_bar.setValue)
        # self.dl_worker.status.connect(self.lbl_status.setText) # lbl_status removed
        self.dl_worker.finished.connect(self.on_download_finished)
        self.dl_worker.error.connect(self.on_download_error)
        self.dl_worker.start()

    def on_download_finished(self, path):
        # One download done, move to next
        self.current_download_index += 1
        self.process_next_download()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("bili.png")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
