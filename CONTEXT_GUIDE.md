# 上下文指南

## 概述

本文档记录了AI助手在对话中需要读取的关键文档和上下文信息，用于理解项目结构、代码实现和开发规范。

## 核心文档（必须读取）

### 1. 项目配置文件
- **文件路径**: `PROJECT_CONFIG.md`
- **重要性**: ⭐⭐⭐⭐⭐
- **读取时机**: 每次对话开始时
- **用途**: 
  - 了解测试规则（每次测试50只股票）
  - 了解开发规范
  - 了解项目配置
  - 了解数据源优先级

### 2. 爬虫文档
- **文件路径**: `CRAWLER_README.md`
- **重要性**: ⭐⭐⭐⭐⭐
- **读取时机**: 涉及爬虫功能时
- **用途**:
  - 了解各个数据源的特点
  - 了解爬取逻辑和API接口
  - 了解数据源优先级
  - 了解使用示例

## 代码实现文件（按需读取）

### 3. 多线程爬虫主文件
- **文件路径**: `crawler/multi_source_history_crawler.py`
- **重要性**: ⭐⭐⭐⭐⭐
- **读取时机**: 修改或调试多线程爬虫时
- **用途**:
  - 查看消费者线程实现
  - 查看数据源配置
  - 查看统计报告逻辑
  - 查看测试模式配置

### 4. 各个数据源爬虫
- **文件路径**: 
  - `crawler/eastmoney/history_crawler.py`
  - `crawler/baostock/baostock_history_crawler.py`
  - `crawler/yahoo_finance/yahoo_finance_history_crawler.py`
  - `crawler/sina/sina_history_crawler_fixed.py`
- **重要性**: ⭐⭐⭐⭐
- **读取时机**: 修改或调试特定数据源时
- **用途**:
  - 查看具体实现
  - 查看API调用方式
  - 查看错误处理逻辑

### 5. 数据库工具类
- **文件路径**: `utils/stock_database.py`
- **重要性**: ⭐⭐⭐
- **读取时机**: 涉及数据库操作时
- **用途**:
  - 查看数据库接口
  - 查看数据结构
  - 查看连接管理

## 辅助文档（偶尔读取）

### 6. 数据库文档
- **文件路径**: `STOCK_DATABASE_README.md`
- **重要性**: ⭐⭐
- **读取时机**: 需要了解数据库使用方法时
- **用途**:
  - 了解数据库表结构
  - 了解CRUD操作
  - 了解使用示例

### 7. 工具类文档
- **文件路径**: 
  - `crawler/sina/market_prefix_helper.py`
  - `utils/akshare_data.py`
- **重要性**: ⭐⭐
- **读取时机**: 需要使用特定工具时
- **用途**:
  - 了解市场前缀规则
  - 了解Akshare接口

## 重要规则和约定

### 测试规则
1. **默认测试数量**: 50只股票
2. **测试模式**: 默认启用
3. **全量爬取**: 需要明确设置 `test_mode=False`

### 数据源优先级（历史数据）
1. 东方财富 - 稳定、快速
2. Baostock - 免费、专为A股设计
3. Yahoo Finance - 国际化、稳定
4. Akshare - 数据质量高、速度慢
5. ~~新浪财经~~ - 已移除（不稳定）

### 数据源优先级（实时数据）
1. 新浪 - 使用Playwright，数据准确
2. 腾讯 - 使用HTTP API，速度快
3. 东方财富 - 使用Playwright，数据准确

### 开发规范
1. **异步优先**: 使用async/await提高性能
2. **错误处理**: 完善的异常捕获和处理
3. **日志记录**: 详细的日志输出
4. **代码注释**: 清晰的代码说明

### 文件组织规范
- **爬虫文件**: `crawler/{source}/{name}_crawler.py`
- **工具文件**: `utils/{name}.py`
- **测试文件**: `test_{name}.py`
- **文档文件**: `{name}_README.md`

## 项目结构

```
stock_scraper/
├── crawler/                    # 爬虫目录
│   ├── multi_source_history_crawler.py  # 多线程历史数据爬虫
│   ├── eastmoney/              # 东方财富爬虫
│   ├── baostock/              # Baostock爬虫
│   ├── yahoo_finance/          # Yahoo Finance爬虫
│   ├── sina/                  # 新浪爬虫
│   └── tencent/              # 腾讯爬虫
├── utils/                     # 工具类
│   ├── stock_database.py       # 数据库工具类
│   └── akshare_data.py       # Akshare数据获取
├── PROJECT_CONFIG.md           # 项目配置文件
├── CRAWLER_README.md         # 爬虫文档
├── STOCK_DATABASE_README.md    # 数据库文档
└── CONTEXT_GUIDE.md          # 上下文指南（本文件）
```

## 常见任务参考

### 添加新数据源
1. 参考 `CRAWLER_README.md` 了解现有数据源
2. 参考 `crawler/baostock/baostock_history_crawler.py` 实现新爬虫
3. 更新 `crawler/multi_source_history_crawler.py` 添加新Worker
4. 更新 `CRAWLER_README.md` 添加文档
5. 更新 `PROJECT_CONFIG.md` 更新配置

### 修改测试规则
1. 修改 `PROJECT_CONFIG.md` 中的测试配置
2. 修改 `crawler/multi_source_history_crawler.py` 中的main函数
3. 确保测试模式默认启用

### 调试爬虫问题
1. 查看 `CRAWLER_README.md` 了解数据源特点
2. 查看对应爬虫文件的具体实现
3. 运行测试脚本验证功能
4. 查看日志输出定位问题

### 数据库操作
1. 查看 `STOCK_DATABASE_README.md` 了解表结构
2. 查看 `utils/stock_database.py` 了解接口
3. 使用StockDatabase类进行操作

## 注意事项

1. **测试模式**: 每次测试默认使用50只股票，避免全量测试耗时过长
2. **数据源选择**: 历史数据爬取不使用新浪（不稳定）
3. **并发控制**: 多线程爬虫有最大调用次数限制（5000次）
4. **错误处理**: 所有爬虫都有完善的错误处理和重试机制
5. **日志输出**: 详细的日志输出便于调试和监控

## 更新日志

### 2026-02-15
- 创建上下文指南
- 记录核心文档和读取规则
- 整理项目结构和常见任务参考
