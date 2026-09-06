"""Code-drawn test avatar. No third-party character artwork is bundled."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from core.state import CharacterState


def draw_character(p: QPainter, s: CharacterState, elapsed: float) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(30, 32, 50, 35))
    p.drawEllipse(QRectF(52, 306, 176, 16))
    p.save()
    p.translate(0, math.sin(elapsed * 1.65) * 1.8)
    p.setBrush(QColor("#d9e6ef"))
    body = QPainterPath(QPointF(94, 203))
    body.cubicTo(52, 221, 69, 290, 58, 300)
    body.quadTo(140, 324, 222, 300)
    body.cubicTo(208, 271, 226, 221, 186, 203)
    body.closeSubpath()
    p.drawPath(body)
    p.setBrush(QColor("#27394d"))
    p.drawRoundedRect(QRectF(114, 212, 52, 91), 8, 8)
    p.setPen(QPen(QColor("#9faebb"), 2))
    p.drawLine(QPointF(95, 252), QPointF(91, 291))
    p.drawLine(QPointF(185, 252), QPointF(189, 291))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#83c8c5"))
    p.drawRoundedRect(QRectF(173, 252, 20, 8), 3, 3)

    p.translate(s.head_x * 10 + (-7 if s.behavior == "evade" else 0), s.head_y * 7)
    p.setBrush(QColor("#75534f"))
    p.drawRoundedRect(QRectF(60, 57, 160, 179), 68, 68)
    p.setBrush(QColor("#f6dfcd"))
    p.drawRoundedRect(QRectF(73, 84, 134, 137), 57, 57)
    p.setBrush(QColor("#75534f"))
    fringe = QPainterPath(QPointF(72, 119))
    fringe.cubicTo(70, 47, 209, 47, 208, 121)
    fringe.lineTo(169, 106)
    fringe.lineTo(153, 88)
    fringe.lineTo(137, 115)
    fringe.lineTo(112, 105)
    fringe.closeSubpath()
    p.drawPath(fringe)

    annoyed = s.expression in {"mild_annoyed", "annoyed"} or s.behavior in {"annoyed", "evade"}
    focused = s.expression in {"focused", "skeptical", "concerned"}
    surprised = s.expression == "surprised"
    openness_scale = 1.18 if surprised else (0.72 if annoyed or focused else 1.0)
    openness = max(0.08, min(1.2, s.eye_open * openness_scale))
    for cx in (111, 169):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(cx - 16, 153 - 13 * openness, 32, 26 * openness))
        if openness > 0.25:
            p.setBrush(QColor("#53798e"))
            p.drawEllipse(QRectF(cx - 7 + s.eye_x * 6, 153 - 9 * openness + s.eye_y * 2, 14, 18 * openness))
            p.setBrush(QColor("#24374a"))
            p.drawEllipse(QRectF(cx - 3 + s.eye_x * 6, 149 + s.eye_y * 2, 6, 8 * openness))
        p.setPen(QPen(QColor("#59464a"), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if annoyed:
            slope = 4 if cx < 140 else -4
        elif focused:
            slope = 2 if cx < 140 else -2
        else:
            slope = 0
        p.drawLine(QPointF(cx - 13, 133 - slope), QPointF(cx + 13, 133 + slope))
        if openness <= 0.25:
            p.drawLine(QPointF(cx - 12, 153), QPointF(cx + 12, 153))

    mouth = QPainterPath(QPointF(131, 187))
    if s.behavior == "speaking":
        mouth.quadTo(140, 198, 149, 187)
    elif annoyed or s.expression == "skeptical":
        mouth.quadTo(140, 181, 149, 187)
    else:
        mouth.quadTo(140, 191, 149, 187)
    p.drawPath(mouth)
    p.restore()
