#!/usr/bin/env python3
"""多线程生产者-消费者历史数据爬虫"""

import sys
import os
import threading
import asyncio
import time
from queue import Queue
from datetime import datetime
from typing import Dict, List, Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.stock_database import StockDatabase
from crawler.sina.sina_history_crawler_fixed import SinaStockCrawler
from crawler.eastmoney.history_crawler import EnhancedEastMoneyCrawler
from utils.akshare_data import AkshareDataFetcher
from crawler.baostock.baostock_history_crawler import BaostockStockCrawler
from crawler.yahoo_finance.yahoo_finance_history_crawler import YahooFinanceStockCrawler


class WorkerStats:
    """消费者统计信息"""
    
    def __init__(self, worker_name: str):
        self.worker_name = worker_name
        self.success_count = 0
        self.failure_count = 0
        self.call_count = 0
        self.lock = threading.Lock()
    
    def add_success(self):
        with self.lock:
            self.success_count += 1
            self.call_count += 1
    
    def add_failure(self):
        with self.lock:
            self.failure_count += 1
            self.call_count += 1
    
    def get_failure_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return (self.failure_count / total) * 100
    
    def get_summary(self) -> Dict:
        return {
            "worker_name": self.worker_name,
            "success": self.success_count,
            "failure": self.failure_count,
            "failure_rate": self.get_failure_rate(),
            "call_count": self.call_count
        }


class BaseWorker(threading.Thread):
    """消费者基类"""
    
    def __init__(self, queue: Queue, db_path: str, target_date: str, max_calls: int):
        super().__init__()
        self.queue = queue
        self.db_path = db_path
        self.target_date = target_date
        self.max_calls = max_calls
        self.stats = WorkerStats(self.__class__.__name__)
        self.running = True
    
    def run(self):
        """线程主循环"""
        print(f"🚀 {self.__class__.__name__} 启动")
        
        with StockDatabase(self.db_path) as db:
            while self.running and self.stats.call_count < self.max_calls:
                try:
                    if self.queue.empty():
                        print(f"⏸️  {self.__class__.__name__}: 队列为空，等待任务...")
                        break
                    
                    stock_code = self.queue.get(timeout=5)
                    
                    if stock_code is None:
                        print(f"🛑 {self.__class__.__name__}: 收到终止信号")
                        break
                    
                    print(f"🔄 {self.__class__.__name__} 处理 {stock_code}")
                    
                    data = self.crawl_stock(stock_code)
                    
                    if self.validate_data(data):
                        if self.save_to_database(db, data):
                            self.stats.add_success()
                            print(f"✅ {self.__class__.__name__} 成功爬取 {stock_code}")
                        else:
                            self.stats.add_failure()
                            print(f"❌ {self.__class__.__name__} 保存 {stock_code} 失败，重新放回队列")
                            self.queue.put(stock_code)
                    else:
                        self.stats.add_failure()
                        print(f"⚠️  {self.__class__.__name__} {stock_code} 数据无效，重新放回队列")
                        self.queue.put(stock_code)
                    
                    self.queue.task_done()
                    
                    time.sleep(1)
                    
                except Exception as e:
                    self.stats.add_failure()
                    print(f"❌ {self.__class__.__name__} 处理异常: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"🏁 {self.__class__.__name__} 结束")
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取股票数据（子类实现）"""
        raise NotImplementedError
    
    def validate_data(self, data: Dict) -> bool:
        """验证数据完整性"""
        if not data:
            return False
        
        required_fields = ['open', 'high', 'low', 'close']
        
        for field in required_fields:
            value = data.get(field)
            if value is None or value <= 0:
                return False
        
        return True
    
    def save_to_database(self, db: StockDatabase, data: Dict) -> bool:
        """保存到数据库"""
        try:
            if db.exists_stock_data(data["code"], data["date"]):
                print(f"⚠️  {data['code']} {data['date']} 数据已存在，跳过")
                return True
            
            return db.insert_stock_data(data)
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")
            return False
    
    def stop(self):
        """停止线程"""
        self.running = False


class SinaWorker(BaseWorker):
    """新浪爬虫线程"""
    
    def __init__(self, queue: Queue, db_path: str, target_date: str, max_calls: int):
        super().__init__(queue, db_path, target_date, max_calls)
        self.crawler = SinaStockCrawler(self.db_path)
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取股票数据"""
        try:
            data = asyncio.run(
                self.crawler.crawl_stock_price(stock_code, self.target_date)
            )
            return data
        except Exception as e:
            print(f"❌ 新浪爬虫爬取 {stock_code} 失败: {e}")
            return None


class EastMoneyWorker(BaseWorker):
    """东方财富爬虫线程"""
    
    def __init__(self, queue: Queue, db_path: str, target_date: str, max_calls: int):
        super().__init__(queue, db_path, target_date, max_calls)
        self.crawler = EnhancedEastMoneyCrawler()
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取股票数据"""
        try:
            data = asyncio.run(
                self.crawler.crawl_history_price(stock_code, self.target_date)
            )
            return data
        except Exception as e:
            print(f"❌ 东方财富爬虫爬取 {stock_code} 失败: {e}")
            return None


class AkshareWorker(BaseWorker):
    """Akshare爬虫线程"""
    
    def __init__(self, queue: Queue, db_path: str, target_date: str, max_calls: int):
        super().__init__(queue, db_path, target_date, max_calls)
        self.crawler = AkshareDataFetcher()
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取股票数据"""
        try:
            data = self.crawler.get_historical_price(stock_code, self.target_date)
            return data
        except Exception as e:
            print(f"❌ Akshare爬虫爬取 {stock_code} 失败: {e}")
            return None


class BaostockWorker(BaseWorker):
    """Baostock爬虫线程"""
    
    def __init__(self, queue: Queue, db_path: str, target_date: str, max_calls: int):
        super().__init__(queue, db_path, target_date, max_calls)
        self.crawler = BaostockStockCrawler(self.db_path)
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取股票数据"""
        try:
            data = asyncio.run(
                self.crawler.crawl_history_price(stock_code, self.target_date)
            )
            return data
        except Exception as e:
            print(f"❌ Baostock爬虫爬取 {stock_code} 失败: {e}")
            return None
    
    def stop(self):
        """停止线程并登出"""
        super().stop()
        if self.crawler:
            try:
                self.crawler.fetcher.logout()
                print(f"✅ Baostock已登出")
            except Exception as e:
                print(f"❌ Baostock登出失败: {e}")


class YahooFinanceWorker(BaseWorker):
    """Yahoo Finance爬虫线程"""
    
    def __init__(self, queue: Queue, db_path: str, target_date: str, max_calls: int):
        super().__init__(queue, db_path, target_date, max_calls)
        self.crawler = YahooFinanceStockCrawler(self.db_path)
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取股票数据"""
        try:
            data = asyncio.run(
                self.crawler.crawl_history_price(stock_code, self.target_date)
            )
            return data
        except Exception as e:
            print(f"❌ Yahoo Finance爬虫爬取 {stock_code} 失败: {e}")
            return None


class MultiThreadHistoryCrawler:
    """多线程生产者-消费者爬虫"""
    
    def __init__(self, db_path: str, target_date: str, max_calls: int = 5000):
        self.db_path = db_path
        self.target_date = target_date
        self.max_calls = max_calls
        self.queue = Queue()
        self.workers = []
    
    def load_stock_codes(self) -> List[str]:
        """加载所有股票代码"""
        with StockDatabase(self.db_path) as db:
            codes = db.get_all_stock_codes()
            print(f"📋 从数据库加载了 {len(codes)} 只股票")
            return codes
    
    def clean_database(self) -> int:
        """清理指定日期的数据"""
        with StockDatabase(self.db_path) as db:
            deleted_count = db.clean_date_data(self.target_date)
            print(f"🗑️  已清理 {deleted_count} 条 {self.target_date} 的历史数据")
            return deleted_count
    
    def start_workers(self):
                """启动消费者线程"""
                worker_classes = [EastMoneyWorker, AkshareWorker, BaostockWorker, YahooFinanceWorker]
                
                for worker_class in worker_classes:
                    worker = worker_class(
                        self.queue,
                        self.db_path,
                        self.target_date,
                        self.max_calls
                    )
                    worker.start()
                    self.workers.append(worker)
                
                print(f"🚀 已启动 {len(self.workers)} 个消费者线程")
    
    def wait_for_completion(self):
        """等待所有任务完成"""
        print("⏳ 等待所有任务完成...")
        self.queue.join()
        print("✅ 所有任务已完成")
    
    def stop_workers(self):
        """停止所有消费者线程"""
        print("🛑 停止所有消费者线程...")
        
        for _ in self.workers:
            self.queue.put(None)
        
        for worker in self.workers:
            worker.join(timeout=10)
            if worker.is_alive():
                print(f"⚠️  {worker.__class__.__name__} 未正常退出，强制停止")
                worker.stop()
        
        print("✅ 所有消费者线程已停止")
    
    def print_summary(self):
        """打印统计报告"""
        print("\n" + "=" * 60)
        print("📊 爬虫统计报告")
        print("=" * 60)
        
        total_success = 0
        total_failure = 0
        
        for worker in self.workers:
            summary = worker.stats.get_summary()
            total_success += summary['success']
            total_failure += summary['failure']
            
            print(f"\n{summary['worker_name']}:")
            print(f"  成功: {summary['success']}")
            print(f"  失败: {summary['failure']}")
            print(f"  失败率: {summary['failure_rate']:.2f}%")
            print(f"  调用次数: {summary['call_count']}")
        
        print("\n" + "-" * 60)
        print("整体统计:")
        print(f"  成功: {total_success}")
        print(f"  失败: {total_failure}")
        
        total = total_success + total_failure
        if total > 0:
            success_rate = (total_success / total) * 100
            print(f"  成功率: {success_rate:.2f}%")
        
        print("=" * 60)
    
    def start(self, test_mode: bool = False, test_count: int = None):
        """启动爬虫"""
        print("=" * 60)
        print("多线程生产者-消费者历史数据爬虫")
        print("=" * 60)
        print(f"📅 目标日期: {self.target_date}")
        print(f"🔢 最大调用次数: {self.max_calls}")
        if test_mode:
            print(f"🧪 测试模式: 只爬取前 {test_count} 只股票")
        
        try:
            step1 = time.time()
            
            step2 = time.time()
            stock_codes = self.load_stock_codes()
            print(f"⏱️  加载股票代码耗时: {time.time() - step2:.2f}s")
            
            if not stock_codes:
                print("❌ 没有股票代码可爬取")
                return
            
            # 测试模式：只爬取前N只股票
            if test_mode and test_count:
                stock_codes = stock_codes[:test_count]
                print(f"🧪 测试模式：只爬取前 {len(stock_codes)} 只股票")
            
            step3 = time.time()
            deleted_count = self.clean_database()
            print(f"⏱️  清理数据库耗时: {time.time() - step3:.2f}s")
            
            step4 = time.time()
            for code in stock_codes:
                self.queue.put(code)
            print(f"⏱️  添加任务到队列耗时: {time.time() - step4:.2f}s")
            
            print(f"📋 队列中共有 {self.queue.qsize()} 个任务")
            
            step5 = time.time()
            self.start_workers()
            print(f"⏱️  启动消费者耗时: {time.time() - step5:.2f}s")
            
            step6 = time.time()
            self.wait_for_completion()
            print(f"⏱️  等待完成耗时: {time.time() - step6:.2f}s")
            
            self.stop_workers()
            
            self.print_summary()
            
            print(f"\n⏱️  总耗时: {time.time() - step1:.2f}s")
            
        except Exception as e:
            print(f"❌ 爬虫运行失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop_workers()



def main():
    """主函数"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    target_date = "2026-02-13"
    max_calls = 5000
    
    # 全量爬取模式（5475只股票）
    # 如需测试模式，请设置 test_mode=True, test_count=50
    test_mode = False
    test_count = None
    
    crawler = MultiThreadHistoryCrawler(db_path, target_date, max_calls)
    crawler.start(test_mode=test_mode, test_count=test_count)


if __name__ == "__main__":
    main()
