#!/usr/bin/env python3
"""市场前缀助手模块"""


def get_market_prefix(stock_code: str) -> str:
    """
    根据股票代码获取正确的市场前缀

    股票代码规则：
    - 沪市A股: 600, 601, 603, 605, 688 → sh
    - 深市A股: 000, 001, 002, 003, 300, 301 → sz
    - 北交所: 83, 87, 88, 920 → bj

    Args:
        stock_code (str): 6位股票代码

    Returns:
        str: 市场前缀 ('sh', 'sz', 'bj')
    """
    if not stock_code or len(stock_code) != 6:
        raise ValueError(f"Invalid stock code: {stock_code}")

    # 北交所股票 (83, 87, 88, 920开头)
    if stock_code.startswith(("83", "87", "88")) or stock_code.startswith("920"):
        return "bj"

    # 沪市股票 (6开头)
    elif stock_code.startswith(("600", "601", "603", "605", "688")):
        return "sh"

    # 深市股票 (0, 2, 3开头)
    elif stock_code.startswith(("000", "001", "002", "003", "300", "301")):
        return "sz"

    # 默认处理：6开头为沪市，其他为深市
    elif stock_code.startswith("6"):
        return "sh"
    else:
        return "sz"


def test_market_prefix():
    """测试市场前缀函数"""
    test_cases = [
        ("600000", "sh"),  # 浦发银行
        ("000001", "sz"),  # 平安银行
        ("300059", "sz"),  # 东方财富
        ("688001", "sh"),  # 华兴源创
        ("920000", "bj"),  # 安徽凤凰 (北交所)
        ("830796", "bj"),  # 北交所示例
    ]

    for code, expected in test_cases:
        result = get_market_prefix(code)
        status = "✓" if result == expected else "✗"
        print(f"{status} {code} → {result} (expected: {expected})")


if __name__ == "__main__":
    test_market_prefix()
