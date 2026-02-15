#!/usr/bin/env python3
"""情感评分计算模块"""

from typing import Optional


def calculate_overall_sentiment_score(
    news_score: Optional[float] = None,
    announcement_score: Optional[float] = None,
    comment_score: Optional[float] = None,
    report_score: Optional[float] = None,
) -> float:
    """计算综合情感评分"""
    scores = []
    weights = []

    if news_score is not None and isinstance(news_score, (int, float)):
        scores.append(float(news_score))
        weights.append(0.3)  # 新闻权重30%

    if announcement_score is not None and isinstance(announcement_score, (int, float)):
        scores.append(float(announcement_score))
        weights.append(0.25)  # 公告权重25%

    if comment_score is not None and isinstance(comment_score, (int, float)):
        scores.append(float(comment_score))
        weights.append(0.2)  # 评论权重20%

    if report_score is not None and isinstance(report_score, (int, float)):
        scores.append(float(report_score))
        weights.append(0.25)  # 报告权重25%

    if not scores:
        return 5.0  # 默认中性分数

    # 归一化权重
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # 加权平均
    overall_score = sum(
        score * weight for score, weight in zip(scores, normalized_weights)
    )
    return round(overall_score, 2)
