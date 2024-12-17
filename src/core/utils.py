import cv2
from PyQt6.QtGui import QImage, QPixmap
import numpy as np

import torch
import torch.nn.functional as F

from .model import UVDocnet

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

def load_model(ckpt_path):
    """
    Load UVDocnet model.
    """
    model = UVDocnet(num_filter=32, kernel_size=5)
    ckpt = torch.load(ckpt_path, map_location=torch.device('cpu'))
    model.load_state_dict(ckpt["model_state"])
    return model

def bilinear_unwarping(warped_img, point_positions, img_size):
    """
    Utility function that unwarps an image.
    Unwarp warped_img based on the 2D grid point_positions with a size img_size.
    Args:
        warped_img  :       torch.Tensor of shape BxCxHxW (dtype float)
        point_positions:    torch.Tensor of shape Bx2xGhxGw (dtype float)
        img_size:           tuple of int [w, h]
    """
    upsampled_grid = F.interpolate(
        point_positions, size=(img_size[1], img_size[0]), mode="bilinear", align_corners=True
    )
    unwarped_img = F.grid_sample(warped_img, upsampled_grid.transpose(1, 2).transpose(2, 3), align_corners=True)

    return unwarped_img


def bilinear_unwarping_from_numpy(warped_img, point_positions, img_size):
    """
    Utility function that unwarps an image.
    Unwarp warped_img based on the 2D grid point_positions with a size img_size.
    Accept numpy arrays as input.
    """
    warped_img = torch.unsqueeze(torch.from_numpy(warped_img.transpose(2, 0, 1)).float(), dim=0)
    point_positions = torch.unsqueeze(torch.from_numpy(point_positions.transpose(2, 0, 1)).float(), dim=0)

    unwarped_img = bilinear_unwarping(warped_img, point_positions, img_size)

    unwarped_img = unwarped_img[0].numpy().transpose(1, 2, 0)
    return unwarped_img
