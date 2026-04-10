from flask import Flask, render_template, request, jsonify
import json
import cv2
import numpy as np
import pytesseract

app = Flask(__name__)

# 物资数据
data = {
    'valley': {
        'name': '四号谷地',
        'default_qty': 210,
        'item_list': [
            '锚点厨具货组',
            '悬空腕兽骨殖货组',
            '巫术矿钻货组',
            '天使罐头货组',
            '谷地水培肉货组',
            '团结牌口服液货组',
            '塞什卡钟石货组',
            '漂石树幼苗货组',
            '星体晶块货组',
            '警戒者矿镐货组',
            '边角料积木货组'
        ]
    },
    'wuling': {
        'name': '武陵',
        'default_qty': 50,
        'item_list': [
            '岳研避瘴茶货组',
            '武侠电影货组',
            '冬虫夏笋货组',
            '武陵冻梨货组'
        ]
    }
}

@app.route('/')
def index():
    return render_template('index.html', data=data)

@app.route('/calculate', methods=['POST'])
def calculate():
    region = request.json.get('region')
    qty = request.json.get('qty')
    prices = request.json.get('prices', {})
    
    results = []
    region_data = data.get(region, {})
    
    for item in region_data.get('item_list', []):
        item_prices = prices.get(item, {})
        buy_price = float(item_prices.get('buy', 2000))
        sell_price = float(item_prices.get('sell', 2000))
        
        single_profit = sell_price - buy_price
        total_profit = single_profit * qty
        profit_rate = (single_profit / buy_price * 100) if buy_price > 0 else 0
        
        results.append({
            'name': item,
            'buyPrice': buy_price,
            'sellPrice': sell_price,
            'qty': qty,
            'singleProfit': single_profit,
            'totalProfit': total_profit,
            'profitRate': profit_rate
        })
    
    # 计算最优项
    best_profit_rate = max(results, key=lambda x: x['profitRate']) if results else None
    best_total_profit = max(results, key=lambda x: x['totalProfit']) if results else None
    
    # 生成建议
    suggestion = generate_suggestion(region, results, best_profit_rate, best_total_profit)
    
    return jsonify({
        'results': results,
        'bestProfitRate': best_profit_rate,
        'bestTotalProfit': best_total_profit,
        'suggestion': suggestion
    })

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        import base64
        from io import BytesIO
        from PIL import Image as PILImage
        
        # 获取图片数据
        image_data = request.json.get('image')
        region = request.json.get('region')
        
        if not image_data or not region:
            return jsonify({'error': '缺少参数'}), 400
        
        # 解码base64图片
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'error': '无法读取图片'}), 400
        
        # 预处理图片
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR识别
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        data_result = pytesseract.image_to_data(binary, config=custom_config, output_type=pytesseract.Output.DICT)
        
        # 提取数字
        numbers = []
        for i in range(len(data_result['text'])):
            text = data_result['text'][i].strip()
            if text and text.isdigit():
                numbers.append({
                    'value': int(text),
                    'x': data_result['left'][i],
                    'y': data_result['top'][i],
                    'width': data_result['width'][i],
                    'height': data_result['height'][i],
                    'conf': data_result['conf'][i]
                })
        
        # 过滤和排序
        numbers = [n for n in numbers if n['conf'] > 50 and len(str(n['value'])) >= 3]
        numbers.sort(key=lambda x: (x['y'] // 100, x['x']))
        
        # 匹配物资
        item_list = data[region]['item_list']
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
        
        return jsonify({'prices': extracted_prices})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_suggestion(region, results, best_profit_rate, best_total_profit):
    if not results:
        return '请输入物资价格后生成专业调度分析报告'
    
    region_name = data[region]['name']
    suggestion = f'{region_name}调度分析报告\n\n'
    
    # 计算平均收益率和总利润
    avg_profit_rate = sum(item['profitRate'] for item in results) / len(results)
    total_profit = sum(item['totalProfit'] for item in results)
    
    suggestion += f'本次调度分析基于当前输入价格数据，共分析了 {len(results)} 种物资。\n'
    suggestion += f'平均收益率：{avg_profit_rate:.1f}%，总利润：{total_profit:.0f}。\n\n'
    
    if best_profit_rate:
        suggestion += f'【最优收益率】{best_profit_rate["name"]}，收益率：{best_profit_rate["profitRate"]:.1f}%\n'
    
    if best_total_profit:
        suggestion += f'【最高总利润】{best_total_profit["name"]}，总利润：{best_total_profit["totalProfit"]:.0f}\n\n'
    
    # 分析亏损项目
    loss_items = [item for item in results if item['profitRate'] < 0]
    if loss_items:
        suggestion += f'【需要注意】以下 {len(loss_items)} 种物资收益率为负，建议谨慎采购：\n'
        for item in loss_items:
            suggestion += f'- {item["name"]}：{item["profitRate"]:.1f}%\n'
    else:
        suggestion += '【良好】所有物资均有正收益，可根据需求合理安排采购。\n'
    
    return suggestion

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
