#!/usr/bin/env python3
"""数据保存模块"""

import sqlite3
from datetime import datetime


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
