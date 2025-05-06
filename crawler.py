from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from models import db, Trade
import time
from datetime import datetime
import pandas as pd
import os
import sqlite3
import random
import re
import csv
import json
import sys
import requests

def get_chrome_driver():
    """获取配置好的Chrome浏览器实例"""
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    # options.add_argument('--headless')  # 暂时注释掉无头模式，方便调试
    
    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"初始化Chrome浏览器失败：{str(e)}")
        print("请确保：")
        print("1. Chrome浏览器已安装")
        print("2. ChromeDriver版本与Chrome浏览器版本匹配")
        print("3. ChromeDriver文件未被损坏")
        raise

def generate_random_price(base_price, min_ratio=0.8, max_ratio=1.2):
    """生成随机价格"""
    return round(base_price * random.uniform(min_ratio, max_ratio), 2)

def generate_random_date(start_date, end_date):
    """生成随机日期"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + pd.Timedelta(days=random_days)).strftime('%Y-%m-%d')

def clean_item_name(name):
    """清理物品名称，移除超链接和特殊字符"""
    # 移除超链接部分
    name = re.sub(r'=HYPERLINK\(".*?",\s*"', '', name)
    # 移除末尾的引号和括号
    name = name.rstrip('")')
    # 移除多余的双引号
    name = name.replace('""', '"')
    # 移除首尾的引号
    name = name.strip('"')
    return name

def clean_price(price):
    """清理价格，移除货币符号并转换为浮点数"""
    return float(price.replace('¥', '').strip())

def update_buff_trades():
    """更新BUFF交易记录"""
    try:
        # 读取购买记录
        buy_records = {}
        buy_file_path = 'data/buff/U1101693104_20200503_20250503_buy.csv'
        if os.path.exists(buy_file_path):
            with open(buy_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 获取基础物品名称（移除颜色信息）
                    base_name = clean_item_name(row['饰品']).split(' (')[0]
                    price = clean_price(row['价格'])
                    trade_date = datetime.strptime(row['时间'], '%Y-%m-%d %H:%M:%S')
                    
                    if base_name not in buy_records:
                        buy_records[base_name] = {
                            'quantity': 1,
                            'total_price': price,
                            'trade_date': trade_date
                        }
                    else:
                        buy_records[base_name]['quantity'] += 1
                        buy_records[base_name]['total_price'] += price
                        # 更新为最早的交易日期
                        if trade_date < buy_records[base_name]['trade_date']:
                            buy_records[base_name]['trade_date'] = trade_date

        # 读取卖出记录
        sell_records = {}
        sell_file_path = 'data/buff/U1101693104_20200503_20250503_sale.csv'
        if os.path.exists(sell_file_path):
            with open(sell_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 获取基础物品名称（移除颜色信息）
                    base_name = clean_item_name(row['饰品']).split(' (')[0]
                    price = clean_price(row['价格'])
                    trade_date = datetime.strptime(row['时间'], '%Y-%m-%d %H:%M:%S')
                    
                    if base_name not in sell_records:
                        sell_records[base_name] = {
                            'quantity': 1,
                            'total_price': price,
                            'trade_date': trade_date
                        }
                    else:
                        sell_records[base_name]['quantity'] += 1
                        sell_records[base_name]['total_price'] += price
                        # 更新为最早的交易日期
                        if trade_date < sell_records[base_name]['trade_date']:
                            sell_records[base_name]['trade_date'] = trade_date

        # 将BUFF交易记录整合到现有交易记录中
        for base_name, record in buy_records.items():
            # 计算平均单价
            avg_price = record['total_price'] / record['quantity']
            
            # 查找是否已存在相同物品的交易记录
            existing_trade = Trade.query.filter_by(item_name=base_name).first()
            if existing_trade:
                # 更新现有记录
                existing_trade.quantity = record['quantity']
                existing_trade.unit_price = avg_price
                existing_trade.total_price = record['total_price']
                existing_trade.purchase_date = record['trade_date'].date()
                existing_trade.platform = 'BUFF'
                existing_trade.type = 'buy'
            else:
                # 创建新记录
                new_trade = Trade(
                    item_name=base_name,
                    quantity=record['quantity'],
                    unit_price=avg_price,
                    total_price=record['total_price'],
                    purchase_date=record['trade_date'].date(),
                    platform='BUFF',
                    type='buy'
                )
                db.session.add(new_trade)

        for base_name, record in sell_records.items():
            # 计算平均单价
            avg_price = record['total_price'] / record['quantity']
            
            # 查找是否已存在相同物品的交易记录
            existing_trade = Trade.query.filter_by(item_name=base_name).first()
            if existing_trade:
                # 更新现有记录
                existing_trade.sale_price = avg_price
                existing_trade.sale_date = record['trade_date'].date()
                existing_trade.platform = 'BUFF'
                existing_trade.type = 'sale'
            else:
                # 创建新记录
                new_trade = Trade(
                    item_name=base_name,
                    quantity=record['quantity'],
                    unit_price=avg_price,
                    total_price=record['total_price'],
                    sale_price=avg_price,
                    sale_date=record['trade_date'].date(),
                    platform='BUFF',
                    type='sale'
                )
                db.session.add(new_trade)

        db.session.commit()
        print(f"成功更新BUFF交易记录：{len(buy_records)}条买入记录，{len(sell_records)}条卖出记录")
    except Exception as e:
        db.session.rollback()
        print(f"更新BUFF交易记录失败：{str(e)}")
        raise

def update_trades():
    """更新交易记录"""
    try:
        # 确保data目录存在
        os.makedirs('data', exist_ok=True)
        
        # 清空现有交易记录
        Trade.query.delete()
        
        # 读取CSV文件
        df = pd.read_csv('data/trades.csv')
        
        # 处理每一行数据
        for _, row in df.iterrows():
            trade = Trade(
                item_name=row['item_name'],
                quantity=row['quantity'],
                unit_price=row['unit_price'],
                total_price=row['total_price'],
                current_price=row['current_price'] if pd.notna(row['current_price']) else None,
                purchase_date=pd.to_datetime(row['purchase_date']).date() if pd.notna(row['purchase_date']) else None,
                sale_date=pd.to_datetime(row['sale_date']).date() if pd.notna(row['sale_date']) else None,
                sale_price=row['sale_price'] if pd.notna(row['sale_price']) else None,
                platform='CSV',
                type='buy' if pd.notna(row['purchase_date']) else 'sale'
            )
            db.session.add(trade)
        
        # 提交更改
        db.session.commit()
        print("交易记录更新成功")
        
    except Exception as e:
        print(f"更新交易记录时出错: {str(e)}")
        db.session.rollback()
        raise

def update_all_trades():
    """更新所有交易记录"""
    update_trades()
    update_buff_trades()

def update_trades_selenium():
    """
    更新交易记录
    注意：这是一个框架函数，需要根据具体网站进行修改
    """
    # 初始化浏览器
    driver = webdriver.Chrome()
    
    try:
        driver.get("YOUR_WEBSITE_URL")
        
        
    except Exception as e:
        print(f"爬取过程中出现错误: {str(e)}")
        raise
    finally:
        driver.quit()

def parse_cookie_string(cookie_str):
    """将cookie字符串转换为cookie对象列表"""
    cookies = []
    for item in cookie_str.split('; '):
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                'name': name,
                'value': value,
                'domain': 'buff.163.com',
                'path': '/'
            })
    return cookies

def verify_cookies(cookies):
    """验证cookies是否有效"""
    required_cookies = ['session', 'remember_me', 'csrf_token']
    cookie_names = [cookie.get('name') for cookie in cookies]
    return all(name in cookie_names for name in required_cookies)

def save_buff_cookies():
    """手动保存cookies"""
    try:
        # 初始化浏览器
        driver = get_chrome_driver()
        
        print("正在访问BUFF登录页面...")
        driver.get("https://buff.163.com/")
        
        print("等待登录...")
        input("请在浏览器中完成登录，然后按回车键继续...")
        
        # 获取cookies
        cookies = driver.get_cookies()
        
        # 验证cookies
        if not verify_cookies(cookies):
            print("警告：获取的cookies可能不完整，请确保已成功登录")
            print("当前cookies:", [cookie.get('name') for cookie in cookies])
            if input("是否继续保存？(y/n): ").lower() != 'y':
                return False
        
        # 保存cookies
        os.makedirs('data', exist_ok=True)
        with open('data/cookie/buff_cookies.json', 'w') as f:
            json.dump(cookies, f)
            
        print("Cookies已保存到 data/buff_cookies.json")
        return True
    except Exception as e:
        print(f"保存cookies失败：{str(e)}")
        return False
    finally:
        try:
            driver.quit()
        except:
            pass

def get_inventory_value():
    """获取BUFF库存价值"""
    try:
        # 使用新的get_chrome_driver函数初始化浏览器
        driver = get_chrome_driver()
        
        # 尝试加载cookies
        try:
            if os.path.exists('data/cookie/buff_cookies.json'):
                print("正在加载cookies...")
                driver.get("https://buff.163.com/")
                with open('data/cookie/buff_cookies.json', 'r') as f:
                    cookies = json.load(f)
                    # 如果cookies是字符串格式，转换为对象列表
                    if isinstance(cookies, str):
                        cookies = parse_cookie_string(cookies)
                    # 验证cookies
                    if not verify_cookies(cookies):
                        raise Exception("Cookies无效或已过期")
                    # 添加cookies
                    for cookie in cookies:
                        driver.add_cookie(cookie)
                print("Cookies加载成功")
                
                # 刷新页面使cookies生效
                print("刷新页面使cookies生效...")
                driver.refresh()
                time.sleep(1)  # 等待页面刷新完成
            else:
                print("未找到cookies文件，请先运行 save_cookies() 保存登录信息")
                raise Exception("未找到cookies文件")
        except Exception as e:
            print(f"加载cookies失败：{str(e)}")
            raise
        
        print("正在访问BUFF库存页面...")
        driver.get("https://buff.163.com/market/steam_inventory?game=csgo#page_num=1&page_size=50&fold=false&search=&steamid=76561198333752402&state=all")
        
        # 等待页面加载
        print("等待页面加载...")
        time.sleep(1)  # 增加等待时间
        
        try:
            # 等待估值元素出现，使用更精确的选择器
            print("等待估值元素...")
            value_element = WebDriverWait(driver, 20).until(  # 增加等待时间
                EC.presence_of_element_located((By.CSS_SELECTOR, ".l_Right.export-btns.brief-info strong.c_Yellow.f_Normal:nth-child(2)"))
            )
            
            # 获取估值文本
            value_text = value_element.text
            print(f"获取到估值文本：{value_text}")
            
            # 提取数字部分
            value = float(value_text.replace('¥', '').strip())
            
            # 保存到文件
            os.makedirs('data', exist_ok=True)
            with open('data/inventory_value.json', 'w') as f:
                json.dump({
                    'value': value,
                    'timestamp': datetime.now().isoformat(),
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'is_manual_update': True  # 添加标志，表示这是手动更新的值
                }, f)
            
            # 更新数据库中的库存价值
            try:
                from models import db, Trade
                # 更新所有交易记录的当前价格
                trades = Trade.query.all()
                if len(trades) > 0:
                    avg_price = value / len(trades)
                    for trade in trades:
                        trade.current_price = avg_price
                        trade.net_profit = trade.current_price - trade.unit_price
                        trade.profit_ratio = (trade.current_price - trade.unit_price) / trade.unit_price if trade.unit_price > 0 else 0
                    db.session.commit()
                    print("数据库更新成功")
            except Exception as e:
                print(f"更新数据库失败：{str(e)}")
                db.session.rollback()
            
            return value
            
        except Exception as e:
            print(f"获取估值元素失败：{str(e)}")
            # 如果获取失败，尝试读取上次保存的值
            try:
                if os.path.exists('data/inventory_value.json'):
                    with open('data/inventory_value.json', 'r') as f:
                        data = json.load(f)
                        print(f"使用上次保存的值：{data['value']}")
                        return data['value']
            except Exception as e:
                print(f"读取上次保存的值失败：{str(e)}")
            raise
            
    except Exception as e:
        print(f"获取库存价值失败: {str(e)}")
        raise
    finally:
        try:
            driver.quit()
        except:
            pass 

def get_total_balance():
    """获取所有平台的账户余额"""
    try:
        driver = get_chrome_driver()
        
        # 加载BUFF cookies
        if os.path.exists('data/cookie/buff_cookies.json'):
            driver.get("https://buff.163.com/")
            with open('data/cookie/buff_cookies.json', 'r') as f:
                cookies = json.load(f)
                if isinstance(cookies, str):
                    cookies = parse_cookie_string(cookies)
                if not verify_cookies(cookies):
                    raise Exception("BUFF Cookies无效或已过期")
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(1)
        
        # 获取BUFF余额
        buff_balance = get_buff_balance(driver)
        
        # 加载IGXE cookies
        if os.path.exists('data/cookie/igxe_cookies.json'):
            driver.get("https://www.igxe.cn/")
            with open('data/cookie/igxe_cookies.json', 'r') as f:
                cookies = json.load(f)
                if isinstance(cookies, str):
                    cookies = parse_cookie_string(cookies)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(1)
        
        # 获取IGXE余额
        igxe_balance = get_igxe_balance(driver)

        # youyou cookies
        if os.path.exists('data/cookie/youpin_cookies.json'):
            driver.get("https://www.youpin898.com/")
            with open('data/cookie/youpin_cookies.json', 'r') as f:
                cookies = json.load(f)
                if isinstance(cookies, str):
                    cookies = parse_cookie_string(cookies)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(1)
        # 悠悠有品余额
        youpin_balance = get_youpin_balance(driver)
        
        # 获取C5余额
        if os.path.exists('data/cookie/c5_cookies.json'):
            driver.get("https://www.c5game.com/csgo")
            with open('data/cookie/c5_cookies.json', 'r') as f:
                cookies = json.load(f)
                if isinstance(cookies, str):
                    cookies = parse_cookie_string(cookies)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(1)
        c5_balance = get_c5_balance()
        
        # 计算总余额
        total_balance = buff_balance + igxe_balance + youpin_balance + c5_balance
        
        # 保存余额数据
        balance_data = {
            'buff_balance': buff_balance,
            'igxe_balance': igxe_balance,
            'youpin_balance': youpin_balance,
            'c5_balance': c5_balance,
            'total_balance': total_balance,
            'timestamp': datetime.now().isoformat()
        }
        
        with open('data/balance.json', 'w', encoding='utf-8') as f:
            json.dump(balance_data, f, ensure_ascii=False, indent=4)
        
        print(f"余额获取完成 - BUFF: {buff_balance}, IGXE: {igxe_balance}, 悠悠有品: {youpin_balance}, C5: {c5_balance}, 总计: {total_balance}")
        return balance_data
        
    except Exception as e:
        print(f"获取余额失败: {str(e)}")
        return {
            'buff_balance': 0.0,
            'igxe_balance': 0.0,
            'youpin_balance': 0.0,
            'c5_balance': 0.0,
            'total_balance': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    finally:
        driver.quit() 

def save_igxe_cookies():
    """保存IGXE登录cookies"""
    try:
        driver = get_chrome_driver()
        driver.get("https://www.igxe.cn/")
        
        print("请在浏览器中登录IGXE账号...")
        print("登录成功后，请按回车键继续...")
        input()
        
        # 获取cookies
        cookies = driver.get_cookies()
        
        # 保存cookies
        os.makedirs('data', exist_ok=True)
        with open('data/cookie/igxe_cookies.json', 'w') as f:
            json.dump(cookies, f)
        
        print("IGXE cookies保存成功！")
        driver.quit()
        return True
        
    except Exception as e:
        print(f"保存IGXE cookies失败: {str(e)}")
        driver.quit()
        return False 

def save_youpin_cookies():
    """保存悠悠有品cookies"""
    try:
        driver = get_chrome_driver()
        driver.get("https://www.youpin898.com/")
        
        print("请在浏览器中登录悠悠有品账号...")
        input("登录完成后按回车键继续...")
        
        # 获取cookies
        cookies = driver.get_cookies()
        
        # 保存cookies到文件
        os.makedirs('data', exist_ok=True)
        with open('data/cookie/youpin_cookies.json', 'w') as f:
            json.dump(cookies, f)
        
        print("悠悠有品cookies保存成功！")
        driver.quit()
    except Exception as e:
        print(f"保存悠悠有品cookies失败: {str(e)}")
        if driver:
            driver.quit() 

def get_c5_balance():
    """获取C5账户余额（使用API）"""
    try:
        # 读取API key
        try:
            with open('data/cookie/c5_api_key.json', 'r') as f:
                api_config = json.load(f)
                APP_KEY = api_config.get('app_key')
                if not APP_KEY:
                    raise ValueError("API key不能为空")
        except Exception as e:
            print(f"读取C5 API key失败: {str(e)}")
            return 0.0
        
        # API配置
        BASE_URL = "http://openapi.c5game.com"
        
        # 构建请求URL和头部
        endpoint = "/merchant/account/v1/balance"
        url = f"{BASE_URL}{endpoint}"
        
        # 设置请求参数和头部
        params = {
            "app-key": APP_KEY,
            "accountType": 0  # 0-账户余额
        }
        
        headers = {
            "app-key": APP_KEY
        }
        
        # 发送请求
        response = requests.get(url, params=params, headers=headers)
        
        # 检查响应状态码
        if response.status_code == 200:
            data = response.json()
            
            # 检查API响应是否成功
            if data.get("success"):
                balance_info = data.get("data", {})
                balance = balance_info.get("balance", 0.0)
                print(f"成功获取C5余额: {balance}")
                return balance
            else:
                print(f"获取C5余额失败: {data.get('errorMsg')}")
                return 0.0
        else:
            print(f"获取C5余额失败: HTTP {response.status_code}")
            return 0.0
            
    except Exception as e:
        print(f"获取C5余额失败: {str(e)}")
        return 0.0

def get_buff_balance(driver):
    """获取BUFF账户余额"""
    try:
        # 访问BUFF余额页面
        driver.get('https://buff.163.com/user-center/asset/recharge/')
        time.sleep(3)  # 等待页面加载
        
        # 等待余额元素出现
        balance_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "cash_amount"))
        )
        
        # 提取余额数值
        balance_text = balance_element.text.replace('¥', '').strip()
        balance = float(balance_text)
        
        # 保存余额数据
        balance_data = {
            'buff_balance': balance,
            'timestamp': datetime.now().isoformat()
        }
        
        # 确保data目录存在
        os.makedirs('data', exist_ok=True)
        
        # 读取现有余额数据
        if os.path.exists('data/balance.json'):
            with open('data/balance.json', 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                balance_data.update(existing_data)
        
        # 保存更新后的余额数据
        with open('data/balance.json', 'w', encoding='utf-8') as f:
            json.dump(balance_data, f, ensure_ascii=False, indent=4)
        
        print(f"成功获取BUFF余额：¥{balance:.2f}")
        return balance
        
    except Exception as e:
        print(f"获取BUFF余额失败：{str(e)}")
        return 0.0

def get_youpin_balance(driver):
    """获取悠悠有品余额"""
    try:
        # 访问悠悠有品钱包页面
        driver.get("https://www.youpin898.com/mine?menu=wallet")
        time.sleep(2)  # 等待页面加载
        
        # 等待余额元素出现
        balance_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.total____0lXK span:nth-child(2)"))
        )
        
        # 获取余额值
        balance = float(balance_element.text)
        print(f"成功获取悠悠有品余额: {balance}")
        
        return balance
    except Exception as e:
        print(f"获取悠悠有品余额失败: {str(e)}")
        return 0.0

def get_igxe_balance(driver):
    """获取IGXE账户余额"""
    try:
        # 访问IGXE提现页面
        driver.get("https://www.igxe.cn/cashout")
        time.sleep(2)  # 等待页面加载
        
        # 等待余额元素出现
        balance_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".wallet-tixian--money .c-4"))
        )
        
        # 提取余额值
        balance_text = balance_element.text.replace('￥', '').strip()
        balance = float(balance_text)
        
        # 准备余额数据
        balance_data = {
            'igxe_balance': balance,
            'timestamp': datetime.now().isoformat()
        }
        
        # 确保data目录存在
        os.makedirs('data', exist_ok=True)
        
        # 读取现有余额数据
        if os.path.exists('data/balance.json'):
            with open('data/balance.json', 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_data.update(balance_data)
                balance_data = existing_data
        
        # 保存余额数据
        with open('data/balance.json', 'w', encoding='utf-8') as f:
            json.dump(balance_data, f, ensure_ascii=False, indent=4)
        
        print(f"成功获取IGXE余额: {balance}")
        return balance
        
    except Exception as e:
        print(f"获取IGXE余额失败: {str(e)}")
        return 0.0