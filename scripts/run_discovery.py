"""
手动运行视频发现任务
"""
import sys
sys.path.insert(0, '.')

from src.tasks.video_tasks import video_discovery_task

if __name__ == "__main__":
    print("=" * 50)
    print("开始视频发现任务...")
    print("=" * 50)

    result = video_discovery_task()

    print("=" * 50)
    print("任务完成!")
    print(f"结果: {result}")
    print("=" * 50)