#!/usr/bin/env python3
"""优化后的新浪财经历史数据爬虫 - 使用完整的页面请求headers"""

import asyncio
import sys
import os
import json
import re
import requests
from datetime import datetime
from typing import Dict, Optional
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crawler.sina.market_prefix_helper import get_market_prefix


class SinaHistoryFetcher:
    """新浪财经历史数据获取器 - 优化版"""
    
    def __init__(self):
        self.name = "SinaHistoryFetcher"
        self.session = requests.Session()
        self.cookies = {}
        self.headers = {}
        self.session_initialized = False
    
    async def init_session(self, stock_code: str):
        """初始化会话：访问页面获取cookies和所有headers"""
        if self.session_initialized:
            return True
        
        try:
            print(f"  🌐 初始化会话: {stock_code}")
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            # 收集页面请求的headers
            page_headers = {}
            
            async def handle_request(request):
                url = request.url
                if "finance.sina.com.cn" in url and "realstock" in url:
                    page_headers.update(dict(request.headers))
            
            page.on("request", handle_request)
            
            # 访问页面
            market_prefix = get_market_prefix(stock_code)
            url = f"http://finance.sina.com.cn/realstock/company/{market_prefix}{stock_code}/nc.shtml"
            
            print(f"  📄 访问页面: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)
            
            # 获取cookies
            cookies = await context.cookies()
            print(f"  🍪 获取到 {len(cookies)} 个cookies")
            
            # 转换cookies为requests格式
            for cookie in cookies:
                self.cookies[cookie['name']] = cookie['value']
            
            # 获取页面请求的headers
            if page_headers:
                print(f"  📋 获取到页面请求headers: {len(page_headers)} 个")
                self.headers = page_headers
            else:
                print(f"  ⚠️  未获取到页面请求headers，使用默认headers")
                self.headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'http://finance.sina.com.cn/',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
            
            await browser.close()
            await playwright.stop()
            
            self.session_initialized = True
            print(f"  ✅ 会话初始化完成")
            return True
            
        except Exception as e:
            print(f"  ❌ 会话初始化失败: {e}")
            return False
    
    def fetch_history_data(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """从API获取历史数据"""
        try:
            market_code = get_market_prefix(stock_code)
            api_url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
            
            params = {
                'symbol': f'{market_code}{stock_code}',
                'scale': '240',
                'ma': 'no',
                'count': '30'
            }
            
            # 构造headers - 使用页面请求的所有headers
            headers = self.headers.copy()
            
            # 添加cookies
            if self.cookies:
                cookie_str = '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
                headers['Cookie'] = cookie_str
            
            print(f"  📡 请求API: {api_url}")
            print(f"  📋 请求参数: {params}")
            print(f"  📋 请求headers: {len(headers)} 个")
            
            response = self.session.get(api_url, params=params, headers=headers, timeout=15)
            
            print(f"  📊 状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  📄 响应数据: {len(data) if isinstance(data, list) else 'dict'} 条")
                    
                    return self._parse_api_history_data(data, target_date)
                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON解析失败: {e}")
                    print(f"  📄 响应内容: {response.text[:200]}")
                    return None
            else:
                print(f"  ❌ API请求失败: {response.status_code}")
                print(f"  📄 响应内容: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"  ❌ 获取历史数据失败: {e}")
            import traceback
            traceback.print_exc()
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
            except (KeyError, ValueError) as e:
                print(f"  ⚠️  解析数据项失败: {e}")
                continue
        
        return None


class SinaStockCrawler:
    """新浪财经股票爬虫 - 优化版"""
    
    def __init__(self, db_path: str = None):
        self.fetcher = SinaHistoryFetcher()
        self.db_path = db_path
    
    async def crawl_stock_price(self, stock_code: str, target_date: str = None) -> Optional[Dict]:
        """爬取单个股票价格（优化版）"""
        print(f"🕷️ 爬取新浪财经 {stock_code}")
        print(f"📅 目标日期: {target_date}")
        
        try:
            if target_date:
                # 初始化会话（只初始化一次）
                if not self.fetcher.session_initialized:
                    success = await self.fetcher.init_session(stock_code)
                    if not success:
                        print(f"❌ 会话初始化失败")
                        return None
                    await asyncio.sleep(2)
                
                # 使用会话获取历史数据
                data = self.fetcher.fetch_history_data(stock_code, target_date)
                
                if data:
                    data["code"] = stock_code
                    print(f"✅ 成功从API提取 {stock_code}: 价格 {data.get('close')} 元")
                    return data
                else:
                    print(f"⚠️  API未找到 {stock_code} 在 {target_date} 的数据")
                    return None
            else:
                print(f"⚠️  实时数据模式暂不支持")
                return None
                
        except Exception as e:
            print(f"❌ 爬取 {stock_code} 失败: {e}")
            import traceback
            traceback.print_exc()
            return None


async def test_optimized_crawler():
    """测试优化后的爬虫"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    test_stocks = ["000001", "600519", "000858"]
    target_date = "2026-02-09"
    
    print("=" * 60)
    print("测试优化后的新浪爬虫 - 使用完整headers")
    print("=" * 60)
    print(f"目标日期: {target_date}")
    print(f"测试股票: {test_stocks}")
    
    crawler = SinaStockCrawler(db_path)
    
    try:
        results = []
        
        for i, stock_code in enumerate(test_stocks):
            print(f"\n{'='*60}")
            print(f"测试第 {i+1}/{len(test_stocks)} 只股票: {stock_code}")
            print(f"{'='*60}")
            
            data = await crawler.crawl_stock_price(stock_code, target_date)
            if data:
                results.append(data)
            
            await asyncio.sleep(1)
        
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
    success = asyncio.run(test_optimized_crawler())
    sys.exit(0 if success else 1)
