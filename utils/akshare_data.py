#!/usr/bin/env python3
"""akshare股票数据获取模块"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
from typing import Dict, List, Optional

# 配置日志
logger = logging.getLogger(__name__)

class AkshareDataFetcher:
    """akshare数据获取器"""
    
    def __init__(self):
        self.name = "Akshare"
        self.enabled = True
        self.weight = 0.8  # akshare权重较高，因为数据质量更好
        self.max_retries = 3
        self.retry_delay = 1
        
    def get_real_time_price(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票实时价格数据
        """
        for attempt in range(self.max_retries):
            try:
                # 转换股票代码格式
                formatted_code = self._format_stock_code(stock_code)
                if not formatted_code:
                    return None
                    
                # 获取实时行情数据
                stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
                
                # 查找对应股票
                stock_data = stock_zh_a_spot_em_df[
                    stock_zh_a_spot_em_df['代码'] == formatted_code
                ]
                
                if stock_data.empty:
                    logger.warning(f"未找到股票 {stock_code} 的实时数据")
                    return None
                    
                row = stock_data.iloc[0]
                
                # 构造返回数据
                result = {
                    "code": stock_code,
                    "name": row['名称'],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "open": float(row['今开']) if pd.notna(row['今开']) else None,
                    "high": float(row['最高']) if pd.notna(row['最高']) else None,
                    "low": float(row['最低']) if pd.notna(row['最低']) else None,
                    "close": float(row['最新价']) if pd.notna(row['最新价']) else None,
                    "volume": int(row['成交量']) if pd.notna(row['成交量']) else None,
                    "amount": float(row['成交额']) if pd.notna(row['成交额']) else None,
                    "change": float(row['涨跌额']) if pd.notna(row['涨跌额']) else None,
                    "change_percent": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
                    "source": "akshare"
                }
                
                logger.info(f"✅ akshare获取 {stock_code} 实时数据成功")
                return result
                
            except Exception as e:
                logger.warning(f"akshare获取 {stock_code} 实时数据第{attempt+1}次尝试失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"❌ akshare获取 {stock_code} 实时数据最终失败: {e}")
                    return None
    
    def get_historical_price(self, stock_code: str, target_date: str) -> Optional[Dict]:
        """
        获取股票历史价格数据 - 增强版
        """
        for attempt in range(self.max_retries):
            try:
                # 转换股票代码格式
                formatted_code = self._format_stock_code(stock_code)
                if not formatted_code:
                    return None
                    
                # 转换日期格式
                target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                
                # 尝试多种历史数据获取方式
                historical_data = None
                
                # 方法1: 使用标准历史行情接口
                try:
                    logger.info(f"📡 尝试标准历史接口获取 {stock_code} 数据...")
                    historical_data = self._fetch_standard_history(formatted_code, target_dt)
                except Exception as e:
                    logger.warning(f"标准历史接口失败: {e}")
                
                # 方法2: 使用分钟数据接口获取日线数据
                if historical_data is None:
                    try:
                        logger.info(f"🔄 尝试分钟数据接口获取 {stock_code} 数据...")
                        historical_data = self._fetch_minute_to_daily(formatted_code, target_dt)
                    except Exception as e:
                        logger.warning(f"分钟数据接口失败: {e}")
                
                # 方法3: 使用实时数据作为当日历史数据的备选
                if historical_data is None and target_date == datetime.now().strftime("%Y-%m-%d"):
                    try:
                        logger.info(f"🔄 使用实时数据作为当日历史数据...")
                        historical_data = self._fetch_today_as_history(formatted_code, target_date)
                    except Exception as e:
                        logger.warning(f"当日数据获取失败: {e}")
                
                if historical_data is None:
                    logger.warning(f"未能获取 {stock_code} 在 {target_date} 的历史数据")
                    return None
                
                # 构造返回数据
                result = {
                    "code": stock_code,
                    "name": historical_data.get("name"),
                    "date": target_date,
                    "open": historical_data.get("open"),
                    "high": historical_data.get("high"),
                    "low": historical_data.get("low"),
                    "close": historical_data.get("close"),
                    "volume": historical_data.get("volume"),
                    "amount": historical_data.get("amount"),
                    "change": historical_data.get("change"),
                    "change_percent": historical_data.get("change_percent"),
                    "source": "akshare"
                }
                
                logger.info(f"✅ akshare获取 {stock_code} 历史数据成功")
                return result
                
            except Exception as e:
                logger.warning(f"akshare获取 {stock_code} 历史数据第{attempt+1}次尝试失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"❌ akshare获取 {stock_code} 历史数据最终失败: {e}")
                    return None
    
    def _fetch_standard_history(self, formatted_code: str, target_dt: datetime) -> Optional[Dict]:
        """使用标准历史行情接口获取数据"""
        try:
            # 获取历史行情数据（获取前后几天的数据以确保能找到目标日期）
            start_date = (target_dt - timedelta(days=15)).strftime("%Y%m%d")
            end_date = (target_dt + timedelta(days=15)).strftime("%Y%m%d")
            
            # 尝试不同的参数组合
            param_combinations = [
                {"period": "daily", "adjust": ""},
                {"period": "daily", "adjust": "qfq"},  # 前复权
                {"period": "daily", "adjust": "hfq"},  # 后复权
            ]
            
            for params in param_combinations:
                try:
                    stock_zh_a_hist_df = ak.stock_zh_a_hist(
                        symbol=formatted_code,
                        period=params["period"],
                        start_date=start_date,
                        end_date=end_date,
                        adjust=params["adjust"]
                    )
                    
                    if not stock_zh_a_hist_df.empty:
                        # 查找目标日期的数据
                        if '日期' in stock_zh_a_hist_df.columns:
                            stock_zh_a_hist_df['date'] = pd.to_datetime(stock_zh_a_hist_df['日期'])
                            target_data = stock_zh_a_hist_df[
                                stock_zh_a_hist_df['date'] == target_dt
                            ]
                            
                            if not target_data.empty:
                                row = target_data.iloc[0]
                                return {
                                    "name": None,  # 历史数据中可能没有名称
                                    "open": self._safe_float(row, ['开盘', 'open']),
                                    "high": self._safe_float(row, ['最高', 'high']),
                                    "low": self._safe_float(row, ['最低', 'low']),
                                    "close": self._safe_float(row, ['收盘', 'close']),
                                    "volume": self._safe_int(row, ['成交量', 'volume']),
                                    "amount": self._safe_float(row, ['成交额', 'amount']),
                                    "change": self._safe_float(row, ['涨跌额', 'change']),
                                    "change_percent": self._safe_float(row, ['涨跌幅', 'change_percent']),
                                }
                except Exception as inner_e:
                    logger.debug(f"参数组合 {params} 失败: {inner_e}")
                    continue
                    
            return None
            
        except Exception as e:
            logger.debug(f"标准历史接口获取失败: {e}")
            return None
    
    def _fetch_minute_to_daily(self, formatted_code: str, target_dt: datetime) -> Optional[Dict]:
        """通过分钟数据聚合获取日线数据"""
        try:
            target_date_str = target_dt.strftime("%Y%m%d")
            
            # 获取分钟数据
            minute_data = ak.stock_zh_a_hist_min_em(
                symbol=formatted_code,
                period="1",
                adjust="",
                start_date=target_date_str,
                end_date=target_date_str
            )
            
            if minute_data.empty:
                return None
            
            # 聚合分钟数据为日线数据
            open_price = self._safe_float(minute_data.iloc[0], ['开盘', 'open'])
            close_price = self._safe_float(minute_data.iloc[-1], ['收盘', 'close'])
            
            high_price = minute_data[['最高', 'high']].max().max() if '最高' in minute_data.columns else close_price
            low_price = minute_data[['最低', 'low']].min().min() if '最低' in minute_data.columns else close_price
            
            volume = minute_data[['成交量', 'volume']].sum().sum() if '成交量' in minute_data.columns else None
            amount = minute_data[['成交额', 'amount']].sum().sum() if '成交额' in minute_data.columns else None
            
            return {
                "name": None,
                "open": float(open_price) if open_price else None,
                "high": float(high_price) if high_price else None,
                "low": float(low_price) if low_price else None,
                "close": float(close_price) if close_price else None,
                "volume": int(volume) if volume else None,
                "amount": float(amount) if amount else None,
                "change": None,
                "change_percent": None,
            }
            
        except Exception as e:
            logger.debug(f"分钟数据聚合失败: {e}")
            return None
    
    def _fetch_today_as_history(self, formatted_code: str, target_date: str) -> Optional[Dict]:
        """使用实时数据作为当日历史数据"""
        try:
            # 获取实时数据
            real_time_data = self.get_real_time_price(formatted_code.replace('sh', '').replace('sz', ''))
            
            if real_time_data:
                # 转换为历史数据格式
                return {
                    "name": real_time_data.get("name"),
                    "open": real_time_data.get("open"),
                    "high": real_time_data.get("high"),
                    "low": real_time_data.get("low"),
                    "close": real_time_data.get("close"),
                    "volume": real_time_data.get("volume"),
                    "amount": real_time_data.get("amount"),
                    "change": real_time_data.get("change"),
                    "change_percent": real_time_data.get("change_percent"),
                }
            return None
            
        except Exception as e:
            logger.debug(f"当日数据获取失败: {e}")
            return None
    
    def get_batch_real_time_prices(self, stock_codes: List[str]) -> List[Dict]:
        """
        批量获取实时价格数据
        """
        results = []
        
        try:
            # 获取所有A股实时行情
            stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
            
            # 创建代码映射
            code_mapping = {}
            for original_code in stock_codes:
                formatted_code = self._format_stock_code(original_code)
                if formatted_code:
                    code_mapping[formatted_code] = original_code
            
            # 筛选需要的股票
            filtered_data = stock_zh_a_spot_em_df[
                stock_zh_a_spot_em_df['代码'].isin(code_mapping.keys())
            ]
            
            # 转换为标准格式
            for _, row in filtered_data.iterrows():
                formatted_code = row['代码']
                original_code = code_mapping[formatted_code]
                
                result = {
                    "code": original_code,
                    "name": row['名称'],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "open": self._safe_float(row, ['今开', 'open']),
                    "high": self._safe_float(row, ['最高', 'high']),
                    "low": self._safe_float(row, ['最低', 'low']),
                    "close": self._safe_float(row, ['最新价', 'close']),
                    "volume": self._safe_int(row, ['成交量', 'volume']),
                    "amount": self._safe_float(row, ['成交额', 'amount']),
                    "change": self._safe_float(row, ['涨跌额', 'change']),
                    "change_percent": self._safe_float(row, ['涨跌幅', 'change_percent']),
                    "source": "akshare"
                }
                
                results.append(result)
                logger.info(f"✅ akshare获取 {original_code} 数据成功")
                
        except Exception as e:
            logger.error(f"❌ akshare批量获取数据失败: {e}")
            
        return results
    
    def _format_stock_code(self, stock_code: str) -> Optional[str]:
        """
        格式化股票代码以匹配akshare格式
        akshare使用6位数字代码，不需要市场前缀
        """
        try:
            # 移除可能的市场前缀
            code = stock_code.replace('sh', '').replace('sz', '')
            
            # 确保是6位数字
            if len(code) != 6 or not code.isdigit():
                logger.error(f"无效的股票代码格式: {stock_code}")
                return None
            
            # 返回6位代码（保持前导零）
            return code
            
        except Exception as e:
            logger.error(f"股票代码格式化错误 {stock_code}: {e}")
            return None
    
    def _safe_float(self, row, column_names):
        """安全地转换为浮点数"""
        for col_name in column_names:
            if col_name in row and pd.notna(row[col_name]):
                try:
                    return float(row[col_name])
                except (ValueError, TypeError):
                    continue
        return None
    
    def _safe_int(self, row, column_names):
        """安全地转换为整数"""
        for col_name in column_names:
            if col_name in row and pd.notna(row[col_name]):
                try:
                    return int(row[col_name])
                except (ValueError, TypeError):
                    continue
        return None

# 导出函数供外部使用
def get_akshare_real_time(stock_code: str) -> Optional[Dict]:
    """获取单个股票实时数据"""
    fetcher = AkshareDataFetcher()
    return fetcher.get_real_time_price(stock_code)

def get_akshare_historical(stock_code: str, target_date: str) -> Optional[Dict]:
    """获取单个股票历史数据"""
    fetcher = AkshareDataFetcher()
    return fetcher.get_historical_price(stock_code, target_date)

def get_akshare_batch(stock_codes: List[str]) -> List[Dict]:
    """批量获取股票数据"""
    fetcher = AkshareDataFetcher()
    return fetcher.get_batch_real_time_prices(stock_codes)