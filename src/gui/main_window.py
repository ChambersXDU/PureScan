from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QIcon, QDragEnterEvent, QDropEvent, QPainter
import cv2
import os
from core.utils import cv2_to_qpixmap

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class MainWindow(QMainWindow):
    # 定义信号
    image_loaded = pyqtSignal(str)  # 发送图片路径
    scan_requested = pyqtSignal()    # 发送扫描请求
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PureScan")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #f0f0f0;")  # 背景色
        
        # 设置中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # 创建UI组件
        self.setup_ui()
        
    def setup_ui(self):
        # 创建水平布局
        image_layout = QHBoxLayout()
        
        # 原始图像显示区域
        self.original_image_label = ClickableLabel("请选择或拖入图片\n支持jpg,png")
        self.original_image_label.setFixedSize(300, 400)
        self.original_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_image_label.setStyleSheet("""
            border: 2px dashed #ccc;
            border-radius: 10px;
            background-color: #fff;
            color: #666;
            font-size: 14px;
            padding: 10px;
        """)
        self.original_image_label.setAcceptDrops(True)
        self.original_image_label.clicked.connect(self.import_image)
        image_layout.addWidget(self.original_image_label)
        
        # 扫描按钮（箭头样式）
        self.scan_btn = QPushButton("→")
        self.scan_btn.setFixedSize(50, 50)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #007aff;
                color: white;
                border-radius: 25px;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0066cc;
            }
            QPushButton:pressed {
                background-color: #005299;
            }
        """)
        self.scan_btn.clicked.connect(self.scan_document)
        image_layout.addWidget(self.scan_btn)
        
        # 处理后图像显示区域
        self.processed_image_label = QLabel("处理后的图片")
        self.processed_image_label.setFixedSize(300, 400)
        self.processed_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processed_image_label.setStyleSheet("""
            border: 1px solid #ccc;
            border-radius: 10px;
            background-color: #fff;
            color: #333;
            font-size: 14px;
            padding: 10px;
        """)
        image_layout.addWidget(self.processed_image_label)
        
        self.layout.addLayout(image_layout)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_name = urls[0].toLocalFile()
            if os.path.isfile(file_name):
                self.image_loaded.emit(file_name)
        
    def import_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择图像",
            "",
            "图像文件 (*.png *.jpg *.bmp)"
        )
        if file_name:
            self.image_loaded.emit(file_name)
            # 显示预览
            image = cv2.imread(file_name)
            self.display_image(image, self.original_image_label)
            
    def scan_document(self):
        self.scan_requested.emit()
            
    def display_image(self, image, label):
        """显示图像到指定标签上"""
        if image is None:
            return
            
        # 获取标签和图像的尺寸
        label_width = label.width() - 20  # 减去padding
        label_height = label.height() - 20
        img_height, img_width = image.shape[:2]
        
        # 计算缩放比例，保持长宽比
        width_ratio = label_width / img_width
        height_ratio = label_height / img_height
        scale = min(width_ratio, height_ratio)
        
        # 计算新的尺寸
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # 缩放图像
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # 创建背景
        background = QImage(label_width, label_height, QImage.Format.Format_RGB888)
        background.fill(Qt.GlobalColor.white)
        
        # 将调整后的图像绘制到背景中央
        pixmap = cv2_to_qpixmap(resized)
        result = QPixmap.fromImage(background)
        painter = QPainter(result)
        x = (label_width - new_width) // 2
        y = (label_height - new_height) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()
        
        # 设置图像
        label.setPixmap(result)

    def show_warning(self, title, message):
        """显示警告对话框"""
        QMessageBox.warning(self, title, message)