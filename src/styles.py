"""
UI样式和主题定义
闻铎点名器 - Styles
"""

# ========== 颜色主题 ==========
PRIMARY = "#3B82F6"       # 主蓝色
PRIMARY_DARK = "#2563EB"
PRIMARY_LIGHT = "#93C5FD"
SECONDARY = "#10B981"     # 绿色
SECONDARY_DARK = "#059669"
ACCENT = "#8B5CF6"        # 紫色
ACCENT_DARK = "#7C3AED"
NEUTRAL = "#1F2937"       # 深灰
NEUTRAL_LIGHT = "#F3F4F6" # 浅灰
WHITE = "#FFFFFF"
DANGER = "#EF4444"        # 红色
WARNING = "#F59E0B"       # 橙色
TEXT_PRIMARY = "#1F2937"
TEXT_SECONDARY = "#6B7280"
TEXT_WHITE = "#FFFFFF"
BG_MAIN = "#F9FAFB"

# 渐变背景
GRADIENT_PRIMARY = f"""
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {PRIMARY}, stop:1 {ACCENT});
"""
GRADIENT_BALL = f"""
    background: qradialgradient(cx:0.35, cy:0.35, radius:0.7,
        stop:0 #60A5FA, stop:0.5 {PRIMARY}, stop:1 {PRIMARY_DARK});
"""

# ========== 全局样式表 ==========
GLOBAL_STYLE = f"""
/* 主窗口 */
QMainWindow {{
    background-color: {BG_MAIN};
}}

/* 卡片/容器 */
QFrame#card {{
    background-color: {WHITE};
    border-radius: 12px;
    border: 1px solid #E5E7EB;
}}

/* 按钮通用样式 */
QPushButton {{
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 600;
    border: none;
}}

QPushButton:hover {{
    filter: brightness(1.1);
}}

QPushButton:pressed {{
    filter: brightness(0.95);
}}

/* 主按钮 */
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
    border: 2px solid {PRIMARY};
}}

QPushButton#btnOutline:hover {{
    background-color: rgba(59, 130, 246, 0.1);
}}

/* 危险按钮 */
QPushButton#btnDanger {{
    background-color: {DANGER};
    color: {WHITE};
}}

/* 输入框 */
QLineEdit, QSpinBox {{
    border: 2px solid #D1D5DB;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    background-color: {WHITE};
}}

QLineEdit:focus, QSpinBox:focus {{
    border-color: {PRIMARY};
}}

/* 滑块 */
QSlider::groove:horizontal {{
    height: 6px;
    background-color: #E5E7EB;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background-color: {PRIMARY};
    border-radius: 9px;
    border: 2px solid {WHITE};
}}

QSlider::handle:horizontal:hover {{
    background-color: {PRIMARY_DARK};
}}

QSlider::sub-page:horizontal {{
    background-color: {PRIMARY};
    border-radius: 3px;
}}

/* 滚动条 */
QScrollBar:vertical {{
    width: 8px;
    background: transparent;
}}

QScrollBar::handle:vertical {{
    background: #D1D5DB;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: #9CA3AF;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* 复选框 */
QCheckBox {{
    font-size: 14px;
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #D1D5DB;
}}

QCheckBox::indicator:checked {{
    background-color: {PRIMARY};
    border-color: {PRIMARY};
}}

/* 标签 */
QLabel#title {{
    font-size: 20px;
    font-weight: 700;
    color: {TEXT_PRIMARY};
}}

QLabel#subtitle {{
    font-size: 14px;
    color: {TEXT_SECONDARY};
}}

/* 分组框 */
QGroupBox {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
}}

/* 表格 */
QTableWidget {{
    border: none;
    background-color: {WHITE};
    gridline-color: #F3F4F6;
    font-size: 13px;
}}

QTableWidget::item {{
    padding: 6px;
}}

QHeaderView::section {{
    background-color: {NEUTRAL_LIGHT};
    padding: 8px;
    border: none;
    font-weight: 600;
    font-size: 13px;
}}

/* TabWidget */
QTabWidget::pane {{
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    background-color: {WHITE};
}}

QTabBar::tab {{
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    border: none;
    border-bottom: 2px solid transparent;
    color: {TEXT_SECONDARY};
}}

QTabBar::tab:selected {{
    color: {PRIMARY};
    border-bottom: 2px solid {PRIMARY};
}}

QTabBar::tab:hover {{
    color: {PRIMARY};
}}
"""

# 悬浮球样式
FLOATING_BALL_STYLE = f"""
QWidget#floatingBall {{
    background: qradialgradient(cx:0.35, cy:0.35, radius:0.7,
        stop:0 #60A5FA, stop:0.4 {PRIMARY}, stop:1 #1D4ED8);
    border-radius: 30px;
    border: 2px solid rgba(255, 255, 255, 0.3);
}}

QWidget#floatingBall:hover {{
    border: 2px solid rgba(255, 255, 255, 0.6);
}}

QLabel#ballLabel {{
    color: white;
    font-size: 18px;
    font-weight: bold;
    background: transparent;
}}
"""

# 点名显示区域样式
DISPLAY_AREA_STYLE = f"""
QFrame#displayArea {{
    background-color: {NEUTRAL_LIGHT};
    border-radius: 12px;
    border: 2px solid #E5E7EB;
}}

QLabel#displayLabel {{
    font-size: 48px;
    font-weight: 800;
    color: {NEUTRAL};
    background: transparent;
}}
"""

# 名单标签样式
NAME_TAG_STYLE = f"""
QFrame#nameTag {{
    background-color: rgba(59, 130, 246, 0.1);
    border-radius: 16px;
    padding: 4px 12px;
}}

QLabel#nameTagLabel {{
    color: {PRIMARY};
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#nameTagClose {{
    background: transparent;
    color: rgba(59, 130, 246, 0.6);
    font-size: 12px;
    padding: 0px;
    border-radius: 8px;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
}}

QPushButton#nameTagClose:hover {{
    color: {DANGER};
}}
"""

# 历史记录项样式
HISTORY_ITEM_STYLE = f"""
QFrame#historyItem {{
    background-color: {WHITE};
    border-radius: 8px;
    border: 1px solid #E5E7EB;
    padding: 8px;
}}

QLabel#historyTime {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

QLabel#historyResult {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#historyType {{
    color: {PRIMARY};
    font-size: 11px;
    background-color: rgba(59, 130, 246, 0.1);
    border-radius: 4px;
    padding: 2px 6px;
}}
"""