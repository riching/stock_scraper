# StockDatabase 使用说明

## 概述

`StockDatabase` 是一个线程安全的股票数据库操作工具类，支持增删改查等常用操作。

## 特性

- ✅ **线程安全**：每个线程独立的数据库连接
- ✅ **事务支持**：自动事务管理，支持回滚
- ✅ **WAL模式**：启用Write-Ahead Logging，提高并发性能
- ✅ **上下文管理**：支持 `with` 语句，自动关闭连接
- ✅ **完整CRUD**：支持增删改查所有操作

## 基本使用

### 1. 初始化

```python
from utils.stock_database import StockDatabase

# 方式1：普通使用
db = StockDatabase("/path/to/database.db")

# 方式2：使用上下文管理器（推荐）
with StockDatabase("/path/to/database.db") as db:
    # 数据库操作
    pass
# 自动关闭连接
```

### 2. 插入数据

#### 插入单条数据

```python
data = {
    "code": "000001",
    "date": "2026-02-15",
    "open": 10.0,
    "high": 11.0,
    "low": 9.5,
    "close": 10.5,
    "volume": 1000000,
    "name": "平安银行"
}

success = db.insert_stock_data(data)
if success:
    print("插入成功")
```

#### 批量插入数据

```python
data_list = [
    {
        "code": "000001",
        "date": "2026-02-15",
        "open": 10.0,
        "high": 11.0,
        "low": 9.5,
        "close": 10.5,
        "volume": 1000000,
        "name": "平安银行"
    },
    {
        "code": "600519",
        "date": "2026-02-15",
        "open": 1480.0,
        "high": 1490.0,
        "low": 1470.0,
        "close": 1485.0,
        "volume": 500000,
        "name": "贵州茅台"
    }
]

count = db.insert_stock_data_batch(data_list)
print(f"插入了 {count} 条数据")
```

### 3. 查询数据

#### 查询单只股票

```python
# 查询指定股票的所有数据
data = db.select_stock_data(code="000001")
print(f"查询到 {len(data)} 条数据")

# 查询指定股票在指定日期的数据
data = db.select_stock_data(code="000001", date="2026-02-15")
if data:
    print(f"收盘价: {data[0]['close']}")

# 查询指定股票在日期范围内的数据
data = db.select_stock_data(
    code="000001",
    start_date="2026-02-01",
    end_date="2026-02-15",
    limit=10
)
```

#### 根据代码列表查询

```python
codes = ["000001", "600519", "000858"]
data = db.select_stock_data_by_codes(codes, date="2026-02-15")
for item in data:
    print(f"{item['code']}: {item['close']}")
```

#### 获取所有股票代码

```python
codes = db.get_all_stock_codes()
print(f"数据库中共有 {len(codes)} 只股票")
```

#### 获取股票日期列表

```python
# 获取指定股票的所有日期
dates = db.get_stock_dates(code="000001")
print(f"000001 有 {len(dates)} 天的数据")

# 获取数据库中所有日期
all_dates = db.get_stock_dates()
print(f"数据库中共有 {len(all_dates)} 个日期")
```

### 4. 更新数据

```python
# 更新指定股票在指定日期的数据
update_data = {
    "close": 10.6,
    "volume": 1500000
}

success = db.update_stock_data("000001", "2026-02-15", update_data)
if success:
    print("更新成功")
```

### 5. 删除数据

```python
# 删除指定股票在指定日期的数据
count = db.delete_stock_data(code="000001", date="2026-02-15")
print(f"删除了 {count} 条数据")

# 删除指定股票的所有数据
count = db.delete_stock_data(code="000001")

# 删除指定日期的所有数据
count = db.delete_stock_data(date="2026-02-15")

# 清理指定日期的数据（推荐）
count = db.clean_date_data("2026-02-15")
print(f"清理了 {count} 条数据")
```

### 6. 检查数据

```python
# 检查数据是否存在
exists = db.exists_stock_data("000001", "2026-02-15")
if exists:
    print("数据已存在")

# 统计数据数量
count = db.count_stock_data(code="000001")
print(f"000001 有 {count} 条数据")

count = db.count_stock_data(date="2026-02-15")
print(f"2026-02-15 有 {count} 条数据")
```

### 7. 数据状态管理

```python
# 插入或更新数据状态
db.insert_or_update_data_status(
    code="000001",
    last_updated="2026-02-15T10:00:00",
    record_count=100,
    status="success"
)

# 获取数据状态
status = db.get_data_status(code="000001")
if status:
    print(f"最后更新: {status[0]['last_updated']}")
    print(f"状态: {status[0]['status']}")

# 获取所有数据状态
all_status = db.get_data_status()
for item in all_status:
    print(f"{item['code']}: {item['status']}")
```

### 8. 高级操作

#### 使用事务

```python
# 自动事务管理
with db.transaction() as conn:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO merged_stocks ...")
    cursor.execute("UPDATE merged_stocks ...")
    # 自动提交

# 异常时自动回滚
try:
    with db.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO merged_stocks ...")
        # 发生异常
        raise Exception("测试异常")
except Exception as e:
    print(f"事务已回滚: {e}")
```

#### 执行自定义SQL

```python
# 查询
result = db.execute_sql(
    "SELECT code, date, close FROM merged_stocks WHERE code = ? LIMIT 1",
    ("000001",)
)
if result:
    print(result[0])

# 更新
result = db.execute_sql(
    "UPDATE merged_stocks SET close = ? WHERE code = ? AND date = ?",
    (10.6, "000001", "2026-02-15")
)
print(f"影响了 {result[0]['affected_rows']} 行")

# 删除
result = db.execute_sql(
    "DELETE FROM merged_stocks WHERE code = ? AND date = ?",
    ("000001", "2026-02-15")
)
```

#### 获取表结构

```python
table_info = db.get_table_info("merged_stocks")
for field in table_info:
    print(f"{field['name']}: {field['type']} (主键: {field['pk']})")
```

#### 备份数据库

```python
success = db.backup_database("/path/to/backup.db")
if success:
    print("备份成功")
```

## 线程安全使用

### 多线程环境

```python
import threading

def worker(db_path, stock_code):
    with StockDatabase(db_path) as db:
        data = db.select_stock_data(code=stock_code)
        print(f"{stock_code}: {len(data)} 条数据")

# 创建多个线程
threads = []
for code in ["000001", "600519", "000858"]:
    t = threading.Thread(target=worker, args=("/path/to/database.db", code))
    t.start()
    threads.append(t)

# 等待所有线程完成
for t in threads:
    t.join()
```

### 消费者线程示例

```python
import threading
from queue import Queue

def consumer_worker(queue, db_path):
    with StockDatabase(db_path) as db:
        while True:
            stock_code = queue.get()
            if stock_code is None:  # 终止信号
                break
            
            # 爬取数据
            data = crawl_stock(stock_code)
            
            # 保存到数据库
            if data:
                db.insert_stock_data(data)
            
            queue.task_done()

# 创建队列和消费者线程
queue = Queue()
threads = []
for i in range(3):
    t = threading.Thread(target=consumer_worker, args=(queue, "/path/to/database.db"))
    t.start()
    threads.append(t)

# 添加任务
for code in stock_codes:
    queue.put(code)

# 添加终止信号
for _ in range(3):
    queue.put(None)

# 等待所有线程完成
for t in threads:
    t.join()
```

## 数据字段说明

### merged_stocks 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| created_at | DATETIME | 创建时间 |
| code | TEXT | 股票代码 |
| date | TEXT | 日期 |
| open | REAL | 开盘价 |
| high | REAL | 最高价 |
| low | REAL | 最低价 |
| close | REAL | 收盘价 |
| volume | INTEGER | 成交量 |
| amount | REAL | 成交额 |
| outstanding_share | REAL | 流通股本 |
| turnover | REAL | 换手率 |
| name | TEXT | 股票名称 |
| ma5 | REAL | 5日均线 |
| ma10 | REAL | 10日均线 |
| ma20 | REAL | 20日均线 |
| rsi6 | REAL | RSI(6) |
| rsi14 | REAL | RSI(14) |
| pct_change | REAL | 涨跌幅 |

### data_status 表

| 字段 | 类型 | 说明 |
|------|------|------|
| code | TEXT | 股票代码 |
| last_updated | TEXT | 最后更新时间 |
| record_count | INTEGER | 记录数量 |
| status | TEXT | 状态 |

## 注意事项

1. **线程安全**：每个线程会创建独立的数据库连接，使用完毕后自动关闭
2. **事务管理**：推荐使用 `with db.transaction()` 进行事务管理
3. **WAL模式**：已启用WAL模式，提高并发性能
4. **异常处理**：所有方法都有异常处理，失败时返回False或空列表
5. **上下文管理**：推荐使用 `with` 语句，确保连接正确关闭

## 性能优化建议

1. **批量操作**：大量数据插入时使用 `insert_stock_data_batch`
2. **索引优化**：确保 code 和 date 字段有索引
3. **连接复用**：在同一个线程中复用数据库连接
4. **事务批处理**：将多个操作放在一个事务中

## 示例：完整爬虫流程

```python
import threading
from queue import Queue
from utils.stock_database import StockDatabase

def crawl_worker(queue, db_path, max_calls=5000):
    """爬虫工作线程"""
    with StockDatabase(db_path) as db:
        call_count = 0
        while call_count < max_calls:
            stock_code = queue.get()
            if stock_code is None:
                break
            
            # 爬取数据
            data = crawl_stock(stock_code)
            
            # 验证数据
            if validate_data(data):
                # 保存到数据库
                if db.insert_stock_data(data):
                    print(f"✅ {stock_code} 保存成功")
                else:
                    print(f"❌ {stock_code} 保存失败，重新放回队列")
                    queue.put(stock_code)
            else:
                print(f"⚠️  {stock_code} 数据无效，重新放回队列")
                queue.put(stock_code)
            
            call_count += 1
            queue.task_done()

# 主程序
def main():
    db_path = "/path/to/database.db"
    stock_codes = get_all_stock_codes()
    
    # 创建队列
    queue = Queue()
    
    # 添加股票代码
    for code in stock_codes:
        queue.put(code)
    
    # 启动消费者线程
    threads = []
    for i in range(3):
        t = threading.Thread(target=crawl_worker, args=(queue, db_path))
        t.start()
        threads.append(t)
    
    # 等待所有任务完成
    queue.join()
    
    # 发送终止信号
    for _ in range(3):
        queue.put(None)
    
    # 等待所有线程结束
    for t in threads:
        t.join()
    
    print("✅ 所有任务完成")

if __name__ == "__main__":
    main()
```
