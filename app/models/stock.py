import sqlite3
from typing import List, Dict, Optional
from config.settings import DB_PATH


class StockDatabase:
    """股票数据库访问层"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_industries(self) -> List[Dict]:
        """获取所有行业分类"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 一级行业名称, COUNT(DISTINCT 股票代码) as stock_count
            FROM stock_classifications 
            WHERE 一级行业名称 IS NOT NULL 
            GROUP BY 一级行业名称 
            ORDER BY stock_count DESC
        """)

        industries = []
        for row in cursor.fetchall():
            industries.append({"name": row[0], "stock_count": row[1]})

        conn.close()
        return industries

    def get_stocks_by_industry(
        self, industry_name: str, page: int = 1, page_size: int = 100
    ) -> Dict:
        """获取指定行业的股票列表"""
        offset = (page - 1) * page_size

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取总数量
        cursor.execute(
            """
            SELECT COUNT(DISTINCT sc.股票代码)
            FROM stock_classifications sc
            WHERE sc.一级行业名称 = ?
        """,
            (industry_name,),
        )
        total_count = cursor.fetchone()[0]

        cursor.execute(
            """
            WITH latest_dates AS (
                SELECT code, MAX(date) as max_date
                FROM merged_stocks
                GROUP BY code
            )
            SELECT DISTINCT sc.股票代码, sl.name, ms.close, ms.pct_change, 
                   sc.二级行业名称, sc.三级行业名称, ms.date
            FROM stock_classifications sc
            JOIN stock_list sl ON CAST(sl.code AS INTEGER) = sc.股票代码
            JOIN latest_dates ld ON sl.code = ld.code
            JOIN merged_stocks ms ON sl.code = ms.code AND ms.date = ld.max_date
            WHERE sc.一级行业名称 = ?
            ORDER BY ms.pct_change DESC
            LIMIT ? OFFSET ?
        """,
            (industry_name, page_size, offset),
        )

        stocks = []
        for row in cursor.fetchall():
            stocks.append(
                {
                    "code": str(row[0]).zfill(6),  # 补齐6位股票代码
                    "name": row[1],
                    "close": row[2],
                    "pct_change": row[3],
                    "level2_industry": row[4],
                    "level3_industry": row[5],
                    "date": row[6],
                }
            )

        conn.close()

        return {
            "stocks": stocks,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
            },
        }

    def get_stock_detail(self, stock_code: str) -> Optional[Dict]:
        """获取股票详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取基本信息和最新行情
        cursor.execute(
            """
            SELECT sl.code, sl.name, sc.一级行业名称, sc.二级行业名称, sc.三级行业名称,
                   ms.open, ms.high, ms.low, ms.close, ms.volume, ms.amount,
                   ms.ma5, ms.ma10, ms.ma20, ms.rsi6, ms.rsi14, ms.pct_change, ms.date
            FROM stock_list sl
            LEFT JOIN stock_classifications sc ON CAST(sl.code AS INTEGER) = sc.股票代码
            LEFT JOIN merged_stocks ms ON sl.code = ms.code
            WHERE sl.code = ?
            AND ms.date = (
                SELECT MAX(date) 
                FROM merged_stocks ms2 
                WHERE ms2.code = sl.code
            )
        """,
            (stock_code,),
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        detail = {
            "code": row[0],
            "name": row[1],
            "industry": {"level1": row[2], "level2": row[3], "level3": row[4]},
            "price_data": {
                "open": row[5],
                "high": row[6],
                "low": row[7],
                "close": row[8],
                "volume": row[9],
                "amount": row[10],
                "ma5": row[11],
                "ma10": row[12],
                "ma20": row[13],
                "rsi6": row[14],
                "rsi14": row[15],
                "pct_change": row[16],
                "date": row[17],
            },
        }

        conn.close()
        return detail

    def get_stock_kline_data(self, stock_code: str, period: int = 120) -> List[Dict]:
        """获取股票K线数据"""
        # 限制最大周期为500
        period = min(period, 500)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT date, open, high, low, close, volume, ma5, ma10, ma20, rsi6, rsi14, pct_change
            FROM merged_stocks
            WHERE code = ?
            ORDER BY date DESC
            LIMIT ?
        """,
            (stock_code, period),
        )

        kline_data = []
        for row in cursor.fetchall():
            kline_data.append(
                {
                    "date": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                    "ma5": row[6],
                    "ma10": row[7],
                    "ma20": row[8],
                    "rsi6": row[9],
                    "rsi14": row[10],
                    "pct_change": row[11],
                }
            )

        # 按日期升序排列（从旧到新）
        kline_data.reverse()

        conn.close()
        return kline_data

    def search_stocks(self, query: str, page: int = 1, page_size: int = 50) -> Dict:
        """搜索股票"""
        offset = (page - 1) * page_size

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 搜索股票代码或名称
        search_pattern = f"%{query}%"
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM stock_list
            WHERE code LIKE ? OR name LIKE ?
        """,
            (search_pattern, search_pattern),
        )
        total_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT code, name
            FROM stock_list
            WHERE code LIKE ? OR name LIKE ?
            LIMIT ? OFFSET ?
        """,
            (search_pattern, search_pattern, page_size, offset),
        )

        results = []
        for row in cursor.fetchall():
            results.append({"code": row[0], "name": row[1]})

        conn.close()

        return {
            "results": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size,
            },
        }
