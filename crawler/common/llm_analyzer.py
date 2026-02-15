#!/usr/bin/env python3
"""大模型分析器"""

import json
import os
from typing import Dict, Any
import dashscope

dashscope.api_key = os.getenv("QWEN_API_KEY")


class LLMAnalyzer:
    """大模型分析器"""

    def __init__(self):
        self.model_name = "qwen3-max"

    def analyze_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        使用大模型分析内容

        Args:
            content: 原始内容
            content_type: 内容类型 ('news', 'announcement', 'comment', 'report')

        Returns:
            {
                'is_valid': bool,  # 是否有效
                'sentiment_score': float,  # 情感分数 (0-10)
                'summary': str,  # 内容摘要
                'key_points': list,  # 关键要点
                'reasoning': str  # 评分理由
            }
        """
        # 构建系统提示词
        system_prompt = f"你是一个专业的中文文本分析助手，专门分析金融领域的内容。请对以下{content_type}内容进行详细分析。"
        
        # 构建用户提示词
        user_prompt = f"""分析以下{content_type}内容：\n\n{content}\n\n请按照以下JSON格式返回分析结果：\n{{\n    \"is_valid\": true/false,  # 内容是否有效\n    \"sentiment_score\": 数值,  # 情感分数 (0-10, 0为极度负面，10为极度正面)\n    \"summary\": \"内容摘要\",\n    \"key_points\": [\"关键点1\", \"关键点2\", \"关键点3\"],  # 最多提取3个关键点\n    \"reasoning\": \"评分理由\"\n}}\n\n请确保返回有效的JSON格式，不包含任何其他解释文字。"""        
        try:
            # 调用千问API
            response = dashscope.Generation.call(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                result_format="message"
            )
            
            if response.status_code == 200:
                # 解析API响应
                response_content = response.output.choices[0].message.content
                # 尝试解析JSON响应
                try:
                    # 清理可能的非JSON内容
                    json_str = response_content.strip()
                    if json_str.startswith('```json'):
                        json_str = json_str[7:json_str.rfind('```')].strip()
                    elif json_str.startswith('```'):
                        json_str = json_str[3:json_str.rfind('```')].strip()
                    
                    analysis_result = json.loads(json_str)
                    
                    # 确保情感分数在0-10范围内
                    if "sentiment_score" in analysis_result:
                        analysis_result["sentiment_score"] = max(0.0, min(10.0, float(analysis_result["sentiment_score"])))
                    
                    return analysis_result
                except json.JSONDecodeError:
                    # 如果无法解析JSON，则返回默认值
                    return {
                        "is_valid": True,
                        "sentiment_score": 5.0,
                        "summary": content[:100] + "..." if len(content) > 100 else content,
                        "key_points": [],
                        "reasoning": "API响应无法解析为JSON"
                    }
            else:
                # API调用失败时返回默认值
                return {
                    "is_valid": True,
                    "sentiment_score": 5.0,
                    "summary": content[:100] + "..." if len(content) > 100 else content,
                    "key_points": [],
                    "reasoning": f"API调用失败: {response.code} - {response.message}"
                }
        except Exception as e:
            # 发生异常时返回默认值
            return {
                "is_valid": True,
                "sentiment_score": 5.0,
                "summary": content[:100] + "..." if len(content) > 100 else content,
                "key_points": [],
                "reasoning": f"API调用异常: {str(e)}"
            }


    def analyze_stock_comprehensive(
        self,
        stock_code: str,
        news_data: list,
        announcement_data: list,
        comment_data: list,
        report_data: list,
    ) -> Dict[str, Any]:
        """
        综合分析股票的多维度信息
        """
        # 分析各类数据
        news_scores = []
        for item in news_data:
            if item.get("is_valid", False):
                news_scores.append(item.get("sentiment_score", 5.0))

        announcement_scores = []
        for item in announcement_data:
            if item.get("is_valid", False):
                announcement_scores.append(item.get("sentiment_score", 5.0))

        comment_scores = []
        for item in comment_data:
            if item.get("is_valid", False):
                comment_scores.append(item.get("sentiment_score", 5.0))

        report_scores = []
        for item in report_data:
            if item.get("is_valid", False):
                report_scores.append(item.get("sentiment_score", 5.0))

        # 计算平均分
        news_score = sum(news_scores) / len(news_scores) if news_scores else None
        announcement_score = (
            sum(announcement_scores) / len(announcement_scores)
            if announcement_scores
            else None
        )
        comment_score = (
            sum(comment_scores) / len(comment_scores) if comment_scores else None
        )
        report_score = (
            sum(report_scores) / len(report_scores) if report_scores else None
        )

        # 综合评分
        from utils import calculate_overall_sentiment_score

        overall_score = calculate_overall_sentiment_score(
            news_score, announcement_score, comment_score, report_score
        )

        # 生成综合摘要
        total_items = (
            len(news_data)
            + len(announcement_data)
            + len(comment_data)
            + len(report_data)
        )
        valid_items = len(
            [
                x
                for x in news_data + announcement_data + comment_data + report_data
                if x.get("is_valid", False)
            ]
        )

        summary = f"分析了{total_items}条信息，其中{valid_items}条有效。综合评分为{overall_score}/10。"

        return {
            "stock_code": stock_code,
            "news_score": news_score,
            "announcement_score": announcement_score,
            "comment_score": comment_score,
            "report_score": report_score,
            "overall_score": overall_score,
            "analysis_summary": summary,
            "total_items": total_items,
            "valid_items": valid_items,
        }
