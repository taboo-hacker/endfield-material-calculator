import sys
import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QFileDialog, QMessageBox, QComboBox, QSpinBox, QHeaderView,
    QSplitter, QTextEdit, QGroupBox, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

matplotlib.use('Qt5Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# 配色方案
COLORS = {
    'bg_endfield': '#0f1724',
    'bg_card': '#1e293b',
    'text_primary': '#38bdf8',
    'border_primary': '#38bdf8',
    'border_gray': '#4b5563',
    'text_loss': '#ef4444',
    'tag_valley': '#0ea5e9',
    'tag_wuling': '#10b981',
    'text_gray': '#94a3b8',
    'text_light_gray': '#64748b',
    'border_light_gray': '#374151'
}

# 物资数据配置
DATA_CONFIG = {
    'valley': {
        'name': '四号谷地',
        'default_qty': 210,
        'items': [
            '锚点厨具货组', '悬空腕兽骨殖货组', '巫术矿钻货组',
            '天使罐头货组', '谷地水培肉货组', '团结牌口服液货组',
            '塞什卡钟石货组', '漂石树幼苗货组', '星体晶块货组',
            '警戒者矿镐货组', '边角料积木货组'
        ]
    },
    'wuling': {
        'name': '武陵',
        'default_qty': 50,
        'items': [
            '岳研避瘴茶货组', '武侠电影货组', '冬虫夏笋货组',
            '武陵冻梨货组'
        ]
    }
}

def set_widget_style(widget):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS['bg_endfield']))
    widget.setPalette(palette)
    widget.setAutoFillBackground(True)

class OCRThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, image_path, region):
        super().__init__()
        self.image_path = image_path
        self.region = region

    def run(self):
        try:
            results = self.extract_data_from_image(self.image_path, self.region)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def extract_data_from_image(self, image_path, region):
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("无法读取图片")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        data = pytesseract.image_to_data(binary, config=custom_config, output_type=pytesseract.Output.DICT)

        numbers = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if text and text.isdigit():
                numbers.append({
                    'value': int(text),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': data['conf'][i]
                })

        numbers = [n for n in numbers if n['conf'] > 50 and len(str(n['value'])) >= 3]
        numbers.sort(key=lambda x: (x['y'] // 100, x['x']))

        item_list = DATA_CONFIG[region]['items']
        extracted_prices = {}

        for i, item in enumerate(item_list):
            if i < len(numbers):
                price = numbers[i]['value']
                extracted_prices[item] = {
                    'buy': price,
                    'sell': 2000
                }
            else:
                extracted_prices[item] = {
                    'buy': 2000,
                    'sell': 2000
                }

        return extracted_prices

class MaterialTable(QTableWidget):
    def __init__(self, region, parent=None):
        super().__init__(parent)
        self.region = region
        self.config = DATA_CONFIG[region]
        self.init_ui()

    def init_ui(self):
        headers = ['物资名称', '建议价', '实际购入价', '售出价']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: #e5e7eb;
                gridline-color: {COLORS['border_light_gray']};
                border: none;
                border-radius: 0px;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border_light_gray']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_gray']};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {COLORS['border_gray']};
                font-weight: normal;
                font-size: 14px;
            }}
            QTableWidget QLineEdit {{
                background-color: {COLORS['bg_endfield']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_gray']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }}
        """)

        self.setRowCount(len(self.config['items']))
        for row, item_name in enumerate(self.config['items']):
            name_item = QTableWidgetItem(item_name)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.setItem(row, 0, name_item)

            suggest_item = QTableWidgetItem('2000')
            suggest_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            suggest_item.setForeground(QColor(COLORS['text_gray']))
            self.setItem(row, 1, suggest_item)

            self.setItem(row, 2, QTableWidgetItem(''))
            self.setItem(row, 3, QTableWidgetItem(''))

            self.setRowHeight(row, 36)

        self.itemChanged.connect(self.on_item_changed)

    def on_item_changed(self, item):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'calculate'):
                parent.calculate()
                break
            parent = parent.parent()

    def get_prices(self):
        prices = {}
        for row in range(self.rowCount()):
            name = self.item(row, 0).text()
            buy_text = self.item(row, 2).text()
            sell_text = self.item(row, 3).text()

            buy_price = float(buy_text) if buy_text else 2000.0
            sell_price = float(sell_text) if sell_text else 2000.0

            prices[name] = {'buy': buy_price, 'sell': sell_price}
        return prices

    def set_prices(self, prices):
        for row in range(self.rowCount()):
            name = self.item(row, 0).text()
            if name in prices:
                buy_price = prices[name]['buy']
                sell_price = prices[name]['sell']
                self.setItem(row, 2, QTableWidgetItem(str(buy_price)))
                self.setItem(row, 3, QTableWidgetItem(str(sell_price)))

    def fill_default(self):
        for row in range(self.rowCount()):
            self.setItem(row, 2, QTableWidgetItem('2000'))

    def clear_all(self):
        for row in range(self.rowCount()):
            self.setItem(row, 2, QTableWidgetItem(''))
            self.setItem(row, 3, QTableWidgetItem(''))

class ResultTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        headers = ['物资名称', '购入价', '售出价', '采购数量', '单个利润', '总利润', '收益率', '标记']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: #e5e7eb;
                gridline-color: {COLORS['border_light_gray']};
                border: none;
                border-radius: 0px;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border_light_gray']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_gray']};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {COLORS['border_gray']};
                font-weight: normal;
                font-size: 14px;
            }}
        """)

        self.verticalHeader().setDefaultSectionSize(36)

    def update_data(self, items, best_profit_rate=None, best_total_profit=None, sort_type='profitRate'):
        self.setRowCount(len(items))
        for row, item in enumerate(items):
            self.setItem(row, 0, QTableWidgetItem(item['name']))
            self.setItem(row, 1, QTableWidgetItem(str(item['buyPrice'])))
            self.setItem(row, 2, QTableWidgetItem(str(item['sellPrice'])))
            self.setItem(row, 3, QTableWidgetItem(str(item['qty'])))
            self.setItem(row, 4, QTableWidgetItem(f"{item['singleProfit']:.0f}"))
            self.setItem(row, 5, QTableWidgetItem(f"{item['totalProfit']:.0f}"))
            self.setItem(row, 6, QTableWidgetItem(f"{item['profitRate']:.1f}%"))

            tag_text = ''
            if best_profit_rate and item['name'] == best_profit_rate['name']:
                tag_text += '最优收益率'
            if best_total_profit and item['name'] == best_total_profit['name']:
                tag_text += ' / 最高总利润' if tag_text else '最高总利润'

            self.setItem(row, 7, QTableWidgetItem(tag_text or '-'))

            for col in range(4, 7):
                cell_item = self.item(row, col)
                if col == 4 and item['singleProfit'] < 0:
                    cell_item.setForeground(QColor(COLORS['text_loss']))
                elif col == 5 and item['totalProfit'] < 0:
                    cell_item.setForeground(QColor(COLORS['text_loss']))
                elif col == 6 and item['profitRate'] < 0:
                    cell_item.setForeground(QColor(COLORS['text_loss']))

            if (sort_type == 'profitRate' and best_profit_rate and item['name'] == best_profit_rate['name']) or \
               (sort_type == 'totalProfit' and best_total_profit and item['name'] == best_total_profit['name']):
                for col in range(self.columnCount()):
                    self.item(row, col).setBackground(QColor(239, 68, 68, 25))
                    self.item(row, col).setData(Qt.UserRole, 'highlighted')

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(15, 10))
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def update_charts(self, items):
        self.figure.clear()
        gs = self.figure.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        ax1 = self.figure.add_subplot(gs[0, 0])
        names = [item['name'] for item in items]
        profits = [item['totalProfit'] for item in items]
        colors = ['#0ea5e980' if profit >= 0 else '#ef444480' for profit in profits]
        ax1.barh(names, profits, color=colors)
        ax1.set_title('总利润', color='#e5e7eb')
        ax1.tick_params(axis='x', colors='#94a3b8')
        ax1.tick_params(axis='y', colors='#94a3b8')
        ax1.spines['bottom'].set_color('#4b5563')
        ax1.spines['top'].set_color('#4b5563')
        ax1.spines['left'].set_color('#4b5563')
        ax1.spines['right'].set_color('#4b5563')
        ax1.set_facecolor('#1e293b')
        ax1.grid(True, alpha=0.3)

        ax2 = self.figure.add_subplot(gs[0, 1])
        rates = [item['profitRate'] for item in items]
        colors2 = ['#3b82f680' if rate >= 0 else '#ef444480' for rate in rates]
        ax2.barh(names, rates, color=colors2)
        ax2.set_title('收益率 (%)', color='#e5e7eb')
        ax2.tick_params(axis='x', colors='#94a3b8')
        ax2.tick_params(axis='y', colors='#94a3b8')
        ax2.spines['bottom'].set_color('#4b5563')
        ax2.spines['top'].set_color('#4b5563')
        ax2.spines['left'].set_color('#4b5563')
        ax2.spines['right'].set_color('#4b5563')
        ax2.set_facecolor('#1e293b')
        ax2.grid(True, alpha=0.3)

        ax3 = self.figure.add_subplot(gs[1, :])
        ax3.plot(names, profits, 'o-', color='#0ea5e9', label='总利润', linewidth=2)
        ax3.set_xlabel('物资名称', color='#e5e7eb')
        ax3.set_ylabel('总利润', color='#0ea5e9')
        ax3.tick_params(axis='x', rotation=45, colors='#94a3b8')
        ax3.tick_params(axis='y', colors='#94a3b8')
        ax3.spines['bottom'].set_color('#4b5563')
        ax3.spines['top'].set_color('#4b5563')
        ax3.spines['left'].set_color('#4b5563')
        ax3.spines['right'].set_color('#4b5563')
        ax3.set_facecolor('#1e293b')

        ax4 = ax3.twinx()
        ax4.plot(names, rates, 's-', color='#3b82f6', label='收益率', linewidth=2)
        ax4.set_ylabel('收益率 (%)', color='#3b82f6')
        ax4.tick_params(axis='y', colors='#94a3b8')
        ax4.spines['bottom'].set_color('#4b5563')
        ax4.spines['top'].set_color('#4b5563')
        ax4.spines['left'].set_color('#4b5563')
        ax4.spines['right'].set_color('#4b5563')

        ax3.set_title('多维度对比分析', color='#38bdf8', fontsize=14)
        ax3.grid(True, alpha=0.3)

        self.figure.set_facecolor('#0f1724')
        self.canvas.draw()

class EndfieldButton(QPushButton):
    def __init__(self, text, primary=False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setStyleSheet(self.get_style())
        self.setCursor(Qt.PointingHandCursor)

    def get_style(self):
        if self.primary:
            return f"""
                QPushButton {{
                    background-color: {COLORS['bg_card']};
                    color: #e5e7eb;
                    border: 1px solid {COLORS['border_primary']};
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['text_primary']}20;
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['text_primary']}40;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: {COLORS['bg_card']};
                    color: #e5e7eb;
                    border: 1px solid {COLORS['border_gray']};
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: #37415180;
                }}
                QPushButton:pressed {{
                    background-color: #374151;
                }}
            """

    def set_primary(self, primary):
        self.primary = primary
        self.setStyleSheet(self.get_style())

class RegionTag(QLabel):
    def __init__(self, region, parent=None):
        super().__init__(parent)
        self.region = region
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(self.get_style())

    def get_style(self):
        tag_color = COLORS['tag_valley'] if self.region == 'valley' else COLORS['tag_wuling']
        return f"""
            QLabel {{
                background-color: {tag_color};
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 500;
            }}
        """

class RegionTab(QWidget):
    def __init__(self, region, parent=None):
        super().__init__(parent)
        self.region = region
        self.config = DATA_CONFIG[region]
        self.current_sort = 'profitRate'
        self.results = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 32, 24, 32)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.sort_rate_btn = EndfieldButton('按收益率排序', primary=True)
        self.sort_rate_btn.clicked.connect(lambda: self.sort('profitRate'))
        toolbar.addWidget(self.sort_rate_btn)

        self.sort_profit_btn = EndfieldButton('按总利润排序')
        self.sort_profit_btn.clicked.connect(lambda: self.sort('totalProfit'))
        toolbar.addWidget(self.sort_profit_btn)

        toolbar.addSpacing(16)

        self.fill_btn = EndfieldButton('一键填充建议价(2000)')
        self.fill_btn.clicked.connect(self.fill_default)
        toolbar.addWidget(self.fill_btn)

        self.clear_btn = EndfieldButton('清空所有数据')
        self.clear_btn.clicked.connect(self.clear_all)
        toolbar.addWidget(self.clear_btn)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(24)

        # 物资录入卡片
        input_group = QGroupBox()
        input_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLORS['bg_card']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_light_gray']};
                border-radius: 8px;
                margin-top: 0px;
                padding-top: 24px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 24px;
                top: 0px;
            }}
        """)
        
        # 创建标题布局
        input_header_layout = QHBoxLayout()
        input_header_layout.setContentsMargins(24, 0, 24, 16)
        
        tag = RegionTag(self.region)
        input_header_layout.addWidget(tag)
        
        title_label = QLabel('物资录入')
        title_label.setFont(QFont('Arial', 16, QFont.Bold))
        title_label.setStyleSheet('color: #e5e7eb;')
        input_header_layout.addWidget(title_label)
        input_header_layout.addStretch()
        
        # 统一采购数量
        qty_layout = QHBoxLayout()
        qty_label = QLabel('统一采购数量:')
        qty_label.setStyleSheet(f'color: {COLORS["text_gray"]}; font-size: 14px;')
        qty_layout.addWidget(qty_label)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 10000)
        self.qty_spin.setValue(self.config['default_qty'])
        self.qty_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['bg_endfield']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_gray']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                width: 80px;
            }}
        """)
        self.qty_spin.valueChanged.connect(self.calculate)
        qty_layout.addWidget(self.qty_spin)
        
        input_header_layout.addLayout(qty_layout)

        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 24)
        input_layout.addLayout(input_header_layout)
        self.material_table = MaterialTable(self.region)
        input_layout.addWidget(self.material_table)
        input_group.setLayout(input_layout)
        content_layout.addWidget(input_group)

        # 调度分析报告
        suggestion_group = QGroupBox()
        suggestion_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLORS['bg_card']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_light_gray']};
                border-radius: 8px;
                margin-top: 0px;
                padding-top: 24px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 24px;
                top: 0px;
            }}
        """)
        suggestion_layout = QVBoxLayout()
        suggestion_layout.setContentsMargins(24, 0, 24, 24)
        
        suggestion_title = QLabel(f'{self.config["name"]}调度分析报告')
        suggestion_title.setFont(QFont('Arial', 14, QFont.Medium))
        suggestion_title.setStyleSheet(f'color: {COLORS["text_primary"]};')
        suggestion_layout.addWidget(suggestion_title)
        
        self.suggestion_text = QTextEdit()
        self.suggestion_text.setReadOnly(True)
        self.suggestion_text.setMaximumHeight(200)
        self.suggestion_text.setText('请输入物资价格后生成专业调度分析报告')
        self.suggestion_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_endfield']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_light_gray']};
                border-radius: 6px;
                padding: 16px;
                font-size: 14px;
                line-height: 1.8;
            }}
        """)
        suggestion_layout.addWidget(self.suggestion_text)
        suggestion_group.setLayout(suggestion_layout)
        content_layout.addWidget(suggestion_group)

        # 结果表格
        result_group = QGroupBox()
        result_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLORS['bg_card']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_light_gray']};
                border-radius: 8px;
                margin-top: 0px;
                padding-top: 24px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 24px;
                top: 0px;
            }}
        """)
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(24, 0, 24, 24)
        
        result_header_layout = QHBoxLayout()
        result_tag = RegionTag(self.region)
        result_header_layout.addWidget(result_tag)
        
        result_title = QLabel('收益计算结果')
        result_title.setFont(QFont('Arial', 16, QFont.Bold))
        result_title.setStyleSheet('color: #e5e7eb;')
        result_header_layout.addWidget(result_title)
        result_header_layout.addStretch()
        
        result_layout.addLayout(result_header_layout)
        
        self.result_table = ResultTable()
        result_layout.addWidget(self.result_table)
        result_group.setLayout(result_layout)
        content_layout.addWidget(result_group)

        # 图表
        chart_group = QGroupBox()
        chart_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLORS['bg_card']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_light_gray']};
                border-radius: 8px;
                margin-top: 0px;
                padding-top: 24px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 24px;
                top: 0px;
            }}
        """)
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(24, 0, 24, 24)
        self.chart_widget = ChartWidget()
        chart_layout.addWidget(self.chart_widget)
        chart_group.setLayout(chart_layout)
        content_layout.addWidget(chart_group)
        
        # 添加OCR按钮
        ocr_layout = QHBoxLayout()
        ocr_layout.addStretch()
        self.ocr_btn = EndfieldButton('从图片读取数据')
        self.ocr_btn.clicked.connect(self.load_image_ocr)
        ocr_layout.addWidget(self.ocr_btn)
        content_layout.addLayout(ocr_layout)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

    def calculate(self):
        prices = self.material_table.get_prices()
        qty = self.qty_spin.value()

        self.results = []
        for item_name in self.config['items']:
            buy_price = prices[item_name]['buy']
            sell_price = prices[item_name]['sell']

            single_profit = sell_price - buy_price
            total_profit = single_profit * qty
            profit_rate = (single_profit / buy_price * 100) if buy_price > 0 else 0

            self.results.append({
                'name': item_name,
                'buyPrice': buy_price,
                'sellPrice': sell_price,
                'qty': qty,
                'singleProfit': single_profit,
                'totalProfit': total_profit,
                'profitRate': profit_rate
            })

        self.sort(self.current_sort, auto=True)

    def sort(self, sort_type, auto=False):
        if not auto:
            self.current_sort = sort_type

        if sort_type == 'profitRate':
            self.results.sort(key=lambda x: x['profitRate'], reverse=True)
            self.sort_rate_btn.set_primary(True)
            self.sort_profit_btn.set_primary(False)
        else:
            self.results.sort(key=lambda x: x['totalProfit'], reverse=True)
            self.sort_rate_btn.set_primary(False)
            self.sort_profit_btn.set_primary(True)

        best_profit_rate = max(self.results, key=lambda x: x['profitRate']) if self.results else None
        best_total_profit = max(self.results, key=lambda x: x['totalProfit']) if self.results else None

        self.result_table.update_data(self.results, best_profit_rate, best_total_profit, self.current_sort)

        if self.results:
            self.chart_widget.update_charts(self.results)

        self.update_suggestion(best_profit_rate, best_total_profit)

    def update_suggestion(self, best_profit_rate, best_total_profit):
        if not self.results:
            suggestion = '请输入物资价格后生成专业调度分析报告'
        else:
            avg_rate = sum(r['profitRate'] for r in self.results) / len(self.results)
            total_profit = sum(r['totalProfit'] for r in self.results)

            suggestion = f'本次调度分析基于当前输入价格数据，共分析了 {len(self.results)} 种物资。\n'
            suggestion += f'平均收益率：{avg_rate:.1f}%，总利润：{total_profit:.0f}。\n\n'

            if best_profit_rate:
                suggestion += f'【最优收益率】{best_profit_rate["name"]}，收益率：{best_profit_rate["profitRate"]:.1f}%\n'
            if best_total_profit:
                suggestion += f'【最高总利润】{best_total_profit["name"]}，总利润：{best_total_profit["totalProfit"]:.0f}\n\n'

            loss_items = [r for r in self.results if r['profitRate'] < 0]
            if loss_items:
                suggestion += f'【需要注意】以下 {len(loss_items)} 种物资收益率为负，建议谨慎采购：\n'
                for item in loss_items:
                    suggestion += f'- {item["name"]}：{item["profitRate"]:.1f}%\n'
            else:
                suggestion += '【良好】所有物资均有正收益，可根据需求合理安排采购。\n'

        self.suggestion_text.setText(suggestion)

    def fill_default(self):
        self.material_table.fill_default()
        self.calculate()

    def clear_all(self):
        self.material_table.clear_all()
        self.qty_spin.setValue(self.config['default_qty'])
        self.calculate()

    def load_image_ocr(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '选择图片', '', '图片文件 (*.png *.jpg *.jpeg *.bmp)')
        if not file_path:
            return

        self.ocr_btn.setEnabled(False)
        self.ocr_btn.setText('正在识别...')

        self.ocr_thread = OCRThread(file_path, self.region)
        self.ocr_thread.finished.connect(self.on_ocr_finished)
        self.ocr_thread.error.connect(self.on_ocr_error)
        self.ocr_thread.start()

    def on_ocr_finished(self, prices):
        self.material_table.set_prices(prices)
        self.calculate()
        self.ocr_btn.setEnabled(True)
        self.ocr_btn.setText('从图片读取数据')
        QMessageBox.information(self, '成功', '数据识别完成！')

    def on_ocr_error(self, error_msg):
        self.ocr_btn.setEnabled(True)
        self.ocr_btn.setText('从图片读取数据')
        QMessageBox.warning(self, '错误', f'识别失败：{error_msg}\n请手动输入数据。')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('终末地物资调度计算器')
        self.setMinimumSize(1600, 1000)
        self.resize(1920, 1080)
        self.init_ui()

    def init_ui(self):
        set_widget_style(self)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部导航栏
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_endfield']};
                border-bottom: 1px solid {COLORS['border_light_gray']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel('终末地物资调度计算器')
        title.setFont(QFont('Arial', 20, QFont.Bold))
        title.setStyleSheet(f'color: {COLORS["text_primary"]};')
        header_layout.addWidget(title)

        header_layout.addStretch()

        # 地区选择
        region_label = QLabel('选择地区:')
        region_label.setStyleSheet(f'color: {COLORS["text_gray"]}; font-size: 14px;')
        header_layout.addWidget(region_label)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_card']};
                color: #e5e7eb;
                border: 1px solid {COLORS['border_gray']};
                border-radius: 6px;
                padding: 6px 16px;
                margin: 0 4px;
                font-size: 14px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['text_primary']};
                border-color: {COLORS['text_primary']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #374151;
            }}
        """)
        self.valley_tab = RegionTab('valley')
        self.wuling_tab = RegionTab('wuling')
        self.tab_widget.addTab(self.valley_tab, '四号谷地')
        self.tab_widget.addTab(self.wuling_tab, '武陵')

        # 让TabWidget小一点，只做标签切换
        tab_container = QWidget()
        tab_container_layout = QVBoxLayout(tab_container)
        tab_container_layout.addWidget(self.tab_widget.tabBar())
        tab_container_layout.setContentsMargins(0, 0, 0, 0)

        # 创建一个主TabWidget用于内容
        self.content_tab = QTabWidget()
        self.content_tab.setTabPosition(QTabWidget.South)
        self.content_tab.tabBar().hide()
        self.content_tab.addTab(self.valley_tab, '')
        self.content_tab.addTab(self.wuling_tab, '')

        self.tab_widget.currentChanged.connect(self.content_tab.setCurrentIndex)

        header_layout.addWidget(tab_container)

        header_layout.addSpacing(16)

        info = QLabel('建议价格线：2000')
        info.setStyleSheet(f'color: {COLORS["text_gray"]}; font-size: 14px;')
        header_layout.addWidget(info)

        main_layout.addWidget(header)

        main_layout.addWidget(self.content_tab)

        # 页脚
        footer = QLabel('终末地物资调度计算器 | 数据仅本地计算，无上传')
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_light_gray']};
                padding: 16px;
                border-top: 1px solid {COLORS['border_light_gray']};
                background-color: {COLORS['bg_endfield']};
                font-size: 13px;
            }}
        """)
        main_layout.addWidget(footer)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
