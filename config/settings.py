"""配置文件"""

import os

# 数据库路径
DB_PATH = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"

# 数据源配置
DATA_SOURCES = [
    {
        "name": "SinaFinance",
        "base_url": "http://finance.sina.com.cn/realstock/company/{market}{code}/nc.shtml",
        "enabled": True,
        "timeout": 10,
        "retry_count": 3,
    },
    {
        "name": "TencentSecurities",
        "base_url": "https://gu.qq.com/{market}{code}",
        "enabled": False,  # 暂时禁用，需要浏览器自动化
        "timeout": 15,
        "retry_count": 2,
    },
]

# 爬虫配置
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# 批处理配置
BATCH_SIZE = 20
REQUEST_DELAY = (0.5, 1.5)  # 随机延迟范围

# 调试配置
DEBUG = True
