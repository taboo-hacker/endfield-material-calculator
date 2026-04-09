# 终末地物资调度计算器 - PyQt5版本

## 功能说明

这是一个基于PyQt5的桌面应用程序，用于计算终末地游戏中的物资调度收益。

### 主要功能
- 四号谷地和武陵两个地区的物资管理
- 手动输入或从图片中OCR识别物资价格
- 实时计算单个利润、总利润和收益率
- 按收益率或总利润排序
- 可视化图表展示
- 智能调度建议

## 安装依赖

### 1. 安装Python依赖
```bash
pip install -r requirements.txt
```

### 2. 安装Tesseract OCR引擎（用于图片识别功能）

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### macOS:
```bash
brew install tesseract
```

#### Windows:
从 https://github.com/UB-Mannheim/tesseract/wiki 下载并安装

## 运行程序

```bash
python main.py
```

## 使用说明

### 手动输入价格
1. 选择地区（四号谷地/武陵）
2. 在物资录入表格中输入购入价和售出价
3. 设置统一采购数量
4. 程序会自动计算收益并显示结果

### 从图片读取数据
1. 点击"从图片读取数据"按钮
2. 选择包含物资价格的截图
3. 程序会尝试OCR识别价格并填充到表格中
4. 核对识别结果，如有错误可手动修正

### 功能按钮
- **按收益率排序**：按收益率从高到低排序
- **按总利润排序**：按总利润从高到低排序
- **一键填充建议价(2000)**：将所有购入价设置为2000
- **清空所有数据**：清空所有价格输入

## 项目结构

```
/workspace/
├── main.py          # 主程序文件
├── requirements.txt # 依赖文件
└── README.md        # 说明文档
```
