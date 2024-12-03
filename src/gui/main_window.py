from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from core.processor import ImageProcessor
from core.utils import cv2_to_qpixmap, enhance_image
import cv2

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PureScan")
        self.setMinimumSize(800, 600)
        
        # 初始化图像处理器
        self.processor = ImageProcessor()
        
        # 设置中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # 创建UI组件
        self.setup_ui()
        
    def setup_ui(self):
        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)
        
        # 按钮区域
        self.import_btn = QPushButton("导入图像")
        self.import_btn.clicked.connect(self.import_image)
        self.layout.addWidget(self.import_btn)
        
        self.scan_btn = QPushButton("扫描文档")
        self.scan_btn.clicked.connect(self.scan_document)
        self.layout.addWidget(self.scan_btn)
        
    def import_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择图像",
            "",
            "图像文件 (*.png *.jpg *.bmp)"
        )
        if file_name:
            # 加载并显示图像
            self.processor.load_image(file_name)
            self.display_image(self.processor.image)
            # 启用扫描按钮
            self.scan_btn.setEnabled(True)
            
    def scan_document(self):
        if self.processor.image is None:
            return
            
        # 检测文档边界
        corners = self.processor.detect_document()
        if corners is not None:
            # 执行透视变换
            warped = self.processor.perspective_transform(self.processor.image, corners)
            # 图像增强
            enhanced = enhance_image(warped)
            # 显示处理后的图像
            self.display_image(enhanced)
        else:
            # 如果没有检测到边界，显示提示
            QMessageBox.warning(self, "警告", "未能检测到文档边界！")
            
    def display_image(self, image):
        """显示图像到界面上"""
        if image is None:
            return
            
        # 调整图像大小以适应显示区域
        h, w = image.shape[:2]
        max_height = self.image_label.height()
        max_width = self.image_label.width()
        
        # 计算缩放比例
        scale = min(max_width/w, max_height/h)
        new_size = (int(w*scale), int(h*scale))
        
        # 缩放图像
        resized = cv2.resize(image, new_size)
        
        # 转换并显示图像
        pixmap = cv2_to_qpixmap(resized)
        self.image_label.setPixmap(pixmap)