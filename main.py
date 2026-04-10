import sys
import os
import json
import cv2
import numpy as np
from PIL import Image
import pytesseract
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QFileDialog, QMessageBox, QComboBox, QSpinBox, QHeaderView,
    QSplitter, QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

matplotlib.use('Qt5Agg')

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

        height, width = img.shape[:2]
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
        self.qty = self.config['default_qty']
        self.init_ui()

    def init_ui(self):
        headers = ['物资名称', '建议价', '实际购入价', '售出价']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.setRowCount(len(self.config['items']))
        for row, item_name in enumerate(self.config['items']):
            self.setItem(row, 0, QTableWidgetItem(item_name))
            self.setItem(row, 1, QTableWidgetItem('2000'))
            self.setItem(row, 2, QTableWidgetItem(''))
            self.setItem(row, 3, QTableWidgetItem(''))

        self.itemChanged.connect(self.on_item_changed)

    def on_item_changed(self, item):
        # 遍历父对象，找到RegionTab
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
        headers = ['物资名称', '购入价', '售出价', '采购数量', '单个利润', '总利润', '收益率', '标记']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

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
                    cell_item.setForeground(QColor(239, 68, 68))
                elif col == 5 and item['totalProfit'] < 0:
                    cell_item.setForeground(QColor(239, 68, 68))
                elif col == 6 and item['profitRate'] < 0:
                    cell_item.setForeground(QColor(239, 68, 68))

            if (sort_type == 'profitRate' and best_profit_rate and item['name'] == best_profit_rate['name']) or \
               (sort_type == 'totalProfit' and best_total_profit and item['name'] == best_total_profit['name']):
                for col in range(self.columnCount()):
                    self.item(row, col).setBackground(QColor(239, 68, 68, 30))

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(12, 8))
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
        ax1.set_title('总利润')
        ax1.grid(True, alpha=0.3)

        ax2 = self.figure.add_subplot(gs[0, 1])
        rates = [item['profitRate'] for item in items]
        colors2 = ['#3b82f680' if rate >= 0 else '#ef444480' for rate in rates]
        ax2.barh(names, rates, color=colors2)
        ax2.set_title('收益率 (%)')
        ax2.grid(True, alpha=0.3)

        ax3 = self.figure.add_subplot(gs[1, :])
        ax3.plot(names, profits, 'o-', color='#0ea5e9', label='总利润', linewidth=2)
        ax3.set_xlabel('物资名称')
        ax3.set_ylabel('总利润', color='#0ea5e9')
        ax3.tick_params(axis='x', rotation=45)

        ax4 = ax3.twinx()
        ax4.plot(names, rates, 's-', color='#3b82f6', label='收益率', linewidth=2)
        ax4.set_ylabel('收益率 (%)', color='#3b82f6')

        ax3.set_title('多维度对比分析')
        ax3.grid(True, alpha=0.3)

        self.canvas.draw()

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

        toolbar = QHBoxLayout()

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 10000)
        self.qty_spin.setValue(self.config['default_qty'])
        self.qty_spin.setPrefix('统一采购数量: ')
        self.qty_spin.valueChanged.connect(self.calculate)
        toolbar.addWidget(self.qty_spin)

        self.sort_rate_btn = QPushButton('按收益率排序')
        self.sort_rate_btn.clicked.connect(lambda: self.sort('profitRate'))
        toolbar.addWidget(self.sort_rate_btn)

        self.sort_profit_btn = QPushButton('按总利润排序')
        self.sort_profit_btn.clicked.connect(lambda: self.sort('totalProfit'))
        toolbar.addWidget(self.sort_profit_btn)

        self.fill_btn = QPushButton('一键填充建议价(2000)')
        self.fill_btn.clicked.connect(self.fill_default)
        toolbar.addWidget(self.fill_btn)

        self.clear_btn = QPushButton('清空所有数据')
        self.clear_btn.clicked.connect(self.clear_all)
        toolbar.addWidget(self.clear_btn)

        self.ocr_btn = QPushButton('从图片读取数据')
        self.ocr_btn.clicked.connect(self.load_image_ocr)
        toolbar.addWidget(self.ocr_btn)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Vertical)

        input_group = QGroupBox('物资录入')
        input_layout = QVBoxLayout()
        self.material_table = MaterialTable(self.region)
        input_layout.addWidget(self.material_table)
        input_group.setLayout(input_layout)
        splitter.addWidget(input_group)

        suggestion_group = QGroupBox('调度分析报告')
        suggestion_layout = QVBoxLayout()
        self.suggestion_text = QTextEdit()
        self.suggestion_text.setReadOnly(True)
        self.suggestion_text.setMaximumHeight(150)
        self.suggestion_text.setText('请输入物资价格后生成专业调度分析报告')
        suggestion_layout.addWidget(self.suggestion_text)
        suggestion_group.setLayout(suggestion_layout)
        splitter.addWidget(suggestion_group)

        result_group = QGroupBox('收益计算结果')
        result_layout = QVBoxLayout()
        self.result_table = ResultTable()
        result_layout.addWidget(self.result_table)
        result_group.setLayout(result_layout)
        splitter.addWidget(result_group)

        chart_group = QGroupBox('可视化图表')
        chart_layout = QVBoxLayout()
        self.chart_widget = ChartWidget()
        chart_layout.addWidget(self.chart_widget)
        chart_group.setLayout(chart_layout)
        splitter.addWidget(chart_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)
        splitter.setStretchFactor(3, 3)

        main_layout.addWidget(splitter)
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
            self.sort_rate_btn.setStyleSheet('background-color: #38bdf8; color: white;')
            self.sort_profit_btn.setStyleSheet('')
        else:
            self.results.sort(key=lambda x: x['totalProfit'], reverse=True)
            self.sort_rate_btn.setStyleSheet('')
            self.sort_profit_btn.setStyleSheet('background-color: #38bdf8; color: white;')

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

            suggestion = f'{self.config["name"]}调度分析报告\n\n'
            suggestion += f'本次调度分析基于当前输入价格数据，共分析了 {len(self.results)} 种物资。\n'
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
        self.setMinimumSize(1400, 900)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        header = QHBoxLayout()
        title = QLabel('终末地物资调度计算器')
        title.setFont(QFont('Arial', 20, QFont.Bold))
        title.setStyleSheet('color: #38bdf8;')
        header.addWidget(title)
        header.addStretch()
        info = QLabel('建议价格线：2000')
        info.setStyleSheet('color: #94a3b8;')
        header.addWidget(info)
        layout.addLayout(header)

        self.tab_widget = QTabWidget()
        self.valley_tab = RegionTab('valley')
        self.wuling_tab = RegionTab('wuling')
        self.tab_widget.addTab(self.valley_tab, '四号谷地')
        self.tab_widget.addTab(self.wuling_tab, '武陵')
        layout.addWidget(self.tab_widget)

        footer = QLabel('终末地物资调度计算器 | 数据仅本地计算，无上传')
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet('color: #64748b; padding: 10px;')
        layout.addWidget(footer)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
