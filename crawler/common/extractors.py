import asyncio
import time
import random
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

# Try to import Playwright, but don't fail if not available
try:
    from playwright.async_api import Page
except ImportError:
    Page = Any


class StockDataExtractor:
    """股票数据提取器基类"""

    def __init__(self):
        self.name = "BaseExtractor"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    async def extract_data(
        self, page: Page, stock_code: str
    ) -> Optional[Dict[str, Any]]:
        """提取股票数据的抽象方法"""
        raise NotImplementedError


class SinaFinanceExtractor(StockDataExtractor):
    """新浪财经数据提取器"""

    def __init__(self):
        super().__init__()
        self.name = "SinaFinance"

    async def extract_data(self, page: Page, stock_code: str) -> Optional[Dict]:
        try:
            content = await page.content()
            data = self._parse_sina_data(content, stock_code)
            return data

        except Exception as e:
            print(f"SinaFinance extraction error for {stock_code}: {e}")
            return None

    def _parse_sina_data(self, html: str, stock_code: str) -> Optional[Dict]:
        """解析新浪财经的HTML内容"""
        data = {
            "code": stock_code,
            "name": None,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
        }

        patterns = {
            "close": r"var now_price\s*=\s*'([^']+)';",
            "open": r"var open_price\s*=\s*'([^']+)';",
            "high": r"var high_price\s*=\s*'([^']+)';",
            "low": r"var low_price\s*=\s*'([^']+)';",
            "volume": r"var volume\s*=\s*'([^']+)';",
            "name": r"var stockName\s*=\s*'([^']+)';",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                try:
                    value = match.group(1).strip()
                    if key == "volume":
                        data[key] = int(value.replace(",", ""))
                    elif key == "name":
                        data[key] = value
                    else:
                        data[key] = float(value)
                except (ValueError, AttributeError):
                    continue

        if data["close"] is not None:
            return data
        return None


class TencentSecuritiesExtractor(StockDataExtractor):
    """腾讯证券数据提取器"""

    def __init__(self):
        super().__init__()
        self.name = "TencentSecurities"

    async def extract_data(self, page: Page, stock_code: str) -> Optional[Dict]:
        try:
            price_selector = ".price, .stock-price, [data-price], .now_price"
            await page.wait_for_selector(price_selector, timeout=8000)

            js_script = """
            () => {
                const data = {};
                const priceSelectors = ['.price', '.stock-price', '[data-price]', '.now_price'];
                for (const selector of priceSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        const text = element.textContent || element.innerText || '';
                        const price = parseFloat(text.replace(/[^0-9.-]/g, ''));
                        if (!isNaN(price)) {
                            data.close = price;
                            break;
                        }
                    }
                }
                const nameElement = document.querySelector('.stock-name, h1, [data-name]');
                if (nameElement) {
                    data.name = nameElement.textContent.trim();
                }
                return data;
            }
            """

            js_data = await page.evaluate(js_script)

            if js_data.get("close"):
                return {
                    "code": stock_code,
                    "name": js_data.get("name"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "close": js_data["close"],
                    "open": None,
                    "high": None,
                    "low": None,
                    "volume": None,
                }

        except Exception as e:
            print(f"TencentSecurities extraction error for {stock_code}: {e}")
            return None


class SinaFinanceExtractor(StockDataExtractor):
    """新浪财经数据提取器"""

    def __init__(self):
        super().__init__()
        self.name = "SinaFinance"

    async def extract_data(self, page: Page, stock_code: str) -> Optional[Dict]:
        try:
            content = await page.content()
            data = self._parse_sina_data(content, stock_code)
            return data

        except Exception as e:
            print(f"SinaFinance extraction error for {stock_code}: {e}")
            return None

    def _parse_sina_data(self, html: str, stock_code: str) -> Dict:
        """解析新浪财经的HTML内容"""
        data = {
            "code": stock_code,
            "name": None,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
        }

        patterns = {
            "close": r"var now_price\s*=\s*'([^']+)';",
            "open": r"var open_price\s*=\s*'([^']+)';",
            "high": r"var high_price\s*=\s*'([^']+)';",
            "low": r"var low_price\s*=\s*'([^']+)';",
            "volume": r"var volume\s*=\s*'([^']+)';",
            "name": r"var stockName\s*=\s*'([^']+)';",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                try:
                    value = match.group(1).strip()
                    if key == "volume":
                        data[key] = int(value.replace(",", ""))
                    elif key == "name":
                        data[key] = value
                    else:
                        data[key] = float(value)
                except (ValueError, AttributeError):
                    continue

        if data["close"] is not None:
            return data
        return None


class TencentSecuritiesExtractor(StockDataExtractor):
    """腾讯证券数据提取器"""

    def __init__(self):
        super().__init__()
        self.name = "TencentSecurities"

    async def extract_data(self, page: Page, stock_code: str) -> Optional[Dict]:
        try:
            price_selector = ".price, .stock-price, [data-price], .now_price"
            await page.wait_for_selector(price_selector, timeout=8000)

            js_script = """
            () => {
                const data = {};
                const priceSelectors = ['.price', '.stock-price', '[data-price]', '.now_price'];
                for (const selector of priceSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        const text = element.textContent || element.innerText || '';
                        const price = parseFloat(text.replace(/[^0-9.-]/g, ''));
                        if (!isNaN(price)) {
                            data.close = price;
                            break;
                        }
                    }
                }
                const nameElement = document.querySelector('.stock-name, h1, [data-name]');
                if (nameElement) {
                    data.name = nameElement.textContent.trim();
                }
                return data;
            }
            """

            js_data = await page.evaluate(js_script)

            if js_data.get("close"):
                return {
                    "code": stock_code,
                    "name": js_data.get("name"),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "close": js_data["close"],
                    "open": None,
                    "high": None,
                    "low": None,
                    "volume": None,
                }

        except Exception as e:
            print(f"TencentSecurities extraction error for {stock_code}: {e}")
            return None
