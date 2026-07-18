"""
丝滑动画辅助模块 - v3.0.1
统一管理所有 UI 动画，支持全局开关
适用于教育场景的温润动画效果
"""
from PyQt6.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QTimer, Qt, QPoint, QSize, pyqtSignal
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget


class AnimationManager:
    """动画管理器 - 全局控制动画开关"""

    _instance = None
    _animations_enabled = True

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_enabled(cls, enabled: bool):
        """全局开启/关闭动画"""
        cls._animations_enabled = enabled

    @classmethod
    def is_enabled(cls) -> bool:
        return cls._animations_enabled

    @classmethod
    def apply_from_settings(cls, settings_manager):
        """从设置管理器读取动画开关状态"""
        if settings_manager:
            cls._animations_enabled = settings_manager.get("enable_animations", True)


def smooth_property(widget, prop_name: bytes, start_val, end_val,
                   duration: int = 300, easing=QEasingCurve.Type.OutCubic):
    """创建一个丝滑属性动画，会自动遵守全局开关"""
    anim = QPropertyAnimation(widget, prop_name)
    anim.setStartValue(start_val)
    anim.setEndValue(end_val)
    anim.setDuration(duration if AnimationManager.is_enabled() else 0)
    anim.setEasingCurve(easing)
    return anim


def fade_in(widget: QWidget, duration: int = 250, from_opacity: float = 0.0):
    """淡入效果"""
    if not AnimationManager.is_enabled():
        widget.setGraphicsEffect(None)
        widget.show()
        return None

    effect = widget.graphicsEffect()
    if effect is None or not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

    effect.setOpacity(from_opacity)
    widget.show()

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(from_opacity)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    return anim


def fade_out(widget: QWidget, duration: int = 200, to_opacity: float = 0.0, hide_after: bool = True):
    """淡出效果"""
    if not AnimationManager.is_enabled():
        if hide_after:
            widget.hide()
        return None

    effect = widget.graphicsEffect()
    if effect is None or not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(effect.opacity())
    anim.setEndValue(to_opacity)
    anim.setEasingCurve(QEasingCurve.Type.InCubic)
    if hide_after:
        anim.finished.connect(widget.hide)
    anim.start()
    return anim


def slide_in(widget: QWidget, direction: str = "right", duration: int = 350, distance: int = 40):
    """滑入效果（同时淡入）"""
    if not AnimationManager.is_enabled():
        widget.show()
        return None

    start_pos = widget.pos()
    if direction == "right":
        offset = QPoint(distance, 0)
    elif direction == "left":
        offset = QPoint(-distance, 0)
    elif direction == "up":
        offset = QPoint(0, -distance)
    elif direction == "down":
        offset = QPoint(0, distance)
    else:
        offset = QPoint(0, 0)

    widget.move(start_pos + offset)
    widget.show()

    effect = widget.graphicsEffect()
    if effect is None or not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)

    group = QParallelAnimationGroup()

    pos_anim = QPropertyAnimation(widget, b"pos")
    pos_anim.setDuration(duration)
    pos_anim.setStartValue(start_pos + offset)
    pos_anim.setEndValue(start_pos)
    pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    op_anim = QPropertyAnimation(effect, b"opacity")
    op_anim.setDuration(duration)
    op_anim.setStartValue(0.0)
    op_anim.setEndValue(1.0)
    op_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    group.addAnimation(pos_anim)
    group.addAnimation(op_anim)
    group.start()
    return group


def bounce_result(widget: QWidget, scale_factor: float = 1.08, duration: int = 500):
    """结果弹跳动画（点名抽中时使用）"""
    if not AnimationManager.is_enabled():
        return None

    # 同时使用缩放几何和淡入
    rect = widget.geometry()
    cx = rect.center()
    w = int(rect.width() * scale_factor)
    h = int(rect.height() * scale_factor)
    big_rect = rect.adjusted(
        -(w - rect.width()) // 2,
        -(h - rect.height()) // 2,
        (w - rect.width()) // 2,
        (h - rect.height()) // 2,
    )

    anim = QPropertyAnimation(widget, b"geometry")
    anim.setDuration(duration)
    anim.setKeyValueAt(0, rect)
    anim.setKeyValueAt(0.3, big_rect)
    anim.setKeyValueAt(0.6, rect.adjusted(-3, -4, 3, 4))
    anim.setEndValue(rect)
    anim.setEasingCurve(QEasingCurve.Type.OutElastic)
    anim.start()
    return anim


def pulse_widget(widget: QWidget, duration: int = 2500):
    """脉冲呼吸动画（悬浮球使用）"""
    if not AnimationManager.is_enabled():
        return None

    anim = QPropertyAnimation(widget, b"windowOpacity")
    anim.setDuration(duration)
    anim.setStartValue(0.82)
    anim.setKeyValueAt(0.5, 1.0)
    anim.setEndValue(0.82)
    anim.setLoopCount(-1)
    anim.setEasingCurve(QEasingCurve.Type.InOutSine)
    anim.start()
    return anim


def press_scale(widget: QWidget, pressed: bool, scale: float = 0.96, duration: int = 100):
    """按钮按下/释放时的缩放反馈"""
    if not AnimationManager.is_enabled():
        return None

    target_size = widget.size() * scale if pressed else widget.size()
    # 对于没有minimumSize约束的widget，用minimumSize来实现缩放
    anim = QPropertyAnimation(widget, b"minimumSize")
    anim.setDuration(duration)
    anim.setEndValue(QSize(int(widget.sizeHint().width() * scale if pressed else widget.sizeHint().width()),
                          int(widget.sizeHint().height() * scale if pressed else widget.sizeHint().height())))
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    return anim


def animate_smooth_move(widget: QWidget, target_pos: QPoint, duration: int = 300):
    """丝滑移动动画"""
    if not AnimationManager.is_enabled():
        widget.move(target_pos)
        return None

    anim = QPropertyAnimation(widget, b"pos")
    anim.setDuration(duration)
    anim.setStartValue(widget.pos())
    anim.setEndValue(target_pos)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    return anim


def animate_size(widget: QWidget, target_size: QSize, duration: int = 200):
    """丝滑尺寸变化"""
    if not AnimationManager.is_enabled():
        widget.resize(target_size)
        return None

    anim = QPropertyAnimation(widget, b"size")
    anim.setDuration(duration)
    anim.setStartValue(widget.size())
    anim.setEndValue(target_size)
    anim.setEasingCurve(QEasingCurve.Type.OutBack)
    anim.start()
    return anim


def stagger_fade_in(widgets: list, duration: int = 200, delay_step: int = 50):
    """依次淡入一组控件（交错动画）"""
    if not AnimationManager.is_enabled():
        for w in widgets:
            w.show()
        return None

    group = QSequentialAnimationGroup()
    for i, w in enumerate(widgets):
        effect = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        w.show()

        op_anim = QPropertyAnimation(effect, b"opacity")
        op_anim.setDuration(duration)
        op_anim.setStartValue(0.0)
        op_anim.setEndValue(1.0)
        op_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if i > 0:
            # 添加延迟
            pause = QTimer()
            pause.setSingleShot(True)
            # 使用 QPauseAnimation 在组中实现间隔
            from PyQt6.QtCore import QPauseAnimation
            group.addAnimation(QPauseAnimation(delay_step))

        group.addAnimation(op_anim)

    group.start()
    return group
