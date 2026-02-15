#!/usr/bin/env python3
"""增量爬虫管理器模块"""

import sqlite3
from datetime import datetime
from .deduplication import DeduplicationManager


class IncrementalCrawler:
    """增量爬虫管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.dedup_manager = DeduplicationManager(db_path)

    def should_crawl_stock(self, stock_code: str, content_type: str) -> bool:
        """判断是否需要爬取某只股票的特定类型内容"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 获取上次爬取时间
            cursor.execute(
                """
                SELECT last_crawl_time FROM crawl_status 
                WHERE code = ? AND content_type = ?
            """,
                (stock_code, content_type),
            )
            result = cursor.fetchone()

            if result is None:
                # 从未爬取过，需要爬取
                return True

            last_crawl_time = result[0]
            if last_crawl_time is None:
                return True

            # 计算时间间隔（小时）
            last_crawl_dt = datetime.fromisoformat(last_crawl_time)
            hours_since_crawl = (datetime.now() - last_crawl_dt).total_seconds() / 3600

            # 根据内容类型设置爬取频率
            if content_type == "news":
                return hours_since_crawl > 2  # 新闻每2小时爬取一次
            elif content_type == "announcement":
                return hours_since_crawl > 6  # 公告每6小时爬取一次
            elif content_type == "comment":
                return hours_since_crawl > 1  # 评论每1小时爬取一次
            elif content_type == "report":
                return hours_since_crawl > 12  # 报告每12小时爬取一次
            else:
                return hours_since_crawl > 6  # 默认6小时

        finally:
            conn.close()

    def get_default_score_for_stock(self, stock_code: str) -> float:
        """获取股票的默认评分（-1表示未处理）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 检查是否有近期的综合评分
            cursor.execute(
                """
                SELECT overall_score FROM stock_sentiment_scores 
                WHERE code = ? AND date >= date('now', '-30 days')
                ORDER BY date DESC LIMIT 1
                """,
                (stock_code,),
            )
            result = cursor.fetchone()

            if result and result[0] is not None:
                return float(result[0])
            else:
                return -1.0  # 默认评分-1表示未处理

        finally:
            conn.close()

    def update_crawl_status(
        self, stock_code: str, content_type: str, success_count: int = 0
    ):
        """更新爬取状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT OR REPLACE INTO crawl_status 
                (code, content_type, last_crawl_time, total_count, status)
                VALUES (?, ?, ?, 
                    COALESCE((SELECT total_count FROM crawl_status WHERE code = ? AND content_type = ?), 0) + ?,
                    'active'
                )
            """,
                (
                    stock_code,
                    content_type,
                    now,
                    stock_code,
                    content_type,
                    success_count,
                ),
            )

            conn.commit()
        finally:
            conn.close()
