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
        
        # 5. 调整面积筛选条件
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
        """透视变换矫正"""
        # 获取矩形的宽度和高度
        rect = np.zeros((4, 2), dtype="float32")
        corners = corners.reshape(4, 2)
        
        # 计算左上、右上、右下、左下点
        s = corners.sum(axis=1)
        rect[0] = corners[np.argmin(s)]  # 左上
        rect[2] = corners[np.argmax(s)]  # 右下
        
        diff = np.diff(corners, axis=1)
        rect[1] = corners[np.argmin(diff)]  # 右上
        rect[3] = corners[np.argmax(diff)]  # 左下
        
        # 计算最大宽度和高度
        widthA = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + 
                        ((rect[2][1] - rect[3][1]) ** 2))
        widthB = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + 
                        ((rect[1][1] - rect[0][1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + 
                         ((rect[1][1] - rect[2][1]) ** 2))
        heightB = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + 
                         ((rect[0][1] - rect[3][1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        # 目标坐标
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        # 计算透视变换矩阵
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        
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