"""爬虫基类"""

import requests
import time
import random
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from config import USER_AGENTS, DEBUG


class BaseScraper:
    """爬虫基类"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.session = requests.Session()
        self.success_count = 0
        self.total_count = 0

    def fetch_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if DEBUG:
                print(f"Request failed for {url}: {e}")
            return None
