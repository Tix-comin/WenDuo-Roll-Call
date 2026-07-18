"""
悬浮球点出的小窗 - 快速点名面板
小巧的尺寸，便于在PPT放映时使用
"""
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPen, QPixmap, QIcon

import os
import sys


def _resolve_asset(rel_path: str) -> str:
    """小窗版资源路径解析：优先打包时的 _MEIPASS，再退到项目根目录"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cand = os.path.join(meipass, rel_path)
        if os.path.exists(cand):
            return cand
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", rel_path)

try:
    from src.data_manager import NameListManager, HistoryManager, SettingsManager
    from src.picker_engine import PickerEngine
    from src.tts_engine import TTSEngine
    from src.styles import PRIMARY, PRIMARY_DARK, ACCENT, SECONDARY, NEUTRAL, DANGER, WHITE
except ImportError:
    from data_manager import NameListManager, HistoryManager, SettingsManager
    from picker_engine import PickerEngine
    from tts_engine import TTSEngine
    from styles import PRIMARY, PRIMARY_DARK, ACCENT, SECONDARY, NEUTRAL, DANGER, WHITE


class QuickPickerWindow(QWidget):
    """小点名窗口 - 悬浮球点出的小窗"""

    WINDOW_WIDTH = 380
    WINDOW_HEIGHT = 440

    def __init__(self, name_manager, history_manager, settings_manager, tts_engine, parent=None):
        super().__init__(parent)
        # 共享自主窗口的引擎，保持数据一致性
        self.name_manager = name_manager
        self.history_manager = history_manager
        self.settings_manager = settings_manager
        self.tts_engine = tts_engine
        # PickerEngine 使用共享的管理器，保证记录写入同一份历史
        self.picker_engine = PickerEngine(
            self.name_manager, self.history_manager, self.settings_manager
        )

        # 状态
        self._is_rolling = False
        self._rolling_timer = None
        self._rolling_index = 0
        self._rolling_sequence = []
        self._is_batch_rolling = False
        self._batch_rolling_timer = None
        self._batch_results = []
        self._batch_index = 0
        self._like_count = 0
        self._drag_pos = None

        self._init_ui()

        # 数据信号订阅：与主窗口共享数据变化时小窗也会自动刷新
        try:
            self.name_manager.changed.connect(self._refresh_count)
            self.history_manager.changed.connect(self._refresh_count)
            self.settings_manager.changed.connect(self._refresh_count)
        except Exception:
            pass

    def _refresh_count(self):
        """刷新剩余/总人数显示"""
        remaining, total = self.picker_engine.get_counts()
        if hasattr(self, 'count_label') and self.count_label is not None:
            self.count_label.setText(f"剩余 {remaining} / 总 {total} 人")

    def _init_ui(self):
        """初始化UI（美化版：放大名字显示、渐变背景、卡片阴影）"""
        self.setWindowTitle("快速点名")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 统一应用图标（小窗虽无系统标题栏，但在 ALT+TAB/任务切换中会用到）
        # 优先用 ICO（已居中裁剪为正方形多尺寸，避免 Qt 对 565x648 PNG 拉伸变形）
        icon_path = _resolve_asset("assets/app_icon.ico")
        if not (icon_path and os.path.exists(icon_path)):
            icon_path = _resolve_asset("assets/icons/app_icon.png")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 主容器（圆角 + 渐变背景 + 阴影边框）
        container = QFrame(self)
        container.setGeometry(0, 0, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-radius: 20px;
                border: 1px solid #E2E8F0;
            }}
        """)

        # ========== 顶部栏（渐变蓝） ==========
        top_bar = QFrame(container)
        top_bar.setGeometry(0, 0, self.WINDOW_WIDTH, 48)
        top_bar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #2563EB);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
        """)
        # 整个顶部栏可点击打开主面板（拖动逻辑保留）
        top_bar.mousePressEvent = self._top_bar_press
        top_bar.mouseMoveEvent = self._top_bar_move
        # 双击顶部栏 = 打开主面板
        top_bar.mouseDoubleClickEvent = self._open_main_window

        # 标题文字（直接贴边，无图标框）
        title = QLabel("闻铎点名", top_bar)
        title.setGeometry(16, 0, 200, 48)
        title.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: 700;
            background: transparent;
            letter-spacing: 2px;
        """)

        # 右侧三个按钮：主面板 / 显示/隐藏小球 / 退出
        btn_size = 30
        # 主面板按钮
        self.top_open_main_btn = QPushButton("▢", top_bar)
        self.top_open_main_btn.setGeometry(self.WINDOW_WIDTH - 130, 9, btn_size, btn_size)
        self.top_open_main_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_open_main_btn.setToolTip("打开主面板")
        self.top_open_main_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.22);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.7);
            }
            QPushButton:pressed {
                background: rgba(29, 78, 216, 0.8);
            }
        """)
        self.top_open_main_btn.clicked.connect(self._open_main_window_clicked)

        # 悬浮球显示/隐藏切换按钮
        self.top_ball_toggle_btn = QPushButton("🟢", top_bar)
        self.top_ball_toggle_btn.setGeometry(self.WINDOW_WIDTH - 88, 9, btn_size, btn_size)
        self.top_ball_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_ball_toggle_btn.setToolTip("显示/隐藏悬浮球")
        self.top_ball_toggle_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.22);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.6);
            }
        """)
        self.top_ball_toggle_btn.clicked.connect(self._toggle_floating_ball)

        # 关闭小窗按钮（仅关闭小窗，不退出整个程序）
        self.top_quit_btn = QPushButton("×", top_bar)
        self.top_quit_btn.setGeometry(self.WINDOW_WIDTH - 46, 9, btn_size, btn_size)
        self.top_quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_quit_btn.setToolTip("关闭小窗")
        self.top_quit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.22);
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.7);
            }
            QPushButton:pressed {
                background: rgba(220, 38, 38, 0.8);
            }
        """)
        self.top_quit_btn.clicked.connect(self._close_window)

        # 兼容旧名：close_btn 仍指向退出按钮（保持向后兼容）
        close_btn = self.top_quit_btn

        # ========== 名字显示区（大幅放大） ==========
        self.display_label = QLabel("准备点名", container)
        self.display_label.setGeometry(24, 64, self.WINDOW_WIDTH - 48, 170)
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #DBEAFE, stop:1 #EFF6FF);
                color: {PRIMARY_DARK};
                border-radius: 16px;
                font-size: 56px;
                font-weight: 900;
                letter-spacing: 4px;
                border: 2px solid #BFDBFE;
            }}
        """)

        # 副标题 / 状态文字
        self.sub_label = QLabel("点击下方按钮开始随机抽取", container)
        self.sub_label.setGeometry(24, 238, self.WINDOW_WIDTH - 48, 22)
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("""
            color: #64748B;
            font-size: 12px;
            font-weight: 500;
            background: transparent;
        """)

        # 剩余/总人数（醒目的胶囊样式）
        self.count_label = QLabel("剩余 0 / 总 0 人", container)
        self.count_label.setGeometry((self.WINDOW_WIDTH - 200) // 2, 264, 200, 28)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #60A5FA, stop:1 #3B82F6);
                color: white;
                font-size: 12px;
                font-weight: 700;
                border-radius: 14px;
                padding: 4px 12px;
            }}
        """)

        # ========== 按钮区 ==========
        # 开始点名按钮（主操作，更大更突出）
        btn_y = 304
        self.start_btn = QPushButton("  ▶  开始点名", container)
        self.start_btn.setGeometry(24, btn_y, self.WINDOW_WIDTH - 48, 52)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_primary_style()
        self.start_btn.clicked.connect(self._toggle_rolling)

        # 底部三个子按钮
        bottom_y = btn_y + 62
        btn_width = (self.WINDOW_WIDTH - 48 - 16) // 3

        # 批量抽取
        self.batch_btn = QPushButton("📋 批量", container)
        self.batch_btn.setGeometry(24, bottom_y, btn_width, 42)
        self.batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F5F3FF;
                color: {ACCENT};
                border: 1.5px solid #DDD6FE;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #EDE9FE;
                border: 1.5px solid #C4B5FD;
            }}
            QPushButton:pressed {{
                background-color: #DDD6FE;
            }}
        """)
        self.batch_btn.clicked.connect(self._do_batch_pick)

        # 抽组
        self.group_btn = QPushButton("👥 抽组", container)
        self.group_btn.setGeometry(32 + btn_width, bottom_y, btn_width, 42)
        self.group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #ECFDF5;
                color: {SECONDARY};
                border: 1.5px solid #A7F3D0;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #D1FAE5;
                border: 1.5px solid #6EE7B7;
            }}
            QPushButton:pressed {{
                background-color: #A7F3D0;
            }}
        """)
        self.group_btn.clicked.connect(self._do_group_pick)

        # 清除历史
        self.like_btn = QPushButton("🗑 清除历史", container)
        self.like_btn.setGeometry(40 + btn_width * 2, bottom_y, btn_width, 42)
        self.like_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.like_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEE2E2;
                color: #B91C1C;
                border: 1.5px solid #FCA5A5;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #FECACA;
                border: 1.5px solid #F87171;
            }}
            QPushButton:pressed {{
                background-color: #FCA5A5;
            }}
        """)
        self.like_btn.clicked.connect(self._on_like)

        # 底部链接样式按钮行（⚙ 完整设置  |  🟢 显示/隐藏小球  |  ✕ 退出应用）
        bottom_row_y = self.WINDOW_HEIGHT - 38
        bottom_width_each = (self.WINDOW_WIDTH - 48) // 3

        self.open_main_btn = QPushButton("⚙ 完整设置", container)
        self.open_main_btn.setGeometry(24, bottom_row_y, bottom_width_each, 26)
        self.open_main_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_main_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #3B82F6;
                text-decoration: underline;
            }
        """)

        self.ball_toggle_btn = QPushButton("🟢 隐藏小球", container)
        self.ball_toggle_btn.setGeometry(24 + bottom_width_each, bottom_row_y, bottom_width_each, 26)
        self.ball_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ball_toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #10B981;
                text-decoration: underline;
            }
        """)
        self.ball_toggle_btn.clicked.connect(self._toggle_floating_ball)

        self.quit_btn = QPushButton("✕ 关闭小窗", container)
        self.quit_btn.setGeometry(24 + bottom_width_each * 2, bottom_row_y, bottom_width_each, 26)
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94A3B8;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #EF4444;
                text-decoration: underline;
            }
        """)
        self.quit_btn.clicked.connect(self._close_window)

        # 外部传入悬浮球引用（由 main.py 设置）
        self.floating_ball = None
        # 外部传入退出函数（由 main.py 设置）
        self.quit_callback = None
        # 外部传入悬浮球状态变更回调（由 main.py 设置，用于托盘菜单同步）
        self.ball_state_changed_callback = None

        # 初始化计数显示
        self._refresh_count()

    def showEvent(self, event):
        """小窗打开时，刷新一次计数显示"""
        super().showEvent(event)
        self._refresh_count()

    # ========== 样式 ==========

    def _apply_primary_style(self, rolling: bool = False):
        if rolling:
            self.start_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #EF4444, stop:1 #DC2626);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 17px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #F87171, stop:1 #DC2626);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #B91C1C, stop:1 #7F1D1D);
                }}
            """)
        else:
            self.start_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {PRIMARY}, stop:1 {PRIMARY_DARK});
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 17px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #60A5FA, stop:1 {PRIMARY});
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {PRIMARY_DARK}, stop:1 #1E3A8A);
                }}
            """)

    # ========== 拖动 ==========

    def _top_bar_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _top_bar_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    # ========== 点名逻辑 ==========

    def _toggle_rolling(self):
        if self._is_rolling:
            self._stop_rolling()
        else:
            self._start_rolling()

    def _start_rolling(self):
        if self.name_manager.count == 0:
            self._show_message("名单为空，请先添加名字")
            return

        self._is_rolling = True
        self.start_btn.setText("  ⏹  停止点名")
        self._apply_primary_style(rolling=True)

        self._rolling_sequence = self.picker_engine.get_rolling_sequence(100)
        self._rolling_index = 0

        interval = max(30, 1000 // self.settings_manager.speed)
        self._rolling_timer = QTimer(self)
        self._rolling_timer.timeout.connect(self._rolling_step)
        self._rolling_timer.start(interval)

        stop_ms = int(self.settings_manager.stop_time * 1000)
        QTimer.singleShot(stop_ms, self._stop_rolling)

    def _rolling_step(self):
        if not self._is_rolling:
            return
        if self._rolling_index < len(self._rolling_sequence):
            name = self._rolling_sequence[self._rolling_index]
            self._rolling_index += 1
            self.display_label.setText(name)
            self.display_label.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #DBEAFE, stop:1 #EFF6FF);
                    color: {NEUTRAL};
                    border-radius: 16px;
                    font-size: 56px;
                    font-weight: 900;
                    letter-spacing: 4px;
                    border: 2px solid #BFDBFE;
                }}
            """)
        else:
            self._rolling_sequence = self.picker_engine.get_rolling_sequence(100)
            self._rolling_index = 0

    def _stop_rolling(self):
        if self._rolling_timer:
            self._rolling_timer.stop()
            self._rolling_timer = None

        self._is_rolling = False
        self.start_btn.setText("  ▶  开始点名")
        self._apply_primary_style(rolling=False)

        result = self.picker_engine.pick_single()
        if result:
            self._set_result(result, f"抽中: {result}", PRIMARY_DARK)
            self.tts_engine.speak(result)

    def _do_batch_pick(self):
        """批量抽取：点击一次开始批量朗读，再次点击停止"""
        if self._is_batch_rolling:
            # 正在批量朗读，再次点击 → 停止
            self._stop_batch_rolling()
            return

        if self.name_manager.count == 0:
            self._show_message("名单为空，请先添加名字")
            return

        count = self.settings_manager.batch_count
        results = self.picker_engine.pick_batch(count)

        if not results:
            self._show_message("没有可抽取的名字")
            return

        # 展示一次性结果（与之前逻辑保持一致）
        result_text = "、".join(results)
        if len(results) <= 1:
            self._set_result(results[0], f"批量 {len(results)} 人: {result_text}", ACCENT)
        elif len(results) <= 3:
            self._set_result(result_text, f"批量 {len(results)} 人", ACCENT, big=True)
        else:
            self._set_result(result_text, f"批量 {len(results)} 人", ACCENT, big=False, small_text=True)

        # 依次朗读
        self._batch_results = list(results)
        self._batch_index = 0
        self._is_batch_rolling = True
        self.batch_btn.setText("⏹ 停止朗读")
        self.batch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEF2F2;
                color: #DC2626;
                border: 1.5px solid #FCA5A5;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #FEE2E2;
                border: 1.5px solid #F87171;
            }}
            QPushButton:pressed {{
                background-color: #FECACA;
            }}
        """)
        self._speak_next_batch()

    def _speak_next_batch(self):
        if not self._is_batch_rolling:
            return
        if self._batch_index >= len(self._batch_results):
            # 读完了，恢复按钮
            self._reset_batch_btn()
            return
        name = self._batch_results[self._batch_index]
        self._batch_index += 1
        # 显示当前朗读的名字
        if self._batch_index <= len(self._batch_results):
            self._set_result(name, f"{self._batch_index} / {len(self._batch_results)}", ACCENT)
        self.tts_engine.speak(name)
        # 1.2 秒后继续下一个（等待朗读大致时间）
        self._batch_rolling_timer = QTimer(self)
        self._batch_rolling_timer.setSingleShot(True)
        self._batch_rolling_timer.timeout.connect(self._speak_next_batch)
        self._batch_rolling_timer.start(1200)

    def _stop_batch_rolling(self):
        if self._batch_rolling_timer:
            self._batch_rolling_timer.stop()
            self._batch_rolling_timer = None
        self.tts_engine.stop()
        self._is_batch_rolling = False
        self._reset_batch_btn()

    def _reset_batch_btn(self):
        self.batch_btn.setText("📋 批量")
        self.batch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F5F3FF;
                color: {ACCENT};
                border: 1.5px solid #DDD6FE;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #EDE9FE;
                border: 1.5px solid #C4B5FD;
            }}
            QPushButton:pressed {{
                background-color: #DDD6FE;
            }}
        """)

    def _do_group_pick(self):
        result = self.picker_engine.pick_group()
        if result is not None:
            result_text = f"{result}组"
            self._set_result(result_text, f"抽中: {result_text}", SECONDARY)
            self.tts_engine.speak(f"第{result}组")

    def _on_like(self):
        """清除历史记录（同步刷新剩余人数）"""
        if hasattr(self, 'history_manager') and self.history_manager is not None:
            self.history_manager.clear_all()
            # 视觉反馈：切换一次高亮色，再恢复
            self.like_btn.setText("✓ 已清除")
            self.like_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #D1FAE5;
                    color: #065F46;
                    border: 2px solid #6EE7B7;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 700;
                }}
            """)
            QTimer.singleShot(800, self._reset_like_style)

    def _reset_like_style(self):
        self.like_btn.setText("🗑 清除历史")
        self.like_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FEE2E2;
                color: #B91C1C;
                border: 1.5px solid #FCA5A5;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #FECACA;
                border: 1.5px solid #F87171;
            }}
            QPushButton:pressed {{
                background-color: #FCA5A5;
            }}
        """)

    def _toggle_floating_ball(self):
        """切换悬浮球显示/隐藏"""
        ball = getattr(self, 'floating_ball', None)
        if ball is None:
            return
        if ball.isVisible():
            ball.hide()
            if hasattr(self, 'ball_toggle_btn') and self.ball_toggle_btn is not None:
                self.ball_toggle_btn.setText("🟢 显示小球")
            if hasattr(self, 'top_ball_toggle_btn') and self.top_ball_toggle_btn is not None:
                self.top_ball_toggle_btn.setText("⚫")
                self.top_ball_toggle_btn.setToolTip("显示悬浮球")
        else:
            ball.show()
            if hasattr(self, 'ball_toggle_btn') and self.ball_toggle_btn is not None:
                self.ball_toggle_btn.setText("🟢 隐藏小球")
            if hasattr(self, 'top_ball_toggle_btn') and self.top_ball_toggle_btn is not None:
                self.top_ball_toggle_btn.setText("🟢")
                self.top_ball_toggle_btn.setToolTip("隐藏悬浮球")
        cb = getattr(self, 'ball_state_changed_callback', None)
        if cb is not None:
            try:
                cb()
            except Exception:
                pass

    def _open_main_window(self, event=None):
        """双击顶部栏打开主窗口"""
        if event is not None and hasattr(event, 'button') and event.button() != Qt.MouseButton.LeftButton:
            return
        cb = getattr(self, 'open_main_callback', None)
        if cb is not None:
            try:
                cb()
            except Exception:
                pass
        if event is not None:
            try:
                event.accept()
            except Exception:
                pass

    def _open_main_window_clicked(self):
        """点击主面板按钮打开主窗口"""
        self._open_main_window()

    def _close_window(self):
        """关闭小窗（隐藏窗口，不退出整个程序）"""
        self.hide()

    def _quit_app(self):
        """退出整个应用（保留接口供外部调用）"""
        cb = getattr(self, 'quit_callback', None)
        if cb is not None:
            cb()

    # ========== 显示辅助 ==========

    def _set_result(self, text: str, sub: str, color: str, big: bool = True, small_text: bool = False):
        self.display_label.setText(text)
        # 根据内容长度自适应字号（big=True 最大，small_text 适合多人名单）
        if small_text:
            font_size = 26
        elif len(text) > 6:
            font_size = 44
        elif big:
            font_size = 64
        else:
            font_size = 56
        self.display_label.setStyleSheet(f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #DBEAFE, stop:1 #EFF6FF);
                color: {color};
                border-radius: 16px;
                font-size: {font_size}px;
                font-weight: 900;
                letter-spacing: 3px;
                border: 2px solid #BFDBFE;
            }}
        """)
        self.sub_label.setText(sub)

    def _show_message(self, message: str):
        self.sub_label.setText(message)
        QTimer.singleShot(2000, lambda: self.sub_label.setText("点击下方按钮开始随机抽取"))

    # ========== 位置 ==========

    def show_near_ball(self, ball_pos: QPoint):
        """在悬浮球附近显示"""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = ball_pos.x() - self.WINDOW_WIDTH - 10
            if x < geo.left():
                x = ball_pos.x() + 60
            y = max(geo.top() + 10, ball_pos.y() - self.WINDOW_HEIGHT // 2)
            y = min(y, geo.bottom() - self.WINDOW_HEIGHT - 10)
            self.move(QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        # 关闭窗口时隐藏，而不是真正关闭
        self.hide()
        event.ignore()
