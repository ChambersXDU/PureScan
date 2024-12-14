import cv2
import numpy as np
import torch
from torchvision import transforms
from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large, deeplabv3_resnet50
import os

class ImageProcessor:
    DEFAULT_MODEL_PATH = 'weights/image_trimming_enhancement/model_mbv3_iou_mix_2C049.pth'
    
    def __init__(self, model_path=None):
        self.image = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.transformer = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.4611, 0.4359, 0.3905), 
                               std=(0.2193, 0.2150, 0.2109))
        ])
        
        # 如果提供了模型路径，直接加载模型
        if model_path:
            self.load_model(model_path)
        elif os.path.exists(self.DEFAULT_MODEL_PATH):
            self.load_model(self.DEFAULT_MODEL_PATH)
        
    def load_image(self, image_path):
        """加载图像"""
        self.image = cv2.imread(image_path)
        return self.image
        
    def load_model(self, model_path, num_classes=2, model_name="mbv3"):
        """加载深度学习模型"""
        if model_name == "mbv3":
            self.model = deeplabv3_mobilenet_v3_large(num_classes=num_classes)
        else:
            self.model = deeplabv3_resnet50(num_classes=num_classes)
        self.model.to(self.device)
        checkpoints = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(checkpoints, strict=False)
        self.model.eval()

    def detect_document(self, image=None):
        """使用深度学习模型检测文档边界"""
        if image is None:
            image = self.image
        
        if self.model is None:
            raise ValueError("请先加载模型")

        IMAGE_SIZE = 384
        half = IMAGE_SIZE // 2
        imH, imW, C = image.shape
        
        # 调整图像大小
        image_resize = cv2.resize(image, (IMAGE_SIZE, IMAGE_SIZE), 
                                interpolation=cv2.INTER_NEAREST)
        
        scale_x = imW / IMAGE_SIZE
        scale_y = imH / IMAGE_SIZE

        # 预处理图像
        image_transformer = self.transformer(image_resize)
        image_transformer = torch.unsqueeze(image_transformer, dim=0)

        # 模型推理
        with torch.no_grad():
            out = self.model(image_transformer)["out"].cpu()

        # 后处理
        out = torch.argmax(out, dim=1, keepdims=True).permute(0, 2, 3, 1)[0].numpy()
        out = out.squeeze().astype(np.int32)

        r_H, r_W = out.shape
        _out_extended = np.zeros((IMAGE_SIZE + r_H, IMAGE_SIZE + r_W), dtype=out.dtype)
        _out_extended[half:half + IMAGE_SIZE, half:half + IMAGE_SIZE] = out * 255
        out = _out_extended.copy()

        # 边缘检测
        canny = cv2.Canny(out.astype(np.uint8), 225, 255)
        canny = cv2.dilate(canny, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        
        # 查找轮廓
        contours, _ = cv2.findContours(canny, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        if not contours:
            return None
        
        page = sorted(contours, key=cv2.contourArea, reverse=True)[0]
        epsilon = 0.02 * cv2.arcLength(page, True)
        corners = cv2.approxPolyDP(page, epsilon, True)
        
        # 调整坐标
        corners = np.concatenate(corners).astype(np.float32)
        corners[:, 0] -= half
        corners[:, 1] -= half
        corners[:, 0] *= scale_x
        corners[:, 1] *= scale_y
        
        return corners

    def perspective_transform(self, image, corners):
        """改进的透视变换方法"""
        def order_points(pts):
            rect = np.zeros((4, 2), dtype='float32')
            pts = np.array(pts)
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]
            rect[2] = pts[np.argmax(s)]
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]
            rect[3] = pts[np.argmax(diff)]
            return rect

        def find_dest(pts):
            (tl, tr, br, bl) = pts
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            destination_corners = [[0, 0], [maxWidth, 0], 
                                 [maxWidth, maxHeight], [0, maxHeight]]
            return order_points(np.array(destination_corners))

        # 处理边界超出图像的情况
        imH, imW = image.shape[:2]
        BUFFER = 10
        
        if not (np.all(corners.min(axis=0) >= (0, 0)) and 
                np.all(corners.max(axis=0) <= (imW, imH))):
            left_pad, top_pad, right_pad, bottom_pad = 0, 0, 0, 0
            rect = cv2.minAreaRect(corners.reshape((-1, 1, 2)))
            box = cv2.boxPoints(rect)
            box_corners = np.int32(box)

            # 计算需要的填充
            box_x_min, box_x_max = np.min(box_corners[:, 0]), np.max(box_corners[:, 0])
            box_y_min, box_y_max = np.min(box_corners[:, 1]), np.max(box_corners[:, 1])

            if box_x_min <= 0: left_pad = abs(box_x_min) + BUFFER
            if box_x_max >= imW: right_pad = (box_x_max - imW) + BUFFER
            if box_y_min <= 0: top_pad = abs(box_y_min) + BUFFER
            if box_y_max >= imH: bottom_pad = (box_y_max - imH) + BUFFER

            # 扩展图像
            image_extended = np.zeros((top_pad + bottom_pad + imH, 
                                     left_pad + right_pad + imW, 3), 
                                    dtype=image.dtype)
            image_extended[top_pad:top_pad + imH, 
                          left_pad:left_pad + imW] = image
            
            # 调整角点位置
            corners[:, 0] += left_pad
            corners[:, 1] += top_pad
            image = image_extended

        # 执行透视变换
        corners = order_points(corners)
        destination_corners = find_dest(corners)
        M = cv2.getPerspectiveTransform(corners, destination_corners)
        
        warped = cv2.warpPerspective(image, M, 
                                    (int(destination_corners[2][0]), 
                                     int(destination_corners[2][1])),
                                    flags=cv2.INTER_LANCZOS4)
        
        warped = np.clip(warped, 0, 255).astype(np.uint8)
        return warped

    def binarize(self, image=None):
        """二值化处理"""
        if image is None:
            image = self.image
            
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 1. 首先进行背景校正
        # 使用大尺寸高斯模糊获取背景
        blur_size = max(gray.shape[0], gray.shape[1]) // 8
        if blur_size % 2 == 0:
            blur_size += 1
        background = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
        
        # 2. 背景减除
        adjusted = cv2.subtract(255, cv2.subtract(background, gray))
        
        # 3. 对比度增强
        alpha = 1.2
        beta = 10
        enhanced = cv2.convertScaleAbs(adjusted, alpha=alpha, beta=beta)
        
        # 4. 自适应阈值处理
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=25,
            C=15
        )
        
        # 5. 去除噪点
        kernel = np.ones((2,2), np.uint8)
        denoised = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return denoised

    def rotate_image(self, clockwise=True):
        """旋转图像90度"""
        if self.image is None:
            return None
        # 顺时针旋转90度，逆时针旋转-90度
        angle = 90 if clockwise else -90
        self.image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE if clockwise else cv2.ROTATE_90_COUNTERCLOCKWISE)
        return self.image

    def process_document(self, image_path):
        """完整的文档处理流程"""
        # 加载图像
        image = self.load_image(image_path)
        if image is None:
            raise ValueError("无法加载图像")

        # 检测边界并进行透视变换
        corners = self.detect_document(image)
        if corners is not None:
            transformed = self.perspective_transform(image, corners)
        else:
            transformed = image  # 如果没有检测到边界，使用原图

        # 二值化处理
        binary = self.binarize(transformed)
        
        return binary