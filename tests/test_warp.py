import sys
from pathlib import Path
import time

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.scan_cli import process_document

def main():
    # 处理示例图片
    example_dir = project_root / "examples"
    output_dir = project_root / "test_outputs"
    
    # 检查目录是否存在
    if not example_dir.exists():
        print(f"错误: examples 目录不存在: {example_dir}")
        return
    
    output_dir.mkdir(exist_ok=True)
    
    # 获取所有包含warp的jpg和png图片
    image_files = []
    for ext in ['.jpg', '.png']:
        image_files.extend(example_dir.glob(f"*warp*{ext}"))
    
    if not image_files:
        print(f"警告: 在 {example_dir} 中没有找到文件名包含warp的jpg或png图片")
        return
        
    # 处理匹配的图片
    for img_path in image_files:
        # 为扭曲矫正测试图片创建特殊的输出文件名
        out_path = output_dir / f"processed_unwarp_{img_path.name}"
        print(f"处理: {img_path.name} (启用扭曲矫正)")
        
        # 记录开始时间
        start_time = time.time()
        
        # 处理图片，启用扭曲矫正
        process_document(
            str(img_path), 
            str(out_path), 
            show=True,
            enable_unwarp=True  # 启用扭曲矫正
        )
        
        # 计算处理时间
        end_time = time.time()
        process_time = end_time - start_time
        print(f"处理完成: {img_path.name}, 耗时: {process_time:.2f} 秒")
        
        # 同时生成一个不进行扭曲矫正的版本作为对比
        out_path_normal = output_dir / f"processed_normal_{img_path.name}"
        print(f"处理: {img_path.name} (不进行扭曲矫正)")
        
        start_time = time.time()
        process_document(
            str(img_path), 
            str(out_path_normal), 
            show=True,
            enable_unwarp=False  # 不进行扭曲矫正
        )
        
        end_time = time.time()
        process_time = end_time - start_time
        print(f"处理完成: {img_path.name}, 耗时: {process_time:.2f} 秒")
        print("-" * 50)  # 添加分隔线以便于区分不同处理结果

if __name__ == "__main__":
    main()