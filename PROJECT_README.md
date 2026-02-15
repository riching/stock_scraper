# 股票爬虫项目文档

## 项目概述

这是一个基于Python的股票数据爬虫和分析系统，用于从多个数据源爬取A股股票数据，提供Web界面和API接口进行数据查询和分析。

## 技术栈

- **Web框架**: Flask 3.1.2
- **数据库**: SQLite
- **数据处理**: pandas 2.2.0, numpy 1.26.0, pandas-ta 1.3.0
- **爬虫工具**: requests 2.32.3, playwright 1.58.0
- **AI分析**: dashscope 1.25.12 (阿里云千问大模型)
- **测试框架**: pytest 9.0.2, pytest-flask 1.3.0
- **数据源**: akshare 1.18.3

## 项目结构

```
stock_scraper/
├── app/                          # Flask应用
│   ├── api/                      # API路由
│   ├── models/                   # 数据模型
│   │   └── stock.py             # StockDatabase类
│   ├── static/                   # 静态资源
│   │   └── css/
│   ├── templates/                # HTML模板
│   │   ├── base.html
│   │   ├── industries.html
│   │   ├── industry_stocks.html
│   │   ├── search_results.html
│   │   └── stock_detail.html
│   ├── __init__.py
│   └── main.py                   # Flask应用入口
├── crawler/                      # 爬虫模块
│   ├── common/                   # 公共模块
│   │   ├── base_scraper.py      # 爬虫基类
│   │   ├── extractors.py        # 数据提取器
│   │   ├── llm_analyzer.py      # 大模型分析器
│   │   └── __init__.py
│   ├── eastmoney/               # 东方财富爬虫
│   │   ├── eastmoney_crawler.py
│   │   ├── history_crawler.py
│   │   ├── hybrid_crawler.py
│   │   ├── optimized_history_crawler.py
│   │   ├── practical_history_fetcher.py
│   │   ├── stock_crawler.py
│   │   ├── improved_crawler.py  # 改进的东方财富爬虫
│   │   └── README.md
│   ├── sina/                    # 新浪财经爬虫
│   │   ├── sina_crawler.py
│   │   ├── sina_history_crawler.py
│   │   ├── sina_scraper.py
│   │   ├── stock_info_crawler.py
│   │   ├── real_stock_crawler.py
│   │   ├── scraper.py
│   │   ├── simple_scraper.py
│   │   ├── large_test_update.py
│   │   ├── market_prefix_helper.py
│   │   └── sina_playwright_crawler.py  # 新浪财经Playwright爬虫
│   ├── tencent/                 # 腾讯证券爬虫
│   │   ├── tencent_crawler.py
│   │   ├── tencent_history_crawler.py  # 腾讯历史数据爬虫
│   │   ├── diagnose_history.py  # 腾讯历史数据诊断工具
│   │   └── demo.py
│   ├── scheduler/               # 调度器
│   │   └── scheduler.py         # 定时更新调度器
│   ├── multi_source_crawler.py  # 多数据源爬虫管理器（实时数据）
│   └── multi_source_history_crawler.py  # 多数据源历史数据爬虫
├── config/                      # 配置文件
│   ├── __init__.py
│   └── settings.py              # 全局配置
├── tests/                       # 测试代码
│   ├── test_api/                # API测试
│   ├── test_models/             # 模型测试
│   ├── test_cron/               # 调度器测试
│   ├── test_pandas/             # pandas测试
│   ├── e2e/                     # 端到端测试
│   ├── conftest.py
│   └── integration_test.py
├── logs/                        # 日志文件
├── run.py                       # 启动脚本
├── requirements.txt             # 依赖包
└── stocks.db                    # SQLite数据库
```

## 核心功能

### 1. 数据爬取

#### 支持的数据源
- **新浪财经**: 实时股票数据、历史数据（API）
- **东方财富**: 实时股票数据、历史数据
- **腾讯证券**: 实时股票数据（不支持历史数据）
- **akshare**: 备用数据源

#### 爬虫模块

**新浪财经爬虫**
- `SinaFinanceScraper`: 新浪财经数据爬虫类（基于requests）
- `SinaPlaywrightCrawler`: 新浪财经数据爬虫类（基于Playwright，推荐）
- 支持实时数据和历史数据爬取
- 使用Playwright无头浏览器，支持JavaScript执行

**东方财富爬虫**
- `EastMoneyStockExtractor`: 东方财富数据提取器
- `ImprovedEastMoneyCrawler`: 改进的东方财富爬虫
- 使用playwright进行浏览器自动化
- 支持JavaScript数据提取

**多数据源爬虫** (推荐)
- `MultiSourceCrawler`: 多数据源爬虫管理器
- 自动检测数据源可用性
- 智能选择最佳数据源
- 数据源故障自动切换
- 统计各数据源的成功率
- 支持JavaScript渲染的页面

**爬虫基类** ([base_scraper.py](crawler/common/base_scraper.py))
- `BaseScraper`: 所有爬虫的基类
- 提供通用的页面获取和错误处理功能

### 2. 数据存储

#### 数据库模型

**StockDatabase** ([stock.py](app/models/stock.py))
- `get_industries()`: 获取所有行业分类
- `get_stocks_by_industry()`: 获取指定行业的股票列表（支持分页）
- `get_stock_detail()`: 获取股票详情
- `get_stock_kline_data()`: 获取股票K线数据
- `search_stocks()`: 搜索股票（支持代码和名称）

#### 数据库表结构
- `stock_list`: 股票基本信息表
- `stock_classifications`: 股票行业分类表
- `merged_stocks`: 合并的股票数据表（包含技术指标）

### 3. Web界面

#### 页面路由

- `/`: 首页 - 行业列表
- `/industry/<industry_name>`: 行业股票列表（支持分页）
- `/stock/<stock_code>`: 股票详情页（包含K线图）
- `/search`: 搜索页面

#### API接口

- `GET /api/industries`: 获取行业列表
- `GET /api/industry/<industry_name>`: 获取指定行业的股票列表
- `GET /api/stock/<stock_code>`: 获取股票详情
- `GET /api/search`: 搜索股票

### 4. 定时调度

**StockUpdateScheduler** ([scheduler.py](crawler/scheduler/scheduler.py))
- `run_afternoon_update()`: 下午更新（3:30后）
- `run_evening_check()`: 晚上检查（11:00）
- `run_update_only()`: 仅更新模式
- `run_check_only()`: 仅检查模式

#### 命令行使用
```bash
# 下午更新
python -m crawler.scheduler.scheduler --afternoon

# 晚上检查
python -m crawler.scheduler.scheduler --evening

# 仅更新
python -m crawler.scheduler.scheduler --update-only

# 仅检查
python -m crawler.scheduler.scheduler --check-only

# 指定日期检查
python -m crawler.scheduler.scheduler --check-only --date 2026-02-13
```

### 5. 爬虫使用（新增）

#### 使用多数据源爬虫（推荐 - 实时数据）

```bash
# 运行多数据源爬虫
python crawler/multi_source_crawler.py
```

#### 使用多数据源历史数据爬虫（推荐 - 历史数据）

```bash
# 运行多数据源历史数据爬虫
python crawler/multi_source_history_crawler.py
```

#### 使用新浪财经Playwright爬虫（实时数据）

```bash
# 运行新浪财经Playwright爬虫
python crawler/sina/sina_playwright_crawler.py
```

#### 使用新浪财经历史数据API（历史数据）

```bash
# 运行新浪财经历史数据API
python crawl_sina_history_api.py
```

#### 使用东方财富改进爬虫（实时数据）

```bash
# 运行东方财富改进爬虫
python crawler/eastmoney/improved_crawler.py
```

#### 清理指定日期的数据

```bash
# 清理数据库中指定日期的数据
python clean_date_data.py
```

#### 在代码中使用

```python
import asyncio
from crawler.multi_source_crawler import MultiSourceCrawler
from crawler.multi_source_history_crawler import MultiSourceHistoryCrawler

# 实时数据爬取
async def crawl_realtime():
    crawler = MultiSourceCrawler("/path/to/database.db")
    
    try:
        await crawler.init_crawlers()
        
        stock_codes = ["000001", "600519", "000858"]
        results = await crawler.crawl_multiple_stocks(stock_codes)
        
        if results:
            crawler.save_to_database(results)
        
        crawler.print_stats()
        
    finally:
        await crawler.close_crawlers()

# 历史数据爬取
async def crawl_history():
    crawler = MultiSourceHistoryCrawler("/path/to/database.db")
    
    try:
        await crawler.init_sources()
        
        stock_codes = ["000001", "600519", "000858"]
        target_date = "2026-02-09"
        results = await crawler.crawl_multiple_stocks(stock_codes, target_date)
        
        if results:
            crawler.save_to_database(results)
        
        crawler.print_stats()
        
    finally:
        await crawler.close_sources()

# 运行
asyncio.run(crawl_realtime())
asyncio.run(crawl_history())
```

### 6. AI分析

**LLMAnalyzer** ([llm_analyzer.py](crawler/common/llm_analyzer.py))
- 使用阿里云千问大模型进行文本分析
- 支持情感分析、内容摘要、关键点提取
- 可分析新闻、公告、评论、研报等内容

## 配置说明

### 全局配置 ([settings.py](config/settings.py))

```python
# 数据库路径
DB_PATH = "/Users/riching/work/hywork/db/sqlite/full_a_stock_cache.db"

# 数据源配置
DATA_SOURCES = [
    {
        "name": "SinaFinance",
        "base_url": "http://finance.sina.com.cn/realstock/company/{market}{code}/nc.shtml",
        "enabled": True,
        "timeout": 10,
        "retry_count": 3,
    },
    # ...
]

# 爬虫配置
USER_AGENTS = [...]  # User-Agent列表
BATCH_SIZE = 20      # 批处理大小
REQUEST_DELAY = (0.5, 1.5)  # 请求延迟范围

# 调试配置
DEBUG = True
```

### 环境变量

需要设置以下环境变量：
- `QWEN_API_KEY`: 阿里云千问API密钥（用于AI分析功能）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

确保数据库路径正确，或修改 [config/settings.py](config/settings.py) 中的 `DB_PATH`

### 3. 启动Web服务

```bash
python run.py
```

服务将在 `http://localhost:5002` 启动

### 4. 运行爬虫

#### 使用多数据源爬虫（推荐）

```bash
python crawler/multi_source_crawler.py
```

#### 使用新浪财经Playwright爬虫

```bash
python crawler/sina/sina_playwright_crawler.py
```

#### 使用东方财富改进爬虫

```bash
python crawler/eastmoney/improved_crawler.py
```

### 5. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api/
pytest tests/test_models/
pytest tests/test_cron/
```

## 数据库表结构

### stock_list
股票基本信息表
- `code`: 股票代码
- `name`: 股票名称

### stock_classifications
股票行业分类表
- `股票代码`: 股票代码
- `一级行业名称`: 一级行业
- `二级行业名称`: 二级行业
- `三级行业名称`: 三级行业

### merged_stocks
合并的股票数据表（包含技术指标）
- `code`: 股票代码
- `date`: 日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 成交量
- `amount`: 成交额
- `ma5`: 5日均线
- `ma10`: 10日均线
- `ma20`: 20日均线
- `rsi6`: RSI(6)
- `rsi14`: RSI(14)
- `pct_change`: 涨跌幅

## 开发指南

### 添加新的数据源

1. 在 `crawler/` 下创建新的数据源目录
2. 继承 `BaseScraper` 类
3. 实现 `fetch_page()` 和 `parse_stock_data()` 方法
4. 在 `config/settings.py` 中添加数据源配置

### 添加新的API端点

在 [app/main.py](app/main.py) 中添加新的路由：

```python
@app.route("/api/your-endpoint")
def your_endpoint():
    # 实现逻辑
    return {"success": True, "data": result}
```

### 添加新的测试

在 `tests/` 目录下创建对应的测试文件：

```python
def test_your_feature():
    # 测试逻辑
    assert True
```

## 常见问题

### 1. 数据库连接失败
检查 `config/settings.py` 中的 `DB_PATH` 是否正确

### 2. 爬虫请求失败
- 检查网络连接
- 检查数据源URL是否有效
- 调整 `REQUEST_DELAY` 避免被反爬

### 3. AI分析功能不可用
确保设置了 `QWEN_API_KEY` 环境变量

## 日志

日志文件位于 `logs/` 目录：
- `scheduler.log`: 调度器日志
- `stock_update_YYYYMMDD.log`: 每日更新日志

## 注意事项

1. 本项目仅用于学习和研究目的
2. 请遵守相关数据源的使用条款
3. 注意控制爬取频率，避免对数据源造成压力
4. 数据仅供参考，不构成投资建议

## 维护者

项目维护者信息

## 许可证

项目许可证信息
