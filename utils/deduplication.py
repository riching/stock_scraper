#!/usr/bin/env python3
"""去重管理器模块"""

import hashlib
import sqlite3
from datetime import datetime


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
