import cv2
import numpy as np

class ImageProcessor:
    def __init__(self):
        self.image = None
        
    def load_image(self, image_path):
        """加载图像"""
        self.image = cv2.imread(image_path)
        return self.image
        
    def detect_document(self, image=None):
        """检测文档边界"""
        if image is None:
            image = self.image
            
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. 增强对比度
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # 2. 使用更大的核进行高斯模糊
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. 使用更激进的Canny参数
        edges = cv2.Canny(blur, 30, 200)
        
        # 4. 使用膨胀操作连接边缘
        kernel = np.ones((3,3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # 5. 调整面��筛选条件
        if contours:
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
            
            for contour in contours:
                perimeter = cv2.arcLength(contour, True)
                epsilon = 0.05 * perimeter  # 增加epsilon值，使轮廓近似更宽松
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # 6. 放宽面积限制条件
                if len(approx) == 4 and cv2.contourArea(approx) > image.shape[0] * image.shape[1] * 0.05:
                    return approx
                    
        return None
        
    def perspective_transform(self, image, corners):
        """执行透视变换"""
        def order_points(pts):
            # 初始化坐标点
            rect = np.zeros((4, 2), dtype="float32")
            
            # 计算左上角和右下角
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]  # 左上
            rect[2] = pts[np.argmax(s)]  # 右下
            
            # 计算右上角和左下角
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]  # 右上
            rect[3] = pts[np.argmax(diff)]  # 左下
            
            return rect

        # 获取图像尺寸
        h, w = image.shape[:2]
        
        # 确保角点顺序：左上、右上、右下、左下
        corners = corners.reshape(4, 2)
        corners = order_points(corners)  # 添加这行来排序角点
        
        # 计算目标矩形的宽度和高度
        width = max(
            np.linalg.norm(corners[1] - corners[0]),  # 上边
            np.linalg.norm(corners[3] - corners[2])   # 下边
        )
        height = max(
            np.linalg.norm(corners[2] - corners[1]),  # 右边
            np.linalg.norm(corners[3] - corners[0])   # 左边
        )
        
        # 设置目标点为规则矩形
        dst_points = np.array([
            [0, 0],           # 左上
            [width, 0],       # 右上
            [width, height],  # 右下
            [0, height]       # 左下
        ], dtype=np.float32)
        
        # 计算透视变换矩阵
        matrix = cv2.getPerspectiveTransform(corners.astype(np.float32), dst_points)
        
        # 执行变换，使用计算出的宽度和高度
        warped = cv2.warpPerspective(image, matrix, (int(width), int(height)))
        
        return warped

    def binarize(self, image=None, threshold=127):
        """二值化处理"""
        if image is None:
            image = self.image
            
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # 锐化处理
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]])
        sharpened = cv2.filter2D(gray, -1, kernel)
        
        # 使用全局阈值进行二值化
        _, binary = cv2.threshold(sharpened, threshold, 255, cv2.THRESH_BINARY)
        
        return binary

    def rotate_image(self, clockwise=True):
        """旋转图像90度"""
        if self.image is None:
            return None
        # 顺时针旋转90度，逆时针旋转-90度
        angle = 90 if clockwise else -90
        self.image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE if clockwise else cv2.ROTATE_90_COUNTERCLOCKWISE)
        return self.image