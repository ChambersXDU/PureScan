# PureScan

PureScan 是一个简洁高效的文档扫描矫正工具，专注于将手机拍摄的文档图片转换为高质量的电子文档。

## 主要功能

- 📱 文档扫描：自动检测并裁剪文档边界
- 📐 透视矫正：修正拍摄角度导致的变形
- 🗞️ 形变矫正：修正纸张褶皱、弯曲导致的变形
- 🎨 图像增强：优化对比度和清晰度
- ⚪ 二值化处理：生成清晰的黑白文档图像


## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/PureScan.git
cd PureScan

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

```bash
# 运行桌面应用
python src/main.py

# 运行cli
python -m src.scan_cli 输入图片路径 -o 输出图片路径

# 运行测试程序，测试example中的图片
python tests/test_scanner.py
```


## 环境要求

- Python 3.8+