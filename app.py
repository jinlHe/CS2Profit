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
        
        # 平台名称映射
        platform_display_names = {
            'buff': 'BUFF',
            'youyou': '悠悠',
            'igxe': 'IGXE',
            'c5': 'C5'
        }
        
        # 处理所有平台的交易记录
        for platform in ['buff', 'youyou', 'igxe', 'c5']:
            platform_dir = os.path.join('data', platform)
            print(f"\n检查平台目录: {platform_dir}")
            
            if os.path.exists(platform_dir):
                print(f"找到{platform}平台目录")
                for filename in os.listdir(platform_dir):
                    print(f"\n处理文件: {filename}")
                    
                    # 检查是否是CSV文件
                    if not filename.endswith('.csv'):
                        print(f"跳过非CSV文件: {filename}")
                        continue
                        
                    # 判断是买入还是卖出记录
                    is_buy = 'buy' in filename.lower()
                    is_sale = 'sale' in filename.lower()
                    
                    if not (is_buy or is_sale):
                        print(f"文件名中未找到buy或sale标记: {filename}")
                        continue
                    
                    print(f"文件类型: {'买入' if is_buy else '卖出'}")
                    
                    file_path = os.path.join(platform_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            print(f"CSV列名: {reader.fieldnames}")
                            
                            row_count = 0
                            for row in reader:
                                row_count += 1
                                print(f"\n处理第 {row_count} 行数据:")
                                print(f"原始数据: {row}")
                                
                                # 根据不同平台处理数据
                                if platform == 'buff':
                                    # BUFF特有的HYPERLINK格式处理
                                    item_info = row.get('饰品', '')
                                    item_name = item_info
                                    item_url = None
                                    
                                    if '=HYPERLINK(' in item_info:
                                        try:
                                            url_start = item_info.find('"', item_info.find('=HYPERLINK(')) + 1
                                            url_end = item_info.find('"', url_start)
                                            name_start = item_info.find('"', url_end + 1) + 1
                                            name_end = item_info.find('"', name_start)
                                            
                                            item_url = item_info[url_start:url_end]
                                            item_name = item_info[name_start:name_end]
                                        except:
                                            pass
                                    
                                    # 处理价格
                                    price_str = row.get('价格', '0')
                                    if isinstance(price_str, str):
                                        price_str = price_str.replace('¥', '').replace('￥', '').strip()
                                    try:
                                        price = float(price_str)
                                    except ValueError:
                                        print(f"警告：无效的价格格式 {price_str}，跳过该记录")
                                        continue
                                    
                                    # 处理时间
                                    time_str = row.get('时间', '')
                                    
                                elif platform == 'youyou':
                                    # 悠悠有品的数据处理
                                    item_name = row.get('\ufeff饰品', '').strip()
                                    if not item_name:
                                        print(f"警告：发现空的商品名称，跳过该记录")
                                        continue
                                    
                                    # 处理价格
                                    price_str = row.get('价格', '0')
                                    try:
                                        price = float(price_str)
                                    except ValueError:
                                        print(f"警告：无效的价格格式 {price_str}，跳过该记录")
                                        continue
                                    
                                    # 处理时间
                                    time_str = row.get('时间', '')
                                    item_url = None

                                    
                                else:
                                    # 其他平台的数据格式
                                    item_name = row.get('name', '')
                                    price_str = row.get('price', '0')
                                    if isinstance(price_str, str):
                                        price_str = price_str.replace('¥', '').replace('￥', '').strip()
                                    try:
                                        price = float(price_str)
                                    except ValueError:
                                        print(f"警告：无效的价格格式 {price_str}，跳过该记录")
                                        continue
                                    time_str = row.get('time', '')
                                
                                print(f"处理后的物品名称: {item_name}")
                                print(f"处理后的价格: {price}")
                                print(f"处理后的时间: {time_str}")
                                
                                # 创建交易记录
                                trade = {
                                    'item_name': item_name,
                                    'item_url': item_url,
                                    'quantity': 1,
                                    'unit_price': price,
                                    'total_price': price,
                                    'platform': platform_display_names[platform]
                                }
                                
                                # 根据记录类型添加不同的字段
                                if is_buy:
                                    trade['purchase_date'] = time_str
                                    print(f"创建的买入交易记录: {trade}")
                                elif is_sale:
                                    trade['sale_date'] = time_str
                                    trade['sale_price'] = price
                                    print(f"创建的卖出交易记录: {trade}")
                                
                                
                                trades.append(trade)
                                
                            print(f"\n文件 {filename} 处理完成，共处理 {row_count} 行数据")
                                
                    except Exception as e:
                        print(f"处理{platform}平台{filename}文件时出错: {str(e)}")
                        print(f"错误详情: ", e.__class__.__name__)
                        import traceback
                        print(traceback.format_exc())
                        continue
            else:
                print(f"未找到{platform}平台目录")
        
        print(f"\n=== 所有平台数据加载完成 ===")
        print(f"总共加载了 {len(trades)} 条交易记录")
        
        # 合并所有交易记录
        all_trades = trades
        print(f"合并前总交易记录数：{len(all_trades)}条")
        
        # 按平台统计记录数
        platform_counts = {}
        for trade in all_trades:
            platform = trade['platform']
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        print("各平台记录数:")
        for platform, count in platform_counts.items():
            print(f"{platform}: {count}条")
        
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
                
                if 'purchase_date' in trade and 'sale_date' in trade:
                    # 既有买入日期又有卖出日期的记录加入成交记录
                    print(f"添加到成交记录: {trade}")
                    completed_trades.append(trade)
                elif 'purchase_date' in trade:
                    # 只有买入日期的记录加入持有记录
                    print(f"添加到持有记录: {trade}")
                    holdings.append(trade)
                elif 'sale_date' in trade:
                    # 只有卖出日期的记录也加入成交记录
                    print(f"添加到成交记录（仅卖出）: {trade}")
                    # 设置purchase_date为None，以便前端可以区分处理
                    trade['purchase_date'] = None
                    completed_trades.append(trade)
                else:
                    print(f"未知类型的记录: {trade}")
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
        # 确保所有余额都是有效的数字
        valid_balances = [float(balance) for balance in [
            balance_data.get('buff_balance', 0.0),
            balance_data.get('youpin_balance', 0.0),
            balance_data.get('igxe_balance', 0.0),
            balance_data.get('c5_balance', 0.0)
        ] if balance is not None]
        
        total_balance = sum(valid_balances)
        total_value = total_balance * 0.99 + float(inventory_value) * 0.965
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
            'buff_balance': round(float(balance_data.get('buff_balance', 0.0) or 0.0), 2),
            'youpin_balance': round(float(balance_data.get('youpin_balance', 0.0) or 0.0), 2),
            'igxe_balance': round(float(balance_data.get('igxe_balance', 0.0) or 0.0), 2),
            'c5_balance': round(float(balance_data.get('c5_balance', 0.0) or 0.0), 2),
            'total_balance': round(total_balance, 2),
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
                print("读取到的现有余额数据:", balance_data)
        
        # 保存原有余额
        original_balances = {
            'buff_balance': balance_data.get('buff_balance'),
            'youpin_balance': balance_data.get('youpin_balance'),
            'igxe_balance': balance_data.get('igxe_balance'),
            'c5_balance': balance_data.get('c5_balance')
        }
        
        # 添加更新状态标记
        update_status = {
            'buff_balance': False,
            'youpin_balance': False,
            'igxe_balance': False,
            'c5_balance': False
        }
        
        # C5使用API获取余额，不需要浏览器
        if platform in ['c5', 'all']:
            print("正在更新C5余额...")
            try:
                c5_balance = get_c5_balance()  # 直接调用API函数
                print(f"C5余额获取结果: {c5_balance}")
                if c5_balance is not None:  # 只有在成功获取余额时才更新
                    balance_data['c5_balance'] = c5_balance
                    update_status['c5_balance'] = True
                    print(f"C5余额更新成功: {c5_balance}")
                else:
                    print("C5余额获取失败，保持原有余额")
                    balance_data['c5_balance'] = original_balances['c5_balance']  # 保持原有余额
            except Exception as e:
                print(f"C5余额更新失败: {str(e)}")
                balance_data['c5_balance'] = original_balances['c5_balance']  # 保持原有余额
            
            # 如果只更新C5余额，直接返回结果
            if platform == 'c5':
                # 更新总余额
                balance_data['total_balance'] = sum(
                    balance for balance in [
                        balance_data.get('buff_balance', 0.0),
                        balance_data.get('youpin_balance', 0.0),
                        balance_data.get('igxe_balance', 0.0),
                        balance_data.get('c5_balance', 0.0)
                    ] if balance is not None
                )
                
                print("准备返回的C5余额数据:", balance_data)
                # 保存更新后的余额数据
                with open('data/balance.json', 'w') as f:
                    json.dump(balance_data, f)
                
                # 添加更新状态到返回数据
                balance_data['update_status'] = update_status
                return jsonify(balance_data)
        
        # 其他平台仍然使用浏览器获取
        # 初始化Chrome浏览器
        driver = get_chrome_driver()
        
        try:
            if platform in ['buff', 'all']:
                print("正在更新BUFF余额...")
                try:
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
                    print(f"BUFF余额获取结果: {buff_balance}")
                    if buff_balance is not None:  # 只有在成功获取余额时才更新
                        balance_data['buff_balance'] = buff_balance
                        update_status['buff_balance'] = True
                        print(f"BUFF余额更新成功: {buff_balance}")
                    else:
                        print("BUFF余额获取失败，保持原有余额")
                        balance_data['buff_balance'] = original_balances['buff_balance']  # 保持原有余额
                except Exception as e:
                    print(f"BUFF余额更新失败: {str(e)}")
                    balance_data['buff_balance'] = original_balances['buff_balance']  # 保持原有余额

            if platform in ['igxe', 'all']:
                print("正在更新IGXE余额...")
                try:
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
                    print(f"IGXE余额获取结果: {igxe_balance}")
                    if igxe_balance is not None:  # 只有在成功获取余额时才更新
                        balance_data['igxe_balance'] = igxe_balance
                        update_status['igxe_balance'] = True
                        print(f"IGXE余额更新成功: {igxe_balance}")
                    else:
                        print("IGXE余额获取失败，保持原有余额")
                        balance_data['igxe_balance'] = original_balances['igxe_balance']  # 保持原有余额
                except Exception as e:
                    print(f"IGXE余额更新失败: {str(e)}")
                    balance_data['igxe_balance'] = original_balances['igxe_balance']  # 保持原有余额

            if platform in ['youpin', 'all']:
                print("正在更新悠悠有品余额...")
                try:
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
                    print(f"悠悠有品余额获取结果: {youpin_balance}")
                    if youpin_balance is not None:  # 只有在成功获取余额时才更新
                        balance_data['youpin_balance'] = youpin_balance
                        update_status['youpin_balance'] = True
                        print(f"悠悠有品余额更新成功: {youpin_balance}")
                    else:
                        print("悠悠有品余额获取失败，保持原有余额")
                        balance_data['youpin_balance'] = original_balances['youpin_balance']  # 保持原有余额
                except Exception as e:
                    print(f"悠悠有品余额更新失败: {str(e)}")
                    balance_data['youpin_balance'] = original_balances['youpin_balance']  # 保持原有余额

            # 更新总余额
            balance_data['total_balance'] = sum(
                balance for balance in [
                    balance_data.get('buff_balance', 0.0),
                    balance_data.get('youpin_balance', 0.0),
                    balance_data.get('igxe_balance', 0.0),
                    balance_data.get('c5_balance', 0.0)
                ] if balance is not None
            )
            
            print("准备返回的最终余额数据:", balance_data)
            # 保存更新后的余额数据
            with open('data/balance.json', 'w') as f:
                json.dump(balance_data, f)
            
            # 添加更新状态到返回数据
            balance_data['update_status'] = update_status
            return jsonify(balance_data)
            
        finally:
            if driver:
                driver.quit()
                
    except Exception as e:
        print(f"更新余额失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

def standardize_date(date_str):
    """
    统一日期格式为 YYYY-MM-DD HH:MM:SS
    """
    try:
        # 处理悠悠有品格式 (2025.02.2114:02:00)
        if '.' in date_str and len(date_str) == 19:
            date_obj = datetime.strptime(date_str, '%Y.%m.%d%H:%M:%S')
            return date_obj.strftime('%Y-%m-%d %H:%M:%S')
        # 处理BUFF格式 (已经是标准格式)
        else:
            return date_str
    except Exception as e:
        print(f"日期格式转换失败: {date_str}, 错误: {str(e)}")
        return date_str

def get_wear_level(name):
    """
    从商品名称中提取磨损等级
    返回: (磨损等级, 剩余名称)
    """
    wear_levels = {
        '崭新出厂': ['崭新出厂', '崭新'],
        '略有磨损': ['略有磨损', '略磨'],
        '久经沙场': ['久经沙场', '久经'],
        '破损不堪': ['破损不堪', '破损'],
        '战痕累累': ['战痕累累', '战痕']
    }
    
    # 检查是否是探员或特殊角色
    agent_features = [
        '专业人士', '游击队', '海豹部队', '军刀', 'FBI特工',
        '上校', '中队长', '海军上尉', '指挥官', '特种部队',
        '达里尔爵士'
    ]
    
    # 检查是否是特殊物品
    special_items = ['印花', '音乐盒', '挂件', '胸章']
    
    # 如果是探员或特殊物品，直接返回None和原始名称
    if any(agent in name for agent in agent_features) or any(item in name for item in special_items):
        return None, name
    
    # 检查磨损等级
    for level, keywords in wear_levels.items():
        for keyword in keywords:
            if keyword in name:
                # 移除磨损等级和括号
                remaining = name.replace(keyword, '').replace('(', '').replace(')', '').replace('（', '').replace('）', '')
                return level, remaining.strip()
    
    return None, name

def calculate_similarity(str1, str2):
    """
    计算两个字符串的相似度
    使用简单的字符匹配算法
    """
    if not str1 or not str2:
        return 0
    
    # 将字符串转换为字符集合
    set1 = set(str1)
    set2 = set(str2)
    
    # 计算交集和并集
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    # 计算相似度
    return intersection / union if union > 0 else 0

def standardize_item_name(name):
    """
    标准化商品名称，移除特殊字符和多余空格
    """
    if not name:
        return ""
    
    # 移除特殊字符，只保留中文、英文和数字
    name = ''.join(char for char in name if '\u4e00' <= char <= '\u9fff' or char.isalnum())
    
    # 移除多余的空格
    name = ' '.join(name.split())
    
    return name

def merge_trades(trades):
    """
    合并交易记录，按照商品名称进行合并，支持跨平台交易
    """
    merged = {}
    print("\n=== 开始合并交易记录 ===")
    
    for trade in trades:
        # 确保必要字段存在
        if not all(key in trade for key in ['item_name', 'platform', 'unit_price']):
            print(f"跳过不完整的交易记录: {trade}")
            continue
            
        # 获取磨损等级和剩余名称
        wear_level, remaining_name = get_wear_level(trade['item_name'])
        standardized_name = standardize_item_name(remaining_name)
        
        print(f"\n处理商品: {trade['item_name']}")
        print(f"磨损等级: {wear_level}")
        print(f"标准化名称: {standardized_name}")
        
        # 标准化日期格式
        if 'purchase_date' in trade:
            trade['purchase_date'] = standardize_date(trade['purchase_date'])
        if 'sale_date' in trade:
            trade['sale_date'] = standardize_date(trade['sale_date'])
        
        # 查找匹配的记录
        matched_key = None
        for key in merged.keys():
            existing_wear_level, existing_remaining = get_wear_level(key)
            existing_standardized = standardize_item_name(existing_remaining)
            
            # 检查磨损等级是否匹配
            wear_match = True  # 默认匹配
            if wear_level is not None and existing_wear_level is not None:
                # 只有当两个记录都有磨损等级时才进行匹配
                wear_match = (wear_level == existing_wear_level) or \
                           any(w in wear_level for w in existing_wear_level.split()) or \
                           any(w in existing_wear_level for w in wear_level.split())
            
            # 检查名称相似度
            name_similarity = calculate_similarity(standardized_name, existing_standardized)
            
            if wear_match and name_similarity >= 0.6:
                matched_key = key
                print(f"找到匹配记录: {key}")
                print(f"磨损等级匹配: {wear_match}")
                print(f"名称相似度: {name_similarity}")
                break
        
        if matched_key is None:
            # 如果是新商品，直接添加
            merged[trade['item_name']] = trade.copy()
            merged[trade['item_name']]['quantity'] = 1
            merged[trade['item_name']]['total_price'] = trade['unit_price']
            merged[trade['item_name']]['platforms'] = {trade['platform']}
            print(f"新增商品记录: {merged[trade['item_name']]}")
        else:
            # 如果已存在，更新记录
            existing = merged[matched_key]
            print(f"已存在的记录: {existing}")
            
            # 如果当前记录是卖出记录
            if 'sale_date' in trade:
                print("处理卖出记录")
                if 'sale_date' not in existing:
                    existing['sale_date'] = trade['sale_date']
                    existing['sale_price'] = trade['unit_price']
                    existing['platforms'].add(trade['platform'])
                    print(f"添加卖出信息: {existing}")
                else:
                    # 如果已有卖出记录，保留价格较高的记录
                    if trade['unit_price'] > existing['sale_price']:
                        existing['sale_date'] = trade['sale_date']
                        existing['sale_price'] = trade['unit_price']
                        existing['platforms'].add(trade['platform'])
                        print(f"更新为更高的卖出价格: {existing}")
            
            # 如果当前记录是买入记录
            if 'purchase_date' in trade:
                print("处理买入记录")
                if 'purchase_date' not in existing:
                    existing['purchase_date'] = trade['purchase_date']
                    existing['unit_price'] = trade['unit_price']
                    existing['total_price'] = trade['total_price']
                    existing['platforms'].add(trade['platform'])
                    print(f"添加买入信息: {existing}")
                else:
                    # 如果已有买入记录，保留价格较低的记录
                    if trade['unit_price'] < existing['unit_price']:
                        existing['purchase_date'] = trade['purchase_date']
                        existing['unit_price'] = trade['unit_price']
                        existing['total_price'] = trade['total_price']
                        existing['platforms'].add(trade['platform'])
                        print(f"更新为更低的买入价格: {existing}")
    
    # 转换回列表，并处理平台显示
    result = []
    print("\n=== 处理最终结果 ===")
    for key, trade in merged.items():
        # 将平台集合转换为排序后的字符串
        platforms = sorted(list(trade['platforms']))
        trade['platform'] = '/'.join(platforms)
        trade.pop('platforms', None)
        
        # 检查是否是完整的交易记录（同时有买入和卖出）
        if 'purchase_date' in trade and 'sale_date' in trade:
            print(f"找到完整的交易记录: {trade}")
            # 计算利润
            trade['profit'] = trade['sale_price'] - trade['unit_price']
            trade['profit_ratio'] = (trade['profit'] / trade['unit_price'] * 100) if trade['unit_price'] > 0 else 0
        elif 'purchase_date' in trade:
            print(f"找到仅买入记录: {trade}")
        elif 'sale_date' in trade:
            print(f"找到仅卖出记录: {trade}")
            
        result.append(trade)
    
    print(f"\n合并后的记录总数: {len(result)}")
    return result

if __name__ == '__main__':
    app.run(debug=True) 