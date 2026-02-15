# 东方财富股票爬虫使用说明

## 功能介绍
这是一个专门从东方财富网站(quote.eastmoney.com)爬取股票价格信息的爬虫工具。

## 文件结构
```
crawler/eastmoney/
├── stock_crawler.py          # 基础版本爬虫
└── eastmoney_crawler.py      # 完整版爬虫（推荐使用）
```

## 使用方法

### 1. 基础使用
```bash
# 测试运行
python crawler/eastmoney/eastmoney_crawler.py
```

### 2. 在代码中调用
```python
import asyncio
from crawler.eastmoney.eastmoney_crawler import crawl_multiple_stocks

# 爬取指定股票
stock_codes = ["002323", "000001", "600519"]
target_date = "2026-02-09"
db_path = "/path/to/your/database.db"

# 异步调用
success_count = asyncio.run(crawl_multiple_stocks(stock_codes, target_date, db_path))
print(f"成功爬取 {success_count} 只股票")
```

### 3. 集成到现有系统
可以将此爬虫集成到 `fill_missing_dates.py` 中作为备用数据源：

```python
# 在 fill_missing_dates.py 中添加东方财富爬虫选项
from crawler.eastmoney.eastmoney_crawler import EastMoneyStockCrawler

# 使用方式类似现有的新浪爬虫
eastmoney_crawler = EastMoneyStockCrawler()
data = await eastmoney_crawler.crawl_stock_price("002323")
```

## 支持的功能

### ✅ 已实现功能
- [x] 自动识别股票市场（上海/深圳）
- [x] 提取股票当前价格
- [x] 提取股票名称
- [x] 提取涨跌幅信息
- [x] 数据库存储支持
- [x] 批量处理多个股票
- [x] 防止重复数据插入
- [x] 详细的日志输出

### 📊 提取的数据字段
```python
{
    "code": "股票代码",        # 如: "002323"
    "name": "股票名称",        # 如: "雅博股份"
    "date": "日期",           # 如: "2026-02-09"
    "close": 6.54,           # 当前价格
    "change": 0.12,          # 涨跌金额
    "change_percent": 1.87,  # 涨跌幅百分比
    "open": None,            # 开盘价（暂未实现）
    "high": None,            # 最高价（暂未实现）
    "low": None,             # 最低价（暂未实现）
    "volume": None           # 成交量（暂未实现）
}
```

## 技术特点

### 🔧 核心技术
- **Playwright**: 无头浏览器自动化
- **智能解析**: 多重策略提取价格数据
- **错误处理**: 完善的异常捕获和重试机制
- **数据验证**: 自动过滤不合理的价格数据

### 🚀 性能优化
- 异步并发处理
- 智能等待策略
- 请求频率控制
- 内存使用优化

## 注意事项

### ⚠️ 使用限制
1. **请求频率**: 建议每次请求间隔2-3秒
2. **数据准确性**: 页面结构可能变化，需定期维护
3. **网络稳定性**: 依赖网络连接质量
4. **反爬虫机制**: 东方财富可能有限制，建议合理使用

### 🛡️ 风险提示
- 仅供学习和研究使用
- 请遵守网站的robots.txt和使用条款
- 不建议用于商业用途
- 数据仅供参考，不构成投资建议

## 故障排除

### 常见问题
1. **页面加载超时**: 增加timeout参数
2. **数据提取失败**: 检查页面结构是否发生变化
3. **数据库连接错误**: 确认数据库路径正确
4. **浏览器启动失败**: 检查Playwright安装和权限

### 调试方法
```bash
# 启用详细日志
export DEBUG=1
python crawler/eastmoney/eastmoney_crawler.py
```

## 版本历史
- v1.0: 基础功能实现
- v1.1: 添加数据库存储功能
- v1.2: 优化数据提取算法
- v1.3: 增加批量处理能力

## 贡献
欢迎提交issue和pull request来改进这个爬虫工具！