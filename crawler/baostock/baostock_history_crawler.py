#!/usr/bin/env python3
"""Baostock历史数据爬虫"""

import sys
import os
from datetime import datetime
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import baostock as bs
except ImportError:
    print("❌ Baostock未安装，请运行: pip install baostock")
    sys.exit(1)


class BaostockHistoryFetcher:
    """Baostock历史数据获取器"""
    
    def __init__(self):
        self.name = "BaostockFetcher"
        self.logged_in = False
    
    def login(self):
        """登录Baostock"""
        if self.logged_in:
            return True
        
        try:
            lg = bs.login()
            if lg.error_code != '0':
                print(f"❌ Baostock登录失败: {lg.error_msg}")
                return False
            
            self.logged_in = True
            print(f"✅ Baostock登录成功")
            return True
        except Exception as e:
            print(f"❌ Baostock登录异常: {e}")
            return False
    
    def logout(self):
        """登出Baostock"""
        if self.logged_in:
            try:
                bs.logout()
                self.logged_in = False
                print(f"✅ Baostock已登出")
            except Exception as e:
                print(f"❌ Baostock登出异常: {e}")
    
    def fetch_history_data(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """获取历史数据"""
        try:
            if not self.logged_in:
                if not self.login():
                    return None
            
            # 转换股票代码格式
            baostock_code = self._convert_stock_code(stock_code)
            
            # 获取历史K线数据
            rs = bs.query_history_k_data_plus(
                baostock_code,
                "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                start_date=target_date,
                end_date=target_date,
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != '0':
                print(f"❌ Baostock API错误: {rs.error_msg}")
                return None
            
            # 提取数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                data = data_list[0]
                return {
                    "date": data[0],
                    "code": stock_code,
                    "open": float(data[2]),
                    "high": float(data[3]),
                    "low": float(data[4]),
                    "close": float(data[5]),
                    "volume": int(float(data[6])),
                }
            else:
                return None
                
        except Exception as e:
            print(f"❌ Baostock获取历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def fetch_realtime_data(self, stock_code: str) -> Optional[Dict]:
        """获取实时数据"""
        try:
            if not self.logged_in:
                if not self.login():
                    return None
            
            # 转换股票代码格式
            baostock_code = self._convert_stock_code(stock_code)
            
            # 获取最新的K线数据（最近一天）
            rs = bs.query_history_k_data_plus(
                baostock_code,
                "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST",
                start_date="1990-01-01",
                end_date=datetime.now().strftime("%Y-%m-%d"),
                frequency="d",
                adjustflag="3"
            )
            
            if rs.error_code != '0':
                print(f"❌ Baostock API错误: {rs.error_msg}")
                return None
            
            # 提取最新数据
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                # 取最新的一条数据
                data = data_list[-1]
                return {
                    "date": data[0],
                    "code": stock_code,
                    "open": float(data[2]),
                    "high": float(data[3]),
                    "low": float(data[4]),
                    "close": float(data[5]),
                    "volume": int(float(data[6])),
                }
            else:
                return None
                
        except Exception as e:
            print(f"❌ Baostock获取实时数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_stock_code(self, stock_code: str) -> str:
        """转换股票代码为Baostock格式"""
        if stock_code.startswith('6') or stock_code.startswith('9'):
            # 上海A股和B股
            return f"sh.{stock_code}"
        elif stock_code.startswith('0') or stock_code.startswith('3'):
            # 深圳A股和创业板
            return f"sz.{stock_code}"
        else:
            return f"sz.{stock_code}"


class BaostockStockCrawler:
    """Baostock股票爬虫"""
    
    def __init__(self, db_path: str = None):
        self.fetcher = BaostockHistoryFetcher()
        self.db_path = db_path
    
    async def crawl_history_price(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """爬取历史价格"""
        print(f"🕷️ 爬取Baostock {stock_code}")
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
        print(f"🕷️ 爬取Baostock实时数据 {stock_code}")
        
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


async def test_baostock_crawler():
    """测试Baostock爬虫"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    test_stocks = ["000001", "600519", "000858"]
    target_date = "2026-02-09"
    
    print("=" * 60)
    print("测试Baostock爬虫")
    print("=" * 60)
    print(f"目标日期: {target_date}")
    print(f"测试股票: {test_stocks}")
    
    crawler = BaostockStockCrawler(db_path)
    
    try:
        results = []
        
        for i, stock_code in enumerate(test_stocks):
            print(f"\n{'='*60}")
            print(f"测试第 {i+1}/{len(test_stocks)} 只股票: {stock_code}")
            print(f"{'='*60}")
            
            data = await crawler.crawl_history_price(stock_code, target_date)
            if data:
                results.append(data)
        
        crawler.fetcher.logout()
        
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
    success = asyncio.run(test_baostock_crawler())
    sys.exit(0 if success else 1)
