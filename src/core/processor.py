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
        
        # 增加模糊处理来减少噪声
        blur = cv2.GaussianBlur(gray, (9, 9), 0)
        
        # 自适应二值化
        binary = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # 形态学操作来清理图像
        kernel = np.ones((5,5), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 调整Canny边缘检测的参数
        edges = cv2.Canny(binary, 50, 150, apertureSize=3)
        
        # 寻找轮廓，使用RETR_LIST来检测所有轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, 
                                       cv2.CHAIN_APPROX_SIMPLE)
        
        # 筛选合适的轮廓
        if contours:
            # 按面积排序，取最大的几个轮廓
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
            
            for contour in contours:
                perimeter = cv2.arcLength(contour, True)
                epsilon = 0.02 * perimeter
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # 检查是否是四边形，且面积足够大
                if len(approx) == 4 and cv2.contourArea(approx) > image.shape[0] * image.shape[1] * 0.1:
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