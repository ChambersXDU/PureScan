import sys
from pathlib import Path

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
    
    # 获取所有jpg和png图片
    image_files = list(example_dir.glob("*.jpg")) + list(example_dir.glob("*.png"))
    
    if not image_files:
        print(f"警告: 在 {example_dir} 中没有找到任何jpg或png图片")
        return
        
    # 处理目录中的所有图片
    for img_path in image_files:
        out_path = output_dir / f"processed_{img_path.name}"
        print(f"处理: {img_path.name}")
        process_document(str(img_path), str(out_path), show=True)

if __name__ == "__main__":
    main() 