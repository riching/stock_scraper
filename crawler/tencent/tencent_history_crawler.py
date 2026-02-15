#!/usr/bin/env python3
"""腾讯财经历史数据爬虫 - 使用API接口"""

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

class TencentHistoryDataFetcher:
    """腾讯财经历史数据获取器"""
    
    def __init__(self):
        self.name = "TencentHistoryFetcher"
        self.api_base = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

    async def fetch_history_data(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """获取指定日期的历史数据"""
        try:
            print(f"🔍 开始获取 {stock_code} 在 {target_date} 的历史数据...")
            
            # 获取市场前缀
            market_prefix = get_market_prefix(stock_code)
            
            # 构造API URL
            # 参数格式: 股票代码,周期,开始日期,结束日期,数量,复权类型
            # 周期: day=日, week=周, month=月
            # 复权类型: qfq=前复权, hfq=后复权, none=不复权
            url = f"{self.api_base}?param={stock_code},day,{target_date},{target_date},640,qfq"
            
            print(f"  📡 请求API: {url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and stock_code in data['data']:
                    kline_data = data['data'][stock_code]
                    
                    if kline_data and len(kline_data) > 0:
                        # 解析K线数据
                        # 格式: [日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌额,涨跌幅,换手率]
                        kline = kline_data[0]
                        
                        history_data = {
                            "code": stock_code,
                            "date": target_date,
                            "open": float(kline[1]) if kline[1] else None,
                            "close": float(kline[2]) if kline[2] else None,
                            "high": float(kline[3]) if kline[3] else None,
                            "low": float(kline[4]) if kline[4] else None,
                            "volume": int(kline[5]) if kline[5] else None,
                            "name": None
                        }
                        
                        print(f"✅ 成功提取历史数据: 开盘={history_data['open']}, 收盘={history_data['close']}, 最高={history_data['high']}, 最低={history_data['low']}")
                        return history_data
                    else:
                        print(f"⚠️  未找到 {target_date} 的K线数据（可能是非交易日）")
                        return None
                else:
                    print(f"⚠️  API返回数据格式异常")
                    return None
            else:
                print(f"❌ API请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 腾讯财经历史数据提取错误 {stock_code}: {e}")
            return None

class TencentHistoryCrawler:
    """腾讯财经历史数据爬虫主类"""
    
    def __init__(self, db_path: str = None):
        self.fetcher = TencentHistoryDataFetcher()
        self.db_path = db_path

    async def crawl_history_price(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """爬取指定日期的历史价格"""
        print(f"🕷️ 爬取腾讯财经历史数据 {stock_code} ({target_date})")
        
        try:
            # 获取历史数据
            data = await self.fetcher.fetch_history_data(stock_code, target_date)
            
            if data:
                print(f"✅ 成功提取历史数据 {stock_code} ({target_date})")
                return data
            else:
                print(f"❌ 未能提取 {stock_code} 在 {target_date} 的历史数据")
                return None
                
        except Exception as e:
            print(f"❌ 爬取历史数据失败 {stock_code}: {e}")
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
                    None,  # pct_change
                )
                
                cursor.execute("""
                    INSERT INTO merged_stocks 
                    (id, created_at, code, date, open, high, low, close, volume, amount, 
                     outstanding_share, turnover, name, ma5, ma10, ma20, rsi6, rsi14, pct_change)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

async def crawl_multiple_history_stocks(stock_codes: List[str], target_date: str, db_path: str = None):
    """批量爬取多个股票的历史数据"""
    crawler = TencentHistoryCrawler(db_path)
    
    try:
        results = []
        for i, stock_code in enumerate(stock_codes):
            print(f"\n--- 处理第 {i+1}/{len(stock_codes)} 只股票 ---")
            data = await crawler.crawl_history_price(stock_code, target_date)
            if data:
                results.append(data)
            
            # 避免请求过于频繁
            if i < len(stock_codes) - 1:
                await asyncio.sleep(0.5)
        
        # 保存到数据库
        if results and db_path:
            crawler.save_to_database(results)
        
        print(f"\n📊 历史数据爬取结果汇总:")
        print(f"成功爬取: {len(results)} 条历史记录")
        for result in results:
            print(f"- {result['code']} ({result['name']}) {result['date']}:")
            print(f"  开盘: {result.get('open')} 最高: {result.get('high')}")
            print(f"  最低: {result.get('low')} 收盘: {result.get('close')}")
            
        return len(results)
        
    except Exception as e:
        print(f"❌ 批量爬取失败: {e}")
        return 0

async def main():
    """主函数 - 测试模式"""
    print("=" * 60)
    print("腾讯财经历史数据爬虫测试")
    print("=" * 60)
    
    # 数据库路径（如果需要保存到数据库）
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    
    # 测试股票代码
    test_stocks = ["000001", "600519", "000858", "600036", "002323"]
    
    # 目标日期
    target_date = "2026-02-12"
    
    print(f"📈 计划爬取 {len(test_stocks)} 只股票")
    print(f"📅 目标日期: {target_date}")
    print()
    
    success_count = await crawl_multiple_history_stocks(test_stocks, target_date, db_path)
    
    if success_count > 0:
        print(f"\n🎉 成功爬取 {success_count} 只股票的历史数据！")
        return True
    else:
        print(f"\n❌ 历史数据爬取失败")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
