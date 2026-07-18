"""自动更新模块 - 检查版本、下载更新、自动安装"""
import os
import sys
import json
import time
import tempfile
import subprocess
from typing import Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer

try:
    import urllib.request
    import urllib.error
    from urllib.parse import urljoin
except ImportError:
    urllib = None

CURRENT_VERSION = "v1.0.0"

GITHUB_OWNER = "Tix-comin"
GITHUB_REPO = "WenDuo-Roll-Call"

CHECK_URLS = [
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
    f"https://ghproxy.com/https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
    f"https://gh-proxy.com/https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
    f"https://mirror.ghproxy.com/https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
]

DOWNLOAD_MIRRORS = [
    "https://ghproxy.com/",
    "https://gh-proxy.com/",
    "https://mirror.ghproxy.com/",
    "",
]


class UpdateInfo:
    def __init__(self, tag_name: str, name: str, body: str, download_url: str, filename: str, size: int = 0):
        self.tag_name = tag_name
        self.name = name
        self.body = body
        self.download_url = download_url
        self.filename = filename
        self.size = size


class CheckUpdateThread(QThread):
    finished = pyqtSignal(object, str)

    def run(self):
        try:
            info = self._check_update()
            self.finished.emit(info, "")
        except Exception as e:
            self.finished.emit(None, str(e))

    def _check_update(self) -> Optional[UpdateInfo]:
        last_error = None
        for check_url in CHECK_URLS:
            try:
                req = urllib.request.Request(
                    check_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    tag_name = data.get("tag_name", "")
                    name = data.get("name", tag_name)
                    body = data.get("body", "")
                    assets = data.get("assets", [])

                    installer_asset = None
                    for asset in assets:
                        fname = asset.get("name", "")
                        if "安装程序" in fname and fname.endswith(".exe"):
                            installer_asset = asset
                            break

                    if installer_asset is None:
                        for asset in assets:
                            fname = asset.get("name", "")
                            if fname.endswith(".exe") and "installer" not in fname.lower():
                                installer_asset = asset
                                break

                    if installer_asset is None and assets:
                        installer_asset = assets[0]

                    if installer_asset is None:
                        last_error = "未找到更新包"
                        continue

                    browser_url = installer_asset.get("browser_download_url", "")
                    fname = installer_asset.get("name", "闻铎点名器 安装程序.exe")
                    size = installer_asset.get("size", 0)

                    if not self._is_newer(tag_name, CURRENT_VERSION):
                        return None

                    return UpdateInfo(
                        tag_name=tag_name,
                        name=name,
                        body=body,
                        download_url=browser_url,
                        filename=fname,
                        size=size,
                    )
            except Exception as e:
                last_error = e
                continue

        raise Exception(f"检查更新失败: {last_error}")

    def _is_newer(self, latest: str, current: str) -> bool:
        def parse_version(v: str) -> Tuple[int, ...]:
            v = v.lstrip("v")
            parts = []
            for p in v.split("."):
                try:
                    parts.append(int(p))
                except ValueError:
                    import re
                    m = re.match(r"(\d+)", p)
                    if m:
                        parts.append(int(m.group(1)))
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts[:3])

        return parse_version(latest) > parse_version(current)


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    speed = pyqtSignal(float)
    finished = pyqtSignal(str, str)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, download_url: str, save_path: str):
        super().__init__()
        self.download_url = download_url
        self.save_path = save_path
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        temp_path = self.save_path + ".part"
        downloaded = 0
        if os.path.exists(temp_path):
            downloaded = os.path.getsize(temp_path)

        last_error = None
        for mirror in DOWNLOAD_MIRRORS:
            if self._cancel:
                self.cancelled.emit()
                return
            try:
                url = mirror + self.download_url if mirror else self.download_url
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    }
                )

                if downloaded > 0:
                    req.add_header("Range", f"bytes={downloaded}-")

                with urllib.request.urlopen(req, timeout=30) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    if resp.status == 206:
                        total += downloaded
                    else:
                        downloaded = 0
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                    mode = "ab" if downloaded > 0 else "wb"
                    start_time = time.time()
                    last_emit = 0
                    bytes_since_last = 0

                    with open(temp_path, mode) as f:
                        while True:
                            if self._cancel:
                                self.cancelled.emit()
                                return
                            chunk = resp.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            bytes_since_last += len(chunk)
                            now = time.time()
                            if now - last_emit > 0.2:
                                if total > 0:
                                    pct = int(downloaded * 100 / total)
                                    elapsed = now - start_time
                                    spd = bytes_since_last / (now - last_emit) if now - last_emit > 0 else 0
                                    self.progress.emit(pct)
                                    self.speed.emit(spd)
                                last_emit = now
                                bytes_since_last = 0

                if os.path.exists(temp_path):
                    if os.path.exists(self.save_path):
                        os.remove(self.save_path)
                    os.rename(temp_path, self.save_path)

                self.progress.emit(100)
                self.finished.emit(self.save_path, self.download_url)
                return
            except Exception as e:
                last_error = e
                continue

        self.failed.emit(f"下载失败: {last_error}")


def launch_installer(installer_path: str):
    try:
        subprocess.Popen(
            [installer_path],
            shell=True,
            cwd=os.path.dirname(installer_path) or os.getcwd(),
        )
    except Exception as e:
        raise Exception(f"启动安装程序失败: {e}")


def get_save_dir() -> str:
    return os.path.join(tempfile.gettempdir(), "WenDuoPicker")
