import asyncio
import time
import random
import re
import json
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

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


class APIStockDataExtractor(StockDataExtractor):
    """基于API的股票数据提取器基类"""

    def __init__(self):
        super().__init__()
        self.session = None
        self.timeout = 10

    async def get_session(self):
        """获取aiohttp session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close_session(self):
        """关闭session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def make_api_request(
        self, url: str, headers: Optional[Dict] = None
    ) -> Optional[Dict]:
        """发起API请求"""
        try:
            session = await self.get_session()
            if headers is None:
                headers = {"User-Agent": random.choice(self.user_agents)}

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        return await response.json()
                    else:
                        # 尝试解析JSON，即使Content-Type不是JSON
                        text = await response.text()
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            print(f"API响应不是有效的JSON: {url}")
                            return None
                else:
                    print(f"API请求失败，状态码: {response.status}, URL: {url}")
                    return None
        except Exception as e:
            print(f"API请求异常: {e}, URL: {url}")
            return None

    async def extract_data_from_api(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """从API提取数据的抽象方法"""
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
            return None

        except Exception as e:
            print(f"TencentSecurities extraction error for {stock_code}: {e}")
            return None


class SinaFinanceNewsExtractor:
    """新浪财经新闻提取器"""

    def __init__(self):
        self.name = "SinaFinanceNews"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    async def extract_news(self, page: Page, stock_code: str) -> List[Dict]:
        """提取新浪财经新闻"""
        try:
            # 新浪财经股票新闻URL模式
            news_url = f"http://finance.sina.com.cn/stock/relnews/{stock_code}.shtml"
            await page.goto(news_url, wait_until="domcontentloaded", timeout=10000)

            # 等待新闻列表加载
            await page.wait_for_selector(".list_001 li", timeout=5000)

            # 提取新闻列表
            news_items = []
            news_elements = await page.query_selector_all(".list_001 li")

            for element in news_elements[:10]:  # 限制获取前10条
                try:
                    title_element = await element.query_selector("a")
                    date_element = await element.query_selector(".time")

                    if title_element:
                        title = await title_element.text_content()
                        href = await title_element.get_attribute("href")

                        if href and title:
                            # 获取新闻详情
                            detail_page = await page.context.new_page()
                            try:
                                await detail_page.goto(
                                    href, wait_until="domcontentloaded", timeout=8000
                                )

                                # 提取新闻内容
                                content_element = await detail_page.query_selector(
                                    ".article-content"
                                )
                                if content_element:
                                    content = await content_element.text_content()
                                else:
                                    content = ""

                                # 提取发布日期
                                publish_date = datetime.now().strftime("%Y-%m-%d")
                                if date_element:
                                    date_text = await date_element.text_content()
                                    if date_text:
                                        publish_date = self._parse_date(date_text)

                                news_item = {
                                    "code": stock_code,
                                    "title": title.strip(),
                                    "content": content.strip(),
                                    "source": "SinaFinance",
                                    "publish_date": publish_date,
                                    "url": href,
                                    "fingerprint": self._generate_fingerprint(
                                        title, content, "SinaFinance"
                                    ),
                                }
                                news_items.append(news_item)

                            except Exception as e:
                                print(
                                    f"Error extracting news detail for {stock_code}: {e}"
                                )
                            finally:
                                await detail_page.close()

                except Exception as e:
                    print(f"Error extracting news item for {stock_code}: {e}")
                    continue

            return news_items

        except Exception as e:
            print(f"SinaFinance news extraction error for {stock_code}: {e}")
            return []

    def _generate_fingerprint(self, title: str, content: str, source: str) -> str:
        """生成内容指纹"""
        from utils import safe_md5

        fingerprint_input = f"{title.strip()}|{content[:500].strip()}|{source}"
        return safe_md5(fingerprint_input)

    def _parse_date(self, date_str: str) -> str:
        """解析日期字符串"""
        # 简单的日期解析，实际项目中可能需要更复杂的逻辑
        try:
            if "-" in date_str:
                parts = date_str.split("-")
                if len(parts) >= 3:
                    return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            return datetime.now().strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")


class TonghuashunNewsExtractor(APIStockDataExtractor):
    """同花顺新闻提取器（基于API）"""

    def __init__(self):
        super().__init__()
        self.name = "TonghuashunNews"

    async def extract_news(self, stock_code: str) -> List[Dict]:
        """提取同花顺新闻"""
        try:
            # 同花顺新闻API（模拟，实际可能需要token）
            # 由于同花顺的API通常需要认证，我们使用网页爬取作为备选
            market_prefix = "sh" if stock_code.startswith(("6", "9")) else "sz"
            news_url = (
                f"http://news.10jqka.com.cn/tapple/s/{market_prefix}{stock_code}/"
            )

            print(f"📡 请求同花顺新闻页面: {news_url}")
            response_data = await self.make_api_request(news_url)

            if not response_data:
                # 尝试直接解析HTML内容
                import aiohttp

                session = await self.get_session()
                async with session.get(
                    news_url, headers={"User-Agent": random.choice(self.user_agents)}
                ) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        # 简单的HTML解析
                        news_items = self._parse_tonghuashun_news_html(
                            html_content, stock_code
                        )
                        return news_items

            return []

        except Exception as e:
            print(f"❌ 同花顺新闻提取失败 {stock_code}: {e}")
            return []

    def _parse_tonghuashun_news_html(self, html: str, stock_code: str) -> List[Dict]:
        """解析同花顺新闻HTML"""
        try:
            import re

            news_items = []

            # 简单的正则表达式匹配新闻标题和链接
            # 这里需要根据实际HTML结构调整
            title_pattern = (
                r'<a[^>]*href="([^"]*news\.10jqka\.com\.cn[^"]*)"[^>]*>([^<]+)</a>'
            )
            matches = re.findall(title_pattern, html, re.IGNORECASE)

            for href, title in matches[:10]:
                news_item = {
                    "code": stock_code,
                    "title": title.strip(),
                    "content": "",  # 需要单独请求详情页
                    "source": "Tonghuashun",
                    "publish_date": datetime.now().strftime("%Y-%m-%d"),
                    "url": href,
                    "fingerprint": self._generate_fingerprint(title, "", "Tonghuashun"),
                }
                news_items.append(news_item)

            return news_items
        except Exception as e:
            print(f"解析同花顺新闻HTML失败: {e}")
            return []

    def _generate_fingerprint(self, title: str, content: str, source: str) -> str:
        """生成内容指纹"""
        from utils import safe_md5

        fingerprint_input = f"{title.strip()}|{content[:500].strip()}|{source}"
        return safe_md5(fingerprint_input)


class XueqiuNewsExtractor:
    """雪球新闻提取器（基于Playwright）"""

    def __init__(self):
        self.name = "XueqiuNews"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    async def extract_news(self, page, stock_code: str) -> List[Dict]:
        """提取雪球新闻（使用Playwright页面）"""
        try:
            # 雪球股票代码需要添加市场前缀
            market_prefix = "SH" if stock_code.startswith(("6", "9")) else "SZ"
            symbol = f"{market_prefix}{stock_code}"

            # 访问雪球股票页面
            await page.goto(
                f"https://xueqiu.com/S/{symbol}",
                wait_until="networkidle",
                timeout=15000,
            )

            # 提取动态内容
            news_items = []
            timeline_items = await page.query_selector_all(".timeline-item")

            for item in timeline_items[:10]:
                try:
                    # 尝试多种选择器获取标题和内容
                    title = ""
                    content = ""

                    # 尝试获取标题
                    title_element = await item.query_selector(".title a")
                    if title_element:
                        title = await title_element.text_content()

                    # 尝试获取内容
                    content_element = await item.query_selector(".content .text")
                    if not content_element:
                        content_element = await item.query_selector(".content")
                    if content_element:
                        content = await content_element.text_content()

                    # 如果没有标题，尝试从内容中提取
                    if not title and content:
                        title = content[:50] + "..." if len(content) > 50 else content

                    if title and len(title.strip()) > 10:
                        news_item = {
                            "code": stock_code,
                            "title": title.strip(),
                            "content": content.strip(),
                            "source": "Xueqiu",
                            "publish_date": datetime.now().strftime("%Y-%m-%d"),
                            "url": f"https://xueqiu.com/S/{symbol}",
                            "fingerprint": self._generate_fingerprint(
                                title, content, "Xueqiu"
                            ),
                        }
                        news_items.append(news_item)

                except Exception as e:
                    print(f"Error processing Xueqiu news item: {e}")
                    continue

            print(f"✅ 雪球新闻提取成功: {len(news_items)} 条")
            return news_items

        except Exception as e:
            print(f"❌ 雪球新闻提取失败 {stock_code}: {e}")
            return []

    def _generate_fingerprint(self, title: str, content: str, source: str) -> str:
        """生成内容指纹"""
        from utils import safe_md5

        fingerprint_input = f"{title.strip()}|{content[:500].strip()}|{source}"
        return safe_md5(fingerprint_input)


class XueqiuCommentExtractor:
    """雪球评论提取器（基于Playwright）"""

    def __init__(self):
        self.name = "XueqiuComment"
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    async def extract_comments(self, page, stock_code: str) -> List[Dict]:
        """提取雪球评论（使用Playwright页面）"""
        try:
            # 雪球股票代码需要添加市场前缀
            market_prefix = "SH" if stock_code.startswith(("6", "9")) else "SZ"
            symbol = f"{market_prefix}{stock_code}"

            # 访问雪球股票页面
            await page.goto(
                f"https://xueqiu.com/S/{symbol}",
                wait_until="networkidle",
                timeout=15000,
            )

            # 提取评论
            comments = []
            comment_items = await page.query_selector_all(".comment-item")

            for item in comment_items[:10]:
                try:
                    # 提取评论内容
                    content_element = await item.query_selector(".content .text")
                    if not content_element:
                        content_element = await item.query_selector(".content")

                    content = ""
                    if content_element:
                        content = await content_element.text_content()

                    # 提取作者
                    author_element = await item.query_selector(".user-info .name")
                    author = ""
                    if author_element:
                        author = await author_element.text_content()

                    # 提取点赞数
                    likes_element = await item.query_selector(".like-count")
                    likes = 0
                    if likes_element:
                        likes_text = await likes_element.text_content()
                        try:
                            likes = int(likes_text)
                        except:
                            likes = 0

                    if content and len(content.strip()) > 10:
                        comment_item = {
                            "code": stock_code,
                            "content": content.strip(),
                            "author": author.strip() if author else "匿名",
                            "platform": "Xueqiu",
                            "publish_date": datetime.now().strftime("%Y-%m-%d"),
                            "url": f"https://xueqiu.com/S/{symbol}",
                            "likes": likes,
                            "fingerprint": self._generate_fingerprint(
                                content, author, "Xueqiu"
                            ),
                        }
                        comments.append(comment_item)

                except Exception as e:
                    print(f"Error processing Xueqiu comment item: {e}")
                    continue

            print(f"✅ 雪球评论提取成功: {len(comments)} 条")
            return comments

        except Exception as e:
            print(f"❌ 雪球评论提取失败 {stock_code}: {e}")
            return []

    def _generate_fingerprint(self, content: str, author: str, source: str) -> str:
        """生成内容指纹"""
        from utils import safe_md5

        fingerprint_input = f"{content.strip()}|{author.strip()}|{source}"
        return safe_md5(fingerprint_input)


class TonghuashunAnnouncementExtractor(APIStockDataExtractor):
    """同花顺公告提取器（基于API）"""

    def __init__(self):
        super().__init__()
        self.name = "TonghuashunAnnouncement"

    async def extract_announcements(self, stock_code: str) -> List[Dict]:
        """提取同花顺公告"""
        try:
            # 同花顺公告页面
            announcement_url = (
                f"http://basic.10jqka.com.cn/{stock_code}/announcement.html"
            )

            print(f"📡 请求同花顺公告页面: {announcement_url}")
            import aiohttp

            session = await self.get_session()
            async with session.get(
                announcement_url,
                headers={"User-Agent": random.choice(self.user_agents)},
            ) as response:
                if response.status == 200:
                    html_content = await response.text()
                    announcements = self._parse_tonghuashun_announcements_html(
                        html_content, stock_code
                    )
                    return announcements

            return []

        except Exception as e:
            print(f"❌ 同花顺公告提取失败 {stock_code}: {e}")
            return []

    def _parse_tonghuashun_announcements_html(
        self, html: str, stock_code: str
    ) -> List[Dict]:
        """解析同花顺公告HTML"""
        try:
            import re

            announcements = []

            # 简单的正则表达式匹配公告
            # 实际实现需要根据具体HTML结构调整
            pattern = (
                r'<a[^>]*href="([^"]*basic\.10jqka\.com\.cn[^"]*)"[^>]*>([^<]+)</a>'
            )
            matches = re.findall(pattern, html, re.IGNORECASE)

            for href, title in matches[:10]:
                announcement_item = {
                    "code": stock_code,
                    "title": title.strip(),
                    "content": "",
                    "announcement_type": "公告",
                    "publish_date": datetime.now().strftime("%Y-%m-%d"),
                    "url": href,
                    "fingerprint": self._generate_fingerprint(title, "", "Tonghuashun"),
                }
                announcements.append(announcement_item)

            return announcements
        except Exception as e:
            print(f"解析同花顺公告HTML失败: {e}")
            return []

    def _generate_fingerprint(self, title: str, content: str, source: str) -> str:
        """生成内容指纹"""
        from utils import safe_md5

        fingerprint_input = f"{title.strip()}|{content[:500].strip()}|{source}"
        return safe_md5(fingerprint_input)

    def _parse_date(self, date_str: str) -> str:
        """解析日期字符串"""
        try:
            if "-" in date_str:
                parts = date_str.split("-")
                if len(parts) >= 3:
                    return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            return datetime.now().strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")


class EastMoneyAnnouncementExtractor(APIStockDataExtractor):
    """东方财富公告提取器（基于API）"""

    def __init__(self):
        super().__init__()
        self.name = "EastMoneyAnnouncement"

    async def extract_announcements(self, stock_code: str) -> List[Dict]:
        """提取东方财富公告"""
        try:
            # 构造东方财富公告API URL
            # 东方财富公告API通常需要通过搜索接口
            market_code = "1" if stock_code.startswith(("6", "9")) else "0"
            api_url = f"https://datacenter.eastmoney.com/api/data/v1/get?callback=&sortColumns=NOTICEDATE&sortTypes=-1&pageSize=20&pageNumber=1&reportName=RPT_ANNOUNCEMENT_RESEARCH&columns=ALL&filter=(SECURITY_CODE%3D%22{stock_code}%22)"

            print(f"📡 请求东方财富公告API: {api_url}")
            response_data = await self.make_api_request(api_url)

            if not response_data:
                print(f"⚠️  东方财富公告API返回空数据: {stock_code}")
                return []

            # 解析API响应
            announcements = []
            if isinstance(response_data, dict) and "result" in response_data:
                result = response_data["result"]
                if isinstance(result, dict) and "data" in result:
                    announcement_list = result["data"]
                    for item in announcement_list[:10]:  # 限制获取前10条
                        try:
                            title = item.get("NOTICETITLE", "")
                            content = item.get("NOTICECONTENT", "")
                            publish_date = item.get("NOTICEDATE", "")
                            url = item.get("PDF_URL", "")

                            if not url:
                                # 构造公告详情页URL
                                notice_id = item.get("INFO_CODE", "")
                                if notice_id:
                                    url = (
                                        f"https://pdf.dfcfw.com/pdf/H2_{notice_id}.pdf"
                                    )

                            if title and content:
                                # 标准化日期格式
                                if publish_date:
                                    # 东方财富日期格式通常是 "2024-01-15 10:30:00"
                                    publish_date = publish_date.split(" ")[0]
                                else:
                                    publish_date = datetime.now().strftime("%Y-%m-%d")

                                announcement_item = {
                                    "code": stock_code,
                                    "title": title.strip(),
                                    "content": content.strip(),
                                    "announcement_type": item.get("TYPE_NAME", "公告"),
                                    "publish_date": publish_date,
                                    "url": url,
                                    "fingerprint": self._generate_fingerprint(
                                        title, content, "EastMoney"
                                    ),
                                }
                                announcements.append(announcement_item)

                        except Exception as e:
                            print(f"Error processing EastMoney announcement item: {e}")
                            continue

            print(f"✅ 东方财富公告提取成功: {len(announcements)} 条")
            return announcements

        except Exception as e:
            print(f"❌ 东方财富公告提取失败 {stock_code}: {e}")
            return []

    def _generate_fingerprint(self, title: str, content: str, source: str) -> str:
        """生成内容指纹"""
        from utils import safe_md5

        fingerprint_input = f"{title.strip()}|{content[:500].strip()}|{source}"
        return safe_md5(fingerprint_input)
