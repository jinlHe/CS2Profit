from flask import Flask, render_template, jsonify, request
from models import db, Trade
from crawler import update_all_trades, get_inventory_value, get_total_balance, get_chrome_driver, get_buff_balance, parse_cookie_string, verify_cookies, get_igxe_balance, get_youpin_balance, get_c5_balance
import os
import json
import time
from datetime import datetime
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trades.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 确保数据库和表存在
with app.app_context():
    db.create_all()
    # 更新所有交易记录
    update_all_trades()

# 存储自定义总投入值
CUSTOM_TOTAL_INVESTMENT_FILE = 'data/custom_total_investment.json'

def load_custom_total_investment():
    if os.path.exists(CUSTOM_TOTAL_INVESTMENT_FILE):
        with open(CUSTOM_TOTAL_INVESTMENT_FILE, 'r') as f:
            data = json.load(f)
            return data.get('total_investment')
    return None

def save_custom_total_investment(value):
    os.makedirs(os.path.dirname(CUSTOM_TOTAL_INVESTMENT_FILE), exist_ok=True)
    with open(CUSTOM_TOTAL_INVESTMENT_FILE, 'w') as f:
        json.dump({'total_investment': value}, f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    try:
        print("\n=== 开始加载数据 ===")
        
        # 加载交易记录
        trades = []
        for platform in ['buff', 'youpin', 'igxe', 'c5']:
            platform_dir = os.path.join('data', platform)
            if os.path.exists(platform_dir):
                for filename in os.listdir(platform_dir):
                    if filename.endswith('_buy.csv'):
                        file_path = os.path.join(platform_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                # 提取饰品名称和URL
                                item_info = row['饰品']
                                item_name = item_info
                                item_url = None
                                
                                # 处理BUFF的HYPERLINK格式
                                if '=HYPERLINK(' in item_info:
                                    try:
                                        # 提取URL和名称
                                        url_start = item_info.find('"', item_info.find('=HYPERLINK(')) + 1
                                        url_end = item_info.find('"', url_start)
                                        name_start = item_info.find('"', url_end + 1) + 1
                                        name_end = item_info.find('"', name_start)
                                        
                                        item_url = item_info[url_start:url_end]
                                        item_name = item_info[name_start:name_end]
                                    except:
                                        pass
                                
                                trade = {
                                    'item_name': item_name,
                                    'item_url': item_url,
                                    'quantity': 1,
                                    'unit_price': float(row['价格'].replace('¥', '').strip()),
                                    'total_price': float(row['价格'].replace('¥', '').strip()),
                                    'purchase_date': row['时间'],
                                    'platform': platform.upper()
                                }
                                trades.append(trade)
                    elif filename.endswith('_sale.csv'):
                        file_path = os.path.join(platform_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                # 提取饰品名称和URL
                                item_info = row['饰品']
                                item_name = item_info
                                item_url = None
                                
                                # 处理BUFF的HYPERLINK格式
                                if '=HYPERLINK(' in item_info:
                                    try:
                                        # 提取URL和名称
                                        url_start = item_info.find('"', item_info.find('=HYPERLINK(')) + 1
                                        url_end = item_info.find('"', url_start)
                                        name_start = item_info.find('"', url_end + 1) + 1
                                        name_end = item_info.find('"', name_start)
                                        
                                        item_url = item_info[url_start:url_end]
                                        item_name = item_info[name_start:name_end]
                                    except:
                                        pass
                                
                                trade = {
                                    'item_name': item_name,
                                    'item_url': item_url,
                                    'quantity': 1,
                                    'unit_price': float(row['价格'].replace('¥', '').strip()),
                                    'total_price': float(row['价格'].replace('¥', '').strip()),
                                    'sale_price': float(row['价格'].replace('¥', '').strip()),
                                    'sale_date': row['时间'],
                                    'platform': platform.upper()
                                }
                                trades.append(trade)
        
        # 合并所有交易记录
        all_trades = trades
        print(f"合并前总交易记录数：{len(all_trades)}条")
        
        # 合并相同商品的交易记录
        merged_trades = merge_trades(all_trades)
        print(f"合并后交易记录数：{len(merged_trades)}条")
        
        # 将交易记录分为持有和成交记录
        holdings = []
        completed_trades = []
        
        for trade in merged_trades:
            try:
                # 确保所有必要的字段都存在
                if not all(key in trade for key in ['item_name', 'quantity', 'unit_price', 'total_price', 'platform']):
                    print(f"跳过不完整的交易记录：{trade}")
                    continue
                
                if trade.get('purchase_date') and not trade.get('sale_date'):
                    # 只有买入日期，没有卖出日期的商品加入持有列表
                    holdings.append(trade)
                elif trade.get('purchase_date') and trade.get('sale_date'):
                    # 既有买入日期，又有卖出日期的商品加入成交记录列表
                    completed_trades.append(trade)
            except Exception as e:
                print(f"处理交易记录时出错：{str(e)}")
                continue
        
        # 读取自定义总投入
        custom_total_investment = 0
        if os.path.exists('data/custom_total_investment.json'):
            try:
                with open('data/custom_total_investment.json', 'r', encoding='utf-8') as f:
                    custom_total_investment = json.load(f).get('total_investment', 0)
                print(f"成功加载自定义总投入：{custom_total_investment}")
            except Exception as e:
                print(f"读取自定义总投入失败：{str(e)}")
        
        # 读取库存价值
        inventory_value = 0
        if os.path.exists('data/inventory_value.json'):
            try:
                with open('data/inventory_value.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    inventory_value = data.get('value', 0)
                print(f"成功加载库存价值：{inventory_value}")
            except Exception as e:
                print(f"读取库存价值失败：{str(e)}")
        
        # 读取账户余额
        balance_data = {
            'buff_balance': 0.0,
            'youpin_balance': 0.0,
            'igxe_balance': 0.0,
            'c5_balance': 0.0,
            'total_balance': 0.0
        }
        if os.path.exists('data/balance.json'):
            try:
                with open('data/balance.json', 'r', encoding='utf-8') as f:
                    balance_data = json.load(f)
                print(f"成功加载账户余额：{balance_data}")
            except Exception as e:
                print(f"读取账户余额失败：{str(e)}")
        
        # 计算总投入（使用自定义总投入或交易记录中的总投入）
        total_investment = custom_total_investment if custom_total_investment > 0 else sum(trade.get('total_price', 0) for trade in holdings)
        print(f"计算得到的总投入：{total_investment}")
        
        # 计算总价值（账户总余额 + 库存价值）
        total_value = float(balance_data.get('total_balance', 0))*0.99 + float(inventory_value)*0.965
        print(f"计算得到的总价值：{total_value}")
        
        # 计算总利润
        total_profit = total_value - total_investment
        print(f"计算得到的总利润：{total_profit}")
        
        # 计算利润率
        profit_ratio = (total_profit / total_investment * 100) if total_investment > 0 else 0
        print(f"计算得到的利润率：{profit_ratio}%")
        
        # 计算BUFF交易统计
        buff_total_buy = sum(trade.get('total_price', 0) for trade in holdings if trade.get('platform') == 'BUFF')
        buff_total_sale = sum(trade.get('sale_price', 0) for trade in completed_trades if trade.get('platform') == 'BUFF')
        buff_net_profit = buff_total_sale - buff_total_buy
        print(f"BUFF交易统计 - 总买入：{buff_total_buy}，总卖出：{buff_total_sale}，净收益：{buff_net_profit}")
        
        # 准备返回数据
        response_data = {
            'total_investment': round(total_investment, 2),
            'inventory_value': round(inventory_value, 2),
            'total_value': round(total_value, 2),
            'total_profit': round(total_profit, 2),
            'profit_ratio': round(profit_ratio, 2),
            'buff_balance': round(float(balance_data.get('buff_balance', 0)), 2),
            'youpin_balance': round(float(balance_data.get('youpin_balance', 0)), 2),
            'igxe_balance': round(float(balance_data.get('igxe_balance', 0)), 2),
            'c5_balance': round(float(balance_data.get('c5_balance', 0)), 2),
            'total_balance': round(float(balance_data.get('total_balance', 0)), 2),
            'buff_total_buy': round(buff_total_buy, 2),
            'buff_total_sale': round(buff_total_sale, 2),
            'buff_net_profit': round(buff_net_profit, 2),
            'holdings': holdings,
            'completed_trades': completed_trades
        }
        
        print("=== 数据加载完成 ===")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"加载数据时发生错误：{str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_total_investment', methods=['POST'])
def update_total_investment():
    data = request.get_json()
    new_value = data.get('total_investment')
    if new_value is not None:
        save_custom_total_investment(new_value)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/update_inventory_value', methods=['POST'])
def update_inventory_value():
    try:
        inventory_value = get_inventory_value()
        return jsonify({'success': True, 'inventory_value': inventory_value})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_balance', methods=['POST'])
def update_balance():
    """更新指定平台的余额"""
    try:
        platform = request.args.get('platform', 'all')
        print(f"开始更新{platform}余额...")
        
        # 读取现有余额数据
        balance_data = {}
        if os.path.exists('data/balance.json'):
            with open('data/balance.json', 'r') as f:
                balance_data = json.load(f)
        
        # C5使用API获取余额，不需要浏览器
        if platform in ['c5', 'all']:
            print("正在更新C5余额...")
            c5_balance = get_c5_balance()  # 直接调用API函数
            balance_data['c5_balance'] = c5_balance
            print(f"C5余额更新成功: {c5_balance}")
            
            # 如果只更新C5余额，直接返回结果
            if platform == 'c5':
                # 更新总余额
                balance_data['total_balance'] = balance_data.get('buff_balance', 0.0) + balance_data.get('youpin_balance', 0.0) + balance_data.get('igxe_balance', 0.0) + c5_balance
                
                # 保存更新后的余额数据
                with open('data/balance.json', 'w') as f:
                    json.dump(balance_data, f)
                    
                return jsonify(balance_data)
        
        # 其他平台仍然使用浏览器获取
        # 初始化Chrome浏览器
        driver = get_chrome_driver()
        
        try:
            if platform in ['buff', 'all']:
                print("正在更新BUFF余额...")
                driver.get("https://buff.163.com/?game=csgo")
                time.sleep(1)  # 等待页面加载
                # 加载BUFF cookies
                if os.path.exists('data/cookie/buff_cookies.json'):
                    with open('data/cookie/buff_cookies.json', 'r') as f:
                        cookies = json.load(f)
                    for cookie in cookies:
                        driver.add_cookie(cookie)
                
                # 获取BUFF余额
                buff_balance = get_buff_balance(driver)
                balance_data['buff_balance'] = buff_balance
                print(f"BUFF余额更新成功: {buff_balance}")

            if platform in ['igxe', 'all']:
                print("正在更新IGXE余额...")
                driver.get("https://www.igxe.cn/")
                time.sleep(1)  # 等待页面加载
                # 加载IGXE cookies
                if os.path.exists('data/cookie/igxe_cookies.json'):
                    with open('data/cookie/igxe_cookies.json', 'r') as f:
                        cookies = json.load(f)
                    for cookie in cookies:
                        driver.add_cookie(cookie)
                
                # 获取IGXE余额
                igxe_balance = get_igxe_balance(driver)
                balance_data['igxe_balance'] = igxe_balance
                print(f"IGXE余额更新成功: {igxe_balance}")

            if platform in ['youpin', 'all']:
                print("正在更新悠悠有品余额...")
                driver.get("https://www.youpin898.com/")
                time.sleep(1)  # 等待页面加载
                # 加载悠悠有品 cookies
                if os.path.exists('data/cookie/youpin_cookies.json'):
                    with open('data/cookie/youpin_cookies.json', 'r') as f:
                        cookies = json.load(f)
                    for cookie in cookies:
                        driver.add_cookie(cookie)
                
                # 获取悠悠有品余额
                youpin_balance = get_youpin_balance(driver)
                balance_data['youpin_balance'] = youpin_balance
                print(f"悠悠有品余额更新成功: {youpin_balance}")

            # 更新总余额
            balance_data['total_balance'] = balance_data.get('buff_balance', 0.0) + balance_data.get('youpin_balance', 0.0) + balance_data.get('igxe_balance', 0.0) + balance_data.get('c5_balance', 0.0)
            
            # 保存更新后的余额数据
            with open('data/balance.json', 'w') as f:
                json.dump(balance_data, f)
            
            return jsonify(balance_data)
            
        finally:
            if driver:
                driver.quit()
                
    except Exception as e:
        print(f"更新余额失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

def merge_trades(trades):
    """合并相同商品的交易记录"""
    merged_trades = {}
    
    for trade in trades:
        item_name = trade['item_name']
        if item_name not in merged_trades:
            merged_trades[item_name] = {
                'item_name': item_name,
                'item_url': trade.get('item_url'),
                'quantity': 0,
                'unit_price': 0,
                'total_price': 0,
                'purchase_date': None,
                'sale_date': None,
                'sale_price': 0,
                'platform': trade['platform']
            }
        
        merged = merged_trades[item_name]
        
        # 更新数量和总价
        merged['quantity'] += trade.get('quantity', 1)
        merged['total_price'] += trade.get('total_price', 0)
        
        # 更新买入日期
        if trade.get('purchase_date'):
            if not merged['purchase_date'] or trade['purchase_date'] < merged['purchase_date']:
                merged['purchase_date'] = trade['purchase_date']
                merged['unit_price'] = trade.get('unit_price', 0)
        
        # 更新卖出日期和价格
        if trade.get('sale_date'):
            if not merged['sale_date'] or trade['sale_date'] > merged['sale_date']:
                merged['sale_date'] = trade['sale_date']
                merged['sale_price'] = trade.get('sale_price', 0)
    
    # 计算平均单价
    for trade in merged_trades.values():
        if trade['quantity'] > 0 and trade['total_price'] > 0:
            trade['unit_price'] = trade['total_price'] / trade['quantity']
    
    return list(merged_trades.values())

if __name__ == '__main__':
    app.run(debug=True) 