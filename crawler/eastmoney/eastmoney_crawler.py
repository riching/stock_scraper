#!/usr/bin/env python3
"""东方财富股票价格爬虫 - 完整版"""

import asyncio
import sys
import os
import sqlite3
import re
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawler.sina.market_prefix_helper import get_market_prefix

class EastMoneyStockExtractor:
    """东方财富股票数据提取器"""
    
    def __init__(self):
        self.name = "EastMoney"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    async def extract_stock_data(self, page, stock_code: str) -> Optional[Dict]:
        """提取东方财富股票数据"""
        try:
            # 等待页面加载完成
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            await page.wait_for_timeout(5000)  # 额外等待确保数据加载
            
            # 解析股票数据
            stock_data = await self._parse_eastmoney_data(page, stock_code)
            return stock_data
            
        except Exception as e:
            print(f"东方财富提取错误 {stock_code}: {e}")
            return None

    async def _parse_eastmoney_data(self, page, stock_code: str) -> Optional[Dict]:
        """解析东方财富页面内容 - 从页面元素中提取价格信息"""
        data = {
            "code": stock_code,
            "name": None,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "change": None,
            "change_percent": None,
        }

        # 提取股票名称（从页面元素）
        # 查找股票名称元素
        name_element = await page.query_selector('.stock-name, [class*="name"]')
        if name_element:
            name_text = await name_element.inner_text()
            # 去掉所有空格
            data["name"] = name_text.replace(' ', '').strip()
            print(f"  📄 从元素提取名称: {data['name']}")
        else:
            # 备选方案：从标题提取
            html = await page.content()
            # 标题格式: <title>平安银行 10.91 -0.05(-0.46%)股票价格_行情_走势图—东方财富网</title>
            # 标题格式: <title>五 粮 液 106.06 1.44... </title>
            title_match = re.search(r'<title>([^0-9]+)', html)
            if title_match:
                data["name"] = title_match.group(1).replace(' ', '').strip()

        # 从页面元素中提取价格数据
        # 使用XPath定位价格信息表格
        try:
            # 查找包含"今开："的td元素
            open_element = await page.query_selector('xpath=//td[contains(text(), "今开：")]/following-sibling::td//span//span')
            if open_element:
                open_text = await open_element.inner_text()
                try:
                    data["open"] = float(open_text)
                    print(f"  📄 今开: {open_text}")
                except ValueError:
                    pass
            
            # 查找包含"最高："的td元素
            high_element = await page.query_selector('xpath=//td[contains(text(), "最高：")]/following-sibling::td//span//span')
            if high_element:
                high_text = await high_element.inner_text()
                try:
                    data["high"] = float(high_text)
                    print(f"  📄 最高: {high_text}")
                except ValueError:
                    pass
            
            # 查找包含"最低："的td元素
            low_element = await page.query_selector('xpath=//td[contains(text(), "最低：")]/following-sibling::td//span//span')
            if low_element:
                low_text = await low_element.inner_text()
                try:
                    data["low"] = float(low_text)
                    print(f"  📄 最低: {low_text}")
                except ValueError:
                    pass
            
            # 查找包含"昨收："的td元素
            close_element = await page.query_selector('xpath=//td[contains(text(), "昨收：")]/following-sibling::td//span//span')
            if close_element:
                close_text = await close_element.inner_text()
                try:
                    data["close"] = float(close_text)
                    print(f"  📄 昨收: {close_text}")
                except ValueError:
                    pass
            
            # 查找包含"成交量："的td元素
            volume_element = await page.query_selector('xpath=//td[contains(text(), "成交量：")]/following-sibling::td//span//span')
            if volume_element:
                volume_text = await volume_element.inner_text()
                try:
                    if '万' in volume_text:
                        data["volume"] = int(float(volume_text.replace('万', '').replace('亿', '')) * 10000)
                    elif '亿' in volume_text:
                        data["volume"] = int(float(volume_text.replace('亿', '')) * 100000000)
                    else:
                        data["volume"] = int(float(volume_text))
                    print(f"  📄 成交量: {volume_text}")
                except ValueError:
                    pass
            
            # 查找包含"换手："的td元素（涨跌幅）
            change_element = await page.query_selector('xpath=//td[contains(text(), "换手：")]/following-sibling::td//span//span')
            if change_element:
                change_text = await change_element.inner_text()
                try:
                    if '%' in change_text:
                        data["change_percent"] = float(change_text.replace('%', ''))
                        print(f"  📄 换手(涨跌幅): {change_text}")
                except ValueError:
                    pass
            
            # 计算涨跌额
            if data["open"] and data["close"]:
                data["change"] = data["close"] - data["open"]
                
        except Exception as e:
            print(f"  ⚠️  从表格提取数据失败: {e}")

        # 确保至少有收盘价才能返回数据
        if data["close"] is not None:
            return data
        return None

class EastMoneyStockCrawler:
    """东方财富股票爬虫主类"""
    
    def __init__(self, db_path: str = None):
        self.extractor = EastMoneyStockExtractor()
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

    def get_eastmoney_url(self, stock_code: str) -> str:
        """获取东方财富股票URL"""
        market_prefix = get_market_prefix(stock_code)
        return f"https://quote.eastmoney.com/{market_prefix}{stock_code}.html"

    async def crawl_stock_price(self, stock_code: str) -> Optional[Dict]:
        """爬取单个股票价格"""
        url = self.get_eastmoney_url(stock_code)
        print(f"🕷️ 爬取东方财富 {stock_code}: {url}")
        
        try:
            page = await self.browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # 提取数据
            data = await self.extractor.extract_stock_data(page, stock_code)
            
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

async def crawl_multiple_stocks(stock_codes: List[str], db_path: str = None):
    """批量爬取多个股票"""
    crawler = EastMoneyStockCrawler(db_path)
    
    try:
        await crawler.init_browser()
        
        results = []
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
            print(f"- {result['code']} ({result['name']}): {result['close']} 元")
            
        return len(results)
        
    except Exception as e:
        print(f"❌ 批量爬取失败: {e}")
        return 0
    finally:
        await crawler.close_browser()

async def main():
    """主函数 - 测试模式"""
    # 数据库路径（如果需要保存到数据库）
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    
    # 测试股票代码
    test_stocks = ["002323", "000001", "600519", "000858", "600036"]
    
    success_count = await crawl_multiple_stocks(test_stocks, db_path)
    
    if success_count > 0:
        print(f"\n🎉 成功爬取 {success_count} 只股票的价格数据！")
        return True
    else:
        print(f"\n❌ 未能成功爬取任何股票数据")
        return False

if __name__ == "__main__":
    import re  # 确保导入re模块
    success = asyncio.run(main())
    sys.exit(0 if success else 1)