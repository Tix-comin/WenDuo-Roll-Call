"""
iOS风格开关控件 - v3.0.0
丝滑的开关动画，用于设置中的动画开关等选项
"""
from PyQt6.QtWidgets import QWidget, QPushButton
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QSize, pyqtSignal, QRect, QPoint
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen

from src.styles import SECONDARY, NEUTRAL_4, WHITE, PRIMARY
from src.animation_helper import AnimationManager


class IOSToggle(QWidget):
    """iOS风格UISwitch - 带丝滑动画的开关控件"""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, checked: bool = True, on_color: str = None):
        super().__init__(parent)
        self._checked = checked
        self._on_color = QColor(on_color or SECONDARY)
        self._off_color = QColor(NEUTRAL_4)
        self._thumb_pos = 0.0  # 0.0 = off, 1.0 = on
        self._pressing = False
        self._drag_start = None
        self._drag_start_pos = 0.0

        self.setFixedSize(51, 31)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 初始位置
        self._thumb_pos = 1.0 if checked else 0.0

        self._anim = None

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, animated: bool = True):
        if checked == self._checked:
            return
        self._checked = checked
        target = 1.0 if checked else 0.0
        if animated and AnimationManager.is_enabled():
            self._animate_to(target)
        else:
            self._thumb_pos = target
            self.update()
        self.toggled.emit(checked)

    def toggle(self):
        self.setChecked(not self._checked)

    def _animate_to(self, target: float):
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"_thumb_pos_prop")
        self._anim.setDuration(250)
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(target)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _get_thumb_pos_prop(self):
        return self._thumb_pos

    def _set_thumb_pos_prop(self, val):
        self._thumb_pos = val
        self.update()

    _thumb_pos_prop = property(_get_thumb_pos_prop, _set_thumb_pos_prop)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressing = True
            self._drag_start = event.position().toPoint()
            self._drag_start_pos = self._thumb_pos
            self.update()

    def mouseMoveEvent(self, event):
        if self._pressing and self._drag_start is not None:
            dx = event.position().x() - self._drag_start.x()
            track_width = self.width() - 31 + 4
            delta = dx / max(1, track_width)
            new_pos = max(0.0, min(1.0, self._drag_start_pos + delta))
            self._thumb_pos = new_pos
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pressing:
            self._pressing = False
            dx = event.position().x() - self._drag_start.x()
            if abs(dx) < 5:
                # 点击：切换
                self.setChecked(not self._checked)
            else:
                # 拖动：超过一半则切换
                self.setChecked(self._thumb_pos > 0.5)
            self._drag_start = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = h / 2
        margin = 2
        thumb_size = h - margin * 2

        # 轨道颜色插值
        t = self._thumb_pos
        if self._checked:
            track_color = self._on_color
        else:
            # 根据位置混合颜色
            r_c = int(self._off_color.red() * (1 - t) + self._on_color.red() * t)
            g_c = int(self._off_color.green() * (1 - t) + self._on_color.green() * t)
            b_c = int(self._off_color.blue() * (1 - t) + self._on_color.blue() * t)
            track_color = QColor(r_c, g_c, b_c)

        # 绘制轨道（圆角矩形）
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(0, 0, w, h, r, r)

        # 绘制thumb
        track_inner = w - thumb_size - margin * 2
        thumb_x = margin + track_inner * self._thumb_pos
        thumb_y = margin

        # 按下时thumb稍微变大
        if self._pressing:
            thumb_size_ext = thumb_size + 2
            thumb_x_ext = thumb_x - 1
            thumb_y_ext = thumb_y - 1
        else:
            thumb_size_ext = thumb_size
            thumb_x_ext = thumb_x
            thumb_y_ext = thumb_y

        # thumb阴影
        p.setBrush(QBrush(QColor(0, 0, 0, 20)))
        p.drawEllipse(int(thumb_x_ext) + 1, int(thumb_y_ext) + 2, int(thumb_size_ext), int(thumb_size_ext))

        # thumb本体
        p.setBrush(QBrush(QColor(WHITE)))
        p.drawEllipse(int(thumb_x_ext), int(thumb_y_ext), int(thumb_size_ext), int(thumb_size_ext))

        p.end()
