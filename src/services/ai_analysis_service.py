"""
AI豆包模型分析服务
使用豆包模型进行视频内容与封面分析
"""
import json
import random
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.models.ai_analysis import VideoAnalysisResult, AIAnalysisResult
from src.models.video import Video
from src.config import settings
from src.utils.database import get_db_session
from src.skills.ai_analysis_skills import COVER_ANALYSIS_SKILL, CONTENT_ANALYSIS_SKILL
from sqlalchemy import text


# 模板缓存
_template_cache: Dict[str, str] = {}


def _get_ai_api_key_from_db() -> str:
    """从数据库获取AI API Key"""
    try:
        with get_db_session() as session:
            result = session.execute(
                text("SELECT config_value FROM system_config WHERE config_key = 'ai_api_key'")
            ).fetchone()
            if result and result[0]:
                return result[0]
    except Exception as e:
        print(f"Failed to get AI API key from database: {e}")
    return ""


class DoubaoService:
    """豆包模型服务"""

    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, model: str = "doubao-seed-2-0-lite-260428"):
        # 优先使用传入的 api_key，其次从数据库读取，最后使用环境变量
        self.api_key = api_key or _get_ai_api_key_from_db() or settings.ARK_API_KEY
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

    def _call_multimodal_api(self, text_prompt: str, image_url: str) -> Optional[Dict[str, Any]]:
        """调用豆包多模态API（支持图片URL输入）"""
        if not self.api_key:
            print("ARK_API_KEY not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 使用 messages + content 数组格式
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Ark Multimodal API call failed: {e}")
            return None

    def analyze_cover(self, video: Video, cover_url: str) -> Optional[VideoAnalysisResult]:
        """分析视频封面（使用多模态API传递图片URL）"""
        prompt = self._build_cover_prompt(video, cover_url)
        # 使用多模态API，图片URL会直接传给AI模型进行分析
        response = self._call_multimodal_api(prompt, cover_url)
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

    def _load_template_from_db(self, template_type: str) -> Optional[str]:
        """从数据库加载模板，支持缓存"""
        global _template_cache

        # 先检查缓存
        if template_type in _template_cache:
            return _template_cache[template_type]

        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT content FROM ai_prompt_template
                        WHERE template_type = :template_type AND is_active = TRUE
                    """),
                    {"template_type": template_type}
                ).fetchone()

                if result and result[0]:
                    _template_cache[template_type] = result[0]
                    return result[0]
        except Exception as e:
            print(f"Failed to load template from database: {e}")

        return None

    def _get_template(self, template_type: str) -> str:
        """获取模板，优先从数据库加载，失败则使用硬编码模板"""
        template = self._load_template_from_db(template_type)
        if template:
            return template

        # 降级到硬编码模板
        if template_type == "cover":
            return COVER_ANALYSIS_SKILL
        elif template_type == "content":
            return CONTENT_ANALYSIS_SKILL

        raise ValueError(f"Unknown template type: {template_type}")

    def _build_cover_prompt(self, video: Video, cover_url: str) -> str:
        """构建封面分析提示词"""
        template = self._get_template("cover")
        # 图片URL通过API单独传递，这里只返回模板文本
        return template

    def _build_content_prompt(self, video: Video) -> str:
        """构建内容分析提示词（4个维度）"""
        template = self._get_template("content")

        # 格式化视频时长
        duration = video.duration or 0
        if duration > 0:
            h = duration // 3600
            m = (duration % 3600) // 60
            s = duration % 60
            if h > 0:
                duration_str = f"{h}小时{m}分钟{s}秒"
            elif m > 0:
                duration_str = f"{m}分钟{s}秒"
            else:
                duration_str = f"{s}秒"
        else:
            duration_str = "未知"

        # 格式化标签
        tags = video.tags
        if tags:
            tags_str = "、".join(tags[:10])  # 最多10个标签
            if len(tags) > 10:
                tags_str += f" 等{len(tags)}个标签"
        else:
            tags_str = "无"

        return template.format(
            video_title=video.title,
            author=video.author,
            channel=video.channel,
            description=getattr(video, 'description', '') or '无',
            duration=duration_str,
            tags=tags_str,
            view_today=video.view_today,
            growth_rate=video.growth_rate,
            like_count=video.like_count,
            favorite_count=video.favorite_count,
            reply_count=video.reply_count,
            coin_count=video.coin_count,
            share_count=video.share_count,
            author_fans=getattr(video, 'author_fans', 0) or 0,
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
            # 尝试 /responses 格式
            output = response.get("output", [])
            for item in output:
                if item.get("type") == "message":
                    content = item.get("content", [])
                    for c in content:
                        if c.get("type") == "output_text":
                            return c.get("text", "").strip()

            # 尝试 /chat/completions 格式
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if content:
                    return content.strip()

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
                # 封面分析 - 新结构
                composition = data.get("composition", {})
                elements = data.get("elements", {})
                style = data.get("style", {})
                appeal = data.get("appeal", {})

                result.composition_rule = composition.get("rule")
                result.composition_desc = composition.get("description")
                result.elements_subjects = elements.get("subjects")
                result.elements_text = elements.get("text")
                result.elements_color_palette = elements.get("color_palette")
                result.elements_lighting = elements.get("lighting")
                result.style_overall = style.get("overall")
                result.style_mood = style.get("mood")
                result.appeal_attraction = appeal.get("attraction")
                result.appeal_hook = appeal.get("hook")
            else:
                # 内容分析 - 新结构（使用camelCase匹配API返回）
                result.short_topic = data.get("shortTopic")
                result.summary_insight = data.get("summaryInsight")
                result.optimization_suggestions = data.get("optimizationSuggestions")

            return result
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}, text: {text[:200]}")
            return None


class GeminiService:
    """Gemini 模型服务"""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MAX_RETRIES = 2
    RETRY_DELAY = 3  # 秒，减少重试次数和等待时间

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model

    def _call_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用 Gemini API (text-only)"""
        if not self.api_key:
            print("GEMINI_API_KEY not configured")
            return None

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
            }
        }

        # 429重试逻辑：指数退避 + 随机抖动 + Retry-After
        max_retries = 5
        retry_count = 0
        base_delay = 2

        while retry_count < max_retries:
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=60,
                )

                # 只对 429 做重试，400/403/404 等错误不重试
                if response.status_code == 429:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"Gemini API 429: 达到最大重试次数 {max_retries}，放弃")
                        return None

                    # 优先读取 Retry-After 响应头
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        delay = min(int(retry_after), 30)
                    else:
                        delay = min(base_delay * (2 ** (retry_count - 1)) + random.random(), 30)

                    print(f"Gemini API 429限流，第{retry_count}次重试，等待{delay:.2f}s")
                    time.sleep(delay)
                    continue

                # 400 等错误不重试，直接返回
                if response.status_code >= 400:
                    print(f"Gemini API 错误 {response.status_code}: {response.text[:200]}")
                    return None

                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"Gemini API 请求失败: {e}")
                    return None
                delay = min(base_delay * (2 ** (retry_count - 1)) + random.random(), 30)
                print(f"Gemini API 请求失败，第{retry_count}次重试，等待{delay:.2f}s: {e}")
                time.sleep(delay)
                continue
        return None

    def _call_multimodal_api(self, text_prompt: str, image_url: str) -> Optional[Dict[str, Any]]:
        """调用 Gemini 多模态 API (下载图片并使用 base64 编码)"""
        if not self.api_key:
            print("GEMINI_API_KEY not configured")
            return None

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"

        # 下载图片并转为 base64
        try:
            import base64
            import time

            # 下载图片
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
            }
            img_response = requests.get(image_url, headers=headers, timeout=30)

            # 检查响应状态和内容类型
            if img_response.status_code != 200:
                print(f"Failed to download image: {image_url}, status: {img_response.status_code}")
                return None

            content_type = img_response.headers.get("Content-Type", "")
            if "text/html" in content_type.lower():
                print(f"Image URL returned HTML instead of image: {image_url}")
                return None

            image_data = img_response.content

            # 检查图片数据有效性
            if len(image_data) < 1000:
                print(f"Image data too small ({len(image_data)} bytes), likely invalid: {image_url}")
                return None

            if "png" in content_type:
                mime_type = "image/png"
            elif "webp" in content_type:
                mime_type = "image/webp"
            else:
                mime_type = "image/jpeg"

            # base64 编码
            base64_image = base64.b64encode(image_data).decode("utf-8")

            payload = {
                "contents": [{
                    "parts": [
                        {"text": text_prompt},
                        {"inlineData": {"mimeType": mime_type, "data": base64_image}}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                }
            }

            # 429重试逻辑：指数退避 + 随机抖动 + Retry-After
            max_retries = 5
            retry_count = 0
            base_delay = 2

            while retry_count < max_retries:
                try:
                    response = requests.post(
                        url,
                        json=payload,
                        timeout=60,
                    )

                    # 只对 429 做重试，400/403/404 等错误不重试
                    if response.status_code == 429:
                        retry_count += 1
                        if retry_count >= max_retries:
                            print(f"Gemini Multimodal API 429: 达到最大重试次数 {max_retries}，放弃")
                            return None

                        # 优先读取 Retry-After 响应头
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            delay = min(int(retry_after), 30)
                        else:
                            delay = min(base_delay * (2 ** (retry_count - 1)) + random.random(), 30)

                        print(f"Gemini Multimodal API 429限流，第{retry_count}次重试，等待{delay:.2f}s")
                        time.sleep(delay)
                        continue

                    # 400 等错误不重试，直接返回
                    if response.status_code >= 400:
                        print(f"Gemini Multimodal API 错误 {response.status_code}: {response.text[:200]}")
                        return None

                    response.raise_for_status()
                    return response.json()

                except requests.RequestException as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"Gemini Multimodal API 请求失败: {e}")
                        return None
                    delay = min(base_delay * (2 ** (retry_count - 1)) + random.random(), 30)
                    print(f"Gemini Multimodal API 请求失败，第{retry_count}次重试，等待{delay:.2f}s: {e}")
                    time.sleep(delay)
                    continue

        except Exception as e:
            print(f"Gemini Multimodal API prepare failed: {e}")
            return None
        return None

    def analyze_cover(self, video: Video, cover_url: str) -> Optional[VideoAnalysisResult]:
        """分析视频封面"""
        prompt = self._build_cover_prompt(video, cover_url)
        response = self._call_multimodal_api(prompt, cover_url)
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

    def _load_template_from_db(self, template_type: str) -> Optional[str]:
        """从数据库加载模板，支持缓存"""
        global _template_cache
        if template_type in _template_cache:
            return _template_cache[template_type]

        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT content FROM ai_prompt_template
                        WHERE template_type = :template_type AND is_active = TRUE
                    """),
                    {"template_type": template_type}
                ).fetchone()

                if result and result[0]:
                    _template_cache[template_type] = result[0]
                    return result[0]
        except Exception as e:
            print(f"Failed to load template from database: {e}")

        return None

    def _get_template(self, template_type: str) -> str:
        """获取模板，优先从数据库加载，失败则使用硬编码模板"""
        template = self._load_template_from_db(template_type)
        if template:
            return template

        if template_type == "cover":
            return COVER_ANALYSIS_SKILL
        elif template_type == "content":
            return CONTENT_ANALYSIS_SKILL

        raise ValueError(f"Unknown template type: {template_type}")

    def _build_cover_prompt(self, video: Video, cover_url: str) -> str:
        """构建封面分析提示词"""
        template = self._get_template("cover")
        return template

    def _build_content_prompt(self, video: Video) -> str:
        """构建内容分析提示词"""
        template = self._get_template("content")

        duration = video.duration or 0
        if duration > 0:
            h = duration // 3600
            m = (duration % 3600) // 60
            s = duration % 60
            if h > 0:
                duration_str = f"{h}小时{m}分钟{s}秒"
            elif m > 0:
                duration_str = f"{m}分钟{s}秒"
            else:
                duration_str = f"{s}秒"
        else:
            duration_str = "未知"

        tags = video.tags
        if tags:
            tags_str = "、".join(tags[:10])
            if len(tags) > 10:
                tags_str += f" 等{len(tags)}个标签"
        else:
            tags_str = "无"

        return template.format(
            video_title=video.title,
            author=video.author,
            channel=video.channel,
            description=getattr(video, 'description', '') or '无',
            duration=duration_str,
            tags=tags_str,
            view_today=video.view_today,
            growth_rate=video.growth_rate,
            like_count=video.like_count,
            favorite_count=video.favorite_count,
            reply_count=video.reply_count,
            coin_count=video.coin_count,
            share_count=video.share_count,
            author_fans=getattr(video, 'author_fans', 0) or 0,
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
        """从 API 响应中提取文本"""
        try:
            candidates = response.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            return ""
        except Exception:
            return ""

    def _parse_to_video_result(self, bvid: str, analysis_type: str, text: str) -> Optional[VideoAnalysisResult]:
        """将响应文本解析为 VideoAnalysisResult"""
        try:
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
                composition = data.get("composition", {})
                elements = data.get("elements", {})
                style = data.get("style", {})
                appeal = data.get("appeal", {})

                result.composition_rule = composition.get("rule")
                result.composition_desc = composition.get("description")
                result.elements_subjects = elements.get("subjects")
                result.elements_text = elements.get("text")
                result.elements_color_palette = elements.get("color_palette")
                result.elements_lighting = elements.get("lighting")
                result.style_overall = style.get("overall")
                result.style_mood = style.get("mood")
                result.appeal_attraction = appeal.get("attraction")
                result.appeal_hook = appeal.get("hook")
            else:
                result.short_topic = data.get("shortTopic")
                result.summary_insight = data.get("summaryInsight")
                result.optimization_suggestions = data.get("optimizationSuggestions")

            return result
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}, text: {text[:200]}")
            return None


class AIAnalysisService:
    """AI分析服务"""

    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower() if settings.AI_PROVIDER else "gemini"
        if self.provider == "gemini":
            self.gemini_service = GeminiService()
            self.doubao_service = None
        else:
            self.doubao_service = DoubaoService()
            self.gemini_service = None

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

        if self.provider == "gemini" and self.gemini_service:
            if analysis_type in ("cover", "both"):
                if not cover_url:
                    cover_url = getattr(video, 'cover_url', None)
                if cover_url:
                    result.cover_analysis = self.gemini_service.analyze_cover(video, cover_url)

            if analysis_type in ("content", "both"):
                result.content_analysis = self.gemini_service.analyze_content(video)
        elif self.doubao_service:
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
                            # 封面分析 - 新结构
                            # 兼容旧格式缓存数据
                            composition = data.get("composition") or {}
                            elements = data.get("elements") or {}
                            style = data.get("style") or {}
                            appeal = data.get("appeal") or {}

                            # 旧格式字段转换 (cover_composition -> composition.description)
                            if not composition and data.get("cover_composition"):
                                composition = {"description": data.get("cover_composition")}
                            if not elements.get("subjects") and data.get("cover_main_element"):
                                elements["subjects"] = data.get("cover_main_element")
                            if not elements.get("color_palette") and data.get("cover_color_scheme"):
                                elements["color_palette"] = data.get("cover_color_scheme")
                            if not style.get("overall") and data.get("cover_visual_style"):
                                style["overall"] = data.get("cover_visual_style")
                            if not style.get("mood") and data.get("cover_mood_atmosphere"):
                                style["mood"] = data.get("cover_mood_atmosphere")

                            video_result.composition_rule = composition.get("rule")
                            video_result.composition_desc = composition.get("description")
                            video_result.elements_subjects = elements.get("subjects")
                            video_result.elements_text = elements.get("text")
                            video_result.elements_color_palette = elements.get("color_palette")
                            video_result.elements_lighting = elements.get("lighting")
                            video_result.style_overall = style.get("overall")
                            video_result.style_mood = style.get("mood")
                            video_result.appeal_attraction = appeal.get("attraction")
                            video_result.appeal_hook = appeal.get("hook")
                            ai_result.cover_analysis = video_result
                        elif analysis_type == "content_analysis":
                            # 内容分析 - 新结构（兼容camelCase和snake_case）
                            # 兼容旧格式缓存数据 (topic_summary -> shortTopic, viral_logic_analysis -> summaryInsight)
                            video_result.short_topic = data.get("shortTopic") or data.get("short_topic") or data.get("topic_summary")
                            video_result.summary_insight = data.get("summaryInsight") or data.get("summary_insight") or data.get("viral_logic_analysis")
                            video_result.optimization_suggestions = data.get("optimizationSuggestions") or data.get("optimization_suggestions") or data.get("content_optimization_suggestions")
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
