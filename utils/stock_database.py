#!/usr/bin/env python3
"""股票数据库操作工具类 - 支持增删改查"""

import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager


class StockDatabase:
    """股票数据库操作类 - 线程安全的增删改查"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.local = threading.local()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接"""
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            self.local.conn = sqlite3.connect(self.db_path)
            self.local.conn.execute("PRAGMA journal_mode=WAL")
            self.local.conn.execute("PRAGMA synchronous=NORMAL")
        return self.local.conn
    
    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self.local, 'conn') and self.local.conn is not None:
            self.local.conn.close()
            self.local.conn = None
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def insert_stock_data(self, data: Dict) -> bool:
        """插入单条股票数据"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                insert_data = (
                    None,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    data["code"],
                    data["date"],
                    data.get("open"),
                    data.get("high"),
                    data.get("low"),
                    data.get("close"),
                    data.get("volume"),
                    data.get("amount"),
                    data.get("outstanding_share"),
                    data.get("turnover"),
                    data.get("name"),
                    data.get("ma5"),
                    data.get("ma10"),
                    data.get("ma20"),
                    data.get("rsi6"),
                    data.get("rsi14"),
                    data.get("pct_change"),
                )
                
                cursor.execute("""
                    INSERT INTO merged_stocks 
                    (id, created_at, code, date, open, high, low, close, volume, amount, 
                     outstanding_share, turnover, name, ma5, ma10, ma20, rsi6, rsi14, pct_change)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_data)
                
                return True
        except Exception as e:
            print(f"❌ 插入股票数据失败: {e}")
            return False
    
    def insert_stock_data_batch(self, data_list: List[Dict]) -> int:
        """批量插入股票数据"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                insert_data_list = []
                for data in data_list:
                    insert_data = (
                        None,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        data["code"],
                        data["date"],
                        data.get("open"),
                        data.get("high"),
                        data.get("low"),
                        data.get("close"),
                        data.get("volume"),
                        data.get("amount"),
                        data.get("outstanding_share"),
                        data.get("turnover"),
                        data.get("name"),
                        data.get("ma5"),
                        data.get("ma10"),
                        data.get("ma20"),
                        data.get("rsi6"),
                        data.get("rsi14"),
                        data.get("pct_change"),
                    )
                    insert_data_list.append(insert_data)
                
                cursor.executemany("""
                    INSERT INTO merged_stocks 
                    (id, created_at, code, date, open, high, low, close, volume, amount, 
                     outstanding_share, turnover, name, ma5, ma10, ma20, rsi6, rsi14, pct_change)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_data_list)
                
                return len(data_list)
        except Exception as e:
            print(f"❌ 批量插入股票数据失败: {e}")
            return 0
    
    def update_stock_data(self, code: str, date: str, data: Dict) -> bool:
        """更新股票数据"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                update_fields = []
                update_values = []
                
                for field in ['open', 'high', 'low', 'close', 'volume', 'amount', 
                            'outstanding_share', 'turnover', 'name', 
                            'ma5', 'ma10', 'ma20', 'rsi6', 'rsi14', 'pct_change']:
                    if field in data and data[field] is not None:
                        update_fields.append(f"{field} = ?")
                        update_values.append(data[field])
                
                if not update_fields:
                    return False
                
                update_values.extend([code, date])
                
                cursor.execute(f"""
                    UPDATE merged_stocks 
                    SET {', '.join(update_fields)}
                    WHERE code = ? AND date = ?
                """, update_values)
                
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 更新股票数据失败: {e}")
            return False
    
    def delete_stock_data(self, code: str = None, date: str = None) -> int:
        """删除股票数据"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                conditions = []
                params = []
                
                if code:
                    conditions.append("code = ?")
                    params.append(code)
                
                if date:
                    conditions.append("date = ?")
                    params.append(date)
                
                if not conditions:
                    return 0
                
                cursor.execute(f"""
                    DELETE FROM merged_stocks 
                    WHERE {' AND '.join(conditions)}
                """, params)
                
                return cursor.rowcount
        except Exception as e:
            print(f"❌ 删除股票数据失败: {e}")
            return 0
    
    def select_stock_data(self, code: str = None, date: str = None, 
                       start_date: str = None, end_date: str = None,
                       limit: int = None) -> List[Dict]:
        """查询股票数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if code:
                conditions.append("code = ?")
                params.append(code)
            
            if date:
                conditions.append("date = ?")
                params.append(date)
            
            if start_date:
                conditions.append("date >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("date <= ?")
                params.append(end_date)
            
            sql = "SELECT * FROM merged_stocks"
            if conditions:
                sql += f" WHERE {' AND '.join(conditions)}"
            
            sql += " ORDER BY date DESC, code"
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ 查询股票数据失败: {e}")
            return []
    
    def select_stock_data_by_codes(self, codes: List[str], date: str = None) -> List[Dict]:
        """根据股票代码列表查询数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            placeholders = ','.join(['?' for _ in codes])
            params = codes
            
            sql = f"SELECT * FROM merged_stocks WHERE code IN ({placeholders})"
            
            if date:
                sql += " AND date = ?"
                params.append(date)
            
            sql += " ORDER BY date DESC, code"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ 根据代码查询股票数据失败: {e}")
            return []
    
    def exists_stock_data(self, code: str, date: str) -> bool:
        """检查股票数据是否存在"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) FROM merged_stocks WHERE code = ? AND date = ?",
                (code, date)
            )
            
            return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"❌ 检查股票数据存在性失败: {e}")
            return False
    
    def get_stock_data_count(self, code: str = None, date: str = None) -> int:
        """统计股票数据数量"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if code:
                conditions.append("code = ?")
                params.append(code)
            
            if date:
                conditions.append("date = ?")
                params.append(date)
            
            sql = "SELECT COUNT(*) FROM merged_stocks"
            if conditions:
                sql += f" WHERE {' AND '.join(conditions)}"
            
            cursor.execute(sql, params)
            return cursor.fetchone()[0]
        except Exception as e:
            print(f"❌ 统计股票数据失败: {e}")
            return 0
    
    def is_data_exists(self, code: str, date: str) -> bool:
        """检查数据是否已存在"""
        return self.get_stock_data_count(code, date) > 0
    
    def get_stock_data(self, code: str, date: str) -> Optional[Dict]:
        """获取指定股票在指定日期的数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT open, high, low, close, volume
                FROM merged_stocks
                WHERE code = ? AND date = ?
                LIMIT 1
            """, (code, date))
            
            row = cursor.fetchone()
            if row:
                return {
                    "open": row[0],
                    "high": row[1],
                    "low": row[2],
                    "close": row[3],
                    "volume": row[4]
                }
            return None
        except Exception as e:
            print(f"❌ 获取股票数据失败: {e}")
            return None
    
    def get_all_stock_codes(self) -> List[str]:
        """获取所有股票代码"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT code FROM stock_list ORDER BY code")
            rows = cursor.fetchall()
            
            return [row[0] for row in rows]
        except Exception as e:
            print(f"❌ 获取所有股票代码失败: {e}")
            return []
    
    def get_stock_dates(self, code: str = None) -> List[str]:
        """获取股票数据日期列表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if code:
                cursor.execute(
                    "SELECT DISTINCT date FROM merged_stocks WHERE code = ? ORDER BY date DESC",
                    (code,)
                )
            else:
                cursor.execute("SELECT DISTINCT date FROM merged_stocks ORDER BY date DESC")
            
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            print(f"❌ 获取股票日期列表失败: {e}")
            return []
    
    def insert_or_update_data_status(self, code: str, last_updated: str, 
                                  record_count: int, status: str) -> bool:
        """插入或更新数据状态"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO data_status 
                    (code, last_updated, record_count, status)
                    VALUES (?, ?, ?, ?)
                """, (code, last_updated, record_count, status))
                
                return True
        except Exception as e:
            print(f"❌ 插入或更新数据状态失败: {e}")
            return False
    
    def get_data_status(self, code: str = None) -> List[Dict]:
        """获取数据状态"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if code:
                cursor.execute(
                    "SELECT * FROM data_status WHERE code = ?",
                    (code,)
                )
            else:
                cursor.execute("SELECT * FROM data_status ORDER BY code")
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ 获取数据状态失败: {e}")
            return []
    
    def execute_sql(self, sql: str, params: Tuple = None) -> List[Dict]:
        """执行自定义SQL查询"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            if sql.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            else:
                conn.commit()
                return [{'affected_rows': cursor.rowcount}]
        except Exception as e:
            print(f"❌ 执行SQL失败: {e}")
            return []
    
    def clean_date_data(self, date: str) -> int:
        """清理指定日期的数据"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM merged_stocks WHERE date = ?",
                    (date,)
                )
                deleted_count = cursor.rowcount
                
                cursor.execute(
                    "DELETE FROM data_status WHERE code IN (SELECT code FROM merged_stocks WHERE date = ?)",
                    (date,)
                )
                
                return deleted_count
        except Exception as e:
            print(f"❌ 清理日期数据失败: {e}")
            return 0
    
    def get_table_info(self, table_name: str) -> List[Dict]:
        """获取表结构信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            rows = cursor.fetchall()
            
            columns = ['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk']
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ 获取表结构信息失败: {e}")
            return []
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ 数据库已备份到: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ 备份数据库失败: {e}")
            return False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()
