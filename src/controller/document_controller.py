from PyQt6.QtCore import QObject
from core.processor import ImageProcessor
from core.utils import enhance_image
import numpy as np

class DocumentController(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.processor = None
        self.manual_corners = None  # 存储手动选择的角点
        self.processed_result = None  # 存储原始分辨率的处理结果
        
        # 连接信号和槽
        self.view.image_loaded.connect(self.handle_image_load)
        self.view.scan_requested.connect(self.handle_scan_request)
        self.view.rotate_requested.connect(self.handle_rotation)
        self.view.manual_corners_selected.connect(self.handle_manual_corners)
        self.view.image_cleared.connect(self.handle_image_clear)
        
    def handle_image_load(self, file_path):
        if self.processor is None:
            self.processor = ImageProcessor()
            
        self.processor.load_image(file_path)
        self.view.display_image(self.processor.image, self.view.original_image_label)
        self.view.scan_btn.setEnabled(True)
        
    def handle_scan_request(self):
        if self.processor is None or self.processor.image is None:
            self.view.show_warning("提示", "请先选择要扫描的图片！")
            return
            
        # 如果有手动选择的角点，直接使用
        if self.manual_corners is not None:
            warped = self.processor.perspective_transform(self.processor.image, self.manual_corners)
            enhanced = enhance_image(warped)
            binary = self.processor.binarize(enhanced)
            
            # 保存原始分辨率的处理结果
            self.processed_result = binary
            # 显示时可能会缩放，但不影响原始图像质量
            self.view.display_image(binary, self.view.processed_image_label)
            return
            
        corners = self.processor.detect_document()
        if corners is not None:
            warped = self.processor.perspective_transform(self.processor.image, corners)
            enhanced = enhance_image(warped)
            binary = self.processor.binarize(enhanced)
            
            # 保存原始分辨率的处理结果
            self.processed_result = binary
            self.view.display_image(binary, self.view.processed_image_label)
        else:
            if not self.view.original_image_label.selecting_points:
                self.view.show_warning("提示", "请手动选择文档边框")
                self.view.original_image_label.selecting_points = True
                self.view.original_image_label.update()
            
    def handle_manual_corners(self, points):
        """处理手动选择的角点"""
        if self.processor and self.processor.image is not None:
            print("Original points:", points)
            points_array = np.array(points, dtype=np.float32)
            self.manual_corners = points_array
            print("Transformed corners shape:", self.manual_corners.shape)
            print("Transformed corners:", self.manual_corners)
            
            width = max(
                np.linalg.norm(points_array[1] - points_array[0]),
                np.linalg.norm(points_array[3] - points_array[2])
            )
            height = max(
                np.linalg.norm(points_array[2] - points_array[1]),
                np.linalg.norm(points_array[3] - points_array[0])
            )
            print(f"Target dimensions: {width} x {height}")
            
            warped = self.processor.perspective_transform(self.processor.image, self.manual_corners)
            if warped is not None:
                print("Warped image shape:", warped.shape)
                enhanced = enhance_image(warped)
                binary = self.processor.binarize(enhanced)
                self.view.display_image(binary, self.view.processed_image_label)
            else:
                print("Perspective transform failed!")
            
    def handle_image_clear(self):
        """处理图片清除事件"""
        self.processor = None
        self.manual_corners = None  # 清除存储的手动角点
        
    def handle_rotation(self, clockwise):
        """处理图像旋转"""
        if self.processor and self.processor.image is not None:
            rotated = self.processor.rotate_image(clockwise)
            self.view.display_image(rotated, self.view.original_image_label)
            # 清除已存储的手动角点，因为图片已旋转
            self.manual_corners = None