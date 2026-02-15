#!/usr/bin/env python3
"""多源股票信息爬取器，使用Playwright提取真实数据"""

import sys
import os
import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from utils.deduplication import DeduplicationManager
from utils.incremental_crawler import IncrementalCrawler
from utils.data_saver import save_stock_info_data
from utils.sentiment_calculator import calculate_overall_sentiment_score
from crawler.common.llm_analyzer import LLMAnalyzer
from crawler.common.extractors_new import (
    SinaFinanceNewsExtractor,
    EastMoneyAnnouncementExtractor,
    TonghuashunNewsExtractor,
    TonghuashunAnnouncementExtractor,
    XueqiuNewsExtractor,
    XueqiuCommentExtractor,
)
from utils.monitor_manager import MonitorManager


class MultiSourceInfoCrawler:
    """多源股票信息爬取系统主类"""

    def __init__(self, db_path: str, progress_file: str = "crawl_progress.json"):
        self.db_path = db_path
        self.dedup_manager = DeduplicationManager(db_path)
        self.incremental_crawler = IncrementalCrawler(db_path)
        self.llm_analyzer = LLMAnalyzer()
        self.monitor_manager = MonitorManager(db_path, progress_file)
        self.three_months_ago = (datetime.now() - timedelta(days=90)).strftime(
            "%Y-%m-%d"
        )

        self.sina_news_extractor = SinaFinanceNewsExtractor()
        self.eastmoney_announcement_extractor = EastMoneyAnnouncementExtractor()
        self.tonghuashun_news_extractor = TonghuashunNewsExtractor()
        self.tonghuashun_announcement_extractor = TonghuashunAnnouncementExtractor()
        self.xueqiu_news_extractor = XueqiuNewsExtractor()
        self.xueqiu_comment_extractor = XueqiuCommentExtractor()

    async def crawl_stock_info(self, stock_code: str, page) -> Optional[float]:
        """爬取单个股票的多维度信息"""
        print(f"🚀 开始爬取股票 {stock_code} 的信息...")

        existing_score = self.incremental_crawler.get_default_score_for_stock(
            stock_code
        )
        if existing_score != -1.0:
            print(f"⏭️  股票 {stock_code} 已有近期评分: {existing_score:.2f}")
            return existing_score

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                all_news_data = []
                all_announcement_data = []
                all_comment_data = []
                all_report_data = []

                print(f"📰 提取多源新闻数据...")

                try:
                    sina_news = await self.sina_news_extractor.extract_news(
                        page, stock_code
                    )
                    if sina_news:
                        all_news_data.extend(sina_news)
                    print(f"✅ 新浪财经新闻: {len(sina_news)} 条")
                except Exception as e:
                    print(f"⚠️  新浪财经新闻提取失败: {e}")

                try:
                    xueqiu_news = await self.xueqiu_news_extractor.extract_news(
                        page, stock_code
                    )
                    if xueqiu_news:
                        all_news_data.extend(xueqiu_news)
                    print(f"✅ 雪球新闻: {len(xueqiu_news)} 条")
                except Exception as e:
                    print(f"⚠️  雪球新闻提取失败: {e}")

                try:
                    tonghuashun_news = (
                        await self.tonghuashun_news_extractor.extract_news(stock_code)
                    )
                    if tonghuashun_news:
                        all_news_data.extend(tonghuashun_news)
                    print(f"✅ 同花顺新闻: {len(tonghuashun_news)} 条")
                except Exception as e:
                    print(f"⚠️  同花顺新闻提取失败: {e}")

                print(f"📢 提取多源公告数据...")

                try:
                    eastmoney_announcements = await self.eastmoney_announcement_extractor.extract_announcements(
                        stock_code
                    )
                    if eastmoney_announcements:
                        all_announcement_data.extend(eastmoney_announcements)
                    print(f"✅ 东方财富公告: {len(eastmoney_announcements)} 条")
                except Exception as e:
                    print(f"⚠️  东方财富公告提取失败: {e}")

                try:
                    tonghuashun_announcements = await self.tonghuashun_announcement_extractor.extract_announcements(
                        stock_code
                    )
                    if tonghuashun_announcements:
                        all_announcement_data.extend(tonghuashun_announcements)
                    print(f"✅ 同花顺公告: {len(tonghuashun_announcements)} 条")
                except Exception as e:
                    print(f"⚠️  同花顺公告提取失败: {e}")

                print(f"💬 提取多源评论数据...")

                try:
                    xueqiu_comments = (
                        await self.xueqiu_comment_extractor.extract_comments(
                            page, stock_code
                        )
                    )
                    if xueqiu_comments:
                        all_comment_data.extend(xueqiu_comments)
                    print(f"✅ 雪球评论: {len(xueqiu_comments)} 条")
                except Exception as e:
                    print(f"⚠️  雪球评论提取失败: {e}")

                unique_news = self._filter_unique_items(all_news_data, "news")
                unique_announcements = self._filter_unique_items(
                    all_announcement_data, "announcement"
                )
                unique_comments = self._filter_unique_items(all_comment_data, "comment")

                analyzed_news = await self._analyze_content_batch(unique_news, "news")
                analyzed_announcements = await self._analyze_content_batch(
                    unique_announcements, "announcement"
                )
                analyzed_comments = await self._analyze_content_batch(
                    unique_comments, "comment"
                )

                if analyzed_news:
                    save_stock_info_data(self.db_path, "stock_news", analyzed_news)
                if analyzed_announcements:
                    save_stock_info_data(
                        self.db_path, "stock_announcements", analyzed_announcements
                    )
                if analyzed_comments:
                    save_stock_info_data(
                        self.db_path, "stock_comments", analyzed_comments
                    )

                news_score = self._calculate_average_score(analyzed_news)
                announcement_score = self._calculate_average_score(
                    analyzed_announcements
                )
                comment_score = self._calculate_average_score(analyzed_comments)
                report_score = None

                overall_score = calculate_overall_sentiment_score(
                    news_score, announcement_score, comment_score, report_score
                )

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO stock_sentiment_scores 
                        (code, date, news_score, announcement_score, comment_score, analyst_score, overall_score, analysis_summary)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            stock_code,
                            datetime.now().strftime("%Y-%m-%d"),
                            news_score,
                            announcement_score,
                            comment_score,
                            report_score,
                            overall_score,
                            f"多源爬取: 新闻{len(analyzed_news)}条, 公告{len(analyzed_announcements)}条, 评论{len(analyzed_comments)}条, 重试{retry_count}次",
                        ),
                    )
                    conn.commit()
                    print(f"✅ 股票 {stock_code} 综合评分: {overall_score:.2f}/10")
                except Exception as e:
                    print(f"❌ 保存综合评分失败: {e}")
                    return None
                finally:
                    conn.close()

                self.incremental_crawler.update_crawl_status(
                    stock_code, "news", len(analyzed_news)
                )
                self.incremental_crawler.update_crawl_status(
                    stock_code, "announcement", len(analyzed_announcements)
                )
                self.incremental_crawler.update_crawl_status(
                    stock_code, "comment", len(analyzed_comments)
                )

                print(f"✅ 股票 {stock_code} 信息爬取完成！")
                return overall_score

            except Exception as e:
                print(
                    f"❌ 股票 {stock_code} 爬取失败 (尝试 {retry_count + 1}/{max_retries}): {e}"
                )
                if retry_count < max_retries - 1:
                    retry_count += 1
                    await asyncio.sleep(5 * (retry_count + 1))
                    continue
                else:
                    return None

        return None

    def _filter_unique_items(self, items: List[Dict], content_type: str) -> List[Dict]:
        """过滤重复内容"""
        unique_items = []
        seen_fingerprints = set()
        for item in items:
            if item["fingerprint"] not in seen_fingerprints:
                seen_fingerprints.add(item["fingerprint"])
                unique_items.append(item)
        return unique_items

    async def _analyze_content_batch(
        self, items: List[Dict], content_type: str
    ) -> List[Dict]:
        """批量分析内容"""
        analyzed_items = []
        for item in items:
            if not self.dedup_manager.is_content_exists(
                item["fingerprint"], f"stock_{content_type}s"
            ):
                analysis = self.llm_analyzer.analyze_content(
                    item["content"], content_type
                )
                item.update(
                    {
                        "sentiment_score": analysis["sentiment_score"],
                        "is_valid": analysis["is_valid"],
                        "llm_analysis": json.dumps(analysis),
                    }
                )
                analyzed_items.append(item)
        return analyzed_items

    def _calculate_average_score(self, items: List[Dict]) -> Optional[float]:
        """计算平均分"""
        valid_scores = [
            item["sentiment_score"] for item in items if item.get("is_valid", False)
        ]
        if valid_scores:
            return sum(valid_scores) / len(valid_scores)
        return None

    async def run_full_crawl(self, batch_size: int = 50):
        """运行全量爬取任务"""
        print("🎯 开始全量爬取任务...")
        print("=" * 60)

        stocks_to_process = self.monitor_manager.get_stocks_to_process(batch_size)
        if not stocks_to_process:
            print("📭 所有股票都已处理过，检查现有结果...")
            high_scoring_stocks = self.monitor_manager.get_high_scoring_stocks()
            self.monitor_manager.save_results_to_file(high_scoring_stocks)
            return high_scoring_stocks

        print(
            f"📊 需要处理 {len(stocks_to_process)} 只股票: {stocks_to_process[:10]}{'...' if len(stocks_to_process) > 10 else ''}"
        )

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                ],
            )

            try:
                page = await browser.new_page()
                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )

                scores = {}
                for stock_code in stocks_to_process:
                    try:
                        score = await self.crawl_stock_info(stock_code, page)
                        if score is not None:
                            scores[stock_code] = score
                            self.monitor_manager.mark_stock_success(stock_code, score)
                        else:
                            scores[stock_code] = -1.0
                            self.monitor_manager.mark_stock_failed(
                                stock_code, "爬取失败"
                            )

                        progress = self.monitor_manager.get_progress_summary()
                        print(f"📈 进度: {progress}")

                        await asyncio.sleep(2)

                    except Exception as e:
                        print(f"❌ 股票 {stock_code} 处理异常: {e}")
                        scores[stock_code] = -1.0
                        self.monitor_manager.mark_stock_failed(stock_code, str(e))

                await browser.close()
                await self.eastmoney_announcement_extractor.close_session()
                await self.tonghuashun_news_extractor.close_session()
                await self.tonghuashun_announcement_extractor.close_session()

                print("=" * 60)
                print(f"🎉 批次处理完成！共处理 {len(stocks_to_process)} 只股票")
                print(
                    f"📊 成功: {len([s for s in scores.values() if s != -1.0])}, 失败: {len([s for s in scores.values() if s == -1.0])}"
                )

                high_scoring_stocks = self.monitor_manager.get_high_scoring_stocks()
                self.monitor_manager.save_results_to_file(high_scoring_stocks)

                return high_scoring_stocks

            except Exception as e:
                print(f"❌ 浏览器操作失败: {e}")
                await browser.close()
                raise


async def main():
    """主函数"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    crawler = MultiSourceInfoCrawler(db_path)

    print("🚀 开始全量数据爬取...")
    try:
        high_scoring_stocks = await crawler.run_full_crawl(batch_size=50)
        print(f"\n🎉 全量爬取完成！找到 {len(high_scoring_stocks)} 只高评分股票")

        print("\n🏆 前10名股票:")
        for i, stock in enumerate(high_scoring_stocks[:10], 1):
            if stock["score"] == -1.0:
                print(f"{i:2d}. {stock['code']} - 默认评分(-1)")
            else:
                print(f"{i:2d}. {stock['code']} - {stock['score']:.2f}/10")

    except KeyboardInterrupt:
        print("\n⚠️  用户中断，保存当前进度...")
        pass
    except Exception as e:
        print(f"\n❌ 爬取过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
