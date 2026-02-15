"""
Pandas 股票数据分析工具模块
提供常用的技术指标计算和数据处理功能
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Dict, List, Optional


class StockAnalyzer:
    """股票数据分析器"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化分析器

        Args:
            df: 包含股票数据的 DataFrame，必须包含 'date', 'open', 'high', 'low', 'close', 'volume' 列
        """
        self.df = df.copy()
        self._validate_dataframe()

    def _validate_dataframe(self):
        """验证 DataFrame 格式"""
        required_columns = ["date", "open", "high", "low", "close", "volume"]
        missing_columns = [
            col for col in required_columns if col not in self.df.columns
        ]
        if missing_columns:
            raise ValueError(f"DataFrame 缺少必要列: {missing_columns}")

        # 确保日期列是 datetime 类型
        if not pd.api.types.is_datetime64_any_dtype(self.df["date"]):
            self.df["date"] = pd.to_datetime(self.df["date"])

        # 按日期排序
        self.df = self.df.sort_values("date").reset_index(drop=True)

    def calculate_moving_averages(
        self, periods: List[int] = [5, 10, 20, 50, 200]
    ) -> pd.DataFrame:
        """计算移动平均线"""
        df_result = self.df.copy()
        for period in periods:
            df_result[f"sma_{period}"] = ta.sma(df_result["close"], length=period)
            df_result[f"ema_{period}"] = ta.ema(df_result["close"], length=period)
        return df_result

    def calculate_rsi(self, periods: List[int] = [6, 14, 21]) -> pd.DataFrame:
        """计算 RSI (相对强弱指数)"""
        df_result = self.df.copy()
        for period in periods:
            df_result[f"rsi_{period}"] = ta.rsi(df_result["close"], length=period)
        return df_result

    def calculate_macd(
        self, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> pd.DataFrame:
        """计算 MACD (移动平均收敛/发散)"""
        df_result = self.df.copy()
        macd_df = ta.macd(df_result["close"], fast=fast, slow=slow, signal=signal)
        df_result = pd.concat([df_result, macd_df], axis=1)
        return df_result

    def calculate_bollinger_bands(self, length: int = 20, std: int = 2) -> pd.DataFrame:
        """计算布林带"""
        df_result = self.df.copy()
        bb_df = ta.bbands(df_result["close"], length=length, std=std)
        # 重命名列以避免冲突
        bb_df = bb_df.rename(
            columns={
                f"BBU_{length}_{std}": "bb_upper",
                f"BBM_{length}_{std}": "bb_middle",
                f"BBL_{length}_{std}": "bb_lower",
                f"BBP_{length}_{std}": "bb_percent",
                f"BBW_{length}_{std}": "bb_width",
            }
        )
        df_result = pd.concat([df_result, bb_df], axis=1)
        return df_result

    def calculate_atr(self, length: int = 14) -> pd.DataFrame:
        """计算 ATR (平均真实波幅)"""
        df_result = self.df.copy()
        df_result["atr"] = ta.atr(
            df_result["high"], df_result["low"], df_result["close"], length=length
        )
        return df_result

    def calculate_adx(self, length: int = 14) -> pd.DataFrame:
        """计算 ADX (平均方向指数)"""
        df_result = self.df.copy()
        adx_df = ta.adx(
            df_result["high"], df_result["low"], df_result["close"], length=length
        )
        df_result = pd.concat([df_result, adx_df], axis=1)
        return df_result

    def calculate_cci(self, length: int = 20) -> pd.DataFrame:
        """计算 CCI (商品通道指数)"""
        df_result = self.df.copy()
        df_result["cci"] = ta.cci(
            df_result["high"], df_result["low"], df_result["close"], length=length
        )
        return df_result

    def calculate_all_indicators(self) -> pd.DataFrame:
        """计算所有常用技术指标"""
        df_result = self.df.copy()

        # 移动平均线
        df_ma = self.calculate_moving_averages([5, 10, 20, 50, 200])
        ma_columns = [
            "sma_5",
            "sma_10",
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_5",
            "ema_10",
            "ema_20",
            "ema_50",
            "ema_200",
        ]
        for col in ma_columns:
            if col in df_ma.columns:
                df_result[col] = df_ma[col]

        # RSI
        df_rsi = self.calculate_rsi([6, 14, 21])
        rsi_columns = ["rsi_6", "rsi_14", "rsi_21"]
        for col in rsi_columns:
            if col in df_rsi.columns:
                df_result[col] = df_rsi[col]

        # MACD
        df_macd = self.calculate_macd()
        for col in df_macd.columns:
            if col.startswith("MACD"):
                df_result[col] = df_macd[col]

        # 布林带
        df_bb = self.calculate_bollinger_bands()
        bb_columns = ["bb_upper", "bb_middle", "bb_lower", "bb_percent", "bb_width"]
        for col in bb_columns:
            if col in df_bb.columns:
                df_result[col] = df_bb[col]

        # ATR
        df_atr = self.calculate_atr()
        if "atr" in df_atr.columns:
            df_result["atr"] = df_atr["atr"]

        # ADX
        df_adx = self.calculate_adx()
        for col in df_adx.columns:
            if col.startswith("ADX"):
                df_result[col] = df_adx[col]

        # CCI
        df_cci = self.calculate_cci()
        if "cci" in df_cci.columns:
            df_result["cci"] = df_cci["cci"]

        return df_result

    def get_technical_signals(self) -> Dict[str, str]:
        """获取技术信号摘要"""
        latest = self.df.iloc[-1]
        signals = {}

        # RSI 信号
        if "rsi_14" in latest:
            if latest["rsi_14"] > 70:
                signals["rsi"] = "超买"
            elif latest["rsi_14"] < 30:
                signals["rsi"] = "超卖"
            else:
                signals["rsi"] = "中性"

        # MACD 信号
        if "MACD_12_26_9" in latest and "MACDs_12_26_9" in latest:
            if latest["MACD_12_26_9"] > latest["MACDs_12_26_9"]:
                signals["macd"] = "看涨"
            else:
                signals["macd"] = "看跌"

        # 布林带信号
        if "bb_upper" in latest and "bb_lower" in latest:
            price = latest["close"]
            if price > latest["bb_upper"]:
                signals["bollinger"] = "超买"
            elif price < latest["bb_lower"]:
                signals["bollinger"] = "超卖"
            else:
                signals["bollinger"] = "中性"

        return signals

    def calculate_returns(self, periods: List[int] = [1, 5, 10, 20]) -> pd.DataFrame:
        """计算不同周期的收益率"""
        df_result = self.df.copy()
        for period in periods:
            df_result[f"return_{period}d"] = df_result["close"].pct_change(
                periods=period
            )
        return df_result

    def calculate_volatility(self, window: int = 20) -> pd.DataFrame:
        """计算波动率"""
        df_result = self.df.copy()
        df_result["volatility"] = df_result["close"].pct_change().rolling(
            window=window
        ).std() * np.sqrt(252)
        return df_result


def create_stock_dataframe_from_db(
    db_path: str, stock_code: str, limit: int = 500
) -> pd.DataFrame:
    """
    从数据库创建股票 DataFrame

    Args:
        db_path: 数据库路径
        stock_code: 股票代码
        limit: 返回的最大记录数

    Returns:
        包含股票数据的 DataFrame
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    query = """
    SELECT date, open, high, low, close, volume, ma5, ma10, ma20, rsi6, rsi14, pct_change
    FROM merged_stocks
    WHERE code = ?
    ORDER BY date DESC
    LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=[stock_code, limit])
    conn.close()

    # 反转顺序，使日期从旧到新
    df = df.iloc[::-1].reset_index(drop=True)
    return df


def merge_technical_indicators_to_db(
    db_path: str, stock_code: str, df_with_indicators: pd.DataFrame
):
    """
    将技术指标合并回数据库

    Args:
        db_path: 数据库路径
        stock_code: 股票代码
        df_with_indicators: 包含新指标的 DataFrame
    """
    import sqlite3

    conn = sqlite3.connect(db_path)

    # 获取现有的列名
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(merged_stocks)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    # 准备要更新的数据
    update_data = []
    new_columns = []

    for _, row in df_with_indicators.iterrows():
        record = {"code": stock_code, "date": row["date"]}

        # 添加现有列的数据
        for col in existing_columns:
            if col in row and col not in ["code", "date"]:
                record[col] = row[col]

        # 添加新指标列
        for col in df_with_indicators.columns:
            if col not in existing_columns and col not in ["code", "date"]:
                if col not in new_columns:
                    new_columns.append(col)
                record[col] = row[col]

        update_data.append(record)

    # 添加新列到表中（如果不存在）
    for col in new_columns:
        try:
            cursor.execute(f"ALTER TABLE merged_stocks ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            # 列已存在
            pass

    # 更新数据
    for record in update_data:
        set_clause = ", ".join(
            [f"{k} = ?" for k in record.keys() if k not in ["code", "date"]]
        )
        values = [record[k] for k in record.keys() if k not in ["code", "date"]]
        values.extend([record["code"], record["date"]])

        cursor.execute(
            f"""
        UPDATE merged_stocks 
        SET {set_clause}
        WHERE code = ? AND date = ?
        """,
            values,
        )

    conn.commit()
    conn.close()


# 使用示例
if __name__ == "__main__":
    # 示例：从数据库加载数据并计算指标
    # df = create_stock_dataframe_from_db("/path/to/db.sqlite", "000923")
    # analyzer = StockAnalyzer(df)
    # df_with_indicators = analyzer.calculate_all_indicators()
    # print(df_with_indicators.tail())
    # print(analyzer.get_technical_signals())
    pass
