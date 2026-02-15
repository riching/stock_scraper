#!/usr/bin/env python3
"""股票数据增量更新调度器"""

import sys
import os
import subprocess
import logging
from datetime import datetime, date, time
import argparse

# 添加项目根目录到Python路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawler.sina.sina_history_crawler import SinaStockCrawler
from config.settings import DB_PATH


class StockUpdateScheduler:
    """股票数据更新调度器"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.setup_logging()

    def setup_logging(self):
        """设置日志"""
        log_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "logs",
        )
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(os.path.join(log_dir, "scheduler.log")),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def is_trading_day(self, check_date=None):
        """检查是否为交易日（简化版：排除周末）"""
        if check_date is None:
            check_date = date.today()
        return check_date.weekday() < 5  # Monday=0, Sunday=6

    async def run_afternoon_update(self):
        """下午更新（3:30后）"""
        if not self.is_trading_day():
            self.logger.info("Today is not a trading day, skipping afternoon update")
            return False

        self.logger.info("Starting afternoon stock data update")
        crawler = SinaStockCrawler()
        await crawler.init_browser()
        
        # 获取股票列表
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM stock_list")
        stock_codes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # 爬取今日数据
        success_count = 0
        for stock_code in stock_codes:
            data = await crawler.crawl_stock_price(stock_code)
            if data:
                success_count += 1
        
        await crawler.close_browser()
        
        success = success_count > 0
        self.logger.info(
            f"Afternoon update completed: {'success' if success else 'no updates'}"
        )
        return success

    async def run_evening_check(self):
        """晚上检查（11:00）"""
        if not self.is_trading_day():
            self.logger.info("Today is not a trading day, skipping evening check")
            return False

        self.logger.info("Starting evening stock data check")
        crawler = SinaStockCrawler()
        await crawler.init_browser()
        
        # 获取股票列表
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM stock_list")
        stock_codes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # 爬取今日数据
        success_count = 0
        for stock_code in stock_codes:
            data = await crawler.crawl_stock_price(stock_code)
            if data:
                success_count += 1
        
        await crawler.close_browser()
        
        success = success_count > 0
        self.logger.info(
            f"Evening check completed: {'success' if success else 'no updates'}"
        )
        return success

    async def run_update_only(self):
        """仅更新模式"""
        self.logger.info("Starting stock data update (update-only mode)")
        crawler = SinaStockCrawler()
        await crawler.init_browser()
        
        # 获取股票列表
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM stock_list")
        stock_codes = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # 爬取今日数据
        success_count = 0
        for stock_code in stock_codes:
            data = await crawler.crawl_stock_price(stock_code)
            if data:
                success_count += 1
        
        await crawler.close_browser()
        
        success = success_count > 0
        self.logger.info(
            f"Update-only completed: {'success' if success else 'no updates'}"
        )
        return success

    def run_check_only(self, check_date=None):
        """仅检查模式"""
        if check_date is None:
            check_date = date.today()

        is_trading = self.is_trading_day(check_date)
        self.logger.info(
            f"Check-only mode: {check_date} is {'trading' if is_trading else 'non-trading'} day"
        )
        return is_trading


def main():
    parser = argparse.ArgumentParser(description="股票数据增量更新调度器")
    parser.add_argument("--afternoon", action="store_true", help="执行下午更新")
    parser.add_argument("--evening", action="store_true", help="执行晚上检查")
    parser.add_argument("--update-only", action="store_true", help="仅执行更新")
    parser.add_argument(
        "--check-only", action="store_true", help="仅检查（不执行更新）"
    )
    parser.add_argument("--date", type=str, help="指定日期进行检查（格式：YYYY-MM-DD）")

    args = parser.parse_args()

    scheduler = StockUpdateScheduler()

    async def run_scheduler():
        try:
            if args.afternoon:
                success = await scheduler.run_afternoon_update()
            elif args.evening:
                success = await scheduler.run_evening_check()
            elif args.update_only:
                success = await scheduler.run_update_only()
            elif args.check_only:
                check_date = None
                if args.date:
                    check_date = datetime.strptime(args.date, "%Y-%m-%d").date()
                success = scheduler.run_check_only(check_date)
            else:
                print("请指定操作模式")
                parser.print_help()
                return 1

            return 0 if success else 1

        except Exception as e:
            scheduler.logger.error(f"Scheduler error: {e}")
            return 1

    import asyncio
    return asyncio.run(run_scheduler())


if __name__ == "__main__":
    sys.exit(main())
