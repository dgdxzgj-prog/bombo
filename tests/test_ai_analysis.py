"""
AI豆包分析单元测试
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.models.video import Video, VideoStatus
from src.models.ai_analysis import VideoAnalysisResult, AIAnalysisResult
from src.services.ai_analysis_service import (
    DoubaoService,
    AIAnalysisService,
    get_ai_analysis_service,
)


class TestVideoAnalysisResult:
    """VideoAnalysisResult测试类"""

    def test_to_dict_cover(self):
        """测试封面分析转换为字典（7个维度）"""
        result = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="cover",
            cover_composition="中心构图法",
            cover_main_element="单人半身女性精致妆容画面",
            cover_color_scheme="粉橙为主暖色调",
            cover_visual_style="精致高级感",
            cover_mood_atmosphere="期待",
            cover_visual_highlights=["博主直视镜头", "超大号标题文字"],
            cover_audience_expectation="妆容教学",
        )

        d = result.to_dict()
        assert d["bvid"] == "BV1234567890"
        assert d["cover_composition"] == "中心构图法"
        assert d["cover_main_element"] == "单人半身女性精致妆容画面"
        assert d["cover_color_scheme"] == "粉橙为主暖色调"
        assert d["cover_visual_style"] == "精致高级感"
        assert d["cover_mood_atmosphere"] == "期待"
        assert "博主直视镜头" in d["cover_visual_highlights"]
        assert d["cover_audience_expectation"] == "妆容教学"

    def test_to_dict_content(self):
        """测试内容分析转换为字典（4个维度）"""
        result = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="content",
            topic_summary="夏日伪素颜仿妆教程",
            viral_logic_analysis="这个视频之所以走红，是因为...",
            content_optimization_suggestions="标题内增加数字、封面添加前后效果对比图",
            replicability_evaluation="中-需要专业化妆技能",
        )

        d = result.to_dict()
        assert d["bvid"] == "BV1234567890"
        assert d["topic_summary"] == "夏日伪素颜仿妆教程"
        assert d["viral_logic_analysis"] == "这个视频之所以走红，是因为..."
        assert d["content_optimization_suggestions"] == "标题内增加数字、封面添加前后效果对比图"
        assert d["replicability_evaluation"] == "中-需要专业化妆技能"


class TestAIAnalysisResult:
    """AIAnalysisResult测试类"""

    def test_init(self):
        """测试初始化"""
        result = AIAnalysisResult(bvid="BV1234567890")
        assert result.bvid == "BV1234567890"
        assert result.cover_analysis is None
        assert result.content_analysis is None


class TestDoubaoService:
    """豆包服务测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.service = DoubaoService(api_key="test-key", model="doubao-seed-2-0-lite-260428")

    def test_init(self):
        """测试初始化"""
        assert self.service.api_key == "test-key"
        assert self.service.model == "doubao-seed-2-0-lite-260428"

    def test_build_cover_prompt(self):
        """测试封面分析提示词构建（7个维度）"""
        video = Video(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
        )
        cover_url = "https://example.com/cover.jpg"
        prompt = self.service._build_cover_prompt(video, cover_url)
        assert "https://example.com/cover.jpg" in prompt
        assert "测试视频" in prompt
        assert "cover_composition" in prompt
        assert "cover_main_element" in prompt
        assert "cover_color_scheme" in prompt
        assert "cover_visual_style" in prompt
        assert "cover_mood_atmosphere" in prompt
        assert "cover_visual_highlights" in prompt
        assert "cover_audience_expectation" in prompt

    def test_build_content_prompt(self):
        """测试内容分析提示词构建（4个维度）"""
        video = Video(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="technology",
        )
        prompt = self.service._build_content_prompt(video)
        assert "测试视频" in prompt
        assert "测试UP主" in prompt
        assert "topic_summary" in prompt
        assert "viral_logic_analysis" in prompt
        assert "content_optimization_suggestions" in prompt
        assert "replicability_evaluation" in prompt

    @patch("src.services.ai_analysis_service.DoubaoService._call_api")
    def test_analyze_cover_no_client(self, mock_call_api):
        """测试无API响应时返回None"""
        mock_call_api.return_value = None
        video = Video(bvid="BV1234567890", title="测试视频")
        result = self.service.analyze_cover(video, "https://example.com/cover.jpg")
        assert result is None

    @patch("src.services.ai_analysis_service.DoubaoService._call_api")
    def test_analyze_content_no_client(self, mock_call_api):
        """测试无API响应时返回None"""
        mock_call_api.return_value = None
        video = Video(bvid="BV1234567890", title="测试视频")
        result = self.service.analyze_content(video)
        assert result is None


class TestAIAnalysisService:
    """AI分析服务测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.service = AIAnalysisService()

    @patch.object(DoubaoService, "analyze_cover")
    def test_analyze_video_cover(self, mock_analyze_cover):
        """测试封面分析"""
        mock_analyze_cover.return_value = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="cover",
            cover_composition="中心构图法",
            cover_main_element="单人半身女性精致妆容画面",
            cover_color_scheme="粉橙为主暖色调",
            cover_visual_style="精致高级感",
            cover_mood_atmosphere="期待",
            cover_visual_highlights=["博主直视镜头"],
            cover_audience_expectation="妆容教学",
        )

        video = Video(bvid="BV1234567890", title="测试视频")
        result = self.service.analyze_video(video, "https://example.com/cover.jpg", analysis_type="cover")

        assert result is not None
        assert result.bvid == "BV1234567890"
        assert result.cover_analysis is not None
        assert result.cover_analysis.cover_composition == "中心构图法"
        assert result.cover_analysis.cover_main_element == "单人半身女性精致妆容画面"

    @patch.object(DoubaoService, "analyze_content")
    def test_analyze_video_content(self, mock_analyze_content):
        """测试内容分析"""
        mock_analyze_content.return_value = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="content",
            topic_summary="夏日伪素颜仿妆教程",
            viral_logic_analysis="这个视频之所以走红...",
            content_optimization_suggestions="标题内增加数字",
            replicability_evaluation="中-需要专业技能",
        )

        video = Video(bvid="BV1234567890", title="测试视频")
        result = self.service.analyze_video(video, analysis_type="content")

        assert result is not None
        assert result.bvid == "BV1234567890"
        assert result.content_analysis is not None
        assert result.content_analysis.topic_summary == "夏日伪素颜仿妆教程"
        assert result.content_analysis.replicability_evaluation == "中-需要专业技能"

    @patch.object(DoubaoService, "analyze_cover")
    @patch.object(DoubaoService, "analyze_content")
    def test_analyze_video_both(self, mock_analyze_content, mock_analyze_cover):
        """测试同时分析封面和内容"""
        mock_analyze_cover.return_value = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="cover",
            cover_composition="中心构图法",
        )
        mock_analyze_content.return_value = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="content",
            topic_summary="编程教程",
        )

        video = Video(bvid="BV1234567890", title="测试视频")
        result = self.service.analyze_video(video, "https://example.com/cover.jpg", analysis_type="both")

        assert result is not None
        assert result.cover_analysis is not None
        assert result.content_analysis is not None

    @patch("src.services.ai_analysis_service.get_db_session")
    def test_cache_analysis(self, mock_get_session):
        """测试缓存分析结果"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        cover_result = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="cover",
            cover_composition="中心构图法",
            cover_main_element="女性精致妆容",
            cover_color_scheme="暖色调",
            cover_visual_style="精致高级感",
            cover_mood_atmosphere="期待",
            cover_visual_highlights=["博主直视镜头"],
            cover_audience_expectation="妆容教学",
        )
        content_result = VideoAnalysisResult(
            bvid="BV1234567890",
            analysis_type="content",
            topic_summary="夏日伪素颜仿妆教程",
            viral_logic_analysis="这个视频之所以走红...",
            content_optimization_suggestions="标题增加数字",
            replicability_evaluation="中",
        )

        ai_result = AIAnalysisResult(
            bvid="BV1234567890",
            cover_analysis=cover_result,
            content_analysis=content_result,
        )

        result = self.service.cache_analysis(ai_result)
        assert result is True
        assert mock_session.execute.call_count == 2

    @patch("src.services.ai_analysis_service.get_db_session")
    def test_get_cached_analysis_found(self, mock_get_session):
        """测试获取缓存的分析结果-存在"""
        import json

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchall.return_value = [
            (
                "BV1234567890",
                "cover_analysis",
                json.dumps({
                    "bvid": "BV1234567890",
                    "analysis_type": "cover",
                    "cover_composition": "中心构图法",
                    "cover_main_element": "女性精致妆容",
                    "cover_color_scheme": "暖色调",
                    "cover_visual_style": "精致高级感",
                    "cover_mood_atmosphere": "期待",
                    "cover_visual_highlights": [],
                    "cover_audience_expectation": "妆容教学",
                }),
                datetime.now(),
            ),
            (
                "BV1234567890",
                "content_analysis",
                json.dumps({
                    "bvid": "BV1234567890",
                    "analysis_type": "content",
                    "topic_summary": "夏日伪素颜仿妆教程",
                    "viral_logic_analysis": "这个视频之所以走红...",
                    "content_optimization_suggestions": "标题增加数字",
                    "replicability_evaluation": "中",
                }),
                datetime.now(),
            ),
        ]

        result = self.service.get_cached_analysis("BV1234567890")

        assert result is not None
        assert result.bvid == "BV1234567890"
        assert result.cover_analysis is not None
        assert result.cover_analysis.cover_composition == "中心构图法"
        assert result.cover_analysis.cover_main_element == "女性精致妆容"
        assert result.content_analysis is not None
        assert result.content_analysis.topic_summary == "夏日伪素颜仿妆教程"
        assert result.content_analysis.replicability_evaluation == "中"

    @patch("src.services.ai_analysis_service.get_db_session")
    def test_get_cached_analysis_not_found(self, mock_get_session):
        """测试获取缓存的分析结果-不存在"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchall.return_value = []

        result = self.service.get_cached_analysis("BV0000000000")
        assert result is None


class TestGetAIService:
    """AI服务单例测试类"""

    def test_get_ai_analysis_service(self):
        """测试获取AI分析服务单例"""
        service1 = get_ai_analysis_service()
        service2 = get_ai_analysis_service()
        assert service1 is service2
