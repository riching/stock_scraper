#!/usr/bin/env python3
"""新浪财经历史数据爬虫 - 从页面提取数据版"""

import asyncio
import sys
import os
import re
from datetime import datetime
from typing import Dict, Optional
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crawler.sina.market_prefix_helper import get_market_prefix


class SinaPageHistoryFetcher:
    """新浪财经历史数据获取器 - 从页面提取"""
    
    def __init__(self):
        self.name = "SinaPageHistoryFetcher"
    
    async def fetch_history_data(self, page, stock_code: str, target_date: str) -> Optional[Dict]:
        """从页面提取历史数据"""
        try:
            print(f"  🔍 开始提取 {stock_code} 在 {target_date} 的历史数据...")
            
            # 等待页面加载
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            
            # 获取页面内容
            content = await page.content()
            
            # 方法1: 尝试从JavaScript变量中提取K线数据
            kline_data = self._extract_kline_from_js(content, target_date)
            if kline_data:
                print(f"  ✅ 从JS变量中提取到K线数据")
                return kline_data
            
            # 方法2: 尝试从页面文本中提取价格信息
            price_data = self._extract_price_from_text(content, stock_code)
            if price_data:
                print(f"  ✅ 从页面文本中提取到价格数据")
                return price_data
            
            # 方法3: 尝试点击K线图表按钮，获取历史数据
            kline_data = await self._extract_kline_from_chart(page, stock_code, target_date)
            if kline_data:
                print(f"  ✅ 从K线图表中提取到数据")
                return kline_data
            
            print(f"  ❌ 未能提取 {stock_code} 在 {target_date} 的历史数据")
            return None
            
        except Exception as e:
            print(f"  ❌ 提取历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_kline_from_js(self, content: str, target_date: str) -> Optional[Dict]:
        """从JavaScript变量中提取K线数据"""
        try:
            # 查找包含K线数据的JavaScript变量
            patterns = [
                r'var\s+kline_data\s*=\s*(\[[^\]]+\])',
                r'var\s+KlineData\s*=\s*(\[[^\]]+\])',
                r'klineData\s*=\s*(\[[^\]]+\])',
                r'data\s*:\s*(\[[^\]]+\])',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    try:
                        kline_json = match.group(1)
                        kline_data = eval(kline_json)
                        
                        # 查找目标日期的数据
                        for item in kline_data:
                            if isinstance(item, dict) and 'day' in item:
                                if item['day'] == target_date:
                                    return {
                                        "date": target_date,
                                        "open": float(item.get('open', 0)),
                                        "high": float(item.get('high', 0)),
                                        "low": float(item.get('low', 0)),
                                        "close": float(item.get('close', 0)),
                                        "volume": int(item.get('volume', 0)),
                                    }
                    except Exception as e:
                        continue
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_price_from_text(self, content: str, stock_code: str) -> Optional[Dict]:
        """从页面文本中提取价格信息"""
        try:
            data = {
                "code": stock_code,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": None,
            }
            
            # 提取当前价格
            close_match = re.search(r'var\s+now_price\s*=\s*["\']?(\d+\.?\d*)["\']?', content)
            if close_match:
                data["close"] = float(close_match.group(1))
            
            # 提取开盘价
            open_match = re.search(r'var\s+open_price\s*=\s*["\']?(\d+\.?\d*)["\']?', content)
            if open_match:
                data["open"] = float(open_match.group(1))
            
            # 提取最高价
            high_match = re.search(r'var\s+high_price\s*=\s*["\']?(\d+\.?\d*)["\']?', content)
            if high_match:
                data["high"] = float(high_match.group(1))
            
            # 提取最低价
            low_match = re.search(r'var\s+low_price\s*=\s*["\']?(\d+\.?\d*)["\']?', content)
            if low_match:
                data["low"] = float(low_match.group(1))
            
            # 提取成交量
            volume_match = re.search(r'var\s+volume\s*=\s*["\']?(\d+)["\']?', content)
            if volume_match:
                data["volume"] = int(volume_match.group(1))
            
            # 如果有收盘价，返回数据
            if data["close"] and data["close"] > 0:
                return data
            
            return None
            
        except Exception as e:
            return None
    
    async def _extract_kline_from_chart(self, page, stock_code: str, target_date: str) -> Optional[Dict]:
        """从K线图表中提取数据"""
        try:
            # 尝试点击K线图表按钮
            try:
                # 查找K线按钮
                kline_button = page.locator('text=日K').first
                if await kline_button.is_visible():
                    await kline_button.click()
                    await page.wait_for_timeout(2000)
                    
                    # 重新获取页面内容
                    content = await page.content()
                    
                    # 再次尝试从JS变量中提取
                    kline_data = self._extract_kline_from_js(content, target_date)
                    if kline_data:
                        return kline_data
            except:
                pass
            
            return None
            
        except Exception as e:
            return None


class SinaStockCrawler:
    """新浪财经股票爬虫 - 从页面提取版"""
    
    def __init__(self, db_path: str = None):
        self.fetcher = SinaPageHistoryFetcher()
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
            ]
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
        """爬取单个股票价格（从页面提取）"""
        print(f"🕷️ 爬取新浪财经 {stock_code}")
        
        try:
            url = self.get_sina_url(stock_code)
            print(f"📄 访问页面: {url}")
            
            page = await self.browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            # 提取数据
            data = await self.fetcher.fetch_history_data(page, stock_code, target_date)
            
            await page.close()
            
            if data:
                data["code"] = stock_code
                print(f"✅ 成功提取 {stock_code}: 价格 {data.get('close')} 元")
                return data
            else:
                print(f"❌ 未能提取 {stock_code} 的数据")
                return None
                
        except Exception as e:
            print(f"❌ 爬取 {stock_code} 失败: {e}")
            import traceback
            traceback.print_exc()
            return None


async def test_page_crawler():
    """测试从页面提取数据的爬虫"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    test_stocks = ["000001", "600519", "000858"]
    target_date = "2026-02-09"
    
    print("=" * 60)
    print("测试从页面提取数据的新浪爬虫")
    print("=" * 60)
    print(f"目标日期: {target_date}")
    print(f"测试股票: {test_stocks}")
    
    crawler = SinaStockCrawler(db_path)
    
    try:
        results = []
        
        await crawler.init_browser()
        
        for i, stock_code in enumerate(test_stocks):
            print(f"\n{'='*60}")
            print(f"测试第 {i+1}/{len(test_stocks)} 只股票: {stock_code}")
            print(f"{'='*60}")
            
            data = await crawler.crawl_stock_price(stock_code, target_date)
            if data:
                results.append(data)
            
            await asyncio.sleep(1)
        
        await crawler.close_browser()
        
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
    success = asyncio.run(test_page_crawler())
    sys.exit(0 if success else 1)
