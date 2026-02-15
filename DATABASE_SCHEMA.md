# 数据库Schema文档

本文档详细描述了股票数据爬虫系统的数据库结构。

## 📊 数据库概览

数据库使用SQLite存储，包含以下主要表：
- 股票基础信息
- 股票价格数据
- 新闻和公告
- 评论和分析
- 情感评分
- 爬虫状态

## 📋 表结构详解

### 1. stock_list - 股票列表

存储所有A股股票的基础信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| code | TEXT | 股票代码 | PRIMARY KEY |
| name | TEXT | 股票名称 | - |
| updated_at | TIMESTAMP | 更新时间 | - |

**示例数据：**
```sql
INSERT INTO stock_list VALUES ('000001', '平安银行', '2026-02-15 10:00:00');
```

---

### 2. merged_stocks - 合并股票数据

存储所有数据源的股票价格数据，包含技术指标。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY AUTOINCREMENT |
| created_at | DATETIME | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| code | TEXT | 股票代码 | - |
| date | TEXT | 日期 | - |
| open | REAL | 开盘价 | - |
| high | REAL | 最高价 | - |
| low | REAL | 最低价 | - |
| close | REAL | 收盘价 | - |
| volume | INTEGER | 成交量 | - |
| amount | REAL | 成交额 | - |
| outstanding_share | REAL | 流通股本 | - |
| turnover | REAL | 换手率 | - |
| name | TEXT | 股票名称 | - |
| ma5 | REAL | 5日均线 | - |
| ma10 | REAL | 10日均线 | - |
| ma20 | REAL | 20日均线 | - |
| rsi6 | REAL | 6日RSI | - |
| rsi14 | REAL | 14日RSI | - |
| pct_change | REAL | 涨跌幅 | - |

**索引：**
```sql
CREATE INDEX idx_merged_stocks_code_date ON merged_stocks (code, date);
CREATE INDEX idx_merged_stocks_id ON merged_stocks (id);
CREATE INDEX idx_merged_stocks_date ON merged_stocks (date);
```

**示例数据：**
```sql
INSERT INTO merged_stocks (code, date, open, high, low, close, volume) 
VALUES ('000001', '2026-02-13', 10.85, 10.95, 10.80, 10.91, 12345678);
```

---

### 3. data_status - 数据状态

跟踪每只股票的数据更新状态。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| code | TEXT | 股票代码 | PRIMARY KEY |
| last_updated | TIMESTAMP | 最后更新时间 | - |
| record_count | INTEGER | 记录数量 | - |
| status | TEXT | 状态 | - |

**示例数据：**
```sql
INSERT INTO data_status VALUES ('000001', '2026-02-15 10:00:00', 1000, 'success');
```

---

### 4. stock_news - 股票新闻

存储爬取的股票新闻数据。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| code | TEXT | 股票代码 | NOT NULL |
| title | TEXT | 新闻标题 | NOT NULL |
| content | TEXT | 新闻内容 | NOT NULL |
| source | TEXT | 数据源 | NOT NULL |
| publish_date | TEXT | 发布日期 | NOT NULL |
| url | TEXT | 新闻链接 | NOT NULL |
| fingerprint | TEXT | 指纹（去重） | UNIQUE |
| created_at | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| sentiment_score | REAL | 情感评分 | - |
| is_valid | BOOLEAN | 是否有效 | DEFAULT 1 |
| llm_analysis | TEXT | LLM分析结果 | - |

**索引：**
```sql
CREATE INDEX idx_news_code_date ON stock_news (code, publish_date);
CREATE INDEX idx_news_fingerprint ON stock_news (fingerprint);
```

---

### 5. stock_announcements - 股票公告

存储上市公司公告信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| code | TEXT | 股票代码 | NOT NULL |
| title | TEXT | 公告标题 | NOT NULL |
| content | TEXT | 公告内容 | NOT NULL |
| announcement_type | TEXT | 公告类型 | - |
| publish_date | TEXT | 发布日期 | NOT NULL |
| url | TEXT | 公告链接 | NOT NULL |
| fingerprint | TEXT | 指纹（去重） | UNIQUE |
| created_at | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| sentiment_score | REAL | 情感评分 | - |
| is_valid | BOOLEAN | 是否有效 | DEFAULT 1 |
| llm_analysis | TEXT | LLM分析结果 | - |

**索引：**
```sql
CREATE INDEX idx_announcements_code_date ON stock_announcements (code, publish_date);
CREATE INDEX idx_announcements_fingerprint ON stock_announcements (fingerprint);
```

---

### 6. stock_comments - 股票评论

存储用户评论数据。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| code | TEXT | 股票代码 | NOT NULL |
| content | TEXT | 评论内容 | NOT NULL |
| author | TEXT | 作者 | - |
| platform | TEXT | 平台 | NOT NULL |
| publish_date | TEXT | 发布日期 | NOT NULL |
| url | TEXT | 评论链接 | - |
| likes | INTEGER | 点赞数 | DEFAULT 0 |
| fingerprint | TEXT | 指纹（去重） | UNIQUE |
| created_at | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| sentiment_score | REAL | 情感评分 | - |
| is_valid | BOOLEAN | 是否有效 | DEFAULT 1 |
| llm_analysis | TEXT | LLM分析结果 | - |

**索引：**
```sql
CREATE INDEX idx_comments_code_date ON stock_comments (code, publish_date);
CREATE INDEX idx_comments_fingerprint ON stock_comments (fingerprint);
```

---

### 7. analyst_reports - 分析师报告

存储券商分析师报告。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| code | TEXT | 股票代码 | NOT NULL |
| title | TEXT | 报告标题 | NOT NULL |
| summary | TEXT | 报告摘要 | - |
| broker | TEXT | 券商名称 | - |
| analyst | TEXT | 分析师姓名 | - |
| rating | TEXT | 评级 | - |
| target_price | REAL | 目标价 | - |
| publish_date | TEXT | 发布日期 | NOT NULL |
| url | TEXT | 报告链接 | NOT NULL |
| fingerprint | TEXT | 指纹（去重） | UNIQUE |
| created_at | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |
| sentiment_score | REAL | 情感评分 | - |
| is_valid | BOOLEAN | 是否有效 | DEFAULT 1 |
| llm_analysis | TEXT | LLM分析结果 | - |

**索引：**
```sql
CREATE INDEX idx_reports_code_date ON analyst_reports (code, publish_date);
CREATE INDEX idx_reports_fingerprint ON analyst_reports (fingerprint);
```

---

### 8. stock_sentiment_scores - 情感评分

存储综合情感评分数据。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| code | TEXT | 股票代码 | NOT NULL |
| date | TEXT | 日期 | NOT NULL |
| news_score | REAL | 新闻情感评分 | - |
| announcement_score | REAL | 公告情感评分 | - |
| comment_score | REAL | 评论情感评分 | - |
| analyst_score | REAL | 分析师评分 | - |
| overall_score | REAL | 综合评分 | - |
| analysis_summary | TEXT | 分析摘要 | - |
| created_at | TIMESTAMP | 创建时间 | DEFAULT CURRENT_TIMESTAMP |

**索引：**
```sql
CREATE INDEX idx_scores_code_date ON stock_sentiment_scores (code, date);
```

**唯一约束：**
```sql
UNIQUE(code, date)
```

---

### 9. crawl_status - 爬虫状态

跟踪爬虫的运行状态和调度信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PRIMARY KEY |
| code | TEXT | 股票代码 | NOT NULL |
| content_type | TEXT | 内容类型 | NOT NULL |
| last_crawl_time | TIMESTAMP | 最后爬取时间 | - |
| last_content_time | TIMESTAMP | 最后内容时间 | - |
| total_count | INTEGER | 总数量 | DEFAULT 0 |
| success_rate | REAL | 成功率 | DEFAULT 1.0 |
| next_scheduled_time | TIMESTAMP | 下次调度时间 | - |
| status | TEXT | 状态 | DEFAULT 'active' |

**索引：**
```sql
CREATE INDEX idx_crawl_status_code_type ON crawl_status (code, content_type);
```

**唯一约束：**
```sql
UNIQUE(code, content_type)
```

---

### 10. stock_classifications - 股票分类

存储股票的行业分类信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| 股票代码 | INTEGER | 股票代码 | - |
| 计入日期 | TIMESTAMP | 计入日期 | - |
| 行业代码 | INTEGER | 行业代码 | - |
| 更新日期 | TIMESTAMP | 更新日期 | - |
| 一级行业名称 | TEXT | 一级行业 | - |
| 二级行业名称 | TEXT | 二级行业 | - |
| 三级行业名称 | TEXT | 三级行业 | - |

**索引：**
```sql
CREATE INDEX idx_stock_classifications_industry ON stock_classifications ("一级行业名称");
CREATE INDEX idx_stock_classifications_code ON stock_classifications ("股票代码");
```

---

## 🔍 常用查询示例

### 查询指定股票的最新数据

```sql
SELECT * FROM merged_stocks 
WHERE code = '000001' 
ORDER BY date DESC 
LIMIT 10;
```

### 查询指定日期的所有股票数据

```sql
SELECT code, name, close, volume 
FROM merged_stocks 
WHERE date = '2026-02-13';
```

### 查询股票新闻

```sql
SELECT * FROM stock_news 
WHERE code = '000001' 
ORDER BY publish_date DESC 
LIMIT 20;
```

### 查询情感评分

```sql
SELECT * FROM stock_sentiment_scores 
WHERE code = '000001' 
ORDER BY date DESC 
LIMIT 30;
```

### 查询行业分类

```sql
SELECT * FROM stock_classifications 
WHERE "一级行业名称" = '银行';
```

---

## 📊 数据统计查询

### 统计股票数量

```sql
SELECT COUNT(*) FROM stock_list;
```

### 统计数据覆盖率

```sql
SELECT 
    COUNT(DISTINCT code) as total_stocks,
    COUNT(DISTINCT date) as total_dates,
    COUNT(*) as total_records
FROM merged_stocks;
```

### 统计各数据源的新闻数量

```sql
SELECT 
    source,
    COUNT(*) as count
FROM stock_news
GROUP BY source;
```

---

## 🛠️ 维护建议

1. **定期清理过期数据**：删除超过一定期限的旧数据
2. **优化索引**：定期运行 `VACUUM` 和 `ANALYZE`
3. **备份策略**：定期备份数据库文件
4. **监控性能**：关注查询性能，必要时添加索引

---

## 📝 注意事项

1. 所有时间字段使用 `TIMESTAMP` 类型
2. 指纹字段用于数据去重，确保唯一性
3. 情感评分范围为 -1.0 到 1.0
4. 状态字段使用标准状态码
5. 索引设计考虑了常用查询场景

---

**最后更新**：2026-02-15
