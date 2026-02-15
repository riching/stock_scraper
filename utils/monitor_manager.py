#!/usr/bin/env python3
"""监控和重启管理器"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3


class MonitorManager:
    """监控和重启管理器，处理失败重试和中断恢复"""

    def __init__(self, db_path: str, progress_file: str = "crawl_progress.json"):
        self.db_path = db_path
        self.progress_file = progress_file
        self.progress_data = self._load_progress()

    def _load_progress(self) -> Dict[str, Any]:
        """加载进度数据"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  警告: 无法加载进度文件 {self.progress_file}: {e}")
                return self._get_default_progress()
        else:
            return self._get_default_progress()

    def _get_default_progress(self) -> Dict[str, Any]:
        """获取默认进度数据"""
        return {
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "total_stocks": 0,
            "processed_stocks": 0,
            "successful_stocks": 0,
            "failed_stocks": 0,
            "current_batch": 0,
            "stocks_status": {},  # {stock_code: {"status": "success|failed|pending", "score": float, "attempts": int, "last_attempt": timestamp}}
            "batch_size": 50,
            "max_retries": 3,
        }

    def _save_progress(self):
        """保存进度数据"""
        try:
            self.progress_data["last_update"] = datetime.now().isoformat()
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 无法保存进度文件: {e}")

    def get_all_stock_codes(self) -> List[str]:
        """获取所有A股股票代码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT code FROM stock_list ORDER BY code")
            stock_codes = [row[0] for row in cursor.fetchall()]
            self.progress_data["total_stocks"] = len(stock_codes)
            self._save_progress()
            return stock_codes
        finally:
            conn.close()

    def should_process_stock(self, stock_code: str) -> bool:
        """判断是否需要处理某只股票"""
        stock_status = self.progress_data["stocks_status"].get(stock_code, {})

        # 如果从未处理过，需要处理
        if not stock_status:
            return True

        # 如果已经成功处理，不需要重新处理（除非是很久以前的）
        if stock_status.get("status") == "success":
            last_attempt = stock_status.get("last_attempt")
            if last_attempt:
                try:
                    last_dt = datetime.fromisoformat(last_attempt)
                    if datetime.now() - last_dt < timedelta(days=7):
                        return False
                except:
                    pass
            # 超过7天的成功记录，可以重新处理

        # 如果失败次数未达到最大重试次数，需要重试
        attempts = stock_status.get("attempts", 0)
        if attempts < self.progress_data["max_retries"]:
            return True

        return False

    def get_stocks_to_process(self, batch_size: int = 50) -> List[str]:
        """获取需要处理的股票列表"""
        all_stocks = self.get_all_stock_codes()
        stocks_to_process = []

        for stock_code in all_stocks:
            if self.should_process_stock(stock_code):
                stocks_to_process.append(stock_code)
                if len(stocks_to_process) >= batch_size:
                    break

        return stocks_to_process

    def mark_stock_success(self, stock_code: str, score: float):
        """标记股票处理成功"""
        if stock_code not in self.progress_data["stocks_status"]:
            self.progress_data["stocks_status"][stock_code] = {}

        self.progress_data["stocks_status"][stock_code].update(
            {
                "status": "success",
                "score": score,
                "attempts": self.progress_data["stocks_status"][stock_code].get(
                    "attempts", 0
                )
                + 1,
                "last_attempt": datetime.now().isoformat(),
            }
        )

        self.progress_data["successful_stocks"] += 1
        self.progress_data["processed_stocks"] += 1
        self._save_progress()

    def mark_stock_failed(self, stock_code: str, error: str = ""):
        """标记股票处理失败"""
        if stock_code not in self.progress_data["stocks_status"]:
            self.progress_data["stocks_status"][stock_code] = {}

        current_attempts = self.progress_data["stocks_status"][stock_code].get(
            "attempts", 0
        )
        self.progress_data["stocks_status"][stock_code].update(
            {
                "status": "failed",
                "error": error,
                "attempts": current_attempts + 1,
                "last_attempt": datetime.now().isoformat(),
            }
        )

        # 如果达到最大重试次数，计入失败统计
        if current_attempts + 1 >= self.progress_data["max_retries"]:
            self.progress_data["failed_stocks"] += 1
        self.progress_data["processed_stocks"] += 1
        self._save_progress()

    def get_existing_scores(self) -> Dict[str, float]:
        """获取现有的股票评分"""
        scores = {}

        # 从进度数据中获取已处理的股票评分
        for stock_code, status in self.progress_data["stocks_status"].items():
            if status.get("status") == "success":
                scores[stock_code] = status.get("score", -1.0)
            elif status.get("status") == "failed":
                # 失败的股票给默认评分-1
                scores[stock_code] = -1.0

        # 从数据库中获取可能存在的评分
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT code, overall_score FROM stock_sentiment_scores 
                WHERE date >= date('now', '-30 days')
            """)
            db_scores = dict(cursor.fetchall())

            # 合并数据库中的评分（优先使用数据库中的评分）
            for stock_code, score in db_scores.items():
                if stock_code not in scores or scores[stock_code] == -1.0:
                    scores[stock_code] = score if score is not None else -1.0

        finally:
            conn.close()

        return scores

    def get_high_scoring_stocks(
        self, min_score: float = 9.0, top_n: int = 100
    ) -> List[Dict]:
        """获取高评分股票列表"""
        scores = self.get_existing_scores()

        # 过滤有效评分（排除-1的默认值）
        valid_scores = {k: v for k, v in scores.items() if v != -1.0}

        # 按评分排序
        sorted_stocks = sorted(valid_scores.items(), key=lambda x: x[1], reverse=True)

        high_score_stocks = []
        nine_plus_count = 0

        for stock_code, score in sorted_stocks:
            if score >= min_score:
                nine_plus_count += 1
                high_score_stocks.append({"code": stock_code, "score": score})
            elif len(high_score_stocks) < top_n:
                high_score_stocks.append({"code": stock_code, "score": score})
            else:
                break

        # 如果评分超过9分的股票不足100个，补充默认评分-1的股票到100个
        if len(high_score_stocks) < top_n:
            all_stocks = self.get_all_stock_codes()
            remaining_stocks = [code for code in all_stocks if code not in scores]
            for stock_code in remaining_stocks[: top_n - len(high_score_stocks)]:
                high_score_stocks.append({"code": stock_code, "score": -1.0})
                if len(high_score_stocks) >= top_n:
                    break

        return high_score_stocks[:top_n]

    def save_results_to_file(
        self,
        high_scoring_stocks: List[Dict],
        filename: str = "high_scoring_stocks_final.txt",
    ):
        """保存结果到文件"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write("高评分股票列表\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"数据来源: 最近3个月新闻、公告、评论、分析师报告\n")
            f.write(f"总股票数: {self.progress_data['total_stocks']}\n")
            f.write(f"已处理: {self.progress_data['processed_stocks']}\n")
            f.write(f"成功: {self.progress_data['successful_stocks']}\n")
            f.write(f"失败: {self.progress_data['failed_stocks']}\n")
            f.write("\n")

            nine_plus_count = sum(
                1 for stock in high_scoring_stocks if stock["score"] >= 9.0
            )
            if nine_plus_count >= 100:
                f.write(f"评分超过9分的股票 ({nine_plus_count}只):\n")
            else:
                f.write(f"评分前100名的股票 (评分≥9分的只有{nine_plus_count}只):\n")
                f.write("注: 未处理的股票默认评分为-1\n")

            f.write("-" * 50 + "\n")

            for i, stock in enumerate(high_scoring_stocks, 1):
                if stock["score"] == -1.0:
                    f.write(f"{i:3d}. {stock['code']} - 默认评分(-1)/10\n")
                else:
                    f.write(f"{i:3d}. {stock['code']} - {stock['score']:.2f}/10\n")

        print(f"📄 结果已保存到 {filename}")
        return filename

    def get_progress_summary(self) -> str:
        """获取进度摘要"""
        total = self.progress_data["total_stocks"]
        processed = self.progress_data["processed_stocks"]
        success = self.progress_data["successful_stocks"]
        failed = self.progress_data["failed_stocks"]

        if total == 0:
            return "尚未开始处理"

        progress_pct = (processed / total) * 100
        success_pct = (success / processed * 100) if processed > 0 else 0

        return f"进度: {processed}/{total} ({progress_pct:.1f}%) | 成功率: {success_pct:.1f}% | 失败: {failed}"
