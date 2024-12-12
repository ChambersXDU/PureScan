from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QIcon, QDragEnterEvent, QDropEvent, QPainter, QPen
import cv2
import os
from core.utils import cv2_to_qpixmap

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    corners_adjusted = pyqtSignal(list)
    
    def __init__(self, text=""):
        super().__init__(text)
        self.points = [(50, 50), (250, 50), (250, 350), (50, 350)]
        self.selecting_points = False
        self.dragging_point = None
        self.drag_threshold = 20
        self.has_image = False
        self.scale_factor = 1.0
        self.image_offset = (0, 0)
        self.original_size = (0, 0)
        
    def get_image_coordinates(self, ui_x, ui_y):
        """将UI坐标转换为原始图像坐标"""
        # 减去图像偏移量
        img_x = (ui_x - self.image_offset[0]) / self.scale_factor
        img_y = (ui_y - self.image_offset[1]) / self.scale_factor
        return (int(img_x), int(img_y))
        
    def get_ui_coordinates(self, img_x, img_y):
        """将图像坐标转换为UI坐标"""
        ui_x = img_x * self.scale_factor + self.image_offset[0]
        ui_y = img_y * self.scale_factor + self.image_offset[1]
        return (int(ui_x), int(ui_y))
        
    def mousePressEvent(self, event):
        if self.selecting_points:
            pos = event.pos()
            for i, point in enumerate(self.points):
                ui_point = self.get_ui_coordinates(point[0], point[1])
                if abs(pos.x() - ui_point[0]) < self.drag_threshold and \
                   abs(pos.y() - ui_point[1]) < self.drag_threshold:
                    self.dragging_point = i
                    break
        elif not self.has_image:
            self.clicked.emit()
            
    def mouseReleaseEvent(self, event):
        if self.selecting_points and self.dragging_point is not None:
            self.update()  # 只更新显示，不发送信号
        self.dragging_point = None
            
    def mouseMoveEvent(self, event):
        if self.selecting_points and self.dragging_point is not None:
            pos = event.pos()
            # 将UI坐标转换为图像坐标
            img_x, img_y = self.get_image_coordinates(pos.x(), pos.y())
            # 确保坐标在图像范围内
            img_x = max(0, min(img_x, self.original_size[0]))
            img_y = max(0, min(img_y, self.original_size[1]))
            self.points[self.dragging_point] = (img_x, img_y)
            self.update()
            
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.has_image and self.selecting_points:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.GlobalColor.red, 2))
            
            # 绘制连接线
            for i in range(len(self.points)):
                start = self.get_ui_coordinates(*self.points[i])
                end = self.get_ui_coordinates(*self.points[(i+1) % len(self.points)])
                painter.drawLine(start[0], start[1], end[0], end[1])
            
            # 绘制角点
            for point in self.points:
                ui_point = self.get_ui_coordinates(*point)
                painter.setBrush(Qt.GlobalColor.red)
                painter.drawEllipse(ui_point[0]-5, ui_point[1]-5, 10, 10)

class MainWindow(QMainWindow):
    # 定义信号
    image_loaded = pyqtSignal(str)  # 发送图片路径
    scan_requested = pyqtSignal()    # 发送扫描请求
    rotate_requested = pyqtSignal(bool)  # True为顺时针，False为逆时针
    manual_corners_selected = pyqtSignal(list)  # 发送选择的四个角点
    image_cleared = pyqtSignal()  # 添加清除图片信号
    
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
        # 创建左侧布局（包含原始图像和其控制按钮）
        left_layout = QVBoxLayout()
        
        # 创建图片区域的容器
        image_container = QWidget()
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加删除按钮
        self.clear_image_btn = QPushButton("×")
        self.clear_image_btn.setFixedSize(30, 30)
        self.clear_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        self.clear_image_btn.clicked.connect(self.clear_image)
        self.clear_image_btn.hide()  # 初始时隐藏
        
        clear_btn_layout = QHBoxLayout()
        clear_btn_layout.addStretch()
        clear_btn_layout.addWidget(self.clear_image_btn)
        image_container_layout.addLayout(clear_btn_layout)
        
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
        self.original_image_label.corners_adjusted.connect(lambda points: self.manual_corners_selected.emit(points))
        image_container_layout.addWidget(self.original_image_label)
        
        left_layout.addWidget(image_container)
        
        # 旋转按钮布局
        rotate_layout = QHBoxLayout()
        rotate_layout.setContentsMargins(50, 10, 50, 10)  # 设置边距使按钮居中
        
        # 逆时针旋转按钮
        self.rotate_ccw_btn = QPushButton("↺")
        self.rotate_ccw_btn.setFixedSize(40, 40)
        self.rotate_ccw_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border-radius: 20px;
                font-size: 20px;
            }
            QPushButton:hover { background-color: #888; }
        """)
        self.rotate_ccw_btn.clicked.connect(lambda: self.rotate_requested.emit(False))
        
        # 顺时针旋转按钮
        self.rotate_cw_btn = QPushButton("↻")
        self.rotate_cw_btn.setFixedSize(40, 40)
        self.rotate_cw_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border-radius: 20px;
                font-size: 20px;
            }
            QPushButton:hover { background-color: #888; }
        """)
        self.rotate_cw_btn.clicked.connect(lambda: self.rotate_requested.emit(True))
        
        rotate_layout.addWidget(self.rotate_ccw_btn)
        rotate_layout.addWidget(self.rotate_cw_btn)
        left_layout.addLayout(rotate_layout)
        
        # 主布局调整
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout)
        
        # 扫描按钮
        self.scan_btn = QPushButton("→")
        self.scan_btn.setFixedSize(50, 50)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #007aff;
                color: white;
                border-radius: 25px;
                font-size: 24px;
            }
            QPushButton:hover { background-color: #0066cc; }
        """)
        self.scan_btn.clicked.connect(self.scan_document)
        self.scan_btn.setEnabled(False)  # 初始时禁用
        
        scan_layout = QVBoxLayout()
        scan_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scan_layout.addWidget(self.scan_btn)
        main_layout.addLayout(scan_layout)
        
        # 创建右侧处理后的图像显示区域
        self.processed_image_label = QLabel("处理后的图片")
        self.processed_image_label.setFixedSize(300, 400)
        self.processed_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processed_image_label.setStyleSheet("""
            border: 2px dashed #ccc;
            border-radius: 10px;
            background-color: #fff;
            color: #666;
            font-size: 14px;
            padding: 10px;
        """)
        
        # 右侧处理后的图像区域添加保存按钮
        right_layout = QVBoxLayout()
        
        # 添加保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                margin: 5px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        self.save_btn.clicked.connect(self.save_processed_image)
        self.save_btn.setEnabled(False)  # 初始时禁用
        
        right_layout.addWidget(self.processed_image_label)
        right_layout.addWidget(self.save_btn)
        main_layout.addLayout(right_layout)
        
        # 手动选点按钮放在底部
        self.manual_select_btn = QPushButton("手动选择边框")
        self.manual_select_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border-radius: 5px;
                padding: 10px;
                margin: 10px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        self.manual_select_btn.clicked.connect(self.start_manual_selection)
        
        # 设置主布局
        container = QVBoxLayout()
        container.addLayout(main_layout)
        container.addWidget(self.manual_select_btn)
        
        # 设置中心部件
        central_widget = QWidget()
        central_widget.setLayout(container)
        self.setCentralWidget(central_widget)
        
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
        """只在没有图片时才允许导入"""
        if not self.original_image_label.has_image:
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
        """触发扫描请求"""
        print("Scan button clicked")  # 调试信息
        if self.original_image_label.selecting_points:
            # 如果在选择模式下，发送当前角点，但保持选择模式
            self.manual_corners_selected.emit(self.original_image_label.points)
            self.original_image_label.update()  # 更新显示
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
        
        # 保存缩放比例和偏移量到label实例
        if label == self.original_image_label:
            label.scale_factor = scale
            label.image_offset = (x, y)
            label.original_size = (img_width, img_height)
            label.has_image = True
            self.clear_image_btn.show()
        elif label == self.processed_image_label:
            self.save_btn.setEnabled(True)
            
    def clear_image(self):
        """清除图片"""
        self.original_image_label.clear()
        self.original_image_label.setText("请选择或拖入图片\n支持jpg,png")
        self.original_image_label.has_image = False
        self.original_image_label.selecting_points = False  # 重置选择状态
        self.clear_image_btn.hide()
        self.processed_image_label.clear()
        self.processed_image_label.setText("处理后的图片")
        self.scan_btn.setEnabled(False)  # 禁用扫描按钮
        self.image_cleared.emit()
        
    def show_warning(self, title, message):
        """显示警告对话框"""
        QMessageBox.warning(self, title, message)

    def start_manual_selection(self):
        """开始手动选择边框"""
        if self.original_image_label.has_image:  # 只在有图片时才能开始选择
            self.original_image_label.selecting_points = True
            self.original_image_label.update()  # 强制重绘
            
    def save_processed_image(self):
        """保存处理后的图片"""
        if self.processed_image_label.pixmap():
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "保存图片",
                "",
                "图像文件 (*.png *.jpg)"
            )
            if file_name:
                self.processed_image_label.pixmap().save(file_name)
                self.show_warning("提示", "图片已保存")

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
        
        # 保存缩放比例和偏移量到label实例
        if label == self.original_image_label:
            label.scale_factor = scale
            label.image_offset = (x, y)
            label.original_size = (img_width, img_height)
            label.has_image = True
            self.clear_image_btn.show()
        elif label == self.processed_image_label:
            self.save_btn.setEnabled(True)
            
    def clear_image(self):
        """清除图片"""
        self.original_image_label.clear()
        self.original_image_label.setText("请选择或拖入图片\n支持jpg,png")
        self.original_image_label.has_image = False
        self.original_image_label.selecting_points = False  # 重置选择状态
        self.clear_image_btn.hide()
        self.processed_image_label.clear()
        self.processed_image_label.setText("处理后的图片")
        self.scan_btn.setEnabled(False)  # 禁用扫描按钮
        self.image_cleared.emit()
        
    def show_warning(self, title, message):
        """显示警告对话框"""
        QMessageBox.warning(self, title, message)

    def start_manual_selection(self):
        """开始手动选择边框"""
        if self.original_image_label.has_image:  # 只在有图片时才能开始选择
            self.original_image_label.selecting_points = True
            self.original_image_label.update()  # 强制重绘
            