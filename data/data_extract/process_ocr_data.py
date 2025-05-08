import pandas as pd
import re
from datetime import datetime

def clean_brackets_content(name):
    """
    清理和规范化括号中的内容
    """
    # 移除首尾的引号（如果同时存在）
    if (name.startswith('"') and name.endswith('"')) or (name.startswith('"') and name.endswith('"')):
        name = name[1:-1]
    
    # 定义允许的括号内容
    wear_conditions = ['崭新出厂', '略有磨损', '久经沙场', '破损不堪', '战痕累累']
    special_marks = ['★', '纪念品', 'StatTrakTM']
    sticker_qualities = ['全息', '闪耀', '闪亮', '金色', '冠军']
    colors = ['灰色', '蓝色', '紫色', '粉色', '红色', '橙色', '黄色', '绿色', '青色', '白色', '黑色']
    
    # 探员特有备注
    agent_notes = ['挑衅者', 'FBI', '三分熟', '护目镜', '抱树人', '野草', '革新派']
    # 达里尔爵士特有备注
    daryl_notes = ['沉默', '聒噪', '穷鬼', '头盖骨', '皇家', '迈阿密']
    
    # 是否是印花
    is_sticker = '印花' in name
    # 是否是达里尔爵士
    is_daryl = '达里尔爵士' in name
    # 是否是探员（包括达里尔爵士）
    is_agent = is_daryl or any(role in name for role in [
        '专业人士', '游击队', '海豹部队', '军刀', 'FBI特工',
        '上校', '中队长', '海军上尉', '指挥官', '特种部队'
    ])
    
    def process_bracket_content(match):
        content = match.group(1)
        
        # 处理多个条件（用空格分隔的情况）
        conditions = content.split()
        valid_conditions = []
        
        for cond in conditions:
            # 对于印花，只允许特定的品质词
            if is_sticker:
                if cond in sticker_qualities:
                    valid_conditions.append(cond)
            # 对于达里尔爵士
            elif is_daryl:
                if (cond in daryl_notes or 
                    cond in colors):
                    valid_conditions.append(cond)
            # 对于其他探员
            elif is_agent:
                if (cond in agent_notes or 
                    cond in colors):
                    valid_conditions.append(cond)
            # 对于其他物品
            else:
                if (cond in wear_conditions or 
                    cond in special_marks or 
                    cond in colors):
                    valid_conditions.append(cond)
        
        # 如果有有效内容，保留括号，否则移除括号
        if valid_conditions:
            return f"（{''.join(valid_conditions)}）"
        return ""
    
    # 处理括号内容
    name = re.sub(r'（([^）]+)）', process_bracket_content, name)
    
    # 清理末尾可能残留的点号
    name = re.sub(r'[.。]+$', '', name)
    
    # 清理多余的空格
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def is_complete_item_name(name):
    """
    判断一个名称是否是完整的物品名称
    """
    # 检查是否包含竖线和完整的括号
    has_separator = '|' in name
    has_complete_brackets = all(
        name.count(left) == name.count(right)
        for left, right in [('（', '）'), ('(', ')')]
    )
    
    # 检查是否包含典型的武器/装备特征
    weapon_features = [
        '（★）',
        '（StatTrakTM）',
        '（纪念品）',
        '手套',
        '刀',
        '匕首',
        'AK-47',
        'M4A4',
        'M4A1',
        'AWP',
        'USP',
        'P250',
        'MP5',
        'MP7',
        'MP9',
        'MAG-7',
        'FAMAS',
        'SCAR-20',
        'SG 553',
        'SSG 08',
        'G3SG1',
        'P90',
        'MAC-10',
        'UMP-45',
        'PP-Bizon',
        'Nova',
        'XM1014',
        'M249',
        'Negev',
        'Desert Eagle',
        'R8 左轮手枪',
        'P2000',
        'Glock-18',
        'Five-SeveN',
        'CZ75-Auto',
        'Tec-9',
        'Dual Berettas'
    ]
    
    # 检查是否是探员或特殊角色
    agent_features = [
        '专业人士',
        '游击队',
        '海豹部队',
        '军刀',
        'FBI特工',
        '上校',
        '中队长',
        '海军上尉',
        '指挥官',
        '特种部队',
        '达里尔爵士'
    ]
    
    has_weapon = any(weapon in name for weapon in weapon_features)
    has_agent = any(agent in name for agent in agent_features)
    has_wear = re.search(r'（[^）]*[磨损场]）', name) is not None
    
    # 检查是否是特殊物品（如印花、音乐盒等）
    special_items = ['印花', '音乐盒', '挂件', '胸章']
    is_special = any(item in name for item in special_items)
    
    return has_separator and has_complete_brackets and (has_weapon or has_wear or is_special or has_agent)

def split_item_names(full_name):
    """
    将可能包含多个物品的名称分割成单独的物品名称列表
    """
    # 预处理：清理多余的空格
    full_name = re.sub(r'\s+', ' ', full_name).strip()
    
    # 尝试按空格分割
    parts = full_name.split(' ')
    
    # 存储最终的物品列表
    items = []
    current_item = []
    
    for part in parts:
        # 如果当前部分看起来像是新物品的开始，且之前已经累积了一些内容
        if (any(weapon in part for weapon in ['（★）', '手套', '刀', '匕首', 'AK-47', 'M4', 'AWP']) or 
            any(special in part for special in ['印花', '音乐盒', '挂件', '胸章'])) and current_item:
            # 检查之前累积的内容是否构成完整物品
            prev_item = ' '.join(current_item)
            if is_complete_item_name(prev_item):
                items.append(clean_brackets_content(prev_item))
                current_item = []
        
        current_item.append(part)
        current_name = ' '.join(current_item)
        
        # 如果当前累积的部分构成了一个完整的物品名称
        if is_complete_item_name(current_name):
            items.append(clean_brackets_content(current_name))
            current_item = []
    
    # 处理剩余部分
    if current_item:
        remaining = ' '.join(current_item)
        if is_complete_item_name(remaining):
            items.append(clean_brackets_content(remaining))
    
    # 如果没有找到任何完整物品，返回清理后的原始名称
    if not items:
        return [clean_brackets_content(full_name)]
    
    return items

def clean_name(name_parts):
    """
    清理和规范化商品名称
    """
    # 移除重复的部分
    name_parts = list(dict.fromkeys(name_parts))
    
    # 移除单独的品质词
    quality_words = ['崭新', '略磨', '久经', '破损', '战痕', '非凡', '普通级', '高级', '大师', '卓越']
    name_parts = [part for part in name_parts if part not in quality_words]
    
    # 合并名称部分
    full_name = ' '.join(name_parts)
    
    # 清理多余的空格
    full_name = re.sub(r'\s+', ' ', full_name).strip()
    
    # 移除开头的品质词
    full_name = re.sub(f"^({'|'.join(quality_words)})\\s+", "", full_name)
    
    # 分割多个物品
    items = split_item_names(full_name)
    
    # 如果成功分割出多个物品，只返回最后一个（通常是最贵的那个）
    if items:
        result = items[-1]
        # 再次确保移除开头的品质词
        result = re.sub(f"^({'|'.join(quality_words)})\\s+", "", result)
        # 移除首尾的引号（如果同时存在）
        if (result.startswith('"') and result.endswith('"')) or (result.startswith('"') and result.endswith('"')):
            result = result[1:-1]
        return result
    
    # 移除首尾的引号（如果同时存在）
    if (full_name.startswith('"') and full_name.endswith('"')) or (full_name.startswith('"') and full_name.endswith('"')):
        full_name = full_name[1:-1]
    return clean_brackets_content(full_name)

def extract_info_from_text(file_path):
    """
    从OCR识别的文本中提取信息
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines()]

    data = []
    current_items = []
    current_price = None
    current_wear = None
    current_time = None
    temp_name = []

    for line in lines:
        # 移除置信度信息
        line = re.sub(r'\(置信度: [\d.]+\)', '', line).strip()
        
        # 跳过空行
        if not line:
            continue

        # 提取时间
        time_match = re.search(r'下单时间([\d.]+)(\d{2}:\d{2}:\d{2})', line)
        if time_match:
            # 保存之前的物品
            if temp_name:
                full_name = ' '.join(temp_name)
                items = split_item_names(full_name)
                if items:
                    # 只保存最后一个物品（通常是主要物品）
                    current_items = items
            
            # 如果有完整的信息，保存记录
            if current_items and current_price is not None:
                # 使用最后一个物品（通常是主要物品）
                data.append({
                    'name': clean_name(current_items[-1:]),
                    'price': current_price,
                    'wear': current_wear,
                    'time': time_match.group(1) + time_match.group(2)
                })
            
            # 重置所有变量
            current_items = []
            current_price = None
            current_wear = None
            current_time = time_match.group(1) + time_match.group(2)
            temp_name = []
            continue

        # 提取价格
        price_match = re.search(r'￥([\d.]+)', line)
        if price_match:
            if temp_name:
                full_name = ' '.join(temp_name)
                items = split_item_names(full_name)
                if items:
                    current_items = items
                temp_name = []
            current_price = float(price_match.group(1))
            continue

        # 提取磨损度（0.开头的浮点数）
        wear_match = re.search(r'0\.\d+', line)
        if wear_match and len(wear_match.group()) > 5:  # 确保是磨损度而不是其他数字
            current_wear = float(wear_match.group())
            continue

        # 跳过一些无关的行
        if any(skip in line for skip in ['已完成', '100%', '0%']) or \
           line.strip() in ['StatTrakTM', '★', 'GL']:
            continue
        
        # 如果行包含这些关键词，很可能是名称的一部分
        if any(keyword in line for keyword in ['（★）', '|', '（StatTrakTM）', '（纪念品）']) or \
           any(wear_type in line for wear_type in ['崭新', '略磨', '久经', '破损', '战痕', '纪念品']):
            temp_name.append(line)

    # 处理最后一个项目
    if temp_name:
        full_name = ' '.join(temp_name)
        items = split_item_names(full_name)
        if items and current_price is not None and current_time is not None:
            data.append({
                'name': clean_name(items[-1:]),
                'price': current_price,
                'wear': current_wear,
                'time': current_time
            })

    return data

def main():
    # 读取OCR文本文件
    input_file = '../youyou/ocr_buy_results.txt'
    output_file = '../youyou/youyou_buy.csv'
    
    # 提取信息
    data = extract_info_from_text(input_file)
    
    # 转换为DataFrame
    df = pd.DataFrame(data)
    
    # 重命名列
    df = df.rename(columns={
        'name': '饰品',
        'price': '价格',
        'wear': '磨损',
        'time': '时间'
    })
    
    # 转换时间格式
    df['时间'] = pd.to_datetime(df['时间'], format='%Y.%m.%d%H:%M:%S')
    df = df.sort_values('时间', ascending=False)
    df['时间'] = df['时间'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 保存为CSV
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"数据已保存到: {output_file}")
    print(f"共处理 {len(df)} 条记录")
    
    # 显示前几行数据作为样例
    print("\n数据样例:")
    print(df.head().to_string())

if __name__ == '__main__':
    main() 