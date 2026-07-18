"""
UI样式和主题定义 - Apple风格教育主题
闻铎点名器 v2.0.0 - Styles
温润、大方、适合课堂教育场景
"""

# ========== Apple 教育风配色 ==========
# 主色：温润的教育蓝（比科技蓝更柔和）
PRIMARY = "#007AFF"       # Apple Blue
PRIMARY_DARK = "#0051D5"
PRIMARY_LIGHT = "#64D2FF"
PRIMARY_ULTRALIGHT = "#E0F0FF"

# 辅助色：教育友好的活力色
SECONDARY = "#34C759"     # Apple Green - 积极/成功
SECONDARY_DARK = "#248A3D"
ACCENT = "#AF52DE"        # Apple Purple - 创意/活力
ACCENT_DARK = "#8944AB"
WARNING = "#FF9500"       # Apple Orange
DANGER = "#FF3B30"        # Apple Red

# 中性色：温润的灰色系统
NEUTRAL = "#1D1D1F"       # Apple 深灰文字
NEUTRAL_2 = "#424245"
NEUTRAL_3 = "#8E8E93"
NEUTRAL_4 = "#C7C7CC"
NEUTRAL_5 = "#E5E5EA"
NEUTRAL_6 = "#F2F2F7"     # Apple 浅灰背景
BG_MAIN = "#F5F5F7"       # 温暖的米白背景
WHITE = "#FFFFFF"

# 文字色
TEXT_PRIMARY = "#1D1D1F"
TEXT_SECONDARY = "#6E6E73"
TEXT_TERTIARY = "#AEAEB2"
TEXT_WHITE = "#FFFFFF"

# 毛玻璃效果色
GLASS_BG = "rgba(255, 255, 255, 0.72)"
GLASS_BORDER = "rgba(255, 255, 255, 0.3)"

# ========== 全局样式表 ==========
GLOBAL_STYLE = f"""
/* 主窗口 */
QMainWindow {{
    background-color: {BG_MAIN};
}}

/* 卡片/容器 - Apple风格圆角卡片 */
QFrame#card {{
    background-color: {WHITE};
    border-radius: 16px;
    border: none;
}}

/* 按钮通用样式 - Apple 胶囊按钮 */
QPushButton {{
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 14px;
    font-weight: 500;
    border: none;
    font-family: "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
}}

QPushButton:hover {{
    filter: brightness(1.05);
}}

QPushButton:pressed {{
    filter: brightness(0.92);
}}

/* 主按钮 - Apple Blue 填充 */
QPushButton#btnPrimary {{
    background-color: {PRIMARY};
    color: {WHITE};
}}

QPushButton#btnPrimary:hover {{
    background-color: {PRIMARY_DARK};
}}

/* 绿色按钮 */
QPushButton#btnSecondary {{
    background-color: {SECONDARY};
    color: {WHITE};
}}

QPushButton#btnSecondary:hover {{
    background-color: {SECONDARY_DARK};
}}

/* 紫色按钮 */
QPushButton#btnAccent {{
    background-color: {ACCENT};
    color: {WHITE};
}}

QPushButton#btnAccent:hover {{
    background-color: {ACCENT_DARK};
}}

/* 轮廓按钮 */
QPushButton#btnOutline {{
    background-color: transparent;
    color: {PRIMARY};
    border: 1.5px solid {PRIMARY};
}}

QPushButton#btnOutline:hover {{
    background-color: {PRIMARY_ULTRALIGHT};
}}

/* 危险按钮 */
QPushButton#btnDanger {{
    background-color: {DANGER};
    color: {WHITE};
}}

/* 输入框 - Apple风格柔和边框 */
QLineEdit, QSpinBox {{
    border: 1px solid {NEUTRAL_5};
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 14px;
    background-color: {WHITE};
    color: {TEXT_PRIMARY};
    selection-background-color: {PRIMARY_LIGHT};
}}

QLineEdit:focus, QSpinBox:focus {{
    border-color: {PRIMARY};
    outline: none;
}}

/* 滑块 - Apple风格 */
QSlider::groove:horizontal {{
    height: 4px;
    background-color: {NEUTRAL_5};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 24px;
    height: 24px;
    margin: -10px 0;
    background-color: {WHITE};
    border-radius: 12px;
    border: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15), 0 1px 2px rgba(0,0,0,0.1);
}}

QSlider::handle:horizontal:hover {{
    background-color: {PRIMARY_LIGHT};
    transform: scale(1.1);
}}

QSlider::sub-page:horizontal {{
    background-color: {PRIMARY};
    border-radius: 2px;
}}

/* 滚动条 - 极简细条 */
QScrollBar:vertical {{
    width: 6px;
    background: transparent;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background: {NEUTRAL_4};
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {NEUTRAL_3};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    height: 6px;
    background: transparent;
}}

QScrollBar::handle:horizontal {{
    background: {NEUTRAL_4};
    border-radius: 3px;
    min-width: 30px;
}}

/* 复选框 - Apple 风格开关 */
QCheckBox {{
    font-size: 14px;
    color: {TEXT_PRIMARY};
    spacing: 10px;
    font-family: "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 1.5px solid {NEUTRAL_4};
    background-color: {WHITE};
}}

QCheckBox::indicator:hover {{
    border-color: {PRIMARY};
}}

QCheckBox::indicator:checked {{
    background-color: {PRIMARY};
    border-color: {PRIMARY};
    image: none;
}}

/* 标签 */
QLabel#title {{
    font-size: 28px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    letter-spacing: -0.5px;
}}

QLabel#subtitle {{
    font-size: 15px;
    color: {TEXT_SECONDARY};
    font-weight: 400;
}}

/* 分组框 */
QGroupBox {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    border: 1px solid {NEUTRAL_5};
    border-radius: 12px;
    margin-top: 16px;
    padding-top: 24px;
    background-color: {WHITE};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 10px;
    color: {TEXT_SECONDARY};
}}

/* 表格 */
QTableWidget {{
    border: none;
    background-color: {WHITE};
    gridline-color: {NEUTRAL_6};
    font-size: 14px;
    font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei", sans-serif;
}}

QTableWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {NEUTRAL_6};
}}

QTableWidget::item:selected {{
    background-color: {PRIMARY_ULTRALIGHT};
    color: {PRIMARY_DARK};
}}

QHeaderView::section {{
    background-color: {NEUTRAL_6};
    padding: 12px;
    border: none;
    font-weight: 600;
    font-size: 13px;
    color: {TEXT_SECONDARY};
}}

/* TabWidget */
QTabWidget::pane {{
    border: none;
    border-radius: 12px;
    background-color: {WHITE};
}}

QTabBar::tab {{
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
    border: none;
    color: {TEXT_SECONDARY};
    background: transparent;
}}

QTabBar::tab:selected {{
    color: {PRIMARY};
    border-bottom: 2px solid {PRIMARY};
    font-weight: 600;
}}

QTabBar::tab:hover {{
    color: {PRIMARY};
}}

/* 进度条 */
QProgressBar {{
    border: none;
    border-radius: 6px;
    background-color: {NEUTRAL_6};
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {PRIMARY};
    border-radius: 6px;
}}

/* 滚动区域 */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* 消息框 */
QMessageBox {{
    background-color: {WHITE};
}}
"""

# 悬浮球样式 - Apple风格活力球
FLOATING_BALL_STYLE = f"""
QWidget#floatingBall {{
    background: qradialgradient(cx:0.3, cy:0.3, radius:0.8,
        stop:0 #64D2FF, stop:0.4 {PRIMARY}, stop:1 {PRIMARY_DARK});
    border-radius: 30px;
    border: none;
}}

QWidget#floatingBall:hover {{
    background: qradialgradient(cx:0.3, cy:0.3, radius:0.8,
        stop:0 #80DEFF, stop:0.4 #34A7FF, stop:1 {PRIMARY});
}}

QLabel#ballLabel {{
    color: white;
    font-size: 18px;
    font-weight: 600;
    background: transparent;
}}
"""

# 点名显示区域样式 - Apple风格大卡片
DISPLAY_AREA_STYLE = f"""
QFrame#displayArea {{
    background-color: {WHITE};
    border-radius: 20px;
    border: none;
}}

QLabel#displayLabel {{
    font-size: 56px;
    font-weight: 700;
    color: {PRIMARY_DARK};
    background: transparent;
    letter-spacing: 2px;
}}
"""

# 名单标签样式 - Apple 胶囊标签
NAME_TAG_STYLE = f"""
QFrame#nameTag {{
    background-color: {PRIMARY_ULTRALIGHT};
    border-radius: 20px;
    padding: 6px 14px;
}}

QLabel#nameTagLabel {{
    color: {PRIMARY_DARK};
    font-size: 14px;
    font-weight: 500;
}}

QPushButton#nameTagClose {{
    background: transparent;
    color: {PRIMARY_LIGHT};
    font-size: 14px;
    padding: 0px;
    border-radius: 10px;
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
    max-height: 20px;
}}

QPushButton#nameTagClose:hover {{
    color: {DANGER};
    background-color: rgba(255, 59, 48, 0.1);
}}
"""

# 历史记录项样式
HISTORY_ITEM_STYLE = f"""
QFrame#historyItem {{
    background-color: {WHITE};
    border-radius: 12px;
    border: none;
    padding: 12px;
}}

QLabel#historyTime {{
    color: {TEXT_TERTIARY};
    font-size: 12px;
}}

QLabel#historyResult {{
    color: {TEXT_PRIMARY};
    font-size: 15px;
    font-weight: 600;
}}

QLabel#historyType {{
    color: {PRIMARY};
    font-size: 11px;
    background-color: {PRIMARY_ULTRALIGHT};
    border-radius: 6px;
    padding: 3px 8px;
    font-weight: 500;
}}
"""

# 侧边栏样式
SIDEBAR_STYLE = f"""
QWidget#sidebar {{
    background-color: {WHITE};
    border-right: 1px solid {NEUTRAL_5};
}}
"""

# 设置开关样式（iOS风格UISwitch模拟）
TOGGLE_ON_STYLE = f"""
QPushButton {{
    background-color: {SECONDARY};
    border-radius: 15px;
    min-width: 50px;
    max-width: 50px;
    min-height: 30px;
    max-height: 30px;
    text-align: left;
    padding-left: 4px;
    color: white;
    font-size: 16px;
    font-weight: bold;
}}
"""

TOGGLE_OFF_STYLE = f"""
QPushButton {{
    background-color: {NEUTRAL_4};
    border-radius: 15px;
    min-width: 50px;
    max-width: 50px;
    min-height: 30px;
    max-height: 30px;
    text-align: right;
    padding-right: 4px;
    color: white;
    font-size: 16px;
    font-weight: bold;
}}
"""
