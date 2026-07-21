"""
B站每日热榜API客户端
从多个数据源获取B站热榜视频
"""
import asyncio
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import requests

from src.config import settings
from src.crawlers.anti_crawler import get_anti_crawler


# 21个标准赛道及其细分赛道映射
CHANNEL_MAPPING = {
    '动画': ['MAD·AMV', 'MMD·3D', '短片手书配音', '模玩周边', '特摄', '动漫杂谈', '动漫', '动画'],
    '音乐': ['原创音乐', '翻唱', 'VOCALOID·UTAU', '电音', '演奏', 'MV', '音乐现场', 'OP/ED/OST', '音乐综合', '音乐'],
    '游戏': ['单机游戏', '手机游戏', '网络游戏', '电子竞技', '桌游棋牌', '音游', 'GMV', 'Mugen', '游戏杂谈', '游戏'],
    '娱乐': ['综艺', '娱乐杂谈', '粉丝创作', '明星综合', '韩娱', '脱口秀', '整活', '娱乐'],
    '影视': ['影视解说', '影视剪辑', '影评', '小剧场', '短片', '影视杂谈', '影视'],
    '番剧': ['连载动画', '完结动画', '番剧资讯', '官方延伸', '新番速览', '番剧'],
    '电影': ['院线电影解说', '经典影片剪辑', '短片电影', '电影杂谈', '海外影片', '电影'],
    '鬼畜': ['鬼畜调教', '音 MAD', '人力 VOCALOID', '鬼畜剧场', '教程演示', '鬼畜'],
    '舞蹈': ['宅舞', '街舞', '中国舞', '明星舞蹈', '手势舞', '舞蹈教程', '舞蹈综合', '舞蹈'],
    '生活': ['日常 Vlog', '搞笑', '手工', '家装', '户外', '探店', '生活技巧', '综合', '生活'],
    '国创': ['国产动画', '国产原创二创', '布袋戏', '动态漫·广播剧', '国创资讯', '国创'],
    '纪录片': ['人文纪实', '自然地理', '历史档案', '社会观察', '行业纪实', '纪录片'],
    '科技': ['数码测评', '机械 DIY', '极客硬件', '天文星海', '数码教程', '黑科技', '科技'],
    '资讯': ['社会热点', '财经产业', '行业快讯', '民生观察', '国际资讯', '资讯'],
    '知识': ['校园学习', '历史人文', '法律科普', '心理', '公考', '财经科普', '野生技术协会', '知识'],
    '美食': ['家常菜', '烘焙', '探店', '食材测评', '野外美食', '美食教程', '甜品', '美食'],
    '动物圈': ['喵星人', '汪星人', '小宠异宠', '野生动物', '饲养科普', '动物日常', '动物圈'],
    '汽车': ['新车测评', '改装', '自驾', '用车知识', '二手车', '摩托', '车展', '汽车'],
    '运动': ['健身', '篮球', '足球', '户外徒步', '球类', '格斗', '跑步', '赛事解说', '运动'],
    '时尚': ['美妆', '穿搭', '护肤', '彩妆测评', '发型', '时尚穿搭', '医美科普', '时尚'],
    '软件应用': ['编程教程', '办公软件', '工具分享', 'APP 测评', '电脑技巧', '脚本开发', '软件应用'],
}

# 反向映射：细分赛道 -> 标准赛道
_SUBCHANNEL_TO_STANDARD = {}
for _standard, _subchannels in CHANNEL_MAPPING.items():
    for _sub in _subchannels:
        _SUBCHANNEL_TO_STANDARD[_sub] = _standard


def normalize_channel(channel: str) -> str:
    """
    将B站细分赛道归类到21个标准赛道

    Args:
        channel: B站返回的原始赛道名称

    Returns:
        对应的21个标准赛道之一
    """
    if not channel:
        return '生活'

    # 精确匹配
    if channel in _SUBCHANNEL_TO_STANDARD:
        return _SUBCHANNEL_TO_STANDARD[channel]

    # 模糊匹配
    for _standard, _subchannels in CHANNEL_MAPPING.items():
        for _sub in _subchannels:
            if _sub in channel or channel in _sub:
                return _standard

    # 未匹配到，返回原赛道（后续可人工确认添加映射）
    return channel


@dataclass
class HotVideoItem:
    """热榜视频项"""
    bvid: str
    title: str
    author: str
    description: str
    pic: str  # 封面URL
    play: int  # 播放量
    like: int  # 点赞数
    coin: int  # 投币数
    favorite: int  # 收藏数
    share: int  # 分享数
    reply: int  # 评论数
    pubdate: int  # 发布时间戳
    duration: int  # 视频时长(秒)
    tid: int  # 分区ID
    tname: str  # 分区名称（原始赛道，归类后可能变化）


class DailyHotApiClient:
    """B站每日热榜API客户端"""

    # API端点列表（按优先级排序）
    API_ENDPOINTS = [
        # 官方API（需要代理或WBI）
        "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all",
        # 第三方聚合API
        "https://api.pearktrue.cn/api/bilibili/hot/",
        "https://api.xyurl.cn/api/bilibili/hot",
    ]

    # 热门话题API
    HOT_TOPIC_URL = "https://api.bilibili.com/x/topic/home/v2"

    def __init__(self, cookie: Optional[str] = None):
        """
        初始化热榜API客户端

        Args:
            cookie: B站Cookie，用于官方API认证
        """
        self.anti_crawler = get_anti_crawler()
        self.cookie = cookie or settings.BILI_COOKIE

    def _get_headers(self) -> dict:
        """获取请求头"""
        headers = self.anti_crawler.get_headers()
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """获取代理配置"""
        proxy = self.anti_crawler.get_random_proxy()
        if proxy:
            return {"http": proxy, "https": proxy}
        return None

    def get_hot_videos(self, rid: int = 0, limit: int = 50) -> List[HotVideoItem]:
        """
        获取B站热榜视频

        Args:
            rid: 分区ID，0表示全站
            limit: 返回数量上限

        Returns:
            热榜视频列表
        """
        # 应用延时
        self.anti_crawler.apply_delay()

        # 尝试各API端点
        for endpoint in self.API_ENDPOINTS:
            try:
                result = self._fetch_from_endpoint(endpoint, rid, limit)
                if result:
                    return result
            except Exception as e:
                print(f"Failed to fetch from {endpoint[:50]}: {e}")
                continue

        # 如果所有API都失败，返回空列表
        print("All API endpoints failed")
        return []

    def _fetch_from_endpoint(self, endpoint: str, rid: int, limit: int) -> Optional[List[HotVideoItem]]:
        """从指定端点获取数据"""
        try:
            if "bilibili.com" in endpoint:
                return self._fetch_bilibili_api(endpoint, limit)
            else:
                return self._fetch_third_party_api(endpoint, limit)
        except Exception as e:
            print(f"Fetch error: {e}")
            return None

    def _fetch_bilibili_api(self, endpoint: str, limit: int) -> Optional[List[HotVideoItem]]:
        """获取官方B站API数据"""
        proxies = self._get_proxies()

        response = requests.get(
            endpoint,
            headers=self._get_headers(),
            proxies=proxies,
            timeout=30
        )

        if response.status_code != 200:
            return None

        data = response.json()

        # 检查返回状态 -352表示需要WBI签名
        if data.get("code") == -352:
            print("B站API需要WBI签名认证")
            return None

        if data.get("code") != 0:
            return None

        video_list = data.get("data", {}).get("list", [])
        return self._parse_video_list(video_list, limit)

    def _fetch_third_party_api(self, endpoint: str, limit: int) -> Optional[List[HotVideoItem]]:
        """获取第三方API数据"""
        proxies = self._get_proxies()

        response = requests.get(
            endpoint,
            headers=self._get_headers(),
            proxies=proxies,
            timeout=30
        )

        if response.status_code != 200:
            return None

        data = response.json()

        # 解析第三方API响应
        video_list = data.get("data", []) or data.get("result", []) or []

        if not video_list:
            return None

        return self._parse_video_list(video_list, limit)

    def _parse_video_list(self, raw_list: List[Dict], limit: int) -> List[HotVideoItem]:
        """解析视频列表数据"""
        results = []

        for item in raw_list[:limit]:
            try:
                # 处理不同API返回的数据格式
                stat = item.get("stat", {}) or item

                video = HotVideoItem(
                    bvid=item.get("bvid", ""),
                    title=item.get("title", ""),
                    author=item.get("author", "") or item.get("owner", {}).get("name", ""),
                    description=item.get("description", ""),
                    pic=item.get("pic", ""),
                    play=stat.get("view", 0) or stat.get("play", 0),
                    like=stat.get("like", 0),
                    coin=stat.get("coin", 0),
                    favorite=stat.get("favorite", 0),
                    share=stat.get("share", 0),
                    reply=stat.get("reply", 0) or stat.get("comment", 0),
                    pubdate=item.get("pubdate", 0),
                    duration=item.get("duration", 0),
                    tid=item.get("tid", 0),
                    tname=item.get("tname", ""),
                )

                if video.bvid:
                    results.append(video)

            except Exception as e:
                print(f"Parse video error: {e}")
                continue

        return results

    def get_popular_videos(self, page: int = 1, page_size: int = 20) -> List[HotVideoItem]:
        """
        获取B站近期热门视频（播放量高的视频）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            热门视频列表
        """
        # 使用popular API
        url = f"https://api.bilibili.com/x/web-interface/popular?pn={page}&ps={page_size}"

        proxies = self._get_proxies()

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                proxies=proxies,
                timeout=30
            )

            if response.status_code != 200:
                return []

            data = response.json()
            if data.get("code") != 0:
                return []

            video_list = data.get("data", {}).get("list", [])
            return self._parse_video_list(video_list, page_size)

        except Exception as e:
            print(f"Get popular videos error: {e}")
            return []

    def get_channel_hot_videos(self, channel_id: int, limit: int = 20) -> List[HotVideoItem]:
        """
        获取指定频道的热榜视频

        Args:
            channel_id: 频道ID（如：1=动画，3=音乐，4=游戏等）
            limit: 返回数量

        Returns:
            频道热榜视频列表
        """
        url = f"https://api.bilibili.com/x/web-interface/ranking/v2?rid={channel_id}&type=all"

        videos = self._fetch_bilibili_api(url, limit)
        return videos if videos else []

    def fetch_all_channels(self, videos_per_channel: int = 5) -> List[HotVideoItem]:
        """
        获取所有主要频道的热榜视频

        Args:
            videos_per_channel: 每个频道返回的视频数量

        Returns:
            所有频道的热榜视频列表
        """
        # 主要频道ID
        main_channels = [
            (1, "动画"),
            (3, "音乐"),
            (4, "游戏"),
            (5, "娱乐"),
            (11, "电视剧"),
            (13, "番剧"),
            (23, "电影"),
            (36, "科技"),
            (119, "鬼畜"),
            (129, "舞蹈"),
            (160, "美食"),
            (181, "运动"),
        ]

        all_videos = []
        seen_bvids = set()

        for channel_id, channel_name in main_channels:
            print(f"Fetching {channel_name} channel...")

            videos = self.get_channel_hot_videos(channel_id, videos_per_channel)

            for video in videos:
                if video.bvid not in seen_bvids:
                    all_videos.append(video)
                    seen_bvids.add(video.bvid)

            # 避免请求过快
            time.sleep(1)

        return all_videos
