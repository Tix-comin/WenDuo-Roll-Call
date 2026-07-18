"""自动更新模块 - 检查版本、下载更新、自动安装"""
import os
import sys
import json
import time
import shutil
import threading
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

CURRENT_VERSION = "v3.0.0"

GITHUB_OWNER = "Tix-comin"
GITHUB_REPO = "WenDuo-Roll-Call"

# 可选：Gitee 分流仓库（国内下载更快）。
# 若未配置（为空字符串），则只使用 GitHub 下载源。
GITEE_OWNER = "dawalixijie"
GITEE_REPO = "WenDuo-Roll-Call"

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

# 下载源模板：生成多个候选 URL，程序会依次尝试，优先使用靠前的源。
# 占位符：{tag}, {filename}
# 完整安装包下载源（Gitee 由于大文件上传限制采用分卷，这里只保留 GitHub 源）
DOWNLOAD_SOURCES = [
    # GitHub 官方 Releases（海外用户或全局代理时最快）
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{{tag}}/{{filename}}",
    # 部分 ghproxy 镜像对 release-assets 有一定加速效果
    f"https://gh-proxy.com/https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{{tag}}/{{filename}}",
    f"https://mirror.ghproxy.com/https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/{{tag}}/{{filename}}",
]


class UpdateInfo:
    def __init__(
        self,
        tag_name: str,
        name: str,
        body: str,
        download_url: str,
        filename: str,
        size: int = 0,
        download_urls: Optional[list] = None,
        parts_urls: Optional[list] = None,
    ):
        self.tag_name = tag_name
        self.name = name
        self.body = body
        self.download_url = download_url
        self.filename = filename
        self.size = size
        # 多个候选下载源，优先使用第一个可用的
        self.download_urls = download_urls or [download_url]
        # 分卷下载源：每个元素是一个候选 URL 列表，按顺序尝试
        self.parts_urls = parts_urls or []


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
                    download_urls = [
                        src.format(tag=tag_name, filename=filename)
                        for src in DOWNLOAD_SOURCES
                    ]
                    primary_url = download_urls[0]

                    # 尝试获取 Gitee 分卷列表（国内优先下载源）
                    parts, parts_size = self._get_gitee_parts(tag_name, filename)

                    return UpdateInfo(
                        tag_name=tag_name,
                        name=f"闻铎点名器 {tag_name}",
                        body=release_body,
                        download_url=primary_url,
                        filename=filename,
                        size=parts_size,
                        download_urls=download_urls,
                        parts_urls=parts,
                    )
            except Exception as e:
                last_error = e
                continue

        raise Exception(f"检查更新失败: {last_error}")

    def _get_gitee_parts(self, tag_name: str, filename: str) -> Tuple[list, int]:
        """从 Gitee Release 获取分卷下载 URL 列表与总大小，失败返回 ([], 0)。"""
        if not GITEE_OWNER or not GITEE_REPO:
            return [], 0
        try:
            import re
            api_url = (
                f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/"
                f"releases/tags/{tag_name}"
            )
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                assets = data.get("assets", [])
                # 安装包文件名含 .exe，分卷名不含 .exe，例如 Setup-v3.0.0.part001
                base_filename = os.path.splitext(filename)[0]
                pattern = re.escape(base_filename) + r"\.part\d{3}$"
                matched = sorted(
                    {a.get("name", ""): a for a in assets if re.match(pattern, a.get("name", ""))}.values(),
                    key=lambda a: a.get("name", ""),
                )
                parts_urls = [
                    [a.get("browser_download_url", "")]
                    for a in matched
                    if a.get("browser_download_url")
                ]
                total_size = sum(int(a.get("size") or 0) for a in matched)
                return parts_urls, total_size
        except Exception:
            return [], 0

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

    def __init__(self, download_url, save_path: str):
        super().__init__()
        # 支持单个 URL 字符串或 URL 列表；列表会按顺序尝试
        if isinstance(download_url, (list, tuple)):
            self.download_urls = list(download_url)
        else:
            self.download_urls = [download_url]
        self.save_path = save_path
        self._cancel = False

    def cancel(self):
        self._cancel = True

    # 下载速度保护：若 8 秒内下载不足 64KB，认为该节点过慢，切换到下一个镜像
    _SLOW_CHECK_INTERVAL = 8.0
    _SLOW_MIN_BYTES = 64 * 1024

    def run(self):
        temp_path = self.save_path + ".part"
        last_error = None

        for url in self.download_urls:
            if self._cancel:
                self.cancelled.emit()
                return

            # 每个源独立从头下载，避免不同源的 Range 续传混乱
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            downloaded = 0

            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "*/*",
                    }
                )

                # 30 秒超时；慢速节点会在速度检测中被提前放弃
                with urllib.request.urlopen(req, timeout=30) as resp:
                    total = int(resp.headers.get("Content-Length", 0))

                    start_time = time.time()
                    last_emit = 0
                    bytes_since_last = 0
                    slow_check_start = start_time
                    slow_check_bytes = 0

                    with open(temp_path, "wb") as f:
                        while True:
                            if self._cancel:
                                self.cancelled.emit()
                                return
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            bytes_since_last += len(chunk)
                            slow_check_bytes += len(chunk)

                            now = time.time()

                            # 慢速检测：8 秒不足 64KB 则换源
                            if now - slow_check_start >= self._SLOW_CHECK_INTERVAL:
                                if slow_check_bytes < self._SLOW_MIN_BYTES:
                                    raise Exception(
                                        f"节点过慢: {url[:60]}... "
                                        f"({slow_check_bytes / 1024:.1f} KB / {self._SLOW_CHECK_INTERVAL:.0f}s)"
                                    )
                                slow_check_start = now
                                slow_check_bytes = 0

                            # 进度刷新
                            if now - last_emit > 0.3:
                                if total > 0:
                                    pct = int(downloaded * 100 / total)
                                    self.progress.emit(min(pct, 99))
                                spd = bytes_since_last / (now - last_emit) if now - last_emit > 0 else 0
                                self.speed.emit(spd)
                                last_emit = now
                                bytes_since_last = 0

                if os.path.exists(temp_path):
                    if os.path.exists(self.save_path):
                        os.remove(self.save_path)
                    os.rename(temp_path, self.save_path)

                self.progress.emit(100)
                self.finished.emit(self.save_path, url)
                return
            except Exception as e:
                last_error = e
                continue

        self.failed.emit(f"下载失败: {last_error}")


class DownloadPartsThread(QThread):
    """分卷下载线程：并发下载多个分卷并合并成完整文件（国内 Gitee 优先）。"""

    progress = pyqtSignal(int)
    speed = pyqtSignal(float)
    finished = pyqtSignal(str, str)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, parts_urls, save_path: str, max_workers: int = 3):
        super().__init__()
        # parts_urls: 每个元素是一个分卷的候选 URL 列表
        self.parts_urls = parts_urls
        self.save_path = save_path
        self.max_workers = max_workers
        self._cancel = False
        self._temp_parts = {}
        self._lock = threading.Lock()
        self._total_size = 0
        self._downloaded_bytes = 0
        self._bytes_window = 0
        self._window_start = time.time()
        self._part_sizes = []

    def cancel(self):
        self._cancel = True

    # 下载速度保护：若 8 秒内下载不足 64KB，认为该节点过慢，切换到下一个镜像
    _SLOW_CHECK_INTERVAL = 8.0
    _SLOW_MIN_BYTES = 64 * 1024

    def run(self):
        try:
            os.makedirs(os.path.dirname(self.save_path) or ".", exist_ok=True)
            total_size = 0
            part_sizes = []

            # 获取每个分卷大小
            for idx, urls in enumerate(self.parts_urls):
                size = 0
                for url in urls:
                    try:
                        size = self._get_size(url)
                        break
                    except Exception:
                        continue
                if size <= 0:
                    raise Exception(f"无法获取分卷 {idx + 1} 的大小")
                part_sizes.append(size)
                total_size += size

            self._total_size = total_size
            self._part_sizes = part_sizes
            base_name = os.path.splitext(os.path.basename(self.save_path))[0]
            self._window_start = time.time()

            # 并发下载
            from concurrent.futures import ThreadPoolExecutor, as_completed

            tasks = list(range(len(self.parts_urls)))
            completed = set()
            errors = {}

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_map = {}
                for idx in tasks:
                    part_path = os.path.join(
                        os.path.dirname(self.save_path),
                        f"{base_name}.part{idx + 1:03d}",
                    )
                    future = executor.submit(
                        self._download_part_worker,
                        idx,
                        self.parts_urls[idx],
                        part_path,
                        part_sizes[idx],
                    )
                    future_map[future] = idx

                for future in as_completed(future_map):
                    idx = future_map[future]
                    try:
                        part_path = future.result()
                        with self._lock:
                            self._temp_parts[idx] = part_path
                            completed.add(idx)
                    except Exception as e:
                        errors[idx] = str(e)
                        # 一个分卷失败就取消所有
                        self._cancel = True
                        for f in future_map:
                            f.cancel()

            if errors:
                first_err = list(errors.values())[0]
                raise Exception(f"分卷下载失败: {first_err}")

            if self._cancel:
                self.cancelled.emit()
                return

            # 按序号排序后合并
            sorted_paths = [self._temp_parts[i] for i in sorted(self._temp_parts.keys())]
            self._merge_parts(sorted_paths)
            self.progress.emit(100)
            self.finished.emit(self.save_path, "gitee-parts")
        except Exception as e:
            self.failed.emit(f"分卷下载失败: {e}")

    def _get_size(self, url: str) -> int:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return int(resp.headers.get("Content-Length", 0))

    def _download_part_worker(self, idx: int, urls, part_path: str, part_size: int):
        """单个分卷的下载工作线程，返回最终的 part_path。"""
        last_error = None
        for url in urls:
            if self._cancel:
                raise Exception("已取消")

            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass

            downloaded = 0
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "*/*",
                    },
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    start_time = time.time()
                    slow_check_start = start_time
                    slow_check_bytes = 0

                    with open(part_path, "wb") as f:
                        while True:
                            if self._cancel:
                                raise Exception("已取消")
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            slow_check_bytes += len(chunk)

                            # 全局进度与速度统计（加锁）
                            with self._lock:
                                self._downloaded_bytes += len(chunk)
                                self._bytes_window += len(chunk)
                                now = time.time()
                                elapsed = now - self._window_start
                                if elapsed >= 0.3 and self._total_size > 0:
                                    pct = int(self._downloaded_bytes * 100 / self._total_size)
                                    self.progress.emit(min(pct, 99))
                                    spd = self._bytes_window / elapsed if elapsed > 0 else 0
                                    self.speed.emit(spd)
                                    self._window_start = now
                                    self._bytes_window = 0

                            now2 = time.time()
                            if now2 - slow_check_start >= self._SLOW_CHECK_INTERVAL:
                                if slow_check_bytes < self._SLOW_MIN_BYTES:
                                    raise Exception(
                                        f"节点过慢: {url[:60]}... "
                                        f"({slow_check_bytes / 1024:.1f} KB / {self._SLOW_CHECK_INTERVAL:.0f}s)"
                                    )
                                slow_check_start = now2
                                slow_check_bytes = 0

                # 验证大小
                if os.path.getsize(part_path) != part_size:
                    raise Exception(f"分卷 {idx + 1} 大小不匹配")
                return part_path
            except Exception as e:
                last_error = e
                continue
        raise Exception(f"分卷 {idx + 1} 所有源都失败: {last_error}")

    def _merge_parts(self, sorted_paths):
        with open(self.save_path, "wb") as out:
            for part_path in sorted_paths:
                with open(part_path, "rb") as f:
                    shutil.copyfileobj(f, out)
        for part_path in sorted_paths:
            try:
                os.remove(part_path)
            except Exception:
                pass


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
