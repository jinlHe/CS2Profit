import json
import requests
import pandas as pd
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

class C5Inventory:
    """C5 API库存查询类"""
    
    def __init__(self, api_key_path: str = "data/cookie/c5_api_key.json", steam_id_path: str = "data/cookie/steam_id.json"):
        """
        初始化C5库存查询类
        
        Args:
            api_key_path: API密钥文件路径
            steam_id_path: Steam ID配置文件路径
        """
        self.base_url = "http://openapi.c5game.com"
        self.api_key = self._load_api_key(api_key_path)
        self.steam_id = self._load_steam_id(steam_id_path)
        
    def _load_api_key(self, api_key_path: str) -> str:
        """
        从文件加载API密钥
        
        Args:
            api_key_path: API密钥文件路径
            
        Returns:
            str: API密钥
        """
        try:
            with open(api_key_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('app_key')
        except Exception as e:
            raise Exception(f"加载API密钥失败: {str(e)}")
            
    def _load_steam_id(self, steam_id_path: str) -> str:
        """
        从文件加载Steam ID
        
        Args:
            steam_id_path: Steam ID配置文件路径
            
        Returns:
            str: Steam ID
        """
        try:
            with open(steam_id_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('steam_id')
        except Exception as e:
            raise Exception(f"加载Steam ID失败: {str(e)}")
    
    def get_inventory(self, app_id: str = "730", language: str = "zh", 
                     start_asset_id: str = "0", count: Optional[str] = None) -> Dict:
        """
        获取Steam库存
        
        Args:
            app_id: 游戏ID (CS2: 730, Dota2: 570)
            language: 语言 (zh: 中文, en: 英文)
            start_asset_id: 开始assetId，上次请求返回的lastAssetId
            count: 查询条数，分页返回的数量
            
        Returns:
            Dict: 库存数据
        """
        url = f"{self.base_url}/merchant/inventory/v2/{self.steam_id}/{app_id}"
        
        # 构建查询参数
        params = {
            "language": language,
            "startAssetId": start_asset_id,
            "app-key": self.api_key
        }
        if count:
            params["count"] = count
            
        # 设置请求头
        headers = {
            'app-key': self.api_key
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取库存失败: {str(e)}")
            
    def save_inventory_to_file(self, inventory: Dict, steam_id: str) -> str:
        """
        将库存信息保存到JSON文件
        
        Args:
            inventory: 库存数据
            steam_id: Steam ID
            
        Returns:
            str: 保存的文件路径
        """
        # 创建data/inventory目录（如果不存在）
        save_dir = Path("data/inventory")
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inventory_{steam_id}_{timestamp}.json"
        filepath = save_dir / filename
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, ensure_ascii=False, indent=2)
            
        return str(filepath)

    def save_inventory_to_csv(self, inventory: Dict, output_file: str = "data/steaminventory.csv") -> str:
        """
        将库存信息保存为CSV文件
        
        Args:
            inventory: 库存数据
            output_file: 输出文件名
            
        Returns:
            str: 保存的文件路径
        """
        # 提取物品列表
        items = []
        if 'data' in inventory and 'list' in inventory['data']:
            items = inventory['data']['list']
        
        # 提取指定字段
        extracted_data = []
        for item in items:
            item_info = item.get('itemInfo', {})
            item_data = {
                'name': item.get('name', ''),
                'shortName': item.get('shortName', ''),
                'qualityName': item_info.get('qualityName', ''),
                'rarityName': item_info.get('rarityName', ''),
                'typeName': item_info.get('typeName', ''),
                'weaponName': item_info.get('weaponName', ''),
                'exteriorName': item_info.get('exteriorName', ''),
                'itemSetName': item_info.get('itemSetName', ''),
                'customPlayerName': item_info.get('customPlayerName', ''),
                'stickerCapsuleName': item_info.get('stickerCapsuleName', ''),
                'patchCapsuleName': item_info.get('patchCapsuleName', '')
            }
            extracted_data.append(item_data)
        
        # 转换为DataFrame并保存为CSV
        df = pd.DataFrame(extracted_data)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')  # 使用utf-8-sig以支持Excel正确显示中文
        
        return output_file

def update_inventory():
    """更新库存数据"""
    try:
        # 初始化C5库存查询类
        c5 = C5Inventory()
        
        # 获取库存
        inventory = c5.get_inventory()
        
        # 保存到CSV文件
        csv_filepath = c5.save_inventory_to_csv(inventory)
        print(f"库存信息已保存到CSV文件: {csv_filepath}")
        
        return True
        
    except Exception as e:
        print(f"错误: {str(e)}")
        return False

if __name__ == "__main__":
    update_inventory() 