import cv2
from PyQt6.QtGui import QImage, QPixmap
import numpy as np

def cv2_to_qpixmap(cv_img):
    """将OpenCV图像转换为QPixmap"""
    height, width, channel = cv_img.shape
    bytes_per_line = 3 * width
    q_img = QImage(cv_img.data, width, height, bytes_per_line, 
                  QImage.Format.Format_RGB888).rgbSwapped()
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