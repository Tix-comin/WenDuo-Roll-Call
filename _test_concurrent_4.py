"""测试 4 并发下载速度"""
import sys
import time
import os

sys.path.insert(0, "d:\\桌面\\点名器")
from src.updater import DownloadPartsThread

parts = [
    ["https://gitee.com/dawalixijie/WenDuo-Roll-Call/releases/download/v2.0.0/WenDuo-Roll-Call-Setup-v2.0.0.part001"],
    ["https://gitee.com/dawalixijie/WenDuo-Roll-Call/releases/download/v2.0.0/WenDuo-Roll-Call-Setup-v2.0.0.part002"],
    ["https://gitee.com/dawalixijie/WenDuo-Roll-Call/releases/download/v2.0.0/WenDuo-Roll-Call-Setup-v2.0.0.part003"],
    ["https://gitee.com/dawalixijie/WenDuo-Roll-Call/releases/download/v2.0.0/WenDuo-Roll-Call-Setup-v2.0.0.part004"],
]

t = DownloadPartsThread(parts, r"d:\桌面\点名器\dist-install\test_4part.bin", max_workers=4)

speeds = []
start = time.time()
done = False
result = None


def on_fin(path, src):
    global done, result
    done = True
    result = ("ok", path)


def on_fail(msg):
    global done, result
    done = True
    result = ("fail", msg)


t.finished.connect(on_fin)
t.failed.connect(on_fail)
t.speed.connect(lambda s: speeds.append(s))
t.start()

while not done and t.isRunning():
    t.msleep(100)

elapsed = time.time() - start
print(f"Result: {result}")
print(f"4 parts (120MB) in {elapsed:.1f}s => {120/elapsed:.2f} MB/s")
if speeds:
    print(f"Peak signal speed: {max(speeds)/1024:.2f} MB/s")
path = r"d:\桌面\点名器\dist-install\test_4part.bin"
if os.path.exists(path):
    print(f"File size: {os.path.getsize(path)/1024/1024:.2f} MB")
