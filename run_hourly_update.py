"""手动执行 Hourly Video Update"""
import sys
sys.path.insert(0, '.')

# Brotli解压错误补丁
try:
    import brotlicffi
    _orig_decompress = brotlicffi.Decompressor.decompress
    def _patched_decompress(self, data, max_length=None):
        return _orig_decompress(self, data)
    brotlicffi.Decompressor.decompress = _patched_decompress
except ImportError:
    pass

from src.tasks.video_tasks import hourly_video_update_task
from datetime import datetime

print(f"[{datetime.now().isoformat()}] Starting manual hourly_video_update_task...")
print("=" * 60)

result = hourly_video_update_task()

print("=" * 60)
print(f"[{datetime.now().isoformat()}] Task completed!")
print(f"\nResult: {result}")

# 查询 BV1QEgZ6rEGj 的在线人数
import psycopg2
conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/bombo")
cur = conn.cursor()
cur.execute("SELECT bvid, online_count, max_online_today FROM monitor_pool WHERE bvid = 'BV1QEgZ6rEGj'")
row = cur.fetchone()
print(f"\nBV1QEgZ6rEGj 在线人数:")
print(f"  online_count: {row[1]}")
print(f"  max_online_today: {row[2]}")
cur.close()
conn.close()
