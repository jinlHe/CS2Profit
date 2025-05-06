from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Trade(db.Model):
    """交易记录模型"""
    __tablename__ = 'trade'
    
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)  # 物品名称
    quantity = db.Column(db.Integer, nullable=False)  # 数量
    unit_price = db.Column(db.Float, nullable=False)  # 单价
    total_price = db.Column(db.Float, nullable=False)  # 总价
    current_price = db.Column(db.Float)  # 现价
    purchase_date = db.Column(db.Date)  # 买入日期
    sale_date = db.Column(db.Date)  # 卖出日期
    sale_price = db.Column(db.Float)  # 成交价格
    platform = db.Column(db.String(20))  # 平台
    type = db.Column(db.String(10))  # 类型（买入/卖出）
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'item_name': self.item_name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'current_price': self.current_price,
            'purchase_date': self.purchase_date.strftime('%Y-%m-%d') if self.purchase_date else None,
            'sale_date': self.sale_date.strftime('%Y-%m-%d') if self.sale_date else None,
            'sale_price': self.sale_price,
            'platform': self.platform,
            'type': self.type
        } 