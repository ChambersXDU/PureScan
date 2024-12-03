

# PureScan

PureScan 是一个简洁高效的文档扫描矫正工具，专注于将手机拍摄的文档图片转换为高质量的电子文档。

## 主要功能

- 📱 文档扫描：自动检测并裁剪文档边界
- 📐 透视矫正：修正拍摄角度导致的变形
- 🗞️ 形变矫正：修正纸张褶皱、弯曲导致的变形
- 🎨 图像增强：优化对比度和清晰度
- ⚪ 二值化处理：生成清晰的黑白文档图像

## 技术栈

- **GUI框架**: PyQt6
- **图像处理**: OpenCV

- **其他依赖**:
  - NumPy: 数值计算
  - Albumentations: 数据增强（训练用）
  - cx_Freeze: 应用打包

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
# 运行应用
python src/main.py
```


## 开发计划

- [x] 基础 GUI 界面
- [x] 文档边界检测
- [x] 透视矫正
- [ ] 形变矫正
- [ ] 图像增强优化
- [ ] 应用打包发布

## 环境要求

- Python 3.8+
- OpenCV 4.5+
- PyQt6
