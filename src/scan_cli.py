import argparse
import cv2
from .core.processor import ImageProcessor
from .core.utils import enhance_image

def process_document(input_path, output_path=None, show=False, remove_shadow=False):
    """处理单个文档图像
    Args:
        input_path: 输入图像路径
        output_path: 输出图像路径
        show: 是否显示处理过程
        remove_shadow: 是否启用阴影去除
    """
    # 初始化处理器
    processor = ImageProcessor()
    processor.set_shadow_removal(remove_shadow)  # 设置阴影去除选项
    
    # 加载图像
    image = processor.load_image(input_path)
    if image is None:
        print(f"错误：无法加载图像 {input_path}")
        return False
        
    # 检测文档边界
    corners = processor.detect_document()
    if corners is None:
        print("警告：未能检测到文档边界")
        return False
        
    # 执行透视变换
    warped = processor.perspective_transform(image, corners)
    
    # 先进行图像增强
    enhanced = enhance_image(warped)
    
    # 然后再二值化处理
    binary = processor.binarize(enhanced)
    
    # 保存结果
    if output_path:
        cv2.imwrite(output_path, binary)
        print(f"处理后的图像已保存到: {output_path}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='PureScan 文档扫描工具')
    parser.add_argument('input', help='输入图像的路径')
    parser.add_argument('-o', '--output', help='输出图像的路径')
    parser.add_argument('-d', '--debug', action='store_true', help='显示调试信息')
    parser.add_argument('--remove-shadow', action='store_true', 
                       help='启用阴影去除')
    
    args = parser.parse_args()
    
    if args.debug:
        print(f"处理图像: {args.input}")
        if args.output:
            print(f"输出路径: {args.output}")
    
    # 处理图像，传入阴影去除参数
    success = process_document(
        args.input, 
        args.output,
        remove_shadow=args.remove_shadow
    )
    
    if not success:
        print("处理失败")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())