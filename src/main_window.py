"""
主窗口 - 侧边栏 + 内容区布局
闻铎点名器 - Main Window
"""
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QCheckBox, QLineEdit, QFrame, QStackedWidget,
    QScrollArea, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QSizePolicy, QSpacerItem,
    QSpinBox, QApplication, QButtonGroup, QAbstractButton,
    QDialog, QProgressBar
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize,
    QPoint, pyqtSignal, QRect, QParallelAnimationGroup
)
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPalette, QPen, QIcon, QPixmap

from src.data_manager import NameListManager, HistoryManager, SettingsManager
from src.picker_engine import PickerEngine
from src.tts_engine import TTSEngine
from src.updater import (
    CheckUpdateThread, DownloadThread, DownloadPartsThread, UpdateInfo,
    CURRENT_VERSION, launch_installer, get_save_dir, get_existing_install_dir,
    load_update_state, save_update_state, clear_update_state, is_newer_version
)
from src.icons import icon_label, render_icon
from src.styles import (
    PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, PRIMARY_ULTRALIGHT, SECONDARY, SECONDARY_DARK,
    ACCENT, ACCENT_DARK, NEUTRAL, NEUTRAL_2, NEUTRAL_3, NEUTRAL_4, NEUTRAL_5, NEUTRAL_6,
    WHITE, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, BG_MAIN, GLOBAL_STYLE
)
from src.animation_helper import (
    AnimationManager, bounce_result, fade_in, slide_in, animate_smooth_move
)
from src.ios_toggle import IOSToggle


def _resolve_asset(rel_path: str) -> str:
    """解析资源路径，兼容源码运行与 PyInstaller 打包后的环境。"""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, rel_path))
    # 源码运行：main_window.py 位于 src/，所以要向上一级
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel_path))
    # 打包后 exe 所在目录（与 data/ 同级）
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), rel_path))
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[-1] if candidates else rel_path


# ========== 工具组件 ==========

class DisplayCard(QFrame):
    """中央点名显示卡片 - Apple风格温润渐变卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("displayCard")
        self.setFixedHeight(200)
        self._current_name = "准备点名"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        self.title_label = QLabel("准备点名")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "font-size: 56px; font-weight: 700; color: #0051D5; background: transparent; letter-spacing: 2px;"
        )
        self.title_label.setWordWrap(False)

        self.sub_label = QLabel("点击下方按钮开始")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet(
            "font-size: 14px; color: #8E8E93; background: transparent; font-weight: 500;"
        )

        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.sub_label)

    def set_text(self, text):
        """设置显示文本并自动根据文字长度调整字号"""
        self._current_name = text
        self.title_label.setText(text)
        n = len(text)
        if n <= 2:
            font_size = 72
        elif n <= 3:
            font_size = 60
        elif n <= 4:
            font_size = 50
        elif n <= 6:
            font_size = 40
        elif n <= 8:
            font_size = 32
        else:
            font_size = 26
        self.title_label.setStyleSheet(
            f"font-size: {font_size}px; font-weight: 700; color: #0051D5; background: transparent; letter-spacing: 2px;"
        )

    def paintEvent(self, event):
        """自定义绘制Apple风格渐变背景 + 装饰元素"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 柔和的蓝白渐变
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#F0F7FF"))
        gradient.setColorAt(0.4, QColor("#E0F0FF"))
        gradient.setColorAt(1, QColor("#FFFFFF"))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 20, 20)

        # 装饰圆（左上，柔和蓝）
        painter.setBrush(QColor(PRIMARY_LIGHT))
        painter.setOpacity(0.25)
        painter.drawEllipse(24, 20, 32, 32)

        # 装饰圆（右上，柔和紫）
        painter.setBrush(QColor(ACCENT))
        painter.setOpacity(0.12)
        painter.drawEllipse(self.width() - 70, 16, 50, 50)

        # 装饰圆（右下，柔和绿）
        painter.setBrush(QColor(SECONDARY))
        painter.setOpacity(0.12)
        painter.drawEllipse(self.width() - 90, self.height() - 55, 44, 44)

        # 装饰点（左下）
        painter.setBrush(QColor(WARNING))
        painter.setOpacity(0.2)
        painter.drawEllipse(36, self.height() - 36, 18, 18)

        painter.setOpacity(1.0)
        painter.end()
        super().paintEvent(event)

    def set_result(self, text: str, sub_text: str, color: str = PRIMARY_DARK):
        """设置结果 - 带丝滑弹跳动画"""
        self.title_label.setText(text)
        self.sub_label.setText(sub_text)
        n = len(text)
        if n <= 2:
            font_size = 72
        elif n <= 3:
            font_size = 60
        elif n <= 4:
            font_size = 50
        elif n <= 6:
            font_size = 40
        elif n <= 8:
            font_size = 32
        else:
            font_size = 26
        self.title_label.setStyleSheet(
            f"font-size: {font_size}px; font-weight: 700; color: {color}; background: transparent; letter-spacing: 2px;"
        )
        self._bounce_animation()

    def set_state(self, text: str = "准备点名", sub: str = "点击下方按钮开始", color: str = "#0051D5"):
        """设置静态状态"""
        self.title_label.setText(text)
        self.sub_label.setText(sub)
        n = len(text)
        if n <= 2:
            font_size = 72
        elif n <= 3:
            font_size = 60
        elif n <= 4:
            font_size = 50
        elif n <= 6:
            font_size = 40
        elif n <= 8:
            font_size = 32
        else:
            font_size = 26
        self.title_label.setStyleSheet(
            f"font-size: {font_size}px; font-weight: 700; color: {color}; background: transparent; letter-spacing: 2px;"
        )

    def set_sub_message(self, message: str):
        """仅更新副标题文字"""
        self.sub_label.setText(message)
        self._fade_in_sub()

    def _bounce_animation(self):
        """弹跳动画 - 遵守全局动画开关"""
        if not AnimationManager.is_enabled():
            return
        anim = QPropertyAnimation(self.title_label, b"geometry")
        anim.setDuration(550)
        rect = self.title_label.geometry()
        anim.setStartValue(rect)
        anim.setKeyValueAt(0.25, QRect(rect.x() - 5, rect.y() - 7, rect.width() + 10, rect.height() + 14))
        anim.setKeyValueAt(0.55, QRect(rect.x() - 2, rect.y() - 3, rect.width() + 4, rect.height() + 6))
        anim.setEndValue(rect)
        anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        anim.start()
        self._bounce_anim = anim

    def _fade_in_sub(self):
        """副标题淡入效果"""
        if not AnimationManager.is_enabled():
            return
        effect = self.sub_label.graphicsEffect()
        if effect is None:
            from PyQt6.QtWidgets import QGraphicsOpacityEffect
            effect = QGraphicsOpacityEffect(self.sub_label)
            self.sub_label.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.3)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._fade_anim = anim


class SidebarButton(QPushButton):
    """侧边栏按钮 - Apple风格列表按钮，左侧带 Lucide SVG 图标"""

    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 16, 0)
        layout.setSpacing(10)

        # 左侧 Lucide SVG 图标（带淡蓝底色圆角容器）
        self.icon_label = icon_label(
            icon_name, size=26, color=PRIMARY, bg_color=PRIMARY_ULTRALIGHT,
            radius=7, parent=self
        )

        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("""
            color: #6E6E73;
            background: transparent;
            font-size: 14px;
            font-weight: 500;
            letter-spacing: 0.5px;
        """)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label, 1)
        layout.addStretch()

        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 0;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: #F2F2F7;
            }}
            QPushButton:checked {{
                background-color: {PRIMARY_ULTRALIGHT};
            }}
            QPushButton:checked QLabel {{
                color: {PRIMARY};
                font-weight: 600;
            }}
        """)


class ActionButton(QPushButton):
    """主操作按钮 - Apple风格填充按钮（支持左侧 Lucide SVG 图标）"""

    def __init__(self, icon_name: str, text: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_lbl = None
        if icon_name:
            self._icon_lbl = icon_label(
                icon_name, size=20, color="#FFFFFF", bg_color=None,
                radius=0, parent=self
            )
            layout.addWidget(self._icon_lbl)

        self._text_lbl = QLabel(text)
        self._text_lbl.setStyleSheet(
            "color: #FFFFFF; background: transparent; font-size: 15px; font-weight: 600;"
        )
        layout.addWidget(self._text_lbl)

        self._apply_style(color)

    def setText(self, text: str):
        if getattr(self, "_text_lbl", None) is not None:
            self._text_lbl.setText(text)
        else:
            super().setText(text)

    def text(self) -> str:
        if getattr(self, "_text_lbl", None) is not None:
            return self._text_lbl.text()
        return super().text()

    def _apply_style(self, color: str):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {self._darken(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken2(color)};
            }}
            QPushButton:disabled {{
                background-color: #C7C7CC;
                color: #FFFFFF;
            }}
        """)

    def _darken(self, color: str) -> str:
        color_map = {
            PRIMARY: "#0051D5",
            ACCENT: "#8944AB",
            SECONDARY: "#248A3D",
            DANGER: "#D70015",
        }
        return color_map.get(color, color)

    def _darken2(self, color: str) -> str:
        color_map = {
            PRIMARY: "#003F99",
            ACCENT: "#6B348A",
            SECONDARY: "#1A6B2E",
            DANGER: "#A80012",
        }
        return color_map.get(color, color)


class NameTagWidget(QFrame):
    """名单标签组件"""

    delete_clicked = pyqtSignal(int)

    def __init__(self, name: str, index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("nameTag")
        self.index = index
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 8, 4)
        layout.setSpacing(8)

        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(
            "color: #1D4ED8; font-size: 13px; font-weight: 500; background: transparent;"
        )

        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #93C5FD;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #EF4444;
                background: #FEE2E2;
            }
        """)
        close_btn.clicked.connect(lambda: self.delete_clicked.emit(self.index))

        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(close_btn)

        self.setStyleSheet("""
            QFrame#nameTag {
                background-color: #EFF6FF;
                border: 1px solid #DBEAFE;
                border-radius: 17px;
            }
            QFrame#nameTag:hover {
                background-color: #DBEAFE;
                border: 1px solid #93C5FD;
            }
        """)


class SettingsRow(QFrame):
    """设置行 - SVG 图标 + 标签 + 控件"""

    def __init__(self, icon_name: str, label: str, widget: QWidget, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        # 左侧 Lucide SVG 图标（淡蓝圆角容器）
        ico = icon_label(
            icon_name, size=28, color=PRIMARY, bg_color="#EFF6FF",
            radius=8, parent=self
        )

        # 标签
        text_label = QLabel(label)
        text_label.setFixedWidth(80)
        text_label.setStyleSheet("color: #334155; font-size: 14px; font-weight: 500;")

        layout.addWidget(ico)
        layout.addWidget(text_label)
        layout.addWidget(widget, 1)


# ========== 主窗口 ==========

class MainWindow(QWidget):
    """主窗口 - 侧边栏 + 内容区"""

    WINDOW_WIDTH = 880
    WINDOW_HEIGHT = 640

    def __init__(self):
        super().__init__()
        # 引擎
        self.name_manager = NameListManager()
        self.history_manager = HistoryManager()
        self.settings_manager = SettingsManager()
        self.picker_engine = PickerEngine(
            self.name_manager, self.history_manager, self.settings_manager
        )
        self.tts_engine = TTSEngine()

        # 状态
        self._is_rolling = False
        self._is_group_rolling = False
        self._rolling_timer = None
        self._rolling_index = 0
        self._rolling_sequence = []
        self._is_batch_rolling = False
        self._batch_rolling_timer = None
        self._batch_results = []
        self._batch_index = 0

        self._init_ui()
        self._apply_styles()
        self._refresh_name_list()
        self._refresh_history_table()

        # 应用动画设置
        AnimationManager.apply_from_settings(self.settings_manager)

        # 数据订阅：当名单/历史/设置变化时，UI自动同步
        self.name_manager.changed.connect(self._on_data_changed)
        self.history_manager.changed.connect(self._on_data_changed)
        self.settings_manager.changed.connect(self._on_settings_changed_external)

        # 启动时：若已有下载好的更新包，先提示重启；否则延迟检查更新
        QTimer.singleShot(800, self._check_pending_update_on_startup)
        if self.settings_manager.get("auto_check_update", True):
            QTimer.singleShot(3500, self._silent_check_update)

    def _on_data_changed(self):
        """数据（名单/历史）变化：刷新计数显示 + 历史表 + 名单列表"""
        self._refresh_count_label()
        if hasattr(self, 'history_table') and self.history_table is not None:
            self._refresh_history_table()
        if hasattr(self, 'name_list') and self.name_list is not None:
            self._refresh_name_list()

    def _on_settings_changed_external(self):
        """设置变化：仅刷新计数显示（避免滑块值循环设置）"""
        self._refresh_count_label()

    def _refresh_count_label(self):
        """更新剩余/总人数显示"""
        remaining, total = self.picker_engine.get_counts()
        if hasattr(self, 'count_label') and self.count_label is not None:
            self.count_label.setText(f"剩余 {remaining} / 总 {total} 人")

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("闻铎点名器")
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.setMinimumSize(800, 600)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )

        # 统一应用图标（左上角标题栏 + 任务栏 + ALT+TAB）
        # 优先用 ICO（已居中裁剪为正方形多尺寸，避免 Qt 对 565x648 PNG 拉伸变形）
        icon_path = _resolve_asset("assets/app_icon.ico")
        if not (icon_path and os.path.exists(icon_path)):
            icon_path = _resolve_asset("assets/icons/app_icon.png")
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 主水平布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧栏
        main_layout.addWidget(self._build_sidebar())

        # 右侧内容区
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background-color: {BG_MAIN};")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self._build_topbar())
        right_layout.addWidget(self._build_content_stack(), 1)

        main_layout.addWidget(right_panel, 1)

        self._center_window()

    def _build_title_bar(self) -> QWidget:
        """自定义顶部标题栏：logo + 名称 + 自定义最小/最大/关闭按钮，支持拖动"""
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setObjectName("customTitleBar")
        bar.setStyleSheet("""
            QWidget#customTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 6, 0)
        layout.setSpacing(10)

        # 图标：应用图标（SVG/ICO 优先，缺失时回退字母）
        icon_lbl = self._make_app_icon_label(size=28)
        layout.addWidget(icon_lbl)

        # 应用名
        title_lbl = QLabel("闻铎点名器")
        title_lbl.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #1E3A8A; background: transparent; letter-spacing: 1px;"
        )
        layout.addWidget(title_lbl)
        layout.addStretch()

        # 自定义窗口控制按钮（合并为一个组件以保持一致风格）
        self._title_bar_buttons = self._build_window_controls()
        layout.addWidget(self._title_bar_buttons)

        # 支持拖动
        self._drag_pos = None
        self._is_maximized = False
        bar.mousePressEvent = self._title_bar_mouse_press
        bar.mouseMoveEvent = self._title_bar_mouse_move
        bar.mouseDoubleClickEvent = self._title_bar_mouse_double_click
        # 空白处也能拖
        title_lbl.mousePressEvent = self._title_bar_mouse_press
        title_lbl.mouseMoveEvent = self._title_bar_mouse_move
        icon_lbl.mousePressEvent = self._title_bar_mouse_press
        icon_lbl.mouseMoveEvent = self._title_bar_mouse_move

        return bar

    def _build_window_controls(self) -> QWidget:
        """最小化/最大化/关闭按钮"""
        box = QWidget()
        box.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        def make_btn(symbol: str, hover_bg: str, hover_fg: str = "#1E293B", base_bg: str = "transparent"):
            btn = QPushButton(symbol)
            btn.setFixedSize(36, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {base_bg};
                    color: #64748B;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 700;
                    font-family: "Segoe UI Symbol", "Microsoft YaHei", "Arial";
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                    color: {hover_fg};
                }}
            """)
            return btn

        self.btn_min = make_btn("—", "#F1F5F9")
        self.btn_min.clicked.connect(self.showMinimized)

        self.btn_max = make_btn("▢", "#F1F5F9")
        self.btn_max.clicked.connect(self._toggle_max_restore)

        self.btn_close = make_btn("×", "#EF4444", "#FFFFFF")
        self.btn_close.clicked.connect(self.close)

        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(self.btn_close)
        return box

    def _toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
            self._is_maximized = False
        else:
            self.showMaximized()
            self._is_maximized = True

    def _title_bar_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 双击由 doubleClick 接管；单击记录位置用于拖动
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if self.isMaximized():
                self.showNormal()
                # 重新计算拖动锚点
                self._drag_pos = event.globalPosition().toPoint() - QPoint(20, 12)
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def _title_bar_mouse_double_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_max_restore()
            event.accept()

    def _build_topbar(self) -> QWidget:
        """内容区顶部：左侧"置顶"按钮 + 右侧"关于"按钮。
        位置调整：置顶按钮向左移（不再紧贴右上角），右侧新增"关于"。
        """
        topbar = QWidget()
        topbar.setFixedHeight(48)
        topbar.setStyleSheet(f"background-color: {BG_MAIN};")

        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        # 左侧：置顶按钮（带 pin SVG 图标）
        self.always_top_btn = QPushButton(" 置顶")
        self.always_top_btn.setFixedHeight(32)
        self.always_top_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.always_top_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
                padding: 0 14px 0 10px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #1E293B;
                border: 1px solid #CBD5E1;
            }
        """)
        pin_pix = render_icon("pin", size=16, color="#475569")
        if pin_pix and not pin_pix.isNull():
            self.always_top_btn.setIcon(QIcon(pin_pix))
            self.always_top_btn.setIconSize(QSize(16, 16))
        self.always_top_btn.clicked.connect(self._toggle_always_on_top)
        layout.addWidget(self.always_top_btn)

        # 中间：主页标题
        self.header_title = QLabel("主页")
        self.header_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        layout.addWidget(self.header_title)
        layout.addStretch()

        # 右侧：重启更新按钮（有已下载的更新包时显示）
        self.restart_update_btn = QPushButton(" 重启更新")
        self.restart_update_btn.setFixedHeight(32)
        self.restart_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restart_update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: #FFFFFF;
                border: none;
                border-radius: 16px;
                padding: 0 14px 0 10px;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {PRIMARY_DARK};
            }}
        """)
        restart_pix = render_icon("rotate-cw", size=16, color="#FFFFFF")
        if restart_pix and not restart_pix.isNull():
            self.restart_update_btn.setIcon(QIcon(restart_pix))
            self.restart_update_btn.setIconSize(QSize(16, 16))
        self.restart_update_btn.clicked.connect(self._restart_to_update)
        self.restart_update_btn.hide()
        layout.addWidget(self.restart_update_btn)

        # 右侧：设置按钮
        self.settings_btn = QPushButton(" 设置")
        self.settings_btn.setFixedHeight(32)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
                padding: 0 14px 0 10px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #1E293B;
                border: 1px solid #CBD5E1;
            }
        """)
        settings_pix = render_icon("settings", size=16, color="#475569")
        if settings_pix and not settings_pix.isNull():
            self.settings_btn.setIcon(QIcon(settings_pix))
            self.settings_btn.setIconSize(QSize(16, 16))
        self.settings_btn.clicked.connect(self._show_settings_dialog)
        layout.addWidget(self.settings_btn)

        # 右侧：关于按钮
        self.about_btn = QPushButton(" 关于")
        self.about_btn.setFixedHeight(32)
        self.about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
                padding: 0 14px 0 10px;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #1E293B;
                border: 1px solid #CBD5E1;
            }
        """)
        info_pix = render_icon("info", size=16, color="#475569")
        if info_pix and not info_pix.isNull():
            self.about_btn.setIcon(QIcon(info_pix))
            self.about_btn.setIconSize(QSize(16, 16))
        self.about_btn.clicked.connect(self._show_about_page)
        layout.addWidget(self.about_btn)

        return topbar

    def _make_icon_badge(self, letter: str, color: str = PRIMARY,
                         bg_color: str = PRIMARY_ULTRALIGHT, size: int = 32) -> QLabel:
        """构造一个圆角英文首字母色块图标（兜底）。"""
        lbl = QLabel(letter)
        lbl.setFixedSize(size, size)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"""
            background-color: {bg_color};
            color: {color};
            border-radius: {size // 4}px;
            font-size: {size // 2 - 2}px;
            font-weight: 700;
            font-family: "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
        """)
        return lbl

    def _make_app_icon_label(self, size: int = 28) -> QLabel:
        """构造标题栏应用图标：优先使用 assets/app_icon.ico，缺失时回退 Lucide bell。"""
        icon_path = _resolve_asset("assets/app_icon.ico")
        if icon_path and os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                lbl = QLabel()
                lbl.setFixedSize(size, size)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("background: transparent;")
                lbl.setPixmap(
                    pix.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return lbl

        # 回退：Lucide bell SVG
        return icon_label("bell", size=size, color=PRIMARY, bg_color=None, radius=0, parent=self)

    def _make_row_icon(self, rel_path: str, fallback_letter: str) -> QWidget:
        """构造一个设置行左侧的图标块：
        - 优先加载 rel_path（PNG/JPG），无背景容器
        - 缺失时退回到圆角色块 + 英文首字母
        """
        path = _resolve_asset(rel_path)
        if path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                lbl = QLabel()
                lbl.setFixedSize(32, 32)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("background: transparent;")
                lbl.setPixmap(
                    pix.scaled(
                        28, 28,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return lbl
        return self._make_icon_badge(fallback_letter or "?")

    def _build_sidebar(self) -> QWidget:
        """构建左侧栏"""
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {WHITE}; border-right: 1px solid {NEUTRAL_5};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 0, 16, 16)
        layout.setSpacing(0)

        # Logo 区（优先加载用户提供的 app_brand.png，整张图作为侧边栏顶部品牌区）
        logo_widget = QWidget()
        logo_widget.setStyleSheet("background: transparent;")
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(0, 20, 0, 8)
        logo_layout.setSpacing(0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 把你放在 assets/icons/ 下的那张（博士帽 + 闻铎点名器）作为左上角图
        brand_candidates = [
            _resolve_asset("assets/icons/app_brand.png"),
        ]
        chosen_brand = None
        for p in brand_candidates:
            if p and os.path.exists(p):
                chosen_brand = p
                break

        if chosen_brand:
            brand_pixmap = QPixmap(chosen_brand)
            if not brand_pixmap.isNull():
                # 按原图比例显示，不放大
                logo_icon = QLabel()
                logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_icon.setStyleSheet("background: transparent; border: none; margin: 0; padding: 0;")
                logo_icon.setPixmap(
                    brand_pixmap.scaled(
                        140, 180,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                logo_layout.addWidget(logo_icon)
                layout.addWidget(logo_widget)
            else:
                chosen_brand = None

        if not chosen_brand:
            # 兜底：应用图标 + 标题
            logo_icon = self._make_app_icon_label(size=56)
            logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

            logo_title = QLabel("闻铎点名器")
            logo_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1E3A8A; background: transparent;")

            logo_sub = QLabel("高效·公平·便捷")
            logo_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_sub.setStyleSheet("font-size: 11px; color: #94A3B8; background: transparent; letter-spacing: 2px;")

            logo_layout.addWidget(logo_icon)
            logo_layout.addWidget(logo_title)
            logo_layout.addWidget(logo_sub)

            layout.addWidget(logo_widget)

        # 分隔
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #E2E8F0; max-height: 1px; border: none;")
        layout.addWidget(line)

        # 导航按钮
        layout.addSpacing(16)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.nav_settings = SidebarButton("home", "主页")
        self.nav_settings.setChecked(True)
        self.nav_names = SidebarButton("users", "名单")
        self.nav_history = SidebarButton("history", "历史")

        self.nav_group.addButton(self.nav_settings, 0)
        self.nav_group.addButton(self.nav_names, 1)
        self.nav_group.addButton(self.nav_history, 2)

        self.nav_settings.clicked.connect(lambda: self._switch_page(0))
        self.nav_names.clicked.connect(lambda: self._switch_page(1))
        self.nav_history.clicked.connect(lambda: self._switch_page(2))

        layout.addWidget(self.nav_settings)
        layout.addSpacing(6)
        layout.addWidget(self.nav_names)
        layout.addSpacing(6)
        layout.addWidget(self.nav_history)

        # 弹性空间
        layout.addStretch()

        # 底部装饰 + 版本
        # 左下角品牌区：图 + 版本 + 版权
        bottom_widget = QWidget()
        bottom_widget.setStyleSheet("background: transparent;")
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 12, 0, 8)
        bottom_layout.setSpacing(8)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 装饰图标（优先 ballot_box.png → 缺省 package.png → 兜底 🗳）
        # 显示更大更饱满，并确保白底图与侧边栏白色背景无缝融合（无多余容器边距）
        deco = QLabel()
        deco.setAlignment(Qt.AlignmentFlag.AlignCenter)
        deco.setStyleSheet("background: transparent; border: none; margin: 0; padding: 0;")

        candidate_paths = [
            _resolve_asset("assets/icons/ballot_box.png"),
            _resolve_asset("assets/icons/package.png"),
        ]

        chosen_path = None
        for p in candidate_paths:
            if p and os.path.exists(p):
                chosen_path = p
                break

        if chosen_path:
            pixmap = QPixmap(chosen_path)
            if not pixmap.isNull():
                deco.setPixmap(
                    pixmap.scaled(
                        170, 150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                deco = icon_label("sparkles", size=56, color=PRIMARY_LIGHT, bg_color=None, radius=0, parent=bottom_widget)
        else:
            deco = icon_label("sparkles", size=56, color=PRIMARY_LIGHT, bg_color=None, radius=0, parent=bottom_widget)
        bottom_layout.addWidget(deco)

        version = QLabel(CURRENT_VERSION)
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(f"color: {TEXT_TERTIARY}; font-size: 11px; background: transparent; font-weight: 500;")
        bottom_layout.addWidget(version)

        copyright_lbl = QLabel("@2026 Tix comin 开发")
        copyright_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_lbl.setStyleSheet(f"color: {NEUTRAL_4}; font-size: 10px; background: transparent; letter-spacing: 1px;")
        bottom_layout.addWidget(copyright_lbl)

        layout.addWidget(bottom_widget)

        return sidebar

    def _build_content_stack(self) -> QWidget:
        """构建内容区 - 包含三个页面"""
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {BG_MAIN};")

        # 三个页面
        self.page_settings = self._build_settings_page()
        self.page_names = self._build_names_page()
        self.page_history = self._build_history_page()
        self.page_group = self._build_group_page()

        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_names)
        self.stack.addWidget(self.page_history)
        self.stack.addWidget(self.page_group)

        return self.stack

    def _build_settings_page(self) -> QWidget:
        """设置页 - 一屏内完整展示（无需滚动）"""
        # 整个 settings 页用滚动区包裹，避免窗口缩小时内容被裁掉
        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer_scroll.setObjectName("settingsPageScroll")
        outer_scroll.setStyleSheet("""
            QScrollArea#settingsPageScroll {
                border: none;
                background: transparent;
            }
        """)

        page = QWidget()
        outer_scroll.setWidget(page)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # 显示卡片（恢复大版本）
        self.display_card = DisplayCard()
        self.display_card.setFixedHeight(180)
        self.display_card.title_label.setStyleSheet(
            "font-size: 52px; font-weight: 900; color: #1E3A8A; background: transparent; letter-spacing: 3px;"
        )
        layout.addWidget(self.display_card)

        # 三个操作按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.start_btn = ActionButton("play", "开始点名", PRIMARY)
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self._toggle_rolling)

        self.batch_btn = ActionButton("users", "批量抽取", ACCENT)
        self.batch_btn.setFixedHeight(44)
        self.batch_btn.clicked.connect(self._do_batch_pick)

        self.group_btn = ActionButton("group", "抽组", SECONDARY)
        self.group_btn.setFixedHeight(44)
        self.group_btn.clicked.connect(self._show_group_page)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.batch_btn)
        btn_row.addWidget(self.group_btn)

        layout.addLayout(btn_row)

        # 剩余/总人数
        self.count_label = QLabel("剩余 0 / 总 0 人")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.count_label.setStyleSheet(
            "color: #475569; font-size: 14px; font-weight: 600; padding: 6px; background: transparent;"
        )
        self._refresh_count_label()
        layout.addWidget(self.count_label)

        # 设置卡片（占满剩余空白）
        settings_outer = QFrame()
        settings_outer.setObjectName('settingsOuter')
        settings_outer.setStyleSheet("""
            QFrame#settingsOuter {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }}
        """)
        sc_layout = QVBoxLayout(settings_outer)
        sc_layout.setContentsMargins(20, 16, 20, 20)
        sc_layout.setSpacing(12)

        # 标题
        sc_title = QLabel("点名设置")
        sc_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #475569; background: transparent;")
        sc_layout.addWidget(sc_title)

        # 速度设置
        speed_widget = QWidget()
        speed_widget.setStyleSheet("background: transparent;")
        speed_layout = QHBoxLayout(speed_widget)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(12)

        speed_icon = icon_label("gauge", size=28, color=PRIMARY, bg_color="#EFF6FF", radius=8, parent=speed_widget)
        speed_layout.addWidget(speed_icon)

        speed_label = QLabel("点名速度")
        speed_label.setFixedWidth(80)
        speed_label.setStyleSheet("color: #334155; font-size: 14px;")
        speed_layout.addWidget(speed_label)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 30)
        self.speed_slider.setValue(self.settings_manager.speed)
        self.speed_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: #E2E8F0;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 18px;
                height: 18px;
                margin: -6px 0;
                background: {PRIMARY};
                border-radius: 9px;
                border: 2px solid white;
            }}
            QSlider::sub-page:horizontal {{
                background: {PRIMARY};
                border-radius: 3px;
            }}
        """)
        self.speed_slider.valueChanged.connect(self._on_speed_change)
        speed_layout.addWidget(self.speed_slider, 1)

        self.speed_value = QLabel(f"{self.settings_manager.speed} 人/秒")
        self.speed_value.setStyleSheet("color: #3B82F6; font-weight: 600; min-width: 70px; font-size: 13px;")
        speed_layout.addWidget(self.speed_value)

        sc_layout.addWidget(speed_widget)

        # 停止时间
        stop_widget = QWidget()
        stop_widget.setStyleSheet("background: transparent;")
        stop_layout = QHBoxLayout(stop_widget)
        stop_layout.setContentsMargins(0, 0, 0, 0)
        stop_layout.setSpacing(12)

        stop_icon = icon_label("timer", size=28, color=PRIMARY, bg_color="#EFF6FF", radius=8, parent=stop_widget)
        stop_layout.addWidget(stop_icon)

        stop_label = QLabel("停止时间")
        stop_label.setFixedWidth(80)
        stop_label.setStyleSheet("color: #334155; font-size: 14px;")
        stop_layout.addWidget(stop_label)

        self.stop_slider = QSlider(Qt.Orientation.Horizontal)
        self.stop_slider.setRange(5, 100)
        self.stop_slider.setValue(int(self.settings_manager.stop_time * 10))
        self.stop_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: #E2E8F0;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 18px;
                height: 18px;
                margin: -6px 0;
                background: {PRIMARY};
                border-radius: 9px;
                border: 2px solid white;
            }}
            QSlider::sub-page:horizontal {{
                background: {PRIMARY};
                border-radius: 3px;
            }}
        """)
        self.stop_slider.valueChanged.connect(self._on_stop_time_change)
        stop_layout.addWidget(self.stop_slider, 1)

        self.stop_value = QLabel(f"{self.settings_manager.stop_time:.1f} 秒")
        self.stop_value.setStyleSheet("color: #3B82F6; font-weight: 600; min-width: 70px; font-size: 13px;")
        stop_layout.addWidget(self.stop_value)

        sc_layout.addWidget(stop_widget)

        # 批量人数
        batch_widget = QWidget()
        batch_widget.setStyleSheet("background: transparent;")
        batch_layout = QHBoxLayout(batch_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        batch_layout.setSpacing(12)

        batch_icon = icon_label("users", size=28, color=PRIMARY, bg_color="#EFF6FF", radius=8, parent=batch_widget)
        batch_layout.addWidget(batch_icon)

        batch_label = QLabel("批量人数")
        batch_label.setFixedWidth(80)
        batch_label.setStyleSheet("color: #334155; font-size: 14px;")
        batch_layout.addWidget(batch_label)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 100)
        self.batch_spin.setValue(self.settings_manager.batch_count)
        self.batch_spin.setFixedWidth(90)
        self.batch_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
                background: white;
            }
            QSpinBox:focus {
                border: 1px solid #3B82F6;
            }
        """)
        self.batch_spin.valueChanged.connect(self._on_batch_count_change)
        batch_layout.addWidget(self.batch_spin)
        batch_layout.addStretch()

        sc_layout.addWidget(batch_widget)

        # 允许重复
        repeat_widget = QWidget()
        repeat_widget.setStyleSheet("background: transparent;")
        repeat_layout = QHBoxLayout(repeat_widget)
        repeat_layout.setContentsMargins(0, 0, 0, 0)
        repeat_layout.setSpacing(12)

        repeat_layout.addSpacing(44)  # 对齐到图标位置

        self.repeat_check = QCheckBox("允许重复抽取（勾选后同一人可被多次抽中）")
        self.repeat_check.setChecked(self.settings_manager.allow_repeat)
        self.repeat_check.setStyleSheet("""
            QCheckBox {
                color: #334155;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.5px solid #CBD5E1;
            }
            QCheckBox::indicator:hover {
                border: 1.5px solid #3B82F6;
            }
            QCheckBox::indicator:checked {
                background-color: #3B82F6;
                border: 1.5px solid #3B82F6;
            }
        """)
        self.repeat_check.stateChanged.connect(self._on_repeat_change)
        repeat_layout.addWidget(self.repeat_check)
        repeat_layout.addStretch()

        sc_layout.addWidget(repeat_widget)

        # 动画效果开关
        anim_widget = QWidget()
        anim_widget.setStyleSheet("background: transparent;")
        anim_layout = QHBoxLayout(anim_widget)
        anim_layout.setContentsMargins(0, 0, 0, 0)
        anim_layout.setSpacing(12)

        anim_icon = icon_label("sparkles", size=28, color=PRIMARY, bg_color="#EFF6FF", radius=8, parent=anim_widget)
        anim_layout.addWidget(anim_icon)

        anim_label = QLabel("丝滑动画")
        anim_label.setFixedWidth(80)
        anim_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 500;")
        anim_layout.addWidget(anim_label)

        anim_desc = QLabel("点名弹跳、窗口过渡等效果")
        anim_desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        anim_layout.addWidget(anim_desc, 1)

        self.anim_toggle = IOSToggle(checked=AnimationManager.is_enabled(), on_color=SECONDARY)
        self.anim_toggle.toggled.connect(self._on_animation_toggle)
        anim_layout.addWidget(self.anim_toggle)

        sc_layout.addWidget(anim_widget)

        # 设置卡片占满剩余空白（stretch=1）
        layout.addWidget(settings_outer, 1)

        # 底部按钮
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.setFixedHeight(42)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #3B82F6;
                border: 1.5px solid #3B82F6;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #EFF6FF;
            }
        """)
        self.reset_btn.clicked.connect(self._reset_to_default)
        bottom_row.addWidget(self.reset_btn, 1)

        self.clear_history_btn = QPushButton("清除历史")
        self.clear_history_btn.setFixedHeight(42)
        self.clear_history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #EF4444;
                border: 1.5px solid #FCA5A5;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                border: 1.5px solid #EF4444;
            }
        """)
        self.clear_history_btn.clicked.connect(self._clear_history)
        bottom_row.addWidget(self.clear_history_btn, 1)

        layout.addLayout(bottom_row)

        return outer_scroll

    def _build_names_page(self) -> QWidget:
        """名单管理页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # 顶部输入区
        input_card = QFrame()
        input_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        ic_layout = QVBoxLayout(input_card)
        ic_layout.setContentsMargins(16, 12, 16, 16)
        ic_layout.setSpacing(10)

        # 输入行
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入姓名，多个用逗号/空格/换行分隔")
        self.name_input.setFixedHeight(38)
        self.name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                background: #F8FAFC;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
                background: white;
            }
        """)
        self.name_input.returnPressed.connect(self._add_names)
        input_row.addWidget(self.name_input, 1)

        add_btn = QPushButton("+ 添加")
        add_btn.setFixedSize(80, 38)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {PRIMARY_DARK};
            }}
        """)
        add_btn.clicked.connect(self._add_names)
        input_row.addWidget(add_btn)

        ic_layout.addLayout(input_row)

        # 操作按钮行
        op_row = QHBoxLayout()
        op_row.setSpacing(8)

        import_btn = QPushButton("导入名单")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet("""
            QPushButton {
                background: #F1F5F9;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #E2E8F0;
            }
        """)
        import_btn.clicked.connect(self._import_names)
        op_row.addWidget(import_btn)

        export_btn = QPushButton("导出名单")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet(import_btn.styleSheet())
        export_btn.clicked.connect(self._export_names)
        op_row.addWidget(export_btn)

        clear_names_btn = QPushButton("清空名单")
        clear_names_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_names_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #EF4444;
                border: 1px solid #FCA5A5;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #FEF2F2;
            }
        """)
        clear_names_btn.clicked.connect(self._clear_names)
        op_row.addWidget(clear_names_btn)

        op_row.addStretch()

        self.name_count_label = QLabel(f"共 0 人")
        self.name_count_label.setStyleSheet("color: #64748B; font-size: 12px; background: transparent;")
        op_row.addWidget(self.name_count_label)

        ic_layout.addLayout(op_row)
        layout.addWidget(input_card)

        # 名单区域
        names_card = QFrame()
        names_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        nc_layout = QVBoxLayout(names_card)
        nc_layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        self.name_grid = QWidget()
        self.name_grid.setStyleSheet("background: transparent;")
        self.name_grid_layout = QGridLayout(self.name_grid)
        self.name_grid_layout.setContentsMargins(4, 4, 4, 4)
        self.name_grid_layout.setSpacing(8)
        self.name_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.name_grid)

        nc_layout.addWidget(scroll)
        layout.addWidget(names_card, 1)

        return page

    def _build_history_page(self) -> QWidget:
        """历史记录页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # 历史卡片
        history_card = QFrame()
        history_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        hc_layout = QVBoxLayout(history_card)
        hc_layout.setContentsMargins(0, 0, 0, 0)
        hc_layout.setSpacing(0)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["时间", "类型", "结果"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setShowGrid(False)
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #E2E8F0;
                font-weight: 600;
                color: #475569;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid #F1F5F9;
            }
            QTableWidget::item:selected {
                background-color: #EFF6FF;
                color: #1E40AF;
            }
        """)

        self._refresh_history_table()
        hc_layout.addWidget(self.history_table)
        layout.addWidget(history_card, 1)

        return page

    def _build_group_page(self) -> QWidget:
        """抽组专用页 - 包含显示卡片、抽组设置、开始抽组按钮"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 返回按钮行
        back_row = QHBoxLayout()
        back_row.setSpacing(8)

        self.group_back_btn = QPushButton("返回")
        self.group_back_btn.setFixedHeight(36)
        self.group_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_back_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #1E293B;
            }
        """)
        self.group_back_btn.clicked.connect(self._show_settings_page)
        back_row.addWidget(self.group_back_btn)
        back_row.addStretch()

        layout.addLayout(back_row)

        # 显示卡片（复用 DisplayCard）
        self.group_display_card = DisplayCard()
        self.group_display_card.set_state("准备抽组", "设置范围后点击开始", SECONDARY)
        layout.addWidget(self.group_display_card)

        # 抽组设置卡片
        settings_card = QFrame()
        settings_card.setObjectName("groupSettingsCard")
        settings_card.setStyleSheet("""
            QFrame#groupSettingsCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        sc_layout = QVBoxLayout(settings_card)
        sc_layout.setContentsMargins(20, 16, 20, 20)
        sc_layout.setSpacing(14)

        # 标题
        sc_title = QLabel("抽组设置")
        sc_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #475569; background: transparent;")
        sc_layout.addWidget(sc_title)

        # 抽组范围
        range_widget = QWidget()
        range_widget.setStyleSheet("background: transparent;")
        range_layout = QHBoxLayout(range_widget)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(12)

        range_icon = icon_label("group", size=28, color=SECONDARY, bg_color="#ECFDF5", radius=8, parent=range_widget)
        range_layout.addWidget(range_icon)

        range_label = QLabel("抽组范围")
        range_label.setFixedWidth(70)
        range_label.setStyleSheet("color: #334155; font-size: 13px;")
        range_layout.addWidget(range_label)

        self.group_start_spin = QSpinBox()
        self.group_start_spin.setRange(1, 100)
        self.group_start_spin.setValue(self.settings_manager.get("group_start", 1))
        self.group_start_spin.setFixedWidth(70)
        self.group_start_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                background: white;
            }
            QSpinBox:focus {
                border: 1px solid #10B981;
            }
        """)
        self.group_start_spin.valueChanged.connect(self._on_group_range_change)
        range_layout.addWidget(self.group_start_spin)

        to_label = QLabel("to")
        to_label.setStyleSheet("color: #94A3B8; font-size: 13px;")
        range_layout.addWidget(to_label)

        self.group_end_spin = QSpinBox()
        self.group_end_spin.setRange(1, 100)
        self.group_end_spin.setValue(self.settings_manager.get("group_end", 9))
        self.group_end_spin.setFixedWidth(70)
        self.group_end_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                background: white;
            }
            QSpinBox:focus {
                border: 1px solid #10B981;
            }
        """)
        self.group_end_spin.valueChanged.connect(self._on_group_range_change)
        range_layout.addWidget(self.group_end_spin)
        range_layout.addStretch()

        sc_layout.addWidget(range_widget)

        # 抽组是否重复
        group_repeat_widget = QWidget()
        group_repeat_widget.setStyleSheet("background: transparent;")
        group_repeat_layout = QHBoxLayout(group_repeat_widget)
        group_repeat_layout.setContentsMargins(0, 0, 0, 0)
        group_repeat_layout.setSpacing(12)

        group_repeat_layout.addSpacing(40)  # 对齐到图标位置

        self.group_repeat_check = QCheckBox("允许重复抽组（勾选后同一组可被多次抽中）")
        self.group_repeat_check.setChecked(self.settings_manager.get("group_allow_repeat", False))
        self.group_repeat_check.setStyleSheet("""
            QCheckBox {
                color: #334155;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.5px solid #CBD5E1;
            }
            QCheckBox::indicator:hover {
                border: 1.5px solid #10B981;
            }
            QCheckBox::indicator:checked {
                background-color: #10B981;
                border: 1.5px solid #10B981;
            }
        """)
        self.group_repeat_check.stateChanged.connect(self._on_group_repeat_change)
        group_repeat_layout.addWidget(self.group_repeat_check)
        group_repeat_layout.addStretch()

        sc_layout.addWidget(group_repeat_widget)

        layout.addWidget(settings_card)

        # 开始抽组按钮
        self.group_start_btn = QPushButton("开始抽组")
        self.group_start_btn.setFixedHeight(52)
        self.group_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {SECONDARY}, stop:1 {SECONDARY_DARK});
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34D399, stop:1 {SECONDARY});
            }}
        """)
        self.group_start_btn.clicked.connect(self._toggle_group_rolling)

        layout.addWidget(self.group_start_btn)

        # 清空抽组记录按钮
        self.clear_group_btn = QPushButton("清空抽组记录")
        self.clear_group_btn.setFixedHeight(42)
        self.clear_group_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #EF4444;
                border: 1.5px solid #FCA5A5;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
                border: 1.5px solid #EF4444;
            }
        """)
        self.clear_group_btn.clicked.connect(self._clear_group_history)

        layout.addWidget(self.clear_group_btn)
        layout.addStretch()


        return page

    def _apply_styles(self):
        """应用全局样式"""
        self.setStyleSheet(GLOBAL_STYLE)

    def _center_window(self):
        """窗口居中"""
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.availableGeometry().center()
            self.move(center.x() - self.WINDOW_WIDTH // 2,
                      center.y() - self.WINDOW_HEIGHT // 2)

    def _switch_page(self, index: int):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        titles = ["主页", "名单", "历史", "抽组"]
        self.header_title.setText(titles[index])

    def moveEvent(self, event):
        """主窗口移动时，设置页跟随同步位置。"""
        super().moveEvent(event)
        self._sync_settings_dialog_geometry()

    def resizeEvent(self, event):
        """主窗口尺寸变化时，设置页跟随同步尺寸。"""
        super().resizeEvent(event)
        self._sync_settings_dialog_geometry()

    def _sync_settings_dialog_geometry(self):
        """同步设置对话框与主窗口的位置和尺寸。"""
        dlg = getattr(self, "_settings_dialog", None)
        if dlg and dlg.isVisible():
            geo = self.geometry()
            dlg.setFixedSize(geo.width(), geo.height())
            dlg.move(geo.x(), geo.y())

    def _show_group_page(self):
        """显示抽组专用页面"""
        self.stack.setCurrentIndex(3)
        self.header_title.setText("抽组")
        # 重置抽组按钮状态
        if hasattr(self, "group_btn"):
            self.group_btn.setText("抽组")
            self.group_btn.setStyleSheet("")
        # 重置显示卡片
        if hasattr(self, "group_display_card"):
            self.group_display_card.set_state("准备抽组", "设置范围后点击开始", "#10B981")

    def _show_settings_page(self):
        """返回设置页面"""
        self.stack.setCurrentIndex(0)
        self.header_title.setText("主页")

    # ========== 点名逻辑 ==========

    def _toggle_rolling(self):
        if self._is_rolling:
            self._stop_rolling()
        else:
            self._start_rolling()

    def _start_rolling(self):
        if self.name_manager.count == 0:
            self._show_toast("名单为空，请先添加名字")
            return

        self._is_rolling = True
        self.start_btn.setText("停止点名")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EF4444, stop:1 #DC2626);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #F87171;
            }
        """)

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
            # 滚动中：自适应字号
            n = len(name)
            if n <= 2:
                font_size = 72
            elif n <= 3:
                font_size = 60
            elif n <= 4:
                font_size = 48
            elif n <= 6:
                font_size = 40
            elif n <= 8:
                font_size = 32
            else:
                font_size = 26
            self.display_card.title_label.setText(name)
            self.display_card.title_label.setStyleSheet(
                f"font-size: {font_size}px; font-weight: 900; color: {NEUTRAL}; background: transparent; letter-spacing: 2px;"
            )
        else:
            self._rolling_sequence = self.picker_engine.get_rolling_sequence(100)
            self._rolling_index = 0

    def _stop_rolling(self):
        if self._rolling_timer:
            self._rolling_timer.stop()
            self._rolling_timer = None

        self._is_rolling = False
        self.start_btn.setText("开始点名")
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PRIMARY}, stop:1 {PRIMARY_DARK});
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #60A5FA, stop:1 {PRIMARY});
            }}
        """)

        result = self.picker_engine.pick_single()
        if result:
            self.display_card.set_result(result, f"抽中: {result}", PRIMARY)
            self.tts_engine.speak(result)
            self._refresh_history_table()

    def _do_batch_pick(self):
        """批量抽取：点击一次开始批量朗读，再次点击停止"""
        if self._is_batch_rolling:
            # 正在批量朗读，再次点击 → 停止
            self._stop_batch_rolling()
            return

        if self.name_manager.count == 0:
            self._show_toast("名单为空，请先添加名字")
            return

        count = self.settings_manager.batch_count
        results = self.picker_engine.pick_batch(count)

        if not results:
            self._show_toast("没有可抽取的名字")
            return

        result_text = "、".join(results)
        self.display_card.set_result(results[0], f"批量 {len(results)} 人: {result_text}", ACCENT)
        self._refresh_history_table()

        # 依次朗读
        self._batch_results = list(results)
        self._batch_index = 0
        self._is_batch_rolling = True
        self.batch_btn.setText("停止朗读")
        self.batch_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EF4444, stop:1 #DC2626);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #F87171, stop:1 #EF4444);
            }
        """)
        self._speak_next_batch()

    def _speak_next_batch(self):
        if not self._is_batch_rolling:
            return
        if self._batch_index >= len(self._batch_results):
            self._reset_batch_btn()
            return
        name = self._batch_results[self._batch_index]
        self._batch_index += 1
        # 显示当前朗读的名字
        if self._batch_index <= len(self._batch_results):
            self.display_card.set_result(
                name,
                f"{self._batch_index} / {len(self._batch_results)} · 批量 {len(self._batch_results)} 人",
                ACCENT,
            )
        self.tts_engine.speak(name)
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
        self.batch_btn.setText("批量抽取")
        # 直接用 ActionButton 自带的样式恢复机制
        if hasattr(self.batch_btn, '_apply_style') and hasattr(self.batch_btn, '_color'):
            self.batch_btn._apply_style(self.batch_btn._color)
        else:
            from src.styles import ACCENT as _ACCENT
            self.batch_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {_ACCENT}, stop:1 #7C3AED);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-size: 15px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #A78BFA, stop:1 {_ACCENT});
                }}
            """)

    def _toggle_group_rolling(self):
        if self._is_group_rolling:
            self._stop_group_rolling()
        else:
            self._start_group_rolling()

    def _start_group_rolling(self):
        self._is_group_rolling = True
        self.group_btn.setText("停止抽组")
        self.group_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EF4444, stop:1 #DC2626);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }
        """)

        gs = self.settings_manager.get("group_start", 1)
        ge = self.settings_manager.get("group_end", 9)
        self._rolling_sequence = self.picker_engine.get_rolling_groups(gs, ge, 100)
        self._rolling_index = 0

        interval = max(30, 1000 // self.settings_manager.speed)
        self._rolling_timer = QTimer(self)
        self._rolling_timer.timeout.connect(self._group_rolling_step)
        self._rolling_timer.start(interval)

        stop_ms = int(self.settings_manager.get("group_stop_time", 1.25) * 1000)
        QTimer.singleShot(stop_ms, self._stop_group_rolling)

    def _group_rolling_step(self):
        if not self._is_group_rolling:
            return
        if self._rolling_index < len(self._rolling_sequence):
            text = self._rolling_sequence[self._rolling_index]
            self._rolling_index += 1
            n = len(text)
            if n <= 2:
                font_size = 72
            elif n <= 3:
                font_size = 60
            elif n <= 4:
                font_size = 48
            elif n <= 6:
                font_size = 40
            elif n <= 8:
                font_size = 32
            else:
                font_size = 26
            self.group_display_card.title_label.setText(text)
            self.group_display_card.title_label.setStyleSheet(
                f"font-size: {font_size}px; font-weight: 900; color: {SECONDARY}; background: transparent; letter-spacing: 2px;"
            )
        else:
            gs = self.settings_manager.get("group_start", 1)
            ge = self.settings_manager.get("group_end", 9)
            self._rolling_sequence = self.picker_engine.get_rolling_groups(gs, ge, 100)
            self._rolling_index = 0

    def _stop_group_rolling(self):
        if self._rolling_timer:
            self._rolling_timer.stop()
            self._rolling_timer = None

        self._is_group_rolling = False
        self.group_btn.setText("抽组")
        self.group_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {SECONDARY}, stop:1 {SECONDARY_DARK});
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34D399, stop:1 {SECONDARY});
            }}
        """)

        result = self.picker_engine.pick_group()
        if result is not None:
            result_text = f"{result}组"
            self.group_display_card.set_result(result_text, f"抽中: {result_text}", SECONDARY)
            self.tts_engine.speak(f"第{result}组")
            self._refresh_history_table()

    # ========== 名单管理 ==========

    def _add_names(self):
        text = self.name_input.text().strip()
        if not text:
            return
        names = [n.strip() for n in text.replace("，", ",").replace("、", ",").split(",") if n.strip()]
        added = self.name_manager.add_names(names)
        if added > 0:
            self._show_toast(f"成功添加 {added} 个名字")
            self.name_input.clear()
            self._refresh_name_list()
        else:
            self._show_toast("名字已存在或无效")

    def _remove_name(self, index: int):
        self.name_manager.remove_at(index)
        self._refresh_name_list()

    def _refresh_name_list(self):
        for i in reversed(range(self.name_grid_layout.count())):
            widget = self.name_grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        names = self.name_manager.names
        self.name_count_label.setText(f"共 {len(names)} 人")

        cols = 4
        for i, name in enumerate(names):
            tag = NameTagWidget(name, i)
            tag.delete_clicked.connect(self._remove_name)
            row = i // cols
            col = i % cols
            self.name_grid_layout.addWidget(tag, row, col)

        self.batch_spin.setMaximum(max(1, len(names)))

    def _import_names(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "导入名单", "", "文本文件 (*.txt *.json);;所有文件 (*.*)"
        )
        if filepath:
            try:
                count = self.name_manager.import_from_txt(filepath)
                self._show_toast(f"成功导入 {count} 个名字")
                self._refresh_name_list()
            except Exception as e:
                QMessageBox.warning(self, "导入失败", f"导入名单失败: {e}")

    def _export_names(self):
        if self.name_manager.count == 0:
            self._show_toast("名单为空，无法导出")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出名单", "班级名单.txt", "文本文件 (*.txt)"
        )
        if filepath:
            self.name_manager.export_to_txt(filepath)
            self._show_toast("导出成功")

    def _clear_names(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有名单吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.name_manager.clear_all()
            self._refresh_name_list()

    # ========== 历史记录 ==========

    def _refresh_history_table(self):
        records = self.history_manager.get_recent(50)
        self.history_table.setRowCount(len(records))

        type_map = {"single": "点名", "batch": "批量", "group": "抽组"}
        type_color = {"single": PRIMARY, "batch": ACCENT, "group": SECONDARY}

        for i, record in enumerate(reversed(records)):
            time_item = QTableWidgetItem(record["time"])
            time_item.setForeground(QColor(TEXT_SECONDARY))
            time_item.setFont(QFont("Microsoft YaHei", 11))

            type_text = type_map.get(record["type"], record["type"])
            type_item = QTableWidgetItem(type_text)
            type_item.setForeground(QColor(type_color.get(record["type"], PRIMARY)))
            type_item.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))

            result_item = QTableWidgetItem(record["result"])
            result_item.setForeground(QColor(TEXT_PRIMARY))
            result_item.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))

            self.history_table.setItem(i, 0, time_item)
            self.history_table.setItem(i, 1, type_item)
            self.history_table.setItem(i, 2, result_item)

        self.history_table.scrollToBottom()

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "确认清除", "确定要清除所有历史记录吗？\n清除后将重新开始统计（不重复模式将重置）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.picker_engine.reset_history()
            self._refresh_history_table()
            self._show_toast("历史记录已清除，可以重新抽取")

    def _clear_group_history(self):
        """清空抽组历史记录"""
        reply = QMessageBox.question(
            self, "确认清除", "确定要清除所有抽组记录吗？\n清除后将重新开始不重复抽组。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_manager.clear_groups()
            self._refresh_history_table()
            self._show_toast("抽组记录已清除，可以重新抽取")

    # ========== 设置回调 ==========

    def _on_speed_change(self, value):
        self.settings_manager.speed = value
        self.speed_value.setText(f"{value} 人/秒")

    def _on_stop_time_change(self, value):
        seconds = value / 10.0
        self.settings_manager.stop_time = seconds
        self.settings_manager.set("group_stop_time", seconds)
        self.stop_value.setText(f"{seconds:.1f} 秒")

    def _on_batch_count_change(self, value):
        self.settings_manager.batch_count = value

    def _on_repeat_change(self, state):
        self.settings_manager.allow_repeat = (state == Qt.CheckState.Checked.value)

    def _on_animation_toggle(self, checked: bool):
        """动画开关切换"""
        self.settings_manager.set("enable_animations", checked)
        AnimationManager.set_enabled(checked)
        # 同步刷新悬浮球动画
        try:
            if hasattr(self, '_floating_ball_ref'):
                self._floating_ball_ref.refresh_animations()
        except Exception:
            pass
        # 找到NamePickerApp的floating_ball引用来刷新
        app = QApplication.instance()
        for w in app.topLevelWidgets():
            if hasattr(w, 'floating_ball'):
                try:
                    w.floating_ball.refresh_animations()
                except Exception:
                    pass

    def _on_group_range_change(self):
        self.settings_manager.set("group_start", self.group_start_spin.value())
        self.settings_manager.set("group_end", self.group_end_spin.value())

    def _on_group_repeat_change(self, state):
        self.settings_manager.set("group_allow_repeat", state == Qt.CheckState.Checked.value)

    def _reset_to_default(self):
        reply = QMessageBox.question(
            self, "确认恢复", "确定要恢复所有设置为默认值吗？\n名单也将恢复为默认名单。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_all()
            self.name_manager.reset_to_default()      # 恢复默认名单并保存
            self.history_manager.clear_all()           # 同时清空历史记录（剩余人数归零）
            self._refresh_ui_from_settings()
            self._refresh_name_list()
            self._refresh_count_label()
            self._show_toast("已恢复默认值")

    def _refresh_ui_from_settings(self):
        self.speed_slider.setValue(self.settings_manager.speed)
        self.speed_value.setText(f"{self.settings_manager.speed} 人/秒")
        self.stop_slider.setValue(int(self.settings_manager.stop_time * 10))
        self.stop_value.setText(f"{self.settings_manager.stop_time:.1f} 秒")
        self.batch_spin.setValue(self.settings_manager.batch_count)
        self.repeat_check.setChecked(self.settings_manager.allow_repeat)
        self.group_start_spin.setValue(self.settings_manager.get("group_start", 1))
        self.group_end_spin.setValue(self.settings_manager.get("group_end", 9))
        self.group_repeat_check.setChecked(self.settings_manager.get("group_allow_repeat", False))

    def _toggle_always_on_top(self):
        """切换置顶。**不再调用 setWindowFlags**（会销毁并重建窗口导致闪烁），
        在 Windows 上直接使用 Win32 API `SetWindowPos` 切换 z-order，
        用内部状态变量维护置顶状态，完全无闪烁。
        """
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            hwnd = wintypes.HWND(int(self.winId()))
            # 内部状态：若无则从 windowFlags 判断一次初始值
            if not hasattr(self, "_is_always_on_top"):
                self._is_always_on_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            if self._is_always_on_top:
                # 取消置顶
                user32.SetWindowPos(hwnd, wintypes.HWND(HWND_NOTOPMOST), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                self.always_top_btn.setText("置顶")
                self._is_always_on_top = False
            else:
                # 置顶
                user32.SetWindowPos(hwnd, wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                self.always_top_btn.setText("已置顶")
                self._is_always_on_top = True
        except Exception:
            # 非 Windows：fallback（尽量保留，不调用 setWindowFlags）
            flags = self.windowFlags()
            if flags & Qt.WindowType.WindowStaysOnTopHint:
                self.always_top_btn.setText("置顶")
            else:
                self.always_top_btn.setText("已置顶")

    def _show_settings_dialog(self):
        """打开与主界面同尺寸的全屏设置页：动画开关 + 自动更新 + 版本信息 + 检查更新。
        设置页无标题栏、不可移动、与主窗口位置/尺寸实时同步，视觉上融为一体。"""
        if hasattr(self, "_settings_dialog") and self._settings_dialog and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return

        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
        from PyQt6.QtCore import Qt as _Qt

        class BundledSettingsDialog(QDialog):
            """与主窗口捆绑的设置页：无标题栏、禁止拖动、跟随主窗口移动/缩放。"""

            def __init__(self, parent):
                super().__init__(parent)
                self._parent = parent
                self._dragging = False
                self.setWindowFlags(
                    _Qt.WindowType.Dialog |
                    _Qt.WindowType.FramelessWindowHint
                )
                self.setStyleSheet(f"background-color: {BG_MAIN};")
                self._sync_geometry()

            def _sync_geometry(self):
                """尺寸与位置与主窗口完全一致。"""
                geo = self._parent.geometry()
                self.setFixedSize(geo.width(), geo.height())
                self.move(geo.x(), geo.y())

            def moveEvent(self, event):
                """禁止外部/用户移动；始终跟随主窗口。"""
                if self._parent and not self._dragging:
                    expected = self._parent.geometry().topLeft()
                    if self.pos() != expected:
                        self.move(expected)
                super().moveEvent(event)

            def mousePressEvent(self, event):
                """不允许通过鼠标拖动本窗口。"""
                event.accept()

            def mouseMoveEvent(self, event):
                """不允许通过鼠标拖动本窗口。"""
                event.accept()

        # 设置页与主界面同尺寸、无标题栏、不可拖动
        dlg = BundledSettingsDialog(self)
        dlg.setWindowTitle("设置 · 闻铎点名器")

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶部导航栏（Apple 风格）
        nav = QWidget()
        nav.setFixedHeight(56)
        nav.setStyleSheet(f"background-color: {WHITE}; border-bottom: 1px solid {NEUTRAL_5};")
        nav_lay = QHBoxLayout(nav)
        nav_lay.setContentsMargins(24, 0, 24, 0)
        nav_lay.setSpacing(16)

        back_btn = QPushButton(" 返回")
        back_btn.setFixedHeight(32)
        back_btn.setCursor(_Qt.CursorShape.PointingHandCursor)
        back_btn.setLayoutDirection(_Qt.LayoutDirection.LeftToRight)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_ULTRALIGHT};
                color: {PRIMARY};
                border: none;
                border-radius: 16px;
                padding: 0 14px 0 10px;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{ background-color: #CCE4FF; }}
        """)
        # 左侧 Lucide 返回箭头图标
        back_pix = render_icon("arrow-left", size=18, color=PRIMARY)
        if back_pix and not back_pix.isNull():
            back_btn.setIcon(QIcon(back_pix))
            back_btn.setIconSize(QSize(18, 18))
        back_btn.clicked.connect(dlg.accept)
        nav_lay.addWidget(back_btn)

        nav_title = QLabel("设置")
        nav_title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {TEXT_PRIMARY}; background: transparent;")
        nav_lay.addWidget(nav_title)
        nav_lay.addStretch()
        outer.addWidget(nav)

        # 可滚动内容区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(40, 28, 40, 28)
        c_lay.setSpacing(16)
        c_lay.setAlignment(_Qt.AlignmentFlag.AlignTop)

        # 页面标题
        page_title = QLabel("偏好设置")
        page_title.setStyleSheet(f"font-size: 28px; font-weight: 600; color: {TEXT_PRIMARY}; background: transparent; letter-spacing: -0.5px;")
        c_lay.addWidget(page_title)

        page_sub = QLabel("管理动画、更新与版本信息")
        page_sub.setStyleSheet(f"font-size: 14px; color: {TEXT_SECONDARY}; background: transparent;")
        c_lay.addWidget(page_sub)
        c_lay.addSpacing(8)

        # ---- 动画开关卡片 ----
        anim_row = QWidget()
        anim_row.setStyleSheet(f"background-color: {WHITE}; border-radius: 18px;")
        ar_lay = QHBoxLayout(anim_row)
        ar_lay.setContentsMargins(20, 16, 20, 16)
        ar_lay.setSpacing(16)

        anim_icon = icon_label("sparkles", size=28, color=PRIMARY, bg_color="#EFF6FF", radius=8, parent=anim_row)
        ar_lay.addWidget(anim_icon)

        anim_text = QVBoxLayout()
        anim_text.setSpacing(2)
        at1 = QLabel("丝滑动画")
        at1.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {TEXT_PRIMARY}; background: transparent;")
        at2 = QLabel("点名弹跳、窗口过渡等效果")
        at2.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY}; background: transparent;")
        anim_text.addWidget(at1)
        anim_text.addWidget(at2)
        ar_lay.addLayout(anim_text, 1)

        dlg_anim_toggle = IOSToggle(
            checked=self.settings_manager.get("enable_animations", True),
            on_color=PRIMARY
        )
        def _toggle_anim(checked):
            self.settings_manager.set("enable_animations", checked)
            AnimationManager.set_enabled(checked)
            if hasattr(self, 'anim_toggle') and self.anim_toggle.isChecked() != checked:
                self.anim_toggle.setChecked(checked, animated=False)
            app = QApplication.instance()
            for w in app.topLevelWidgets():
                if hasattr(w, 'floating_ball'):
                    try:
                        w.floating_ball.refresh_animations()
                    except Exception:
                        pass
        dlg_anim_toggle.toggled.connect(_toggle_anim)
        ar_lay.addWidget(dlg_anim_toggle)
        c_lay.addWidget(anim_row)

        # ---- 自动更新开关卡片 ----
        update_row = QWidget()
        update_row.setStyleSheet(f"background-color: {WHITE}; border-radius: 18px;")
        ur_lay = QHBoxLayout(update_row)
        ur_lay.setContentsMargins(20, 16, 20, 16)
        ur_lay.setSpacing(16)

        up_icon = icon_label("rotate-cw", size=28, color=WARNING, bg_color="#FFF3E0", radius=8, parent=update_row)
        ur_lay.addWidget(up_icon)

        up_text = QVBoxLayout()
        up_text.setSpacing(2)
        ut1 = QLabel("自动检查更新")
        ut1.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {TEXT_PRIMARY}; background: transparent;")
        ut2 = QLabel("启动时自动检查新版本")
        ut2.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY}; background: transparent;")
        up_text.addWidget(ut1)
        up_text.addWidget(ut2)
        ur_lay.addLayout(up_text, 1)

        dlg_update_toggle = IOSToggle(
            checked=self.settings_manager.get("auto_check_update", True),
            on_color=PRIMARY
        )
        def _toggle_auto_update(checked):
            self.settings_manager.set("auto_check_update", checked)
        dlg_update_toggle.toggled.connect(_toggle_auto_update)
        ur_lay.addWidget(dlg_update_toggle)
        c_lay.addWidget(update_row)

        # ---- 版本信息卡片 ----
        ver_card = QWidget()
        ver_card.setStyleSheet(f"background-color: {WHITE}; border-radius: 18px;")
        vr_lay = QVBoxLayout(ver_card)
        vr_lay.setContentsMargins(24, 22, 24, 22)
        vr_lay.setSpacing(18)

        ver_header = QHBoxLayout()
        ver_header.setSpacing(16)
        ver_icon = icon_label("info", size=28, color=PRIMARY, bg_color="#EFF6FF", radius=8, parent=ver_card)
        ver_header.addWidget(ver_icon)
        ver_title = QVBoxLayout()
        ver_title.setSpacing(2)
        vt1 = QLabel("版本信息")
        vt1.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {TEXT_PRIMARY}; background: transparent;")
        vt2 = QLabel(f"闻铎点名器 {CURRENT_VERSION}")
        vt2.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY}; background: transparent;")
        ver_title.addWidget(vt1)
        ver_title.addWidget(vt2)
        ver_header.addLayout(ver_title, 1)
        vr_lay.addLayout(ver_header)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {NEUTRAL_5}; max-height: 1px; border: none;")
        vr_lay.addWidget(sep)

        # 检查更新按钮（Apple 胶囊按钮）
        self._dlg_update_btn = QPushButton("检查更新")
        self._dlg_update_btn.setFixedHeight(44)
        self._dlg_update_btn.setCursor(_Qt.CursorShape.PointingHandCursor)
        self._dlg_update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: {WHITE};
                border: none;
                border-radius: 22px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}
            QPushButton:disabled {{
                color: {TEXT_TERTIARY};
                background-color: {NEUTRAL_6};
            }}
        """)
        self._dlg_update_btn.clicked.connect(lambda: self._check_for_updates(self._dlg_update_btn))
        vr_lay.addWidget(self._dlg_update_btn)

        c_lay.addWidget(ver_card)
        c_lay.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._settings_dialog = dlg
        dlg.exec()

    def _show_about_page(self):
        """显示"关于"页面（独立对话框）：
        顶部：打字机效果"中国老师都说好的点名器"
        中部：闻铎的来源与寓意
        底部：开发者 + 建议联系邮箱
        """
        if hasattr(self, "_about_dialog") and self._about_dialog and self._about_dialog.isVisible():
            self._about_dialog.raise_()
            self._about_dialog.activateWindow()
            return

        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt as _Qt, QTimer as _QTimer

        dlg = QDialog(self)
        dlg.setWindowTitle("关于 · 闻铎点名器")
        dlg.setFixedSize(560, 520)
        dlg.setStyleSheet("background-color: #FFFFFF;")

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(32, 28, 32, 24)
        outer.setSpacing(18)

        # 顶部：标题（打字机效果）
        type_label = QLabel("")
        type_label.setAlignment(_Qt.AlignmentFlag.AlignCenter)
        type_label.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {PRIMARY_DARK}; letter-spacing: 2px;")
        outer.addWidget(type_label)

        full_slogan = "中国老师都说好的点名器"
        type_state = {"index": 0}

        def _type_next_char():
            type_state["index"] += 1
            type_label.setText(full_slogan[: type_state["index"]])
            if type_state["index"] >= len(full_slogan):
                type_timer.stop()

        type_timer = _QTimer(dlg)
        type_timer.setInterval(120)
        type_timer.timeout.connect(_type_next_char)
        type_timer.start()

        # 分隔线
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #E2E8F0;")
        outer.addWidget(line)

        # 感谢语
        thanks = QLabel("感谢您的使用")
        thanks.setAlignment(_Qt.AlignmentFlag.AlignCenter)
        thanks.setStyleSheet("font-size: 14px; font-weight: 600; color: #475569; letter-spacing: 2px;")
        outer.addWidget(thanks)

        # 中部：来源与寓意
        meaning = QLabel(
            "闻铎点名器\n\n"
            "古者悬铎于庭，以召万民；今者以器点名，以肃秩序。\n\n"
            "“闻铎”之名，源自《论语》“天将以夫子为木铎”，\n"
            "取其教化传声、闻声而动之意。\n\n"
            "本工具以极简之形，承 “闻令即至、应声报到” 之实，\n"
            "助课堂与会场秩序井然，让每一次点名都成为专注的开端。"
        )
        meaning.setAlignment(_Qt.AlignmentFlag.AlignLeft | _Qt.AlignmentFlag.AlignVCenter)
        meaning.setWordWrap(True)
        meaning.setStyleSheet(
            "font-size: 14px; color: #334155; line-height: 1.9; padding: 12px 4px;"
        )
        outer.addWidget(meaning, 1)

        # 分隔线
        line2 = QLabel()
        line2.setFixedHeight(1)
        line2.setStyleSheet("background-color: #E2E8F0;")
        outer.addWidget(line2)

        # 底部：开发者 + 联系邮箱
        footer = QVBoxLayout()
        footer.setSpacing(4)
        dev_label = QLabel("开发者：Tix comin")
        dev_label.setAlignment(_Qt.AlignmentFlag.AlignCenter)
        dev_label.setStyleSheet("font-size: 13px; color: #475569; font-weight: 600;")
        footer.addWidget(dev_label)

        mail_label = QLabel("建议联系：dwlxjjtz@qq.com")
        mail_label.setAlignment(_Qt.AlignmentFlag.AlignCenter)
        mail_label.setStyleSheet("font-size: 12px; color: #64748B;")
        footer.addWidget(mail_label)
        outer.addLayout(footer)

        # 关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(34)
        close_btn.setCursor(_Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #FFFFFF;
                border-radius: 17px;
                padding: 0 28px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:pressed { background-color: #1E3A8A; }
        """)
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        outer.addLayout(btn_row)

        self._about_dialog = dlg
        dlg.exec()

    def _show_toast(self, message: str, auto_reset_ms: int = 2500):
        """在中央卡片副标题位置显示临时提示，并在指定时间后自动恢复"""
        self.display_card.set_sub_message(message)
        if not hasattr(self, "_toast_timer") or self._toast_timer is None:
            self._toast_timer = QTimer(self)
            self._toast_timer.setSingleShot(True)
            self._toast_timer.timeout.connect(self._reset_toast)
        else:
            self._toast_timer.stop()
        self._toast_timer.start(auto_reset_ms)
        self._toast_default = "点击下方按钮开始"

    def _reset_toast(self):
        """恢复中央卡片副标题为默认提示"""
        default = getattr(self, "_toast_default", "点击下方按钮开始")
        self.display_card.set_sub_message(default)

    def _silent_check_update(self):
        """启动时静默检查更新；若发现新版本则在后台自动下载。"""
        self._silent_check_thread = CheckUpdateThread()
        self._silent_check_thread.finished.connect(self._on_silent_check_finished)
        self._silent_check_thread.start()

    def _on_silent_check_finished(self, info, error_msg):
        """静默检查完成回调：有新版本时自动开始后台下载，无提示打扰。"""
        if error_msg or info is None:
            return
        self._start_silent_download(info)

    def _check_pending_update_on_startup(self):
        """启动时检查是否已有下载好的更新包，若有则提示重启。"""
        state = load_update_state()
        path = state.get("path", "")
        version = state.get("version", "")
        status = state.get("status", "")

        if status == "ready" and path and os.path.exists(path) and version:
            # 若版本不比当前新，则清理旧状态
            if not is_newer_version(version, CURRENT_VERSION):
                clear_update_state()
                return
            self._show_update_ready_prompt(version, path)

    def _start_silent_download(self, info: UpdateInfo):
        """后台静默下载更新包，不显示模态下载窗口。"""
        os.makedirs(get_save_dir(), exist_ok=True)
        save_path = os.path.join(get_save_dir(), info.filename)

        # 记录正在下载的状态
        save_update_state({
            "version": info.tag_name,
            "path": save_path,
            "status": "downloading",
        })

        self._show_toast(f"发现新版本 {info.tag_name}，正在后台下载...", auto_reset_ms=4000)

        if info.parts_urls:
            self._silent_download_thread = DownloadPartsThread(info.parts_urls, save_path)
        else:
            self._silent_download_thread = DownloadThread(info.download_urls, save_path)
        self._silent_download_thread.finished.connect(self._on_silent_download_finished)
        self._silent_download_thread.failed.connect(self._on_silent_download_failed)
        self._silent_download_thread.start()

    def _on_silent_download_finished(self, path: str, url: str):
        """后台下载完成：保存状态并弹出重启提示。"""
        state = load_update_state()
        version = state.get("version", "")
        save_update_state({
            "version": version,
            "path": path,
            "status": "ready",
        })
        self._show_update_ready_prompt(version, path)

    def _on_silent_download_failed(self, error_msg: str):
        """后台下载失败：清空状态并给出轻量提示。"""
        clear_update_state()
        self._show_toast(f"更新下载失败，将下次启动时重试")

    def _show_update_ready_prompt(self, version: str, path: str):
        """显示‘新版本已下载，重启即可更新’提示框，并提供重启按钮。"""
        if getattr(self, "_update_ready_dialog", None) and self._update_ready_dialog.isVisible():
            self._update_ready_dialog.raise_()
            self._update_ready_dialog.activateWindow()
            return

        # 顶部工具栏显示常驻重启按钮
        if getattr(self, "restart_update_btn", None):
            self.restart_update_btn.show()

        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt as _Qt

        dlg = QDialog(self)
        dlg.setWindowTitle("新版本已就绪")
        dlg.setFixedSize(420, 240)
        dlg.setStyleSheet(f"background-color: {BG_MAIN};")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        nav = QWidget()
        nav.setFixedHeight(50)
        nav.setStyleSheet(f"background-color: {WHITE}; border-bottom: 1px solid {NEUTRAL_5};")
        nv = QHBoxLayout(nav)
        nv.setContentsMargins(20, 0, 20, 0)
        t = QLabel("新版本已就绪")
        t.setStyleSheet(f"font-size: 17px; font-weight: 600; color: {TEXT_PRIMARY}; background: transparent;")
        nv.addWidget(t)
        lay.addWidget(nav)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(12)

        ver = QLabel(f"新版本 {version} 已下载完成")
        ver.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {PRIMARY_DARK}; background: transparent;")
        cl.addWidget(ver)

        cur = QLabel(f"当前版本：{CURRENT_VERSION}，重启后即可完成更新")
        cur.setWordWrap(True)
        cur.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY}; background: transparent;")
        cl.addWidget(cur)

        cl.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        later_btn = QPushButton("稍后")
        later_btn.setFixedHeight(36)
        later_btn.setCursor(_Qt.CursorShape.PointingHandCursor)
        later_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {NEUTRAL_6};
                color: {TEXT_PRIMARY};
                border: none;
                border-radius: 18px;
                padding: 0 24px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {NEUTRAL_5}; }}
        """)
        later_btn.clicked.connect(dlg.reject)

        restart_btn = QPushButton("立即重启")
        restart_btn.setFixedHeight(36)
        restart_btn.setCursor(_Qt.CursorShape.PointingHandCursor)
        restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY};
                color: white;
                border: none;
                border-radius: 18px;
                padding: 0 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}
        """)
        def _do_restart():
            dlg.accept()
            self._restart_to_update()
        restart_btn.clicked.connect(_do_restart)

        btn_row.addStretch()
        btn_row.addWidget(later_btn)
        btn_row.addWidget(restart_btn)
        cl.addLayout(btn_row)

        lay.addWidget(content, 1)
        self._update_ready_dialog = dlg
        dlg.exec()

    def _restart_to_update(self):
        """重启以应用已下载的更新：启动安装程序并退出当前程序。"""
        state = load_update_state()
        path = state.get("path", "")
        if not path or not os.path.exists(path):
            self._show_toast("更新包已丢失，将重新检查更新")
            clear_update_state()
            if getattr(self, "restart_update_btn", None):
                self.restart_update_btn.hide()
            return

        install_dir = get_existing_install_dir()
        if not install_dir:
            self._show_toast("未找到安装目录，请手动运行安装包")
            return

        try:
            # 使用 /SILENT /DIR /WAITPID /LAUNCH 让安装程序静默覆盖并重启
            launch_installer(path, install_dir=install_dir, silent=True,
                             wait_pid=os.getpid(), launch=True)
            QApplication.quit()
        except Exception as e:
            QMessageBox.warning(
                self,
                "重启更新失败",
                f"无法启动安装程序：{e}\n\n请手动运行：\n{path}"
            )

    def _check_for_updates(self, button=None):
        """检查更新"""
        self._update_btn_ref = button
        if button is not None:
            button.setEnabled(False)
            button.setText("检查中...")

        self._check_thread = CheckUpdateThread()
        self._check_thread.finished.connect(self._on_check_finished)
        self._check_thread.start()

    def _on_check_finished(self, info, error_msg):
        button = getattr(self, "_update_btn_ref", None)
        if button is not None:
            button.setEnabled(True)
            button.setText("检查更新")
        self._update_btn_ref = None

        if error_msg:
            QMessageBox.warning(
                self,
                "检查更新",
                f"检查更新失败：\n{error_msg}\n\n请检查网络连接后重试。"
            )
            return

        if info is None:
            QMessageBox.information(
                self,
                "检查更新",
                f"当前版本 {CURRENT_VERSION}\n\n已是最新版本！"
            )
            return

        reply = QMessageBox.question(
            self,
            "发现新版本",
            f"发现新版本 {info.tag_name}\n\n{info.body if info.body else '是否现在下载更新？'}\n\n版本大小：{info.size / 1024 / 1024:.1f} MB\n\n是否开始下载？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._start_download(info)

    def _start_download(self, info: UpdateInfo):
        """开始下载更新包"""
        os.makedirs(get_save_dir(), exist_ok=True)
        save_path = os.path.join(get_save_dir(), info.filename)

        self._download_dialog = QDialog(self)
        self._download_dialog.setWindowTitle("下载更新")
        self._download_dialog.setFixedSize(420, 180)
        self._download_dialog.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint
        )

        dlg_layout = QVBoxLayout(self._download_dialog)
        dlg_layout.setContentsMargins(24, 20, 24, 20)
        dlg_layout.setSpacing(12)

        if info.parts_urls:
            title_label = QLabel(f"正在下载 {info.filename}（Gitee 分卷）")
        else:
            title_label = QLabel(f"正在下载 {info.filename}")
        title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E293B;")
        dlg_layout.addWidget(title_label)

        self._download_progress = QProgressBar()
        self._download_progress.setRange(0, 100)
        self._download_progress.setValue(0)
        self._download_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #E2E8F0;
                height: 20px;
                text-align: center;
                font-size: 12px;
                color: #1E293B;
            }
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 6px;
            }
        """)
        dlg_layout.addWidget(self._download_progress)

        self._download_speed_label = QLabel("准备下载...")
        self._download_speed_label.setStyleSheet("color: #64748B; font-size: 12px;")
        dlg_layout.addWidget(self._download_speed_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._cancel_download_btn = QPushButton("取消下载")
        self._cancel_download_btn.setFixedSize(100, 34)
        self._cancel_download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self._cancel_download_btn.clicked.connect(self._cancel_download)
        btn_row.addWidget(self._cancel_download_btn)
        dlg_layout.addLayout(btn_row)

        if info.parts_urls:
            self._download_thread = DownloadPartsThread(info.parts_urls, save_path)
        else:
            self._download_thread = DownloadThread(info.download_urls, save_path)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.speed.connect(self._on_download_speed)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.failed.connect(self._on_download_failed)
        self._download_thread.cancelled.connect(self._on_download_cancelled)
        self._download_thread.start()

        self._download_dialog.exec()

    def _cancel_download(self):
        if hasattr(self, "_download_thread") and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._cancel_download_btn.setEnabled(False)
            self._cancel_download_btn.setText("正在取消...")

    def _on_download_progress(self, pct):
        if hasattr(self, "_download_progress"):
            self._download_progress.setValue(pct)

    def _on_download_speed(self, spd):
        if hasattr(self, "_download_speed_label"):
            if spd > 1024 * 1024:
                spd_str = f"{spd / 1024 / 1024:.1f} MB/s"
            elif spd > 1024:
                spd_str = f"{spd / 1024:.1f} KB/s"
            else:
                spd_str = f"{spd:.0f} B/s"
            self._download_speed_label.setText(f"下载速度：{spd_str}")

    def _on_download_finished(self, path, url):
        if hasattr(self, "_download_dialog"):
            self._download_dialog.accept()

        install_dir = get_existing_install_dir()
        if not install_dir:
            QMessageBox.information(
                self,
                "下载完成",
                f"更新包已下载完成！\n\n文件位置：{path}\n\n未检测到安装目录，请手动运行安装包。"
            )
            return

        reply = QMessageBox.question(
            self,
            "下载完成",
            f"更新包已下载完成！\n\n将安装到：{install_dir}\n\n是否立即安装并重启？\n（安装过程会自动关闭当前程序）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                launch_installer(path, install_dir=install_dir, silent=True,
                                 wait_pid=os.getpid(), launch=True)
                QApplication.quit()
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "启动安装失败",
                    f"启动安装程序失败：{e}\n\n请手动打开下载的文件进行安装：\n{path}"
                )

    def _on_download_failed(self, error_msg):
        if hasattr(self, "_download_dialog"):
            self._download_dialog.reject()

        QMessageBox.warning(
            self,
            "下载失败",
            f"{error_msg}\n\n请检查网络连接后重试。"
        )

    def _on_download_cancelled(self):
        if hasattr(self, "_download_dialog"):
            self._download_dialog.reject()
        self._show_toast("已取消下载")

    def closeEvent(self, event):
        # 关闭窗口时最小化到托盘，而不是退出
        if self._rolling_timer:
            self._rolling_timer.stop()
        self.tts_engine.stop()

        if hasattr(self, "_download_thread") and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait(2000)

        if hasattr(self, "_silent_download_thread") and self._silent_download_thread.isRunning():
            self._silent_download_thread.cancel()
            self._silent_download_thread.wait(2000)

        self.hide()
        event.ignore()
