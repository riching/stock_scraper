#!/usr/bin/env python3
"""多线程生产者-消费者实时数据爬虫"""

import sys
import os
import threading
import asyncio
import time
from queue import Queue
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.stock_database import StockDatabase
from crawler.sina.sina_history_crawler_fixed import SinaStockCrawler
from crawler.eastmoney.eastmoney_crawler import EastMoneyStockCrawler
from crawler.tencent.tencent_crawler import TencentStockCrawler
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
    
    def __init__(self, queue: Queue, db_path: str, target_date: str, max_calls: int = 5000, test_mode: bool = False):
        super().__init__()
        self.queue = queue
        self.db_path = db_path
        self.target_date = target_date
        self.max_calls = max_calls
        self.test_mode = test_mode
        self.stats = WorkerStats(self.__class__.__name__)
        self.running = True
        self.crawler = None
    
    def run(self):
        """线程主循环"""
        print(f"🚀 {self.__class__.__name__} 启动")
        
        try:
            self.init_crawler()
            
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
                            if self.test_mode:
                                # 测试模式：对比数据库中的数据
                                db_data = self.get_db_data(db, stock_code)
                                if self.compare_data(data, db_data):
                                    self.stats.add_success()
                                    print(f"✅ {self.__class__.__name__} 数据一致 {stock_code}")
                                else:
                                    self.stats.add_failure()
                                    print(f"❌ {self.__class__.__name__} 数据不一致 {stock_code}")
                            else:
                                # 正常模式：保存到数据库
                                if self.save_to_database(db, data):
                                    self.stats.add_success()
                                    print(f"✅ {self.__class__.__name__} 成功爬取 {stock_code}")
                                else:
                                    self.stats.add_failure()
                                    print(f"❌ {self.__class__.__name__} 保存 {stock_code} 失败")
                        else:
                            self.stats.add_failure()
                            print(f"❌ {self.__class__.__name__} 数据无效 {stock_code}")
                        
                        self.queue.task_done()
                        
                        # 避免请求过于频繁
                        time.sleep(0.5)
                        
                    except Queue.Empty:
                        print(f"⏸️  {self.__class__.__name__}: 任务队列超时")
                        break
                    except Exception as e:
                        self.stats.add_failure()
                        print(f"❌ {self.__class__.__name__} 处理 {stock_code} 异常: {e}")
                        self.queue.task_done()
                        time.sleep(1)
        finally:
            self.stop()
    
    def get_db_data(self, db: StockDatabase, stock_code: str) -> Optional[Dict]:
        """从数据库获取数据"""
        try:
            data = db.get_stock_data(stock_code, self.target_date)
            if data:
                return {
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "volume": data.get("volume")
                }
            return None
        except Exception as e:
            print(f"❌ 获取数据库数据失败: {e}")
            return None
    
    def compare_data(self, crawl_data: Dict, db_data: Optional[Dict]) -> bool:
        """对比爬取的数据和数据库数据"""
        if not db_data:
            print(f"⚠️  数据库中没有 {crawl_data['code']} 在 {self.target_date} 的数据")
            return False
        
        # 对比价格数据
        for field in ["open", "high", "low", "close"]:
            crawl_value = crawl_data.get(field)
            db_value = db_data.get(field)
            
            if crawl_value is None or db_value is None:
                print(f"⚠️  {field} 数据缺失: 爬取={crawl_value}, 数据库={db_value}")
                return False
            
            # 允许小数点误差
            if abs(crawl_value - db_value) > 0.01:
                print(f"⚠️  {field} 数据不一致: 爬取={crawl_value}, 数据库={db_value}")
                return False
        
        return True
    
    def init_crawler(self):
        """初始化爬虫"""
        pass
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取股票数据"""
        raise NotImplementedError
    
    def validate_data(self, data: Optional[Dict]) -> bool:
        """验证数据"""
        if not data:
            return False
        if not data.get('close'):
            return False
        if data.get('close') <= 0:
            return False
        return True
    
    def save_to_database(self, db: StockDatabase, data: Dict) -> bool:
        """保存数据到数据库"""
        try:
            # 检查数据是否已存在
            if db.is_data_exists(data['code'], data['date']):
                print(f"⚠️  {data['code']} {data['date']} 数据已存在，跳过")
                return True
            
            # 插入数据
            if db.insert_stock_data(data):
                # 更新数据状态
                db.update_data_status(data['code'], "success")
                return True
            return False
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")
            return False
    
    def stop(self):
        """停止线程"""
        self.running = False
        if hasattr(self, 'crawler') and self.crawler:
            try:
                if hasattr(self.crawler, 'close'):
                    asyncio.run(self.crawler.close())
                elif hasattr(self.crawler, 'close_browser'):
                    asyncio.run(self.crawler.close_browser())
                print(f"✅ {self.__class__.__name__} 已关闭")
            except Exception as e:
                print(f"❌ {self.__class__.__name__} 关闭失败: {e}")


class SinaWorker(BaseWorker):
    """新浪财经爬虫线程"""
    
    def init_crawler(self):
        """初始化新浪爬虫"""
        try:
            self.crawler = SinaStockCrawler(self.db_path)
            print("✅ 新浪财经爬虫初始化成功")
        except Exception as e:
            print(f"❌ 新浪财经爬虫初始化失败: {e}")
            self.running = False
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取新浪财经数据"""
        try:
            print(f"🕷️  爬取新浪财经 {stock_code}")
            # 使用目标日期
            data = asyncio.run(self.crawler.crawl_stock_price(stock_code, self.target_date))
            return data
        except Exception as e:
            print(f"❌ 新浪财经爬虫爬取 {stock_code} 失败: {e}")
            return None


class TencentWorker(BaseWorker):
    """腾讯财经爬虫线程"""
    
    def init_crawler(self):
        """初始化腾讯爬虫"""
        try:
            self.crawler = TencentStockCrawler(self.db_path)
            print("✅ 腾讯财经爬虫初始化成功")
        except Exception as e:
            print(f"❌ 腾讯财经爬虫初始化失败: {e}")
            self.running = False
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取腾讯财经数据"""
        try:
            print(f"🕷️  爬取腾讯财经 {stock_code}")
            # 使用目标日期
            return asyncio.run(self.crawler.crawl_stock_price(stock_code, self.target_date))
        except Exception as e:
            print(f"❌ 腾讯财经爬虫爬取 {stock_code} 失败: {e}")
            return None


class EastMoneyWorker(BaseWorker):
    """东方财富爬虫线程"""
    
    def init_crawler(self):
        """初始化东方财富爬虫"""
        try:
            self.crawler = EastMoneyStockCrawler(self.db_path)
            asyncio.run(self.crawler.init_browser())
            print("✅ 东方财富爬虫初始化成功")
        except Exception as e:
            print(f"❌ 东方财富爬虫初始化失败: {e}")
            self.running = False
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取东方财富数据"""
        try:
            print(f"🕷️  爬取东方财富 {stock_code}")
            return asyncio.run(self.crawler.crawl_stock_price(stock_code))
        except Exception as e:
            print(f"❌ 东方财富爬虫爬取 {stock_code} 失败: {e}")
            return None


class AkshareWorker(BaseWorker):
    """Akshare爬虫线程"""
    
    def init_crawler(self):
        """初始化Akshare爬虫"""
        try:
            self.crawler = AkshareDataFetcher()
            print("✅ Akshare爬虫初始化成功")
        except Exception as e:
            print(f"❌ Akshare爬虫初始化失败: {e}")
            self.running = False
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取Akshare数据"""
        try:
            print(f"🕷️  爬取Akshare {stock_code}")
            # 使用目标日期获取历史数据
            data = self.crawler.get_historical_price(stock_code, self.target_date)
            if data:
                return {
                    "code": stock_code,
                    "date": self.target_date,
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "volume": data.get("volume"),
                    "name": data.get("name"),
                    "change_percent": data.get("change_percent")
                }
            return None
        except Exception as e:
            print(f"❌ Akshare爬虫爬取 {stock_code} 失败: {e}")
            return None


class BaostockWorker(BaseWorker):
    """Baostock爬虫线程"""
    
    def init_crawler(self):
        """初始化Baostock爬虫"""
        try:
            self.crawler = BaostockStockCrawler(self.db_path)
            print("✅ Baostock爬虫初始化成功")
        except Exception as e:
            print(f"❌ Baostock爬虫初始化失败: {e}")
            self.running = False
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取Baostock数据"""
        try:
            print(f"🕷️  爬取Baostock {stock_code}")
            # 使用目标日期获取历史数据
            return asyncio.run(self.crawler.crawl_history_price(stock_code, self.target_date))
        except Exception as e:
            print(f"❌ Baostock爬虫爬取 {stock_code} 失败: {e}")
            return None


class YahooFinanceWorker(BaseWorker):
    """Yahoo Finance爬虫线程"""
    
    def init_crawler(self):
        """初始化Yahoo Finance爬虫"""
        try:
            self.crawler = YahooFinanceStockCrawler(self.db_path)
            print("✅ Yahoo Finance爬虫初始化成功")
        except Exception as e:
            print(f"❌ Yahoo Finance爬虫初始化失败: {e}")
            self.running = False
    
    def crawl_stock(self, stock_code: str) -> Optional[Dict]:
        """爬取Yahoo Finance数据"""
        try:
            print(f"🕷️  爬取Yahoo Finance {stock_code}")
            # 使用目标日期获取历史数据
            return asyncio.run(self.crawler.crawl_history_price(stock_code, self.target_date))
        except Exception as e:
            print(f"❌ Yahoo Finance爬虫爬取 {stock_code} 失败: {e}")
            return None


class MultiSourceRealTimeCrawler:
    """多线程生产者-消费者实时数据爬虫"""
    
    def __init__(self, db_path: str, max_calls: int = 5000, test_mode: bool = False):
        self.db_path = db_path
        self.max_calls = max_calls
        self.test_mode = test_mode
        self.queue = Queue()
        self.workers = []
        self.total_stats = {
            "success": 0,
            "failure": 0,
            "total": 0
        }
    
    def load_stock_codes(self) -> List[str]:
        """加载所有股票代码"""
        with StockDatabase(self.db_path) as db:
            codes = db.get_all_stock_codes()
            print(f"📋 从数据库加载了 {len(codes)} 只股票")
            return codes
    
    def add_tasks_to_queue(self, stock_codes: List[str]):
        """添加任务到队列"""
        for code in stock_codes:
            self.queue.put(code)
        print(f"📋 队列中共有 {self.queue.qsize()} 个任务")
    
    def start_workers(self, target_date: str):
        """启动所有消费者线程"""
        worker_classes = [
            SinaWorker,
            TencentWorker,
            EastMoneyWorker,
            AkshareWorker,
            BaostockWorker,
            YahooFinanceWorker
        ]
        
        for worker_class in worker_classes:
            worker = worker_class(
                self.queue,
                self.db_path,
                target_date,
                self.max_calls,
                self.test_mode
            )
            worker.start()
            self.workers.append(worker)
        
        print(f"🚀 已启动 {len(self.workers)} 个消费者线程")
    
    def wait_for_completion(self):
        """等待所有任务完成"""
        print("⏳ 等待所有任务完成...")
        
        # 等待队列清空
        self.queue.join()
        
        # 发送终止信号
        for _ in self.workers:
            self.queue.put(None)
        
        # 等待所有线程结束
        for worker in self.workers:
            worker.join(timeout=30)
            if worker.is_alive():
                print(f"⚠️  {worker.__class__.__name__} 线程未正常结束")
    
    def collect_stats(self):
        """收集统计信息"""
        print("\n" + "="*60)
        print("📊 爬虫统计信息")
        print("="*60)
        
        total_success = 0
        total_failure = 0
        
        for worker in self.workers:
            stats = worker.stats.get_summary()
            success = stats["success"]
            failure = stats["failure"]
            total_success += success
            total_failure += failure
            
            total = success + failure
            success_rate = (success / total * 100) if total > 0 else 0
            
            print(f"{stats['worker_name']}:")
            print(f"  成功: {success}")
            print(f"  失败: {failure}")
            print(f"  成功率: {success_rate:.1f}%")
            print()
        
        self.total_stats["success"] = total_success
        self.total_stats["failure"] = total_failure
        self.total_stats["total"] = total_success + total_failure
        
        overall_success_rate = (total_success / self.total_stats["total"] * 100) if self.total_stats["total"] > 0 else 0
        
        print("="*60)
        print("📊 整体统计")
        print("="*60)
        print(f"总任务数: {self.total_stats['total']}")
        print(f"成功: {total_success}")
        print(f"失败: {total_failure}")
        print(f"整体成功率: {overall_success_rate:.1f}%")
        print("="*60)
    
    def crawl(self, stock_codes: List[str], target_date: str):
        """开始爬取"""
        start_time = time.time()
        
        print("="*60)
        print("多线程生产者-消费者实时数据爬虫")
        print("="*60)
        print(f"📅 目标日期: {target_date}")
        print(f"🔢 最大调用次数: {self.max_calls}")
        if self.test_mode:
            print(f"🧪 测试模式：不写数据库，只对比数据")
        
        # 加载股票代码
        if not stock_codes:
            stock_codes = self.load_stock_codes()
        
        # 添加任务到队列
        self.add_tasks_to_queue(stock_codes)
        
        # 启动消费者
        self.start_workers(target_date)
        
        # 等待完成
        self.wait_for_completion()
        
        # 收集统计信息
        self.collect_stats()
        
        end_time = time.time()
        print(f"⏱️  总耗时: {end_time - start_time:.2f}s")
        print("="*60)
        
        return self.total_stats


def main():
    """主函数"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    
    # 测试模式：只爬取几只股票
    test_mode = True
    test_count = 10
    
    # 设置目标日期为最近的交易日：2026-02-13
    target_date = "2026-02-13"
    
    crawler = MultiSourceRealTimeCrawler(db_path, test_mode=test_mode)
    
    if test_mode:
        # 测试股票
        test_stocks = ["000001", "600519", "000858", "600036", "002323", 
                      "900941", "900943", "900948", "600000", "000002"]
        print(f"🧪 测试模式：爬取 {len(test_stocks)} 只股票")
        print(f"📅 目标日期: {target_date}")
        stats = crawler.crawl(test_stocks, target_date)
    else:
        # 全量爬取
        print("🚀 全量爬取模式")
        print(f"📅 目标日期: {target_date}")
        stats = crawler.crawl([], target_date)
    
    print(f"✅ 爬取完成！成功: {stats['success']}, 失败: {stats['failure']}")


if __name__ == "__main__":
    main()
