import argparse
import cv2
from .core.processor import ImageProcessor
from .core.utils import enhance_image

def process_document(input_path, output_path=None, show=False, remove_shadow=False, enable_unwarp=False):
    """处理单个文档图像
    Args:
        input_path: 输入图像路径
        output_path: 输出图像路径
        show: 是否显示处理过程
        remove_shadow: 是否启用阴影去除
        enable_unwarp: 是否启用扭曲矫正
    """
    # 初始化处理器
    processor = ImageProcessor()
    processor.set_shadow_removal(remove_shadow)
    processor.set_unwarp(enable_unwarp)  # 设置是否启用扭曲矫正
    
    try:
        result = processor.process_document(input_path)
        
        if output_path:
            cv2.imwrite(output_path, result)
            print(f"处理后的图像已保存到: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"处理失败: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='PureScan 文档扫描工具')
    parser.add_argument('input', help='输入图像的路径')
    parser.add_argument('-o', '--output', help='输出图像的路径')
    parser.add_argument('-d', '--debug', action='store_true', help='显示调试信息')
    parser.add_argument('--remove-shadow', action='store_true', help='启用阴影去除')
    parser.add_argument('--unwarp', action='store_true', help='启用扭曲矫正（不进行边界检测）')
    
    args = parser.parse_args()
    
    if args.debug:
        print(f"处理图像: {args.input}")
        if args.output:
            print(f"输出路径: {args.output}")
    
    # 处理图像
    success = process_document(
        args.input, 
        args.output,
        remove_shadow=args.remove_shadow,
        enable_unwarp=args.unwarp
    )
    
    if not success:
        print("处理失败")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())