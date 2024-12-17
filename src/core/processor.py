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
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.transformer = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.4611, 0.4359, 0.3905), 
                               std=(0.2193, 0.2150, 0.2109))
        ])
        self.remove_shadow = False  # 添加阴影处理开关
        
    def _ensure_model_loaded(self):
        """确保模型已加载"""
        if self.model is None and os.path.exists(self.model_path):
            self.load_model(self.model_path)
            
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
        
        # 先将模型移到指定设备
        self.model.to(self.device)
        
        # 加载权重并确保它们在正确的设备上
        checkpoints = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(checkpoints, strict=False)
        self.model.eval()

    def detect_document(self, image=None):
        """使用深度学习模型检测文档边界"""
        self._ensure_model_loaded()  # 只在需要时才加载模型
        
        if image is None:
            image = self.image
            
        if self.model is None:
            raise ValueError("无法加载模型")

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
        # 将输入数据移动到与模型相同的设备上
        image_transformer = image_transformer.to(self.device)

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

    def binarize(self, image=None, remove_shadow=None):
        """二值化处理
        Args:
            image: 输入图像
            remove_shadow: 是否去除阴影，如果为None则使用实例默认设置
        """
        if image is None:
            image = self.image
            
        if remove_shadow is None:
            remove_shadow = self.remove_shadow
            
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            gray = l
        else:
            gray = image

        height, width = gray.shape[:2]
        min_dim = min(height, width)
        
        if remove_shadow:
            # 优化的单尺度 Retinex 处理
            gray_float = gray.astype(np.float32)
            
            # 1. 使用稍大的 sigma 值来减少局部噪声
            sigma = min_dim // 20
            kernel_size = int(sigma * 3) | 1
            blur = cv2.GaussianBlur(gray_float, (kernel_size, kernel_size), 0)
            
            # 2. 调整 Retinex 计算，减少过度增强
            retinex = np.maximum(gray_float / (blur + 1.0), 0.3)  # 限制最小值
            
            # 3. 更温和的归一化
            retinex = ((retinex - retinex.min()) / 
                      (retinex.max() - retinex.min()) * 220 + 35)  # 控制动态范围
            
            # 4. 轻微的高斯模糊去除噪点
            gray = cv2.GaussianBlur(retinex.astype(np.uint8), (3, 3), 0)
        
        # 动态调整参数
        block_size = max(min_dim // 30, 11)
        if block_size % 2 == 0:
            block_size += 1
            
        # 对低分辨率图像进行预处理
        if min_dim < 1000:
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # 自适应阈值处理
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=block_size,
            C=20
        )
        
        # 形态学操作
        kernel_size = 2 if min_dim >= 1000 else 1
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
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

    def set_shadow_removal(self, enabled=True):
        """设置是否启用阴影去除"""
        self.remove_shadow = enabled