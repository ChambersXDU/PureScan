from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QMessageBox, QCheckBox)
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
        self.points = None
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

    def set_default_points(self):
        """根据图片尺寸设置默认的选择框位置"""
        if self.original_size[0] > 0 and self.original_size[1] > 0:
            width, height = self.original_size
            # 设置选择框大小为图片尺寸的80%
            margin_x = width * 0.1  # 左右边距各10%
            margin_y = height * 0.1  # 上下边距各10%
            
            self.points = [
                (int(margin_x), int(margin_y)),                    # 左上
                (int(width - margin_x), int(margin_y)),            # 右上
                (int(width - margin_x), int(height - margin_y)),   # 右下
                (int(margin_x), int(height - margin_y))            # 左下
            ]

class MainWindow(QMainWindow):
    # 定义信号
    image_loaded = pyqtSignal(str)  # 发送图片路径
    scan_requested = pyqtSignal()    # 发送扫描请求
    rotate_requested = pyqtSignal(bool)  # True为顺时针，False为逆时针
    manual_corners_selected = pyqtSignal(list)  # 发送选择的四个角点
    image_cleared = pyqtSignal()  # 添加清除图片信号
    
    def __init__(self):
        super().__init__()
        self.controller = None  # 将在外部设置
        self.setWindowTitle("PureScan")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #f0f0f0;")  # 背景色
        
        # 定义配色方案
        self.COLORS = {
            'primary': '#2196F3',    # 主色调，用于扫描按钮
            'success': '#4CAF50',    # 成功色，用于保存和选择边框按钮
            'neutral': '#757575',    # 中性色，用于旋转按钮
            'danger': '#F44336',     # 危险色，用于删除按钮
            'hover': {
                'primary': '#1976D2',
                'success': '#388E3C',
                'neutral': '#616161',
                'danger': '#D32F2F'
            }
        }
        
        # 设置中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # 创建UI组件
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主布局
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)  # 增加组件之间的间距
        
        # 创建左侧布局（包含原始图像和其控制按钮）
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 创建图片区域的容器
        image_container = QWidget()
        image_container.setFixedSize(400, 500)  # 设置固定大小
        
        # 使用 QVBoxLayout 作为容器的布局
        container_layout = QVBoxLayout(image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加图片标签
        self.original_image_label = ClickableLabel("请选择或拖入图片\n支持jpg,png")
        self.original_image_label.setFixedSize(400, 500)
        self.original_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #BDBDBD;
                border-radius: 10px;
                background-color: white;
                color: #757575;
                font-size: 14px;
                padding: 10px;
            }
        """)
        self.original_image_label.setAcceptDrops(True)
        self.original_image_label.clicked.connect(self.import_image)
        self.original_image_label.corners_adjusted.connect(
            lambda points: self.manual_corners_selected.emit(points)
        )
        
        # 创建删除按钮
        self.clear_image_btn = QPushButton("×")
        self.clear_image_btn.setFixedSize(16, 16)  # 稍微调小一点
        self.clear_image_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['danger']};
                color: white;
                border-radius: 8px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.COLORS['hover']['danger']}; }}
        """)
        self.clear_image_btn.clicked.connect(self.clear_image)
        self.clear_image_btn.hide()
        
        # 将图片标签添加到容器
        container_layout.addWidget(self.original_image_label)
        
        # 使用绝对定位放置删除按钮
        self.clear_image_btn.setParent(image_container)
        self.clear_image_btn.move(375, 5)  # 放在右上角，留出一些边距
        
        # 将图片容器添加到左侧布局
        left_layout.addWidget(image_container)
        
        # 控制按钮布局
        control_layout = QHBoxLayout()
        control_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        control_layout.setSpacing(15)  # 增加按钮间距
        
        # 旋转按钮
        self.rotate_ccw_btn = QPushButton("↺")
        self.rotate_cw_btn = QPushButton("↻")
        rotate_btn_style = f"""
            QPushButton {{
                background-color: {self.COLORS['neutral']};
                color: white;
                border-radius: 22px;
                font-size: 18px;
                min-width: 44px;
                min-height: 44px;
            }}
            QPushButton:hover {{ background-color: {self.COLORS['hover']['neutral']}; }}
        """
        self.rotate_ccw_btn.setStyleSheet(rotate_btn_style)
        self.rotate_cw_btn.setStyleSheet(rotate_btn_style)
        
        self.rotate_ccw_btn.clicked.connect(lambda: self.rotate_requested.emit(False))
        self.rotate_cw_btn.clicked.connect(lambda: self.rotate_requested.emit(True))
        
        # 手动选择按钮
        self.manual_select_btn = QPushButton("选择边框")
        self.manual_select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['success']};
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                min-width: 100px;
            }}
            QPushButton:hover {{ background-color: {self.COLORS['hover']['success']}; }}
        """)
        self.manual_select_btn.clicked.connect(self.start_manual_selection)
        
        # 添加按钮到控制布局
        control_layout.addWidget(self.rotate_ccw_btn)
        control_layout.addWidget(self.manual_select_btn)
        control_layout.addWidget(self.rotate_cw_btn)
        
        # 添加阴影去除复选框
        self.shadow_removal_cb = QCheckBox("去除阴影")
        self.shadow_removal_cb.setChecked(False)
        control_layout.addWidget(self.shadow_removal_cb)
        
        left_layout.addLayout(control_layout)
        
        # 中间的扫描按钮
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.scan_btn = QPushButton("→")
        self.scan_btn.setFixedSize(60, 60)
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['primary']};
                color: white;
                border-radius: 30px;
                font-size: 24px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.COLORS['hover']['primary']}; }}
            QPushButton:disabled {{ background-color: #BDBDBD; }}
        """)
        self.scan_btn.clicked.connect(self.scan_document)
        self.scan_btn.setEnabled(False)
        
        center_layout.addWidget(self.scan_btn)
        
        # 右侧布局
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 处理后的图像显示区域
        self.processed_image_label = QLabel("处理后的图片")
        self.processed_image_label.setFixedSize(400, 500)
        self.processed_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processed_image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #BDBDBD;
                border-radius: 10px;
                background-color: white;
                color: #757575;
                font-size: 14px;
                padding: 10px;
            }
        """)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.COLORS['success']};
                color: white;
                border-radius: 5px;
                padding: 10px 30px;
                font-size: 14px;
                margin-top: 10px;
                min-width: 100px;
            }}
            QPushButton:hover {{ background-color: {self.COLORS['hover']['success']}; }}
            QPushButton:disabled {{ background-color: #BDBDBD; }}
        """)
        self.save_btn.clicked.connect(self.save_processed_image)
        self.save_btn.setEnabled(False)
        
        right_layout.addWidget(self.processed_image_label)
        right_layout.addWidget(self.save_btn)
        
        # 添加所有布局到主布局
        main_layout.addLayout(left_layout)
        main_layout.addLayout(center_layout)
        main_layout.addLayout(right_layout)
        
        # 设置主窗口
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
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
            label.set_default_points()
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
        if hasattr(self, 'controller') and self.controller.processed_result is not None:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "保存图片",
                "",
                "图像文件 (*.png *.jpg)"
            )
            if file_name:
                # 使用原始分辨率的处理结果保存
                if file_name.lower().endswith('.jpg'):
                    cv2.imwrite(file_name, self.controller.processed_result, 
                               [cv2.IMWRITE_JPEG_QUALITY, 95])
                else:
                    cv2.imwrite(file_name, self.controller.processed_result)
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
            label.set_default_points()
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
            