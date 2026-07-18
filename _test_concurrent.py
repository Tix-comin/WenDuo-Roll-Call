"""测试并发下载速度"""
import sys
import time
import os

sys.path.insert(0, "d:\\桌面\\点名器")
from src.updater import DownloadPartsThread

parts = [
    ["https://gitee.com/dawalixijie/WenDuo-Roll-Call/releases/download/v2.0.0/WenDuo-Roll-Call-Setup-v2.0.0.part001"],
    ["https://gitee.com/dawalixijie/WenDuo-Roll-Call/releases/download/v2.0.0/WenDuo-Roll-Call-Setup-v2.0.0.part002"],
]

t = DownloadPartsThread(parts, r"d:\桌面\点名器\dist-install\test_3part.bin", max_workers=3)

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
print(f"2 parts (60MB) in {elapsed:.1f}s => {60/elapsed:.2f} MB/s")
if speeds:
    print(f"Avg signal speed: {sum(speeds)/len(speeds)/1024:.2f} MB/s")
    print(f"Peak signal speed: {max(speeds)/1024:.2f} MB/s")
path = r"d:\桌面\点名器\dist-install\test_3part.bin"
if os.path.exists(path):
    print(f"File size: {os.path.getsize(path)/1024/1024:.2f} MB")
