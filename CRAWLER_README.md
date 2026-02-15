# 股票数据爬虫文档

## 概述

本项目提供多数据源的股票价格数据爬取功能，支持实时数据和历史数据爬取。

## 爬虫列表

### 1. 新浪爬虫

#### 文件位置
- 实时数据: `crawler/sina/sina_history_crawler.py`
- 历史数据: `crawler/sina/sina_history_crawler.py` (同一个文件)

#### 数据源
- 实时数据API: `http://hq.sinajs.cn/list={market_prefix}{stock_code}`
- 历史数据API: `https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData`

#### 爬取逻辑

**实时数据爬取:**
1. 构造API URL: `http://hq.sinajs.cn/list=sh600519`
2. 发送HTTP GET请求获取数据
3. 解析返回的字符串格式数据
4. 数据格式: `var hq_str_sh600519="贵州银行,10.91,10.90,11.00,10.85,1234567,..."`
5. 提取字段: 名称、开盘、收盘、最高、最低、成交量等

**历史数据爬取:**
1. 构造API URL: `https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={stock_code}&scale=240&ma=no&datalen=1023`
2. 发送HTTP GET请求获取JSON数据
3. 解析JSON数组，每个元素包含日期、开盘、收盘、最高、最低、成交量
4. 根据目标日期筛选数据

#### 特点
- ✅ API接口稳定
- ✅ 数据格式简单
- ✅ 支持实时和历史数据
- ✅ 无需浏览器，直接HTTP请求

### 2. 东方财富爬虫

#### 文件位置
- 实时数据: `crawler/eastmoney/eastmoney_crawler.py`
- 历史数据: `crawler/eastmoney/history_crawler.py`

#### 数据源
- 实时数据: 页面元素提取
- 历史数据API: `https://push2his.eastmoney.com/api/qt/stock/kline/get`

#### 爬取逻辑

**实时数据爬取:**
1. 使用Playwright访问股票页面: `https://quote.eastmoney.com/sz000001.html`
2. 使用XPath定位页面中的价格信息表格
3. 从表格元素中提取数据:
   - 今开: `//td[contains(text(), "今开：")]/following-sibling::td//span//span`
   - 最高: `//td[contains(text(), "最高：")]/following-sibling::td//span//span`
   - 最低: `//td[contains(text(), "最低：")]/following-sibling::td//span//span`
   - 昨收: `//td[contains(text(), "昨收：")]/following-sibling::td//span//span`
   - 成交量: `//td[contains(text(), "成交量：")]/following-sibling::td//span//span`
   - 换手率: `//td[contains(text(), "换手：")]/following-sibling::td//span//span`
4. 股票名称从页面元素提取: `.stock-name, [class*="name"]`
5. 去掉名称中的空格

**历史数据爬取:**
1. 构造K线API URL: `https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{code}&klt=101&fqt=1&beg={date}&end={date}`
2. 参数说明:
   - `secid`: 市场代码.股票代码 (0.000001 表示深圳, 1.600519 表示上海)
   - `klt=101`: 日K线数据
   - `fqt=1`: 前复权
   - `beg`: 开始日期 (YYYYMMDD格式)
   - `end`: 结束日期 (YYYYMMDD格式)
3. 发送HTTP GET请求获取JSON数据
4. 解析返回的K线数据数组
5. K线数据格式: `日期,开盘,收盘,最高,最低,成交量,成交额,振幅`
6. 提取指定日期的数据

#### 特点
- ✅ 实时数据从页面元素提取，准确可靠
- ✅ 历史数据使用K线API，支持任意日期查询
- ✅ API返回完整的K线数据
- ✅ 非交易日返回空数组，便于判断

### 3. 腾讯爬虫

#### 文件位置
- 实时数据: `crawler/tencent/tencent_crawler.py`
- 历史数据: `crawler/tencent/tencent_history_crawler.py` ⚠️ API已失效

#### 数据源
- 实时数据API: `http://qt.gtimg.cn/q={market_prefix}{stock_code}`
- 历史数据API: `http://web.ifzq.gtimg.cn/appstock/app/fqkline/get` ⚠️ 已失效

#### 爬取逻辑

**实时数据爬取:**
1. 构造API URL: `http://qt.gtimg.cn/q=sh600519`
2. 发送HTTP GET请求获取数据
3. 解析返回的字符串格式数据
4. 数据格式: `v_sh600519="1~贵州茅台~600519~1485.30~..."`
5. 提取字段: 名称、代码、当前价、昨收、开盘、成交量等
6. 计算涨跌额和涨跌幅

**历史数据爬取:**
⚠️ **注意**: 腾讯历史数据API已失效，所有请求返回"param error"
- 建议使用新浪或东方财富的历史数据API
- 实时数据爬虫功能正常

#### 特点
- ✅ 实时数据API接口稳定
- ✅ 数据格式简单
- ✅ 无需浏览器，直接HTTP请求
- ❌ 历史数据API已失效

### 4. Akshare数据源

#### 文件位置
- 数据获取模块: `utils/akshare_data.py`
- 使用示例: `fill_missing_dates.py`

#### 数据源
- 实时数据API: `ak.stock_zh_a_spot_em()`
- 历史数据API: `ak.stock_zh_a_hist()`, `ak.stock_zh_a_hist_min_em()`

#### 爬取逻辑

**实时数据爬取:**
1. 调用akshare的实时行情接口获取所有A股数据
2. 根据股票代码筛选目标股票
3. 提取字段: 名称、开盘、收盘、最高、最低、成交量等
4. 数据格式: 6位数字代码（保持前导零）

**历史数据爬取:**
1. 尝试多种数据获取方式（容错机制）:
   - 标准历史接口: `ak.stock_zh_a_hist()`
   - 分钟数据聚合: `ak.stock_zh_a_hist_min_em()`
   - 实时数据作为当日数据备选
2. 根据目标日期筛选数据
3. 支持前复权、后复权等选项

#### 特点
- ✅ 数据质量高，直接从交易所获取
- ✅ 支持实时和历史数据
- ✅ 多种数据获取方式，容错性强
- ✅ 支持批量获取
- ❌ 速度较慢
- ❌ 失败率较高
- ❌ 依赖第三方库，需要安装akshare

#### 使用建议
- **适用场景**: 作为备用数据源，当其他爬虫失败时使用
- **不适用场景**: 大批量数据爬取，对速度要求高的场景
- **权重**: 0.8（数据质量高，但速度慢）

### 5. Baostock数据源

#### 文件位置
- 历史数据爬虫: `crawler/baostock/baostock_history_crawler.py`

#### 数据源
- 实时数据API: `bs.query_history_k_data_plus()` (获取最新一天数据)
- 历史数据API: `bs.query_history_k_data_plus()`

#### 爬取逻辑

**实时数据爬取:**
1. 登录Baostock系统
2. 调用历史数据API获取最近一天的数据
3. 提取最新的一条数据作为实时数据
4. 提取字段: 日期、代码、开盘、收盘、最高、最低、成交量等

**历史数据爬取:**
1. 登录Baostock系统
2. 调用历史数据API获取指定日期的数据
3. 根据目标日期筛选数据
4. 提取字段: 日期、代码、开盘、收盘、最高、最低、成交量等

#### 特点
- ✅ 完全免费，无需付费
- ✅ 专为A股设计，数据准确
- ✅ 支持实时和历史数据
- ✅ API稳定，速度快
- ✅ 数据质量高
- ⚠️ 需要登录/登出操作
- ⚠️ 依赖第三方库，需要安装baostock

#### 使用建议
- **适用场景**: 作为主要数据源之一，数据质量高且免费
- **不适用场景**: 需要实时行情的场景（数据有一定延迟）
- **权重**: 0.95（数据质量高，速度快，完全免费）

### 6. Yahoo Finance数据源

#### 文件位置
- 历史数据爬虫: `crawler/yahoo_finance/yahoo_finance_history_crawler.py`

#### 数据源
- 实时数据API: `yf.download(period="1d", interval="1d")`
- 历史数据API: `yf.download(start=date, end=next_day)`

#### 爬取逻辑

**实时数据爬取:**
1. 转换股票代码为Yahoo Finance格式（如: 000001.SZ, 600519.SS）
2. 调用yfinance下载最近一天的数据
3. 提取最新的一条数据作为实时数据
4. 提取字段: 日期、开盘、收盘、最高、最低、成交量等

**历史数据爬取:**
1. 转换股票代码为Yahoo Finance格式
2. 调用yfinance下载指定日期范围的数据
3. 根据目标日期筛选数据
4. 提取字段: 日期、开盘、收盘、最高、最低、成交量等

#### 特点
- ✅ 国际化数据源，支持多市场
- ✅ 支持A股数据
- ✅ 支持实时和历史数据
- ✅ API稳定，数据准确
- ✅ 有Python库支持，使用简单
- ⚠️ 数据有一定延迟
- ⚠️ 依赖第三方库，需要安装yfinance

#### 使用建议
- **适用场景**: 作为备用数据源，国际化数据支持
- **不适用场景**: 需要实时行情的场景（数据有一定延迟）
- **权重**: 0.9（数据质量高，国际化支持）

## 多源爬虫

### 文件位置
- 实时数据: `crawler/multi_source_crawler.py`
- 历史数据: `crawler/multi_source_history_crawler.py`

### 爬取逻辑
1. 按优先级依次尝试多个数据源
2. 如果一个数据源失败，自动切换到下一个
3. 支持自定义数据源顺序
4. 提高数据获取的成功率

### 数据源优先级

#### 实时数据
1. 新浪 (优先级最高) - 使用Playwright浏览器，数据准确
2. 腾讯 - 使用HTTP API，速度快
3. 东方财富 - 使用Playwright浏览器，数据准确

#### 历史数据
1. 东方财富 - 使用K线API，速度快，数据准确，稳定性好
2. Baostock - 专为A股设计，完全免费，数据质量高
3. Yahoo Finance - 国际化数据源，支持多市场，数据准确
4. Akshare - 数据质量高，但速度慢，作为备用
5. 新浪 - 使用API接口，但容易触发反爬虫机制

### 特点
- ✅ 自动fallback机制，提高成功率
- ✅ 支持多个数据源并行初始化
- ✅ 统计各数据源的成功率和平均耗时
- ✅ 自动处理不同爬虫的关闭逻辑（浏览器/HTTP）
- ✅ 数据源优先级可配置
- ✅ 显示数据源特性信息（类型、速度、可靠性）

### 使用示例

```python
import asyncio
from crawler.multi_source_history_crawler import MultiSourceHistoryCrawler

async def main():
    db_path = "/path/to/database.db"
    stock_codes = ["000001", "600519", "000858"]
    target_date = "2026-02-12"
    
    crawler = MultiSourceHistoryCrawler(db_path)
    
    try:
        # 初始化爬虫
        await crawler.init_crawlers()
        
        # 批量爬取
        results = await crawler.crawl_multiple_stocks(stock_codes, target_date)
        
        # 保存到数据库
        if results:
            crawler.save_to_database(results)
        
        # 打印统计信息
        crawler.print_stats()
        
    finally:
        # 关闭爬虫
        await crawler.close_crawlers()

asyncio.run(main())
```

## 辅助工具

### 市场前缀助手
- 文件: `crawler/sina/market_prefix_helper.py`
- 功能: 根据股票代码自动判断市场前缀
- 规则:
  - 600xxx, 601xxx, 603xxx, 688xxx -> sh (上海)
  - 其他 -> sz (深圳)

## 数据格式

### 返回数据结构
```python
{
    "code": "600519",      # 股票代码
    "name": "贵州茅台",    # 股票名称
    "date": "2026-02-14", # 日期
    "open": 1485.30,       # 开盘价
    "close": 1485.30,      # 收盘价
    "high": 1500.00,       # 最高价
    "low": 1480.00,        # 最低价
    "volume": 1234567,     # 成交量
    "change": 5.00,        # 涨跌额
    "change_percent": 0.34  # 涨跌幅(%)
}
```

## 使用示例

### 爬取实时数据
```python
from crawler.sina.sina_history_crawler import SinaStockCrawler

crawler = SinaStockCrawler()
data = await crawler.crawl_stock_price("600519")
print(data)
```

### 爬取历史数据
```python
from crawler.eastmoney.history_crawler import EnhancedEastMoneyCrawler

crawler = EnhancedEastMoneyCrawler()
data = await crawler.crawl_history_price("600519", "2026-02-09")
print(data)
```

## 注意事项

1. **交易日判断**: 股票数据只在交易日有数据，周末和节假日无数据
2. **数据延迟**: 实时数据可能有几分钟的延迟
3. **请求频率**: 避免过于频繁的请求，建议间隔0.5秒以上
4. **错误处理**: 所有爬虫都有完善的错误处理和重试机制
5. **数据验证**: 获取数据后建议进行合理性验证

## 性能优化

1. **API优先**: 优先使用API接口，避免浏览器渲染
2. **异步处理**: 使用async/await提高并发性能
3. **连接复用**: 复用HTTP连接减少开销
4. **缓存机制**: 对相同请求进行缓存

## 故障排查

### 新浪爬虫
- 问题: API返回空数据
- 解决: 检查股票代码格式，确保使用正确的市场前缀

### 东方财富爬虫
- 问题: 页面元素找不到
- 解决: 等待页面完全加载后再提取数据
- 问题: 历史数据返回空数组
- 解决: 检查日期是否为交易日

### 腾讯爬虫
- 问题: API请求失败
- 解决: 检查网络连接，增加请求超时时间

## 更新日志

### 2026-02-14
- ✅ 修复东方财富实时数据爬取逻辑，使用XPath从页面元素提取
- ✅ 修复东方财富历史数据爬取逻辑，使用K线API
- ✅ 优化股票名称提取，去掉空格
- ✅ 删除测试和模拟脚本，清理代码结构
- ✅ 统一使用market_prefix_helper获取市场前缀
