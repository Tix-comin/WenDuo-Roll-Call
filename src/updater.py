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

CURRENT_VERSION = "v2.0.0"

GITHUB_OWNER = "Tix-comin"
GITHUB_REPO = "WenDuo-Roll-Call"

# 安装包命名规则：WenDuo-Roll-Call-Setup-{tag}.exe
INSTALLER_NAME_TEMPLATE = "WenDuo-Roll-Call-Setup-{tag}.exe"

# 检查更新优先使用 GitHub releases/latest 重定向（无 API 速率限制），
# 失败时回退到 API + 镜像。
CHECK_URLS = [
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
    f"https://ghproxy.com/https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
    f"https://gh-proxy.com/https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
    f"https://ghproxy.com/https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
]

DOWNLOAD_MIRRORS = [
    "",
    "https://ghproxy.com/",
    "https://gh-proxy.com/",
    "https://mirror.ghproxy.com/",
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
        tag_name = None
        release_body = ""
        download_url_base = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

        for check_url in CHECK_URLS:
            try:
                req = urllib.request.Request(
                    check_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                    }
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    final_url = resp.geturl()
                    # 优先从重定向后的 URL 解析 tag，例如 .../releases/tag/v1.0.0
                    tag_name = self._extract_tag_from_url(final_url)

                    if "api.github.com" in check_url:
                        # API 模式：从 JSON 读取 tag_name + release notes
                        data = json.loads(resp.read().decode("utf-8"))
                        tag_name = data.get("tag_name", tag_name or "")
                        release_body = data.get("body", "") or ""
                    elif not tag_name:
                        # 非API URL 但未能从URL解析tag，尝试读取内容（可能是JSON）
                        try:
                            ct = resp.headers.get("Content-Type", "")
                            if "json" in ct:
                                data = json.loads(resp.read().decode("utf-8"))
                                tag_name = data.get("tag_name", "")
                                release_body = data.get("body", "") or ""
                        except Exception:
                            pass

                    if not tag_name:
                        last_error = "无法解析版本号"
                        continue

                    if not self._is_newer(tag_name, CURRENT_VERSION):
                        return None

                    # 如果没有从 API 获取到 release notes，尝试单独请求 API
                    if not release_body:
                        try:
                            api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tags/{tag_name}"
                            req2 = urllib.request.Request(api_url, headers={
                                "User-Agent": "Mozilla/5.0",
                                "Accept": "application/json",
                            })
                            with urllib.request.urlopen(req2, timeout=10) as resp2:
                                d2 = json.loads(resp2.read().decode("utf-8"))
                                release_body = d2.get("body", "") or ""
                        except Exception:
                            pass

                    filename = INSTALLER_NAME_TEMPLATE.format(tag=tag_name)
                    download_url = (
                        f"{download_url_base}/releases/download/{tag_name}/{filename}"
                    )

                    return UpdateInfo(
                        tag_name=tag_name,
                        name=f"闻铎点名器 {tag_name}",
                        body=release_body,
                        download_url=download_url,
                        filename=filename,
                        size=0,
                    )
            except Exception as e:
                last_error = e
                continue

        raise Exception(f"检查更新失败: {last_error}")

    def _extract_tag_from_url(self, url: str) -> str:
        """从 releases/tag/vX.Y.Z 形式的 URL 中提取 tag 名。"""
        import re
        match = re.search(r"/releases/tag/([^/?#]+)", url)
        return match.group(1) if match else ""

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
