'''悬浮球窗口 - Apple风格可吸附屏幕边缘、半隐藏、悬停展开
闻铎点名器 v3.0.0 - Floating Ball'''
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QSize, pyqtSignal, QRect
from PyQt6.QtGui import QMouseEvent, QFont, QPainter, QColor, QLinearGradient, QPen, QRadialGradient

from src.styles import PRIMARY, PRIMARY_DARK, PRIMARY_LIGHT, WHITE
from src.animation_helper import AnimationManager, animate_smooth_move, animate_size, pulse_widget

BALL_SIZE = 56
BALL_EXPANDED = 64
EDGE_PEEK = 12
SNAP_DISTANCE = 60
SNAP_DELAY = 800

class FloatingBall(QWidget):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self._is_dragging = False
        self._has_moved = False
        self._drag_start_pos = None
        self._pulse_animation = None
        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.timeout.connect(self._snap_to_edge)
        self._is_snapped = False
        self._snap_side = 'right'
        self._is_hovering = False
        self._move_anim = None
        self._size_anim = None
        self._current_ball_size = BALL_SIZE
        self._init_ui()
        self._setup_animation()

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setFixedSize(BALL_SIZE, BALL_SIZE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel('闻')
        self.label.setObjectName('ballLabel')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont('PingFang SC', 16, QFont.Weight.DemiBold))
        self.label.setStyleSheet('color: white; background: transparent;')
        layout.addWidget(self.label)
        self.setMouseTracking(True)
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - BALL_SIZE - 8, geo.center().y())

    def _setup_animation(self):
        """根据动画开关决定是否启动呼吸动画"""
        if self._pulse_animation:
            self._pulse_animation.stop()
            self._pulse_animation = None

        if AnimationManager.is_enabled():
            self._pulse_animation = pulse_widget(self, 2800)

    def refresh_animations(self):
        """设置改变时刷新动画状态"""
        self._setup_animation()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width(); h = self.height(); margin = 2
        side = min(w, h) - margin * 2
        radius = side * 0.5

        # 阴影
        painter.setPen(Qt.PenStyle.NoPen)
        shadow = QRadialGradient(w/2 + 2, h/2 + 4, side/2 + 4)
        shadow.setColorAt(0, QColor(0, 0, 0, 50))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(shadow)
        painter.drawEllipse(margin - 2, margin - 1, side + 8, side + 8)

        # 主体渐变
        gradient = QRadialGradient(w*0.35, h*0.3, side*0.7)
        gradient.setColorAt(0, QColor('#64D2FF'))
        gradient.setColorAt(0.5, QColor(PRIMARY))
        gradient.setColorAt(1, QColor(PRIMARY_DARK))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(margin, margin, side, side)

        # 高光
        highlight = QRadialGradient(w*0.3, h*0.25, side*0.35)
        highlight.setColorAt(0, QColor(255, 255, 255, 120))
        highlight.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(highlight)
        painter.drawEllipse(margin, margin, side, side)

        painter.end()

    def _get_screen_rect(self) -> QRect:
        screen = QApplication.screenAt(self.geometry().center())
        if not screen:
            screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

    def _snap_to_edge(self):
        if self._is_dragging:
            return
        screen = self._get_screen_rect()
        pos = self.pos()
        center_y = pos.y() + self.height() // 2
        center_y = max(screen.top() + 20, min(screen.bottom() - 20, center_y))
        mid_x = screen.left() + screen.width() // 2
        if pos.x() + self.width() // 2 < mid_x:
            target_x = screen.left() - self.width() + EDGE_PEEK
            self._snap_side = 'left'
        else:
            target_x = screen.right() - EDGE_PEEK
            self._snap_side = 'right'
        target_pos = QPoint(target_x, center_y - self.height() // 2)
        if AnimationManager.is_enabled():
            animate_smooth_move(self, target_pos, duration=320)
        else:
            self.move(target_pos)
        self._is_snapped = True

    def _expand_from_edge(self):
        if not self._is_snapped:
            return
        screen = self._get_screen_rect()
        pos = self.pos()
        center_y = pos.y() + self.height() // 2
        if self._snap_side == 'left':
            target_x = screen.left() + 4
        else:
            target_x = screen.right() - self.width() - 4
        target_pos = QPoint(target_x, center_y - self.height() // 2)
        if AnimationManager.is_enabled():
            animate_smooth_move(self, target_pos, duration=220)
        else:
            self.move(target_pos)

    def _animate_move(self, target: QPoint, duration=300):
        if self._move_anim and self._move_anim.state() == QPropertyAnimation.State.Running:
            self._move_anim.stop()
        if not AnimationManager.is_enabled():
            self.move(target)
            return
        self._move_anim = QPropertyAnimation(self, b'pos')
        self._move_anim.setDuration(duration)
        self._move_anim.setStartValue(self.pos())
        self._move_anim.setEndValue(target)
        self._move_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._move_anim.start()

    def _animate_size(self, target_size: int, duration=180):
        if self._size_anim and self._size_anim.state() == QPropertyAnimation.State.Running:
            self._size_anim.stop()
        if not AnimationManager.is_enabled():
            self.setFixedSize(target_size, target_size)
            self._current_ball_size = target_size
            return
        self._size_anim = QPropertyAnimation(self, b'size')
        self._size_anim.setDuration(duration)
        self._size_anim.setStartValue(self.size())
        self._size_anim.setEndValue(QSize(target_size, target_size))
        self._size_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._size_anim.start()
        self._current_ball_size = target_size

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._has_moved = False
            self._snap_timer.stop()
            if self._is_snapped:
                self._expand_from_edge()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and self._drag_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            screen = self._get_screen_rect()
            new_pos.setY(max(screen.top() - 10, min(screen.bottom() - self.height() + 10, new_pos.y())))
            self.move(new_pos)
            moved = (event.globalPosition().toPoint() - self._drag_start_pos).manhattanLength()
            if moved > 8:
                self._has_moved = True

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            was_drag = self._has_moved
            self._is_dragging = False
            self._drag_pos = None
            if not was_drag:
                self.clicked.emit()
            else:
                self._is_snapped = False
                self._snap_timer.start(SNAP_DELAY)

    def enterEvent(self, event):
        self._is_hovering = True
        self._snap_timer.stop()
        if self._is_snapped:
            self._expand_from_edge()
        if self._current_ball_size < BALL_EXPANDED:
            self._animate_size(BALL_EXPANDED, 180)

    def leaveEvent(self, event):
        self._is_hovering = False
        if self._current_ball_size > BALL_SIZE:
            self._animate_size(BALL_SIZE, 180)
        if not self._is_dragging:
            self._snap_timer.start(SNAP_DELAY)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(500, self._snap_to_edge)

    def closeEvent(self, event):
        if self._pulse_animation:
            self._pulse_animation.stop()
        if self._move_anim:
            self._move_anim.stop()
        if self._size_anim:
            self._size_anim.stop()
        super().closeEvent(event)
