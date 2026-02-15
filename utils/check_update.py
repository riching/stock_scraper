#!/usr/bin/env python3
"""检查股票数据更新状态的脚本"""

import sqlite3
import sys
from datetime import datetime, date


def check_update_status(target_date=None) -> dict:
    """
    检查指定日期的股票数据更新状态

    Args:
        target_date: 要检查的日期，格式为 'YYYY-MM-DD'，如果为None则使用今天

    Returns:
        dict: 包含检查结果的字典
    """
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 获取总股票数量
        cursor.execute("SELECT COUNT(*) FROM stock_list")
        total_stocks = cursor.fetchone()[0]

        # 获取指定日期的已更新股票数量
        cursor.execute(
            "SELECT COUNT(*) FROM merged_stocks WHERE date = ?", (target_date,)
        )
        updated_stocks = cursor.fetchone()[0]

        # 计算完成率
        completion_rate = updated_stocks / total_stocks if total_stocks > 0 else 0

        # 判断是否成功（完成率 > 95%）
        success_threshold = 0.95
        is_successful = completion_rate >= success_threshold

        result = {
            "date": target_date,
            "total_stocks": total_stocks,
            "updated_stocks": updated_stocks,
            "completion_rate": completion_rate,
            "is_successful": is_successful,
            "success_threshold": success_threshold,
        }

        return result

    finally:
        conn.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="检查股票数据更新状态")
    parser.add_argument("--date", type=str, help="要检查的日期 (YYYY-MM-DD)")
    parser.add_argument(
        "--quiet", action="store_true", help="静默模式，只输出成功/失败"
    )

    args = parser.parse_args()

    try:
        result = check_update_status(args.date)

        if args.quiet:
            # 静默模式：只返回退出码
            if result["is_successful"]:
                print("SUCCESS")
                sys.exit(0)
            else:
                print("FAILED")
                sys.exit(1)
        else:
            # 详细模式
            print(f"=== 股票数据更新状态检查 ===")
            print(f"检查日期: {result['date']}")
            print(f"总股票数: {result['total_stocks']}")
            print(f"已更新数: {result['updated_stocks']}")
            print(f"完成率: {result['completion_rate']:.2%}")
            print(f"成功阈值: {result['success_threshold']:.2%}")
            print(f"更新状态: {'✅ 成功' if result['is_successful'] else '❌ 失败'}")

            if not result["is_successful"]:
                missing_count = result["total_stocks"] - result["updated_stocks"]
                print(f"缺失股票数: {missing_count}")

    except Exception as e:
        print(f"检查失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
