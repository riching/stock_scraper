#!/usr/bin/env python3
"""
股票数据增量更新脚本
"""

import sys
import os
import traceback

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simple_scraper import SimpleStockScraper


def main():
    """主函数"""
    db_path = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"

    try:
        scraper = SimpleStockScraper(db_path)
        success = scraper.run_incremental_update()

        if success:
            print("\n✅ 增量更新完成成功！")
            return 0
        else:
            print("\n⚠️  没有数据被更新。请检查网络连接和网站可用性。")
            return 1

    except KeyboardInterrupt:
        print("\n❌ 更新被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 更新失败，错误: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
