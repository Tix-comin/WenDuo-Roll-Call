"""
闻铎点名器 - 主入口
悬浮球 + 主窗口模式
适合在PPT放映时使用
"""
import sys
import os
import traceback

# ------- onefile / windowed 兼容 -------
# 在 windowed 子系统下，sys.stdout / sys.stderr 为 None，print 会直接崩溃
# 这里先把它们重定向到一个文件（exe 同级），既保证可读性又避免崩溃
if getattr(sys, "frozen", False):
    # 打包后：exe 所在目录 = 用户数据目录（data/ 放这里）
    EXE_DIR = os.path.dirname(sys.executable)
else:
    # 源码运行：脚本所在目录
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = EXE_DIR
sys.path.insert(0, PROJECT_ROOT)
# onefile 模式下，PyInstaller 把 src/ 和 assets/ 都解压到 _MEIPASS
# 确保该目录在搜索路径最前，from src.xxx import 才能找到
_meipass = getattr(sys, "_MEIPASS", None)
if _meipass:
    sys.path.insert(0, _meipass)

# 重定向 stdout / stderr 到 exe 同级 run.log
_LOG_PATH = os.path.join(EXE_DIR, "run.log")
try:
    _log_fp = open(_LOG_PATH, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None or not getattr(sys.stdout, "fileno", lambda: -1)() >= 0:
        sys.stdout = _log_fp
    if sys.stderr is None or not getattr(sys.stderr, "fileno", lambda: -1)() >= 0:
        sys.stderr = _log_fp
except Exception:
    _log_fp = None


def _resolve_asset(rel_path: str) -> str:
    """解析资源路径：优先 _MEIPASS（PyInstaller onefile 解压后的临时目录），再退到 exe 目录"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cand = os.path.join(meipass, rel_path)
        if os.path.exists(cand):
            return cand
    return os.path.join(EXE_DIR, rel_path)


# 调试日志（打包后也能看到错误）
def _log(msg):
    try:
        import datetime
        line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n"
        if _log_fp is not None:
            _log_fp.write(line)
            _log_fp.flush()
    except Exception:
        pass

try:
    _log("启动中...")
    _log(f"sys.path OK, PROJECT_ROOT={PROJECT_ROOT}")
    _log(f"sys.executable={sys.executable}")
    _log(f"frozen={getattr(sys, 'frozen', False)}, _MEIPASS={getattr(sys, '_MEIPASS', 'N/A')}")

    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QRadialGradient, QLinearGradient, QBrush, QPen, QFont
    _log("PyQt6 imports OK")

    from src.floating_ball import FloatingBall
    from src.main_window import MainWindow
    from src.quick_picker_window import QuickPickerWindow
    from src.data_manager import ensure_data_dir
    _log("src modules imports OK")
except Exception as e:
    _log(f"IMPORT ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)


class NamePickerApp:
    """点名器应用"""

    def __init__(self):
        _log("NamePickerApp.__init__ 开始")
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("闻铎点名器")
        self.app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出

        # 确保数据目录存在
        ensure_data_dir()

        # 加载应用图标
        self._load_app_icon()
        _log("应用图标加载完成")

        # 创建悬浮球
        self.floating_ball = FloatingBall()
        self.floating_ball.clicked.connect(self._on_ball_clicked)
        _log("悬浮球创建完成")

        # 创建主窗口并显示
        self.main_window = MainWindow()
        self.main_window.destroyed.connect(lambda: setattr(self, 'main_window', None))
        self.main_window.show()
        _log("主窗口创建完成")

        # 小窗（快速点名面板）引用
        self.quick_window = None

        # 创建系统托盘
        self._setup_tray()
        _log("托盘创建完成")

        # 显示悬浮球
        self.floating_ball.show()
        _log("NamePickerApp.__init__ 完成")

    def _load_app_icon(self):
        """加载应用图标：优先用 ICO（已居中裁剪为正方形，多尺寸，避免 Qt 拉伸变形）"""
        candidates = [
            "assets/app_icon.ico",          # 打包后解压到 MEIPASS/运行目录；ICO 是正方形多尺寸
            "assets/icons/app_icon.png",    # 备用：PNG（运行时会按比例缩放）
        ]
        for rel in candidates:
            p = _resolve_asset(rel)
            if p and os.path.exists(p):
                self.app_icon = QIcon(p)
                self.app.setWindowIcon(self.app_icon)
                _log(f"应用图标: {p}")
                return
        # 全部缺失时动态生成
        self._create_app_icon()

    def _create_app_icon(self):
        """创建应用图标 - 从 _resolve_asset 路径加载 PNG"""
        try:
            icon_path = _resolve_asset("assets/app_icon_transparent.png")
            if os.path.exists(icon_path):
                self.app_icon = QIcon(icon_path)
                self.app.setWindowIcon(self.app_icon)
                _log(f"加载图标: {icon_path}")
            else:
                self._create_default_icon()
        except Exception as e:
            _log(f"加载图标失败: {e}")
            self._create_default_icon()

    def _create_default_icon(self):
        """创建默认图标（回退方案）"""
        try:
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            gradient = QLinearGradient(0, 0, 64, 64)
            gradient.setColorAt(0, QColor("#60A5FA"))
            gradient.setColorAt(0.5, QColor("#3B82F6"))
            gradient.setColorAt(1, QColor("#1D4ED8"))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor(255, 255, 255, 80), 2))
            painter.drawRoundedRect(2, 2, 60, 60, 16, 16)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
            painter.drawText(2, 2, 60, 60, Qt.AlignmentFlag.AlignCenter, "闻")
            painter.end()
            self.app_icon = QIcon(pixmap)
            self.app.setWindowIcon(self.app_icon)
        except Exception:
            pass

    def _setup_tray(self):
        """设置系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            _log("系统不支持托盘，跳过托盘初始化")
            self.tray = None
            return

        self.tray = QSystemTrayIcon(self.app)
        if hasattr(self, 'app_icon'):
            self.tray.setIcon(self.app_icon)
        self.tray.setToolTip("闻铎点名器")

        # 把 menu 存为实例属性，避免被 GC 回收
        self.menu = QMenu()
        quick_action = QAction("快速点名", self.menu)
        quick_action.triggered.connect(self._on_ball_clicked)
        show_action = QAction("完整设置", self.menu)
        show_action.triggered.connect(self._open_main_window)
        self.toggle_ball_action = QAction("显示悬浮球", self.menu)
        self.toggle_ball_action.triggered.connect(self._toggle_ball)
        quit_action = QAction("退出", self.menu)
        quit_action.triggered.connect(self._quit)

        self.menu.addAction(quick_action)
        self.menu.addAction(show_action)
        self.menu.addAction(self.toggle_ball_action)
        self.menu.addSeparator()
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        _log("托盘初始化完成")
        _update = getattr(self, '_update_ball_action_text', None)
        if callable(_update):
            _update()

    def _update_ball_action_text(self):
        """更新托盘菜单中悬浮球按钮的文字（根据当前状态）"""
        if not getattr(self, 'toggle_ball_action', None) or not getattr(self, 'floating_ball', None):
            return
        if self.floating_ball.isVisible():
            self.toggle_ball_action.setText("隐藏悬浮球")
        else:
            self.toggle_ball_action.setText("显示悬浮球")

    def _toggle_ball(self):
        """切换悬浮球显示/隐藏"""
        if self.floating_ball.isVisible():
            self.floating_ball.hide()
        else:
            self.floating_ball.show()
        self._update_ball_action_text()

    def _on_tray_activated(self, reason):
        """托盘图标点击 - 单击打开主界面，双击打开小窗"""
        # 1) 单击左键 → 弹出主窗口
        # 2) 双击左键 → 弹出小窗
        # 3) 右键由 setContextMenu 自动弹出（已带父对象，菜单项完整）
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._open_main_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_ball_clicked()

    def _on_ball_clicked(self):
        """点击悬浮球，显示/隐藏小窗（快速点名面板）"""
        if self.quick_window is None:
            # 共享主窗口的数据管理器，保证设置/名单/历史一致
            self.quick_window = QuickPickerWindow(
                self.main_window.name_manager,
                self.main_window.history_manager,
                self.main_window.settings_manager,
                self.main_window.tts_engine,
            )
            self.quick_window.destroyed.connect(lambda: setattr(self, 'quick_window', None))
            self.quick_window.floating_ball = self.floating_ball
            self.quick_window.quit_callback = self._quit
            self.quick_window.ball_state_changed_callback = self._update_ball_action_text
            self.quick_window.open_main_callback = self._open_main_window
            # 点击"打开完整设置"打开主窗口
            if hasattr(self.quick_window, 'open_main_btn'):
                self.quick_window.open_main_btn.clicked.connect(self._open_main_window)

        if self.quick_window.isVisible():
            self.quick_window.hide()
        else:
            ball_pos = self.floating_ball.pos()
            self.quick_window.show_near_ball(ball_pos)

    def _open_main_window(self):
        """打开完整设置的主窗口"""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _show_ball(self):
        """显示悬浮球"""
        if not self.floating_ball.isVisible():
            self.floating_ball.show()

    def _quit(self):
        """退出应用"""
        try:
            self.floating_ball.close()
        except Exception:
            pass
        try:
            if getattr(self, 'quick_window', None):
                self.quick_window.close()
        except Exception:
            pass
        try:
            if getattr(self, 'main_window', None):
                self.main_window.close()
        except Exception:
            pass
        try:
            tray = getattr(self, 'tray', None)
            if tray is not None:
                tray.hide()
        except Exception:
            pass
        try:
            self.app.quit()
        except Exception:
            pass

    def run(self):
        """运行应用"""
        sys.exit(self.app.exec())


if __name__ == "__main__":
    try:
        app = NamePickerApp()
        _log("进入事件循环...")
        app.run()
    except Exception as e:
        _log(f"FATAL: {e}")
        traceback.print_exc()
        sys.exit(1)