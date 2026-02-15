#!/usr/bin/env python3
"""实用工具模块"""

import hashlib
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional


# 安全的哈希函数，处理可能的缺失算法
def safe_md5(data: str) -> str:
    """安全的MD5哈希函数，处理编码问题"""
    try:
        return hashlib.md5(data.encode("utf-8")).hexdigest()
    except Exception as e:
        # 如果MD5不可用，使用简单的哈希作为备选（虽然安全性较低）
        print(f"警告: MD5哈希失败，使用备选方案: {e}")
        return str(hash(data))[:32]


class DeduplicationManager:
    """去重管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def generate_content_fingerprint(
        self, title: str, content: str, source: str
    ) -> str:
        """生成内容指纹用于去重"""
        # 组合关键字段，只取内容前500字符避免过长
        fingerprint_input = f"{title.strip()}|{content[:500].strip()}|{source}"
        return safe_md5(fingerprint_input)

    def generate_url_fingerprint(self, url: str) -> str:
        """生成URL指纹"""
        return safe_md5(url)

    def is_content_exists(self, fingerprint: str, table_name: str) -> bool:
        """检查内容是否已存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                f"SELECT id FROM {table_name} WHERE fingerprint = ?", (fingerprint,)
            )
            exists = cursor.fetchone() is not None
            return exists
        finally:
            conn.close()

    def is_url_exists(self, url: str, table_name: str) -> bool:
        """检查URL是否已存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(f"SELECT id FROM {table_name} WHERE url = ?", (url,))
            exists = cursor.fetchone() is not None
            return exists
        finally:
            conn.close()


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


def save_stock_info_data(db_path: str, table_name: str, data_list: list):
    """保存股票信息数据到数据库"""
    if not data_list:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        for item in data_list:
            # 确保必填字段存在
            required_fields = [
                "code",
                "title",
                "content",
                "source",
                "publish_date",
                "url",
                "fingerprint",
            ]
            for field in required_fields:
                if field not in item or item[field] is None:
                    print(f"警告: 缺少必要字段 {field}，跳过此条目")
                    continue

            # 插入数据
            if table_name == "stock_news":
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO stock_news 
                    (code, title, content, source, publish_date, url, fingerprint, created_at, sentiment_score, is_valid, llm_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item["code"],
                        item["title"],
                        item["content"],
                        item["source"],
                        item["publish_date"],
                        item["url"],
                        item["fingerprint"],
                        datetime.now().isoformat(),
                        item.get("sentiment_score"),
                        item.get("is_valid", 1),
                        item.get("llm_analysis"),
                    ),
                )
            elif table_name == "stock_announcements":
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO stock_announcements 
                    (code, title, content, announcement_type, publish_date, url, fingerprint, created_at, sentiment_score, is_valid, llm_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item["code"],
                        item["title"],
                        item["content"],
                        item.get("announcement_type"),
                        item["publish_date"],
                        item["url"],
                        item["fingerprint"],
                        datetime.now().isoformat(),
                        item.get("sentiment_score"),
                        item.get("is_valid", 1),
                        item.get("llm_analysis"),
                    ),
                )
            elif table_name == "stock_comments":
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO stock_comments 
                    (code, content, author, platform, publish_date, url, likes, fingerprint, created_at, sentiment_score, is_valid, llm_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item["code"],
                        item["content"],
                        item.get("author"),
                        item["platform"],
                        item["publish_date"],
                        item["url"],
                        item.get("likes", 0),
                        item["fingerprint"],
                        datetime.now().isoformat(),
                        item.get("sentiment_score"),
                        item.get("is_valid", 1),
                        item.get("llm_analysis"),
                    ),
                )
            elif table_name == "analyst_reports":
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO analyst_reports 
                    (code, title, summary, broker, analyst, rating, target_price, publish_date, url, fingerprint, created_at, sentiment_score, is_valid, llm_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item["code"],
                        item["title"],
                        item.get("summary"),
                        item.get("broker"),
                        item.get("analyst"),
                        item.get("rating"),
                        item.get("target_price"),
                        item["publish_date"],
                        item["url"],
                        item["fingerprint"],
                        datetime.now().isoformat(),
                        item.get("sentiment_score"),
                        item.get("is_valid", 1),
                        item.get("llm_analysis"),
                    ),
                )

        conn.commit()
        print(f"✅ 成功保存 {len(data_list)} 条记录到 {table_name}")

    except Exception as e:
        print(f"❌ 保存数据到 {table_name} 时出错: {e}")
        conn.rollback()
    finally:
        conn.close()


def calculate_overall_sentiment_score(
    news_score: Optional[float] = None,
    announcement_score: Optional[float] = None,
    comment_score: Optional[float] = None,
    report_score: Optional[float] = None,
) -> float:
    """计算综合情感评分"""
    scores = []
    weights = []

    if news_score is not None and isinstance(news_score, (int, float)):
        scores.append(float(news_score))
        weights.append(0.3)  # 新闻权重30%

    if announcement_score is not None and isinstance(announcement_score, (int, float)):
        scores.append(float(announcement_score))
        weights.append(0.25)  # 公告权重25%

    if comment_score is not None and isinstance(comment_score, (int, float)):
        scores.append(float(comment_score))
        weights.append(0.2)  # 评论权重20%

    if report_score is not None and isinstance(report_score, (int, float)):
        scores.append(float(report_score))
        weights.append(0.25)  # 报告权重25%

    if not scores:
        return 5.0  # 默认中性分数

    # 归一化权重
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # 加权平均
    overall_score = sum(
        score * weight for score, weight in zip(scores, normalized_weights)
    )
    return round(overall_score, 2)
