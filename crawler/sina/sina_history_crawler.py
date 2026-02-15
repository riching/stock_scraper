#!/usr/bin/env python3
"""新浪财经历史数据爬虫

支持两种模式：
1. 历史数据模式（指定target_date）：使用新浪财经API获取历史K线数据，无需浏览器
2. 实时数据模式（不指定target_date）：使用Playwright访问页面获取实时数据
"""

import asyncio
import sys
import os
import json
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crawler.sina.market_prefix_helper import get_market_prefix

class SinaHistoryDataFetcher:
    """新浪财经历史数据获取器"""
    
    def __init__(self):
        self.name = "SinaHistoryFetcher"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    async def fetch_stock_data(self, page, stock_code: str, target_date: str = None) -> Optional[Dict]:
        """获取股票数据（支持当天和历史数据）"""
        try:
            # 等待页面加载
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            
            # 获取页面内容
            content = await page.content()
            
            # 解析数据
            stock_data = self._parse_sina_data(content, stock_code, target_date)
            return stock_data
            
        except Exception as e:
            print(f"新浪财经数据提取错误 {stock_code}: {e}")
            return None

    def _parse_sina_data(self, html: str, stock_code: str, target_date: str = None) -> Optional[Dict]:
        """解析新浪财经HTML内容"""
        data = {
            "code": stock_code,
            "name": None,
            "date": target_date or datetime.now().strftime("%Y-%m-%d"),
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "change": None,
            "change_percent": None,
        }

        # 从JavaScript变量中提取数据
        patterns = {
            "close": r"var\s+now_price\s*=\s*['\"]([^'\"]*)['\"];",
            "open": r"var\s+open_price\s*=\s*['\"]([^'\"]*)['\"];",
            "high": r"var\s+high_price\s*=\s*['\"]([^'\"]*)['\"];",
            "low": r"var\s+low_price\s*=\s*['\"]([^'\"]*)['\"];",
            "volume": r"var\s+volume\s*=\s*['\"]([^'\"]*)['\"];",
            "name": r"var\s+stockName\s*=\s*['\"]([^'\"]*)['\"];",
            "change": r"var\s+change\s*=\s*['\"]([^'\"]*)['\"];",
            "change_percent": r"var\s+change_percent\s*=\s*['\"]([^'\"]*)['\"];",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                try:
                    value = match.group(1).strip()
                    if value and value != '':
                        if key == "volume":
                            data[key] = int(float(value.replace(",", "")))
                        elif key in ["change", "change_percent"]:
                            data[key] = float(value.replace("%", ""))
                        elif key == "name":
                            data[key] = value
                        else:
                            data[key] = float(value)
                except (ValueError, AttributeError):
                    continue

        # 如果没有从变量中获取到close价格，尝试从其他方式获取
        if data["close"] is None:
            # 尝试从页面文本中提取价格
            price_matches = re.findall(r'(\d+\.\d+)', html)
            # 过滤合理的价格范围
            valid_prices = []
            for price_str in price_matches:
                try:
                    price = float(price_str)
                    if 0.1 <= price <= 10000:
                        valid_prices.append(price)
                except ValueError:
                    continue
            
            if valid_prices:
                # 选择最可能的当前价格
                data["close"] = valid_prices[0] if len(valid_prices) == 1 else valid_prices[1]

        # 如果有close价格，返回数据
        if data["close"] is not None:
            return data
        return None

    def fetch_history_data_from_api(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """从API获取历史数据（主要方式）"""
        try:
            # 新浪财经历史数据API
            market_code = get_market_prefix(stock_code)
            api_url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
            
            params = {
                'symbol': f'{market_code}{stock_code}',
                'scale': '240',  # 日线
                'ma': 'no',
                'count': '30'  # 获取最近30天数据
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self._parse_api_history_data(data, target_date)
            else:
                print(f"API请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"新浪财经API获取历史数据失败 {stock_code}: {e}")
            
        return None

    def _parse_api_history_data(self, api_data: list, target_date: str) -> Optional[Dict]:
        """解析API历史数据"""
        if not api_data:
            return None
            
        target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
        
        for item in api_data:
            try:
                item_date = datetime.strptime(item['day'], "%Y-%m-%d")
                if item_date.date() == target_datetime.date():
                    return {
                        "date": target_date,
                        "open": float(item['open']),
                        "high": float(item['high']),
                        "low": float(item['low']),
                        "close": float(item['close']),
                        "volume": int(item['volume']),
                    }
            except (KeyError, ValueError):
                continue
                
        return None

class SinaStockCrawler:
    """新浪财经股票爬虫"""
    
    def __init__(self, db_path: str = None):
        self.fetcher = SinaHistoryDataFetcher()
        self.browser = None
        self.playwright = None
        self.db_path = db_path

    async def init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
            ],
        )

    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def get_sina_url(self, stock_code: str) -> str:
        """获取新浪财经股票URL"""
        market_prefix = get_market_prefix(stock_code)
        return f"http://finance.sina.com.cn/realstock/company/{market_prefix}{stock_code}/nc.shtml"

    async def crawl_stock_price(self, stock_code: str, target_date: str = None) -> Optional[Dict]:
        """爬取单个股票价格（优先使用API获取历史数据）"""
        print(f"🕷️ 爬取新浪财经 {stock_code}")
        
        try:
            # 如果指定了目标日期，优先使用API获取历史数据
            if target_date:
                print(f"📅 目标日期: {target_date}")
                
                # 尝试从API获取历史数据
                data = self.fetcher.fetch_history_data_from_api(stock_code, target_date)
                
                if data:
                    data["code"] = stock_code
                    print(f"✅ 成功从API提取 {stock_code}: 价格 {data.get('close')} 元")
                    return data
                else:
                    print(f"⚠️  API未找到 {stock_code} 在 {target_date} 的数据")
                    return None
            else:
                # 如果没有指定日期，获取实时数据
                url = self.get_sina_url(stock_code)
                print(f"📄 访问页面: {url}")
                
                page = await self.browser.new_page()
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                
                # 提取数据
                data = await self.fetcher.fetch_stock_data(page, stock_code)
                
                await page.close()
                
                if data:
                    print(f"✅ 成功提取 {stock_code}: 价格 {data.get('close')} 元")
                    return data
                else:
                    print(f"❌ 未能提取 {stock_code} 的数据")
                    return None
                
        except Exception as e:
            print(f"❌ 爬取 {stock_code} 失败: {e}")
            return None

    def save_to_database(self, stock_data_list: List[Dict]):
        """保存数据到数据库"""
        if not self.db_path or not stock_data_list:
            return
            
        try:
            import sqlite3
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
    crawler = SinaStockCrawler(db_path)
    
    try:
        results = []
        
        # 如果指定了目标日期，使用API获取历史数据（不需要浏览器）
        if target_date:
            print(f"📅 批量获取历史数据，目标日期: {target_date}")
            print(f"📊 计划爬取 {len(stock_codes)} 只股票")
            
            for i, stock_code in enumerate(stock_codes):
                print(f"\n--- 处理第 {i+1}/{len(stock_codes)} 只股票 ---")
                data = crawler.fetcher.fetch_history_data_from_api(stock_code, target_date)
                if data:
                    data["code"] = stock_code
                    results.append(data)
                
                # 避免请求过于频繁
                if i < len(stock_codes) - 1:
                    await asyncio.sleep(1)
        else:
            # 如果没有指定日期，获取实时数据（需要浏览器）
            print(f"📄 批量获取实时数据")
            print(f"📊 计划爬取 {len(stock_codes)} 只股票")
            
            await crawler.init_browser()
            
            for i, stock_code in enumerate(stock_codes):
                print(f"\n--- 处理第 {i+1}/{len(stock_codes)} 只股票 ---")
                data = await crawler.crawl_stock_price(stock_code)
                if data:
                    results.append(data)
                
                # 避免请求过于频繁
                if i < len(stock_codes) - 1:
                    await asyncio.sleep(2)
        
        # 保存到数据库
        if results and db_path:
            crawler.save_to_database(results)
        
        print(f"\n📊 爬取结果汇总:")
        print(f"成功爬取: {len(results)} 只股票")
        for result in results:
            date_info = f" ({result['date']})" if result.get('date') else ""
            print(f"- {result['code']}{date_info}: {result['close']:.2f} 元")
            
        return len(results)
        
    except Exception as e:
        print(f"❌ 批量爬取失败: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        await crawler.close_browser()

async def main():
    """主函数 - 测试模式"""
    # 数据库路径（如果需要保存到数据库）
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    
    # 测试股票代码
    test_stocks = ["600519", "000001", "002323"]
    
    # 测试历史数据获取（使用API）
    print("="*60)
    print("🎯 测试历史数据获取（使用API）:")
    print("="*60)
    history_date = "2026-02-09"
    history_success = await crawl_multiple_stocks(test_stocks, history_date, db_path)
    
    # 测试实时数据获取（使用浏览器）
    print("\n" + "="*60)
    print("🎯 测试实时数据获取（使用浏览器）:")
    print("="*60)
    today_success = await crawl_multiple_stocks(test_stocks, None, db_path)
    
    print(f"\n🏁 最终结果:")
    print(f"历史数据: {history_success} 只股票")
    print(f"实时数据: {today_success} 只股票")
    
    return history_success > 0 or today_success > 0

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)