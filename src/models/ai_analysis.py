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

    # ========== 封面分析 (新模板) ==========
    # 构图
    composition_rule: Optional[str] = None  # 构图法则
    composition_desc: Optional[str] = None  # 构图描述
    # 元素
    elements_subjects: Optional[str] = None  # 主体/人物
    elements_text: Optional[str] = None  # 文字内容
    elements_color_palette: Optional[str] = None  # 主色调
    elements_lighting: Optional[str] = None  # 光照风格
    # 风格
    style_overall: Optional[str] = None  # 整体视觉风格
    style_mood: Optional[str] = None  # 情绪/氛围
    # 吸引力
    appeal_attraction: Optional[str] = None  # 最吸引眼球的亮点
    appeal_hook: Optional[str] = None  # 用户预期内容

    # ========== 内容分析 (新模板) ==========
    short_topic: Optional[str] = None  # 核心选题（一句话，不超过20字）
    summary_insight: Optional[str] = None  # 爆款分析报告
    optimization_suggestions: Optional[str] = None  # 优化建议

    # 原始响应
    raw_response: Optional[Dict[str, Any]] = None

    # 元数据
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "bvid": self.bvid,
            "analysis_type": self.analysis_type,
            # 封面分析 - 新结构
            "composition": {
                "rule": self.composition_rule,
                "description": self.composition_desc,
            },
            "elements": {
                "subjects": self.elements_subjects,
                "text": self.elements_text,
                "color_palette": self.elements_color_palette,
                "lighting": self.elements_lighting,
            },
            "style": {
                "overall": self.style_overall,
                "mood": self.style_mood,
            },
            "appeal": {
                "attraction": self.appeal_attraction,
                "hook": self.appeal_hook,
            },
            # 内容分析 - 新结构（使用camelCase匹配API返回格式）
            "shortTopic": self.short_topic,
            "summaryInsight": self.summary_insight,
            "optimizationSuggestions": self.optimization_suggestions,
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