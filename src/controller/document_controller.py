from PyQt6.QtCore import QObject
from core.processor import ImageProcessor
from core.utils import enhance_image

class DocumentController(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.processor = None
        
        # 连接信号和槽
        self.view.image_loaded.connect(self.handle_image_load)
        self.view.scan_requested.connect(self.handle_scan_request)
        
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
            
        corners = self.processor.detect_document()
        if corners is not None:
            warped = self.processor.perspective_transform(self.processor.image, corners)
            enhanced = enhance_image(warped)
            self.view.display_image(enhanced, self.view.processed_image_label)
        else:
            self.view.show_warning("警告", "未能检测到文档边界！") 