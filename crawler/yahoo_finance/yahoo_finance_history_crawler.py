#!/usr/bin/env python3
"""Yahoo Finance历史数据爬虫"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import yfinance as yf
except ImportError:
    print("❌ yfinance未安装，请运行: pip install yfinance")
    sys.exit(1)


class YahooFinanceHistoryFetcher:
    """Yahoo Finance历史数据获取器"""
    
    def __init__(self):
        self.name = "YahooFinanceFetcher"
    
    def fetch_history_data(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """获取历史数据"""
        try:
            # 转换股票代码为Yahoo格式
            yahoo_code = self._convert_stock_code(stock_code)
            
            # 计算日期范围
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d")
            next_day = target_date_obj + timedelta(days=1)
            
            # 下载数据
            print(f"  📡 下载Yahoo Finance数据: {yahoo_code}")
            data = yf.download(
                yahoo_code,
                start=target_date,
                end=next_day.strftime("%Y-%m-%d"),
                progress=False
            )
            
            if data.empty:
                print(f"  ⚠️  未获取到数据")
                return None
            
            # 提取目标日期的数据
            if target_date in data.index:
                row = data.loc[target_date]
                
                # Yahoo Finance返回的数据格式是MultiIndex
                # 需要正确提取数据
                close_price = row[('Close', yahoo_code)]
                high_price = row[('High', yahoo_code)]
                low_price = row[('Low', yahoo_code)]
                open_price = row[('Open', yahoo_code)]
                volume = row[('Volume', yahoo_code)]
                
                return {
                "date": target_date,
                "code": stock_code,
                "open": round(float(open_price), 2),
                "high": round(float(high_price), 2),
                "low": round(float(low_price), 2),
                "close": round(float(close_price), 2),
                "volume": int(volume) if volume > 0 else 0,
            }
            else:
                print(f"  ⚠️  目标日期 {target_date} 不在数据中")
                return None
                
        except Exception as e:
            print(f"  ❌ 获取历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_realtime_data(self, stock_code: str) -> Optional[Dict]:
        """获取实时数据"""
        try:
            # 转换股票代码为Yahoo格式
            yahoo_code = self._convert_stock_code(stock_code)
            
            # 获取最近一天的数据
            print(f"  📡 下载Yahoo Finance实时数据: {yahoo_code}")
            data = yf.download(
                yahoo_code,
                period="1d",
                interval="1d",
                progress=False
            )
            
            if data.empty:
                print(f"  ⚠️  未获取到数据")
                return None
            
            # 提取最新数据
            latest_date = data.index[-1]
            row = data.iloc[-1]
            
            # Yahoo Finance返回的数据格式是MultiIndex
            # 需要正确提取数据
            close_price = row[('Close', yahoo_code)]
            high_price = row[('High', yahoo_code)]
            low_price = row[('Low', yahoo_code)]
            open_price = row[('Open', yahoo_code)]
            volume = row[('Volume', yahoo_code)]
            
            return {
                "date": latest_date.strftime("%Y-%m-%d"),
                "code": stock_code,
                "open": round(float(open_price), 2),
                "high": round(float(high_price), 2),
                "low": round(float(low_price), 2),
                "close": round(float(close_price), 2),
                "volume": int(volume) if volume > 0 else 0,
            }
                
        except Exception as e:
            print(f"  ❌ 获取实时数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """转换股票代码为Yahoo Finance格式"""
        if stock_code.startswith('6') or stock_code.startswith('9'):
            # 上海证券交易所（A股和B股）
            return f"{stock_code}.SS"
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            # 深圳证券交易所（A股和创业板）
            return f"{stock_code}.SZ"
        else:
            # 默认深圳
            return f"{stock_code}.SZ"


class YahooFinanceStockCrawler:
    """Yahoo Finance股票爬虫"""
    
    def __init__(self, db_path: str = None):
        self.fetcher = YahooFinanceHistoryFetcher()
        self.db_path = db_path
    
    async def crawl_history_price(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """爬取历史价格"""
        print(f"🕷️ 爬取Yahoo Finance {stock_code}")
        print(f"📅 目标日期: {target_date}")
        
        try:
            data = self.fetcher.fetch_history_data(stock_code, target_date)
            
            if data:
                print(f"✅ 成功提取 {stock_code}: 价格 {data.get('close')} 元")
                return data
            else:
                print(f"⚠️  未找到 {stock_code} 在 {target_date} 的数据")
                return None
                
        except Exception as e:
            print(f"❌ 爬取 {stock_code} 失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def crawl_realtime_price(self, stock_code: str) -> Optional[Dict]:
        """爬取实时价格"""
        print(f"🕷️ 爬取Yahoo Finance实时数据 {stock_code}")
        
        try:
            data = self.fetcher.fetch_realtime_data(stock_code)
            
            if data:
                print(f"✅ 成功提取 {stock_code}: 价格 {data.get('close')} 元")
                return data
            else:
                print(f"⚠️  未找到 {stock_code} 的实时数据")
                return None
                
        except Exception as e:
            print(f"❌ 爬取 {stock_code} 失败: {e}")
            import traceback
            traceback.print_exc()
            return None


async def test_yahoo_finance_crawler():
    """测试Yahoo Finance爬虫"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    test_stocks = ["000001", "600519", "000858"]
    target_date = "2026-02-09"
    
    print("=" * 60)
    print("测试Yahoo Finance爬虫")
    print("=" * 60)
    print(f"目标日期: {target_date}")
    print(f"测试股票: {test_stocks}")
    
    crawler = YahooFinanceStockCrawler(db_path)
    
    try:
        results = []
        
        for i, stock_code in enumerate(test_stocks):
            print(f"\n{'='*60}")
            print(f"测试第 {i+1}/{len(test_stocks)} 只股票: {stock_code}")
            print(f"{'='*60}")
            
            data = await crawler.crawl_history_price(stock_code, target_date)
            if data:
                results.append(data)
        
        print(f"\n{'='*60}")
        print("测试结果汇总:")
        print(f"{'='*60}")
        print(f"成功爬取: {len(results)} 只股票")
        for result in results:
            print(f"- {result['code']} ({result['date']}): {result['close']} 元")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_yahoo_finance_crawler())
    sys.exit(0 if success else 1)
