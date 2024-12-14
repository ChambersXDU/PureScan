import cv2
from PyQt6.QtGui import QImage, QPixmap
import numpy as np

def cv2_to_qpixmap(cv_img):
    """将 OpenCV 图像转换为 QPixmap"""
    if len(cv_img.shape) == 2:  # 如果是单通道图像
        # 转换为三通道图像
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2RGB)
    
    height, width, channel = cv_img.shape
    bytes_per_line = channel * width
    # OpenCV 使用 BGR 格式，需要转换为 RGB
    if channel == 3:  # 确保是彩色图像
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    q_img = QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(q_img)

def enhance_image(image):
    """图像增强"""
    # 对比度增强
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    return enhanced 