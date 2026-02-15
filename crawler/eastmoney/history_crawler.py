#!/usr/bin/env python3
"""东方财富历史价格数据爬虫 - 使用K线API"""

import asyncio
import sys
import os
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawler.sina.market_prefix_helper import get_market_prefix

class EastMoneyHistoryExtractor:
    """东方财富历史价格数据提取器"""
    
    def __init__(self):
        self.name = "EastMoneyHistory"
        self.api_base = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    async def extract_history_data(self, page, stock_code: str, target_date: str) -> Optional[Dict]:
        """提取指定日期的历史价格数据"""
        try:
            print(f"🔍 开始提取 {stock_code} 在 {target_date} 的历史数据...")
            
            # 获取市场代码
            market_prefix = get_market_prefix(stock_code)
            market = "1" if market_prefix == "sh" else "0"
            
            # 构造API请求
            # 将日期格式从YYYY-MM-DD转换为YYYYMMDD
            beg_date = target_date.replace("-", "")
            end_date = target_date.replace("-", "")
            
            url = f"{self.api_base}?secid={market}.{stock_code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=1&beg={beg_date}&end={end_date}"
            
            print(f"  📡 请求API: {url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'klines' in data['data']:
                    klines = data['data']['klines']
                    
                    if klines:
                        # 解析K线数据
                        kline = klines[0]
                        parts = kline.split(',')
                        
                        # 格式: 日期,开盘,收盘,最高,最低,成交量,成交额,振幅
                        history_data = {
                            "code": stock_code,
                            "date": target_date,
                            "open": float(parts[1]),
                            "close": float(parts[2]),
                            "high": float(parts[3]),
                            "low": float(parts[4]),
                            "volume": int(parts[5]),
                            "name": data['data'].get('name', None)
                        }
                        
                        print(f"✅ 成功提取历史数据: 开盘={history_data['open']}, 收盘={history_data['close']}, 最高={history_data['high']}, 最低={history_data['low']}")
                        return history_data
                    else:
                        print(f"⚠️  未找到 {target_date} 的K线数据")
                        return None
                else:
                    print(f"⚠️  API返回数据格式异常")
                    return None
            else:
                print(f"❌ API请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 提取历史数据失败 {stock_code}: {e}")
            return None

class EnhancedEastMoneyCrawler:
    """增强版东方财富爬虫（支持历史数据）"""
    
    def __init__(self):
        self.history_extractor = EastMoneyHistoryExtractor()

    async def crawl_history_price(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """爬取指定日期的历史价格数据"""
        print(f"🕷️ 爬取东方财富历史数据 {stock_code} ({target_date})")
        
        try:
            # 直接使用API获取历史数据，不需要page
            data = await self.history_extractor.extract_history_data(None, stock_code, target_date)
            
            if data:
                print(f"✅ 成功提取历史数据 {stock_code} ({target_date})")
                return data
            else:
                print(f"❌ 未能提取 {stock_code} 在 {target_date} 的历史数据")
                return None
                
        except Exception as e:
            print(f"❌ 爬取历史数据失败 {stock_code}: {e}")
            return None

async def main():
    """测试历史数据爬取功能"""
    crawler = EnhancedEastMoneyCrawler()
    
    try:
        # 测试数据
        test_cases = [
            {"stock": "002323", "date": "2026-02-09"},
            {"stock": "000001", "date": "2026-02-08"},
            {"stock": "600519", "date": "2026-02-05"}
        ]
        
        results = []
        for case in test_cases:
            data = await crawler.crawl_history_price(case["stock"], case["date"])
            if data:
                results.append(data)
            await asyncio.sleep(0.5)  # 避免请求过于频繁
        
        print(f"\n📊 历史数据爬取结果:")
        print(f"成功爬取: {len(results)} 条历史记录")
        for result in results:
            print(f"- {result['code']} ({result['name']}) {result['date']}:")
            print(f"  开盘: {result.get('open')} 最高: {result.get('high')}")
            print(f"  最低: {result.get('low')} 收盘: {result.get('close')}")
            
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ 历史数据爬虫测试失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)