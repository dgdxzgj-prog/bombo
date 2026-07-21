"""
AI分析结果数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class VideoAnalysisResult:
    """视频AI分析结果"""
    bvid: str
    analysis_type: str  # "cover", "content"

    # ========== 封面分析 (7个维度) ==========
    # 第一维度：构图手法
    cover_composition: Optional[str] = None  # 中心构图法、三分法、对称构图、对角线构图等
    # 第二维度：主体元素
    cover_main_element: Optional[str] = None  # 单人半身女性精致妆容画面、大号文字标题、产品实拍图等
    # 第三维度：色彩方案
    cover_color_scheme: Optional[str] = None  # 粉橙为主暖色调、高饱和色彩对比、低饱和温柔色系等
    # 第四维度：视觉风格
    cover_visual_style: Optional[str] = None  # 精致高级感、清新自然风、炫酷科技感、温馨治愈风格等
    # 第五维度：情绪氛围
    cover_mood_atmosphere: Optional[str] = None  # 期待、好奇、惊喜、温暖、紧张等
    # 第六维度：视觉亮点
    cover_visual_highlights: List[str] = field(default_factory=list)  # 博主直视镜头、超大号标题文字、强对比撞色设计等
    # 第七维度：观众预期
    cover_audience_expectation: Optional[str] = None  # 妆容教学、产品测评、情感故事分享等

    # ========== 内容分析 (4个维度) ==========
    # 第一维度：选题总结
    topic_summary: Optional[str] = None  # 一句话概括，不超过20个字
    # 第二维度：爆款逻辑分析
    viral_logic_analysis: Optional[str] = None  # 深度拆解，不少于250字
    # 第三维度：优化建议
    content_optimization_suggestions: Optional[str] = None  # 可落地执行的内容改进方案
    # 第四维度：可复制性评估
    replicability_evaluation: Optional[str] = None  # 高/中/低 + 简短说明

    # 原始响应
    raw_response: Optional[Dict[str, Any]] = None

    # 元数据
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "bvid": self.bvid,
            "analysis_type": self.analysis_type,
            # 封面分析7维度
            "cover_composition": self.cover_composition,
            "cover_main_element": self.cover_main_element,
            "cover_color_scheme": self.cover_color_scheme,
            "cover_visual_style": self.cover_visual_style,
            "cover_mood_atmosphere": self.cover_mood_atmosphere,
            "cover_visual_highlights": self.cover_visual_highlights,
            "cover_audience_expectation": self.cover_audience_expectation,
            # 内容分析4维度
            "topic_summary": self.topic_summary,
            "viral_logic_analysis": self.viral_logic_analysis,
            "content_optimization_suggestions": self.content_optimization_suggestions,
            "replicability_evaluation": self.replicability_evaluation,
            # 元数据
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    bvid: str

    # 分析结果
    cover_analysis: Optional[VideoAnalysisResult] = None
    content_analysis: Optional[VideoAnalysisResult] = None

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
