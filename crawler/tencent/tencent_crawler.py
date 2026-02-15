#!/usr/bin/env python3
"""腾讯财经股票价格爬虫 - 使用API接口"""

import asyncio
import sys
import os
import re
import requests
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawler.sina.market_prefix_helper import get_market_prefix

class TencentStockExtractor:
    """腾讯财经股票数据提取器"""
    
    def __init__(self):
        self.name = "TencentFinance"
        self.api_base = "http://qt.gtimg.cn/q="

    async def extract_stock_data(self, stock_code: str) -> Optional[Dict]:
        """提取腾讯财经股票数据 - 使用API"""
        try:
            # 获取市场前缀
            market_prefix = get_market_prefix(stock_code)
            
            # 构造API URL
            url = f"{self.api_base}{market_prefix}{stock_code}"
            
            print(f"  📡 请求API: {url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # 解析API返回的数据
                # 格式: v_sh600519="1~贵州茅台~1485.30~1480.00~1500.00~1480.00~1234567~..."
                data = self._parse_api_data(content, stock_code)
                
                if data:
                    print(f"✅ 成功提取 {stock_code}: 价格 {data['close']} 元")
                    return data
                else:
                    print(f"❌ 未能解析 {stock_code} 的数据")
                    return None
            else:
                print(f"❌ API请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 腾讯财经提取错误 {stock_code}: {e}")
            return None

    def _parse_api_data(self, content: str, stock_code: str) -> Optional[Dict]:
        """解析API返回的数据"""
        try:
            # 查找数据行
            pattern = rf'v_{get_market_prefix(stock_code)}{stock_code}="([^"]*)"'
            match = re.search(pattern, content)
            
            if match:
                data_str = match.group(1)
                parts = data_str.split('~')
                
                if len(parts) >= 7:
                    # 数据格式: 1~名称~代码~当前价~昨收~开盘~成交量~...
                    data = {
                        "code": parts[2].strip(),
                        "name": parts[1].strip(),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "open": float(parts[5]) if parts[5] else None,
                        "high": None,
                        "low": None,
                        "close": float(parts[3]) if parts[3] else None,
                        "volume": int(parts[6]) if parts[6] and parts[6].isdigit() else None,
                        "change": None,
                        "change_percent": None,
                    }
                    
                    # 计算涨跌额和涨跌幅
                    if data["close"] and parts[4]:
                        yesterday_close = float(parts[4])
                        data["change"] = data["close"] - yesterday_close
                        if yesterday_close > 0:
                            data["change_percent"] = ((data["close"] - yesterday_close) / yesterday_close) * 100
                    
                    return data
            
            return None
            
        except Exception as e:
            print(f"解析API数据失败: {e}")
            return None

class TencentStockCrawler:
    """腾讯财经股票爬虫主类"""
    
    def __init__(self, db_path: str = None):
        self.extractor = TencentStockExtractor()
        self.db_path = db_path

    async def crawl_stock_price(self, stock_code: str, target_date: str = None) -> Optional[Dict]:
        """爬取单个股票价格"""
        print(f"🕷️ 爬取腾讯财经 {stock_code}")
        
        try:
            # 提取数据
            data = await self.extractor.extract_stock_data(stock_code)
            
            if data:
                # 设置目标日期
                if target_date:
                    data["date"] = target_date
                return data
            else:
                return None
                
        except Exception as e:
            print(f"❌ 爬取 {stock_code} 失败: {e}")
            return None

    def save_to_database(self, stock_data_list: List[Dict]):
        """保存数据到数据库"""
        if not self.db_path or not stock_data_list:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for data in stock_data_list:
                # 检查是否已存在相同日期的数据
                cursor.execute(
                    "SELECT COUNT(*) FROM merged_stocks WHERE code = ? AND date = ?",
                    (data["code"], data["date"])
                )
                if cursor.fetchone()[0] > 0:
                    print(f"⚠️  {data['code']} {data['date']} 数据已存在，跳过")
                    continue
                
                # 插入新数据
                insert_data = (
                    None,  # id
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at
                    data["code"],
                    data["date"],
                    data.get("open"),
                    data.get("high"),
                    data.get("low"),
                    data.get("close"),
                    data.get("volume"),
                    None,  # amount
                    None,  # outstanding_share
                    None,  # turnover
                    data.get("name"),
                    None,  # ma5
                    None,  # ma10
                    None,  # ma20
                    None,  # rsi6
                    None,  # rsi14
                    data.get("change_percent"),  # pct_change
                )
                
                cursor.execute("""
                    INSERT INTO merged_stocks 
                    (id, created_at, code, date, open, high, low, close, volume, amount, 
                     outstanding_share, turnover, name, ma5, ma10, ma20, rsi6, rsi14, pct_change)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_data)
                
                # 更新数据状态
                cursor.execute("""
                    INSERT OR REPLACE INTO data_status 
                    (code, last_updated, record_count, status)
                    VALUES (?, ?, ?, ?)
                """, (data["code"], datetime.now().isoformat(), 1, "success"))
            
            conn.commit()
            conn.close()
            print(f"✅ 成功保存 {len(stock_data_list)} 条记录到数据库")
            
        except Exception as e:
            print(f"❌ 数据库保存失败: {e}")

async def crawl_multiple_stocks(stock_codes: List[str], target_date: str = None, db_path: str = None):
    """批量爬取多个股票"""
    crawler = TencentStockCrawler(db_path)
    
    try:
        results = []
        for i, stock_code in enumerate(stock_codes):
            print(f"\n--- 处理第 {i+1}/{len(stock_codes)} 只股票 ---")
            data = await crawler.crawl_stock_price(stock_code, target_date)
            if data:
                results.append(data)
            
            # 避免请求过于频繁
            if i < len(stock_codes) - 1:
                await asyncio.sleep(0.5)
        
        # 保存到数据库
        if results and db_path:
            crawler.save_to_database(results)
        
        print(f"\n📊 爬取结果汇总:")
        print(f"成功爬取: {len(results)} 只股票")
        for result in results:
            change_info = ""
            if result.get("change") is not None:
                change_info = f" (涨跌: {result['change']:+.2f}, {result['change_percent']:+.2f}%)"
            print(f"- {result['code']} ({result['name']}): {result['close']:.2f} 元{change_info}")
            
        return len(results)
        
    except Exception as e:
        print(f"❌ 批量爬取失败: {e}")
        return 0

async def main():
    """主函数 - 测试模式"""
    # 数据库路径（如果需要保存到数据库）
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    
    # 测试股票代码
    test_stocks = ["600519", "000001", "002323", "000858", "600036"]
    
    # 目标日期（可选）
    target_date = "2026-02-09"
    
    success_count = await crawl_multiple_stocks(test_stocks, target_date, db_path)
    
    if success_count > 0:
        print(f"\n🎉 成功爬取 {success_count} 只股票的价格数据！")
        return True
    else:
        print(f"\n❌ 未能成功爬取任何股票数据")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
