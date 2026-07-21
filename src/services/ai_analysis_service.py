"""
AI豆包模型分析服务
使用豆包模型进行视频内容与封面分析
"""
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.models.ai_analysis import VideoAnalysisResult, AIAnalysisResult
from src.models.video import Video
from src.config import settings
from src.utils.database import get_db_session
from src.skills.ai_analysis_skills import COVER_ANALYSIS_SKILL, CONTENT_ANALYSIS_SKILL
from sqlalchemy import text


class DoubaoService:
    """豆包模型服务"""

    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, model: str = "doubao-seed-2-0-lite-260428"):
        self.api_key = api_key or settings.ARK_API_KEY
        self.model = model

    def _call_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用豆包API"""
        if not self.api_key:
            print("ARK_API_KEY not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": prompt,
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/responses",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ark API call failed: {e}")
            return None

    def analyze_cover(self, video: Video, cover_url: str) -> Optional[VideoAnalysisResult]:
        """分析视频封面"""
        prompt = self._build_cover_prompt(video, cover_url)
        response = self._call_api(prompt)
        if not response:
            return None
        return self._parse_cover_response(video.bvid, response)

    def analyze_content(self, video: Video) -> Optional[VideoAnalysisResult]:
        """分析视频内容"""
        prompt = self._build_content_prompt(video)
        response = self._call_api(prompt)
        if not response:
            return None
        return self._parse_content_response(video.bvid, response)

    def _build_cover_prompt(self, video: Video, cover_url: str) -> str:
        """构建封面分析提示词（7个维度）"""
        return COVER_ANALYSIS_SKILL.format(
            video_title=video.title,
            author=video.author,
            cover_url=cover_url,
        )

    def _build_content_prompt(self, video: Video) -> str:
        """构建内容分析提示词（4个维度）"""
        return CONTENT_ANALYSIS_SKILL.format(
            video_title=video.title,
            author=video.author,
            channel=video.channel,
            description=getattr(video, 'description', '') or '无',
        )

    def _parse_cover_response(self, bvid: str, response: Dict[str, Any]) -> Optional[VideoAnalysisResult]:
        """解析封面分析响应"""
        try:
            text = self._extract_output_text(response)
            return self._parse_to_video_result(bvid, "cover", text)
        except Exception as e:
            print(f"Failed to parse cover response: {e}")
            return None

    def _parse_content_response(self, bvid: str, response: Dict[str, Any]) -> Optional[VideoAnalysisResult]:
        """解析内容分析响应"""
        try:
            text = self._extract_output_text(response)
            return self._parse_to_video_result(bvid, "content", text)
        except Exception as e:
            print(f"Failed to parse content response: {e}")
            return None

    def _extract_output_text(self, response: Dict[str, Any]) -> str:
        """从API响应中提取output_text"""
        try:
            output = response.get("output", [])
            for item in output:
                if item.get("type") == "message":
                    content = item.get("content", [])
                    for c in content:
                        if c.get("type") == "output_text":
                            return c.get("text", "").strip()
            return ""
        except Exception:
            return ""

    def _parse_to_video_result(self, bvid: str, analysis_type: str, text: str) -> Optional[VideoAnalysisResult]:
        """将响应文本解析为VideoAnalysisResult"""
        try:
            # 尝试提取JSON
            json_text = text
            if "```json" in text:
                json_text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                json_text = text.split("```")[1].split("```")[0]

            data = json.loads(json_text)

            result = VideoAnalysisResult(
                bvid=bvid,
                analysis_type=analysis_type,
                raw_response=data,
            )

            if analysis_type == "cover":
                # 封面分析7维度
                result.cover_composition = data.get("cover_composition")
                result.cover_main_element = data.get("cover_main_element")
                result.cover_color_scheme = data.get("cover_color_scheme")
                result.cover_visual_style = data.get("cover_visual_style")
                result.cover_mood_atmosphere = data.get("cover_mood_atmosphere")
                result.cover_visual_highlights = data.get("cover_visual_highlights", [])
                result.cover_audience_expectation = data.get("cover_audience_expectation")
            else:
                # 内容分析4维度
                result.topic_summary = data.get("topic_summary")
                result.viral_logic_analysis = data.get("viral_logic_analysis")
                result.content_optimization_suggestions = data.get("content_optimization_suggestions")
                result.replicability_evaluation = data.get("replicability_evaluation")

            return result
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}, text: {text[:200]}")
            return None


class AIAnalysisService:
    """AI分析服务"""

    def __init__(self):
        self.doubao_service = DoubaoService()

    def analyze_video(
        self,
        video: Video,
        cover_url: Optional[str] = None,
        analysis_type: str = "both"
    ) -> Optional[AIAnalysisResult]:
        """
        对视频进行AI分析

        Args:
            video: 视频对象
            cover_url: 封面图片URL(用于封面分析)
            analysis_type: "cover", "content", "both"

        Returns:
            AI分析结果
        """
        result = AIAnalysisResult(bvid=video.bvid)

        if analysis_type in ("cover", "both"):
            if not cover_url:
                cover_url = getattr(video, 'cover_url', None)
            if cover_url:
                result.cover_analysis = self.doubao_service.analyze_cover(video, cover_url)

        if analysis_type in ("content", "both"):
            result.content_analysis = self.doubao_service.analyze_content(video)

        return result

    def cache_analysis(self, result: AIAnalysisResult) -> bool:
        """缓存分析结果到数据库（永久有效）"""
        try:
            with get_db_session() as session:
                # 缓存封面分析结果
                if result.cover_analysis:
                    session.execute(
                        text("""
                            INSERT INTO ai_cache (bvid, analysis_type, result_data)
                            VALUES (:bvid, :analysis_type, :result_data)
                            ON CONFLICT (bvid, analysis_type)
                            DO UPDATE SET
                                result_data = EXCLUDED.result_data,
                                cached_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "bvid": result.bvid,
                            "analysis_type": "cover_analysis",
                            "result_data": json.dumps(result.cover_analysis.to_dict()),
                        }
                    )

                # 缓存内容分析结果
                if result.content_analysis:
                    session.execute(
                        text("""
                            INSERT INTO ai_cache (bvid, analysis_type, result_data)
                            VALUES (:bvid, :analysis_type, :result_data)
                            ON CONFLICT (bvid, analysis_type)
                            DO UPDATE SET
                                result_data = EXCLUDED.result_data,
                                cached_at = CURRENT_TIMESTAMP
                        """),
                        {
                            "bvid": result.bvid,
                            "analysis_type": "content_analysis",
                            "result_data": json.dumps(result.content_analysis.to_dict()),
                        }
                    )
            return True
        except Exception as e:
            print(f"Failed to cache analysis: {e}")
            return False

    def get_cached_analysis(self, bvid: str) -> Optional[AIAnalysisResult]:
        """获取缓存的分析结果（永久有效）"""
        try:
            with get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT bvid, analysis_type, result_data, cached_at
                        FROM ai_cache
                        WHERE bvid = :bvid
                    """),
                    {"bvid": bvid}
                ).fetchall()

                if not results:
                    return None

                ai_result = AIAnalysisResult(bvid=bvid)

                for row in results:
                    _, analysis_type, result_data, _ = row
                    if result_data:
                        # JSONB columns are automatically parsed by SQLAlchemy
                        # so result_data might already be a dict
                        if isinstance(result_data, dict):
                            data = result_data
                        else:
                            data = json.loads(result_data)
                        video_result = VideoAnalysisResult(
                            bvid=bvid,
                            analysis_type=analysis_type.replace("_analysis", ""),
                            raw_response=data,
                        )
                        if analysis_type == "cover_analysis":
                            # 封面分析7维度
                            video_result.cover_composition = data.get("cover_composition")
                            video_result.cover_main_element = data.get("cover_main_element")
                            video_result.cover_color_scheme = data.get("cover_color_scheme")
                            video_result.cover_visual_style = data.get("cover_visual_style")
                            video_result.cover_mood_atmosphere = data.get("cover_mood_atmosphere")
                            video_result.cover_visual_highlights = data.get("cover_visual_highlights", [])
                            video_result.cover_audience_expectation = data.get("cover_audience_expectation")
                            ai_result.cover_analysis = video_result
                        elif analysis_type == "content_analysis":
                            # 内容分析4维度
                            video_result.topic_summary = data.get("topic_summary")
                            video_result.viral_logic_analysis = data.get("viral_logic_analysis")
                            video_result.content_optimization_suggestions = data.get("content_optimization_suggestions")
                            video_result.replicability_evaluation = data.get("replicability_evaluation")
                            ai_result.content_analysis = video_result

                return ai_result
        except Exception as e:
            print(f"Failed to get cached analysis: {e}")
            return None

    def batch_analyze(
        self,
        videos: List[Video],
        analysis_type: str = "both"
    ) -> List[AIAnalysisResult]:
        """批量分析视频"""
        results = []
        for video in videos:
            # 先尝试从缓存获取
            cached = self.get_cached_analysis(video.bvid)
            if cached:
                results.append(cached)
                continue

            # 执行新的分析
            cover_url = getattr(video, 'cover_url', None)
            analysis = self.analyze_video(video, cover_url, analysis_type)
            if analysis:
                # 缓存结果
                self.cache_analysis(analysis)
                results.append(analysis)

        return results


# 全局单例
_ai_analysis_service: Optional[AIAnalysisService] = None


def get_ai_analysis_service() -> AIAnalysisService:
    """获取AI分析服务单例"""
    global _ai_analysis_service
    if _ai_analysis_service is None:
        _ai_analysis_service = AIAnalysisService()
    return _ai_analysis_service
