"""
Faceplate rendering system for RackDesigner.
Each faceplate is drawn programmatically using QPainter.
All faceplates receive: painter, x, y, w, h, slot (RackSlot)
"""
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QLinearGradient
from PyQt6.QtCore import Qt, QRect, QRectF
import math


# ── Palette ───────────────────────────────────────────────────────────────────
C_RACK_BG   = QColor("#0d0d0d")
C_PANEL     = QColor("#1a1a1a")
C_PANEL2    = QColor("#222222")
C_BORDER    = QColor("#333333")
C_SCREW     = QColor("#2a2a2a")
C_SCREW_H   = QColor("#444444")
C_LED_G     = QColor("#00ff44")
C_LED_O     = QColor("#ff8800")
C_LED_R     = QColor("#ff2222")
C_LED_B     = QColor("#0088ff")
C_WHITE     = QColor("#e8e0cc")
C_GREY      = QColor("#666666")
C_DGREY     = QColor("#333333")
C_AMBER     = QColor("#e8a020")
C_DISPLAY   = QColor("#001a00")
C_DISPLAY2  = QColor("#00100a")


# ── Utility draw functions ────────────────────────────────────────────────────

def draw_screw(p: QPainter, cx, cy, r=3):
    p.setPen(QPen(C_SCREW_H, 0.5))
    p.setBrush(QBrush(C_SCREW))
    p.drawEllipse(int(cx-r), int(cy-r), r*2, r*2)
    p.setPen(QPen(C_SCREW_H, 0.8))
    p.drawLine(int(cx-r+1), int(cy), int(cx+r-1), int(cy))


def draw_corner_screws(p, x, y, w, h, r=3, margin=5):
    for cx, cy in [(x+margin, y+margin), (x+w-margin, y+margin),
                   (x+margin, y+h-margin), (x+w-margin, y+h-margin)]:
        draw_screw(p, cx, cy, r)


def draw_led(p: QPainter, cx, cy, r=3, color=None):
    c = color or C_LED_G
    glow = QColor(c)
    glow.setAlpha(60)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(glow))
    p.drawEllipse(int(cx-r*2), int(cy-r*2), r*4, r*4)
    p.setBrush(QBrush(c))
    p.setPen(QPen(c.lighter(150), 0.5))
    p.drawEllipse(int(cx-r), int(cy-r), r*2, r*2)


def draw_label(p: QPainter, text, x, y, w, h, size=7, color=None, align=Qt.AlignmentFlag.AlignCenter, bold=False):
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    p.setFont(f)
    p.setPen(color or C_WHITE)
    p.drawText(QRect(int(x), int(y), int(w), int(h)), align | Qt.AlignmentFlag.AlignVCenter, text)


def draw_rj45_port(p: QPainter, cx, cy, w=12, h=9):
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#111")))
    p.drawRect(int(cx-w//2), int(cy-h//2), w, h)
    p.setPen(QPen(C_LED_G, 0.8))
    p.drawEllipse(int(cx-1), int(cy-h//2+2), 2, 2)
    p.setPen(QPen(C_LED_O, 0.8))
    p.drawEllipse(int(cx+2), int(cy-h//2+2), 2, 2)


def draw_hdmi_port(p: QPainter, cx, cy, w=14, h=8):
    pts_x = [cx-w//2, cx+w//2, cx+w//2-2, cx-w//2+2]
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#111")))
    p.drawRect(int(cx-w//2), int(cy-h//2), w, h)
    p.setPen(QPen(C_GREY, 0.5))
    p.drawLine(int(cx-w//2+2), int(cy+h//2-2), int(cx+w//2-2), int(cy+h//2-2))


def draw_ethercon_port(p: QPainter, cx, cy, r=6):
    """Neutrik EtherCON — round with inner square."""
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#0a0a0a")))
    p.drawEllipse(int(cx-r), int(cy-r), r*2, r*2)
    inner = int(r*0.55)
    p.setBrush(QBrush(QColor("#151515")))
    p.drawRect(int(cx-inner), int(cy-inner), inner*2, inner*2)
    p.setPen(QPen(C_LED_G, 0.8))
    p.drawEllipse(int(cx-1), int(cy+r-3), 2, 2)


def draw_bnc_port(p: QPainter, cx, cy, r=5):
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#111")))
    p.drawEllipse(int(cx-r), int(cy-r), r*2, r*2)
    p.setPen(QPen(C_GREY, 0.5))
    p.drawEllipse(int(cx-2), int(cy-2), 4, 4)


def draw_xlr_port(p: QPainter, cx, cy, r=6):
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#111")))
    p.drawEllipse(int(cx-r), int(cy-r), r*2, r*2)
    p.setPen(QPen(C_GREY, 0.8))
    for angle, dist in [(90, 3), (210, 3), (330, 3)]:
        rad = math.radians(angle)
        px = cx + dist * math.cos(rad)
        py = cy - dist * math.sin(rad)
        p.drawEllipse(int(px-1), int(py-1), 2, 2)


def draw_display(p: QPainter, x, y, w, h, text="", color=C_LED_G):
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(C_DISPLAY))
    p.drawRect(int(x), int(y), int(w), int(h))
    if text:
        f = QFont("Consolas", max(6, int(h*0.4)))
        p.setFont(f)
        p.setPen(color)
        p.drawText(QRect(int(x+2), int(y), int(w-4), int(h)),
                   Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, text)


def draw_handle(p: QPainter, x, y, w, h):
    """Rack handle bar."""
    bar_h = max(4, int(h * 0.25))
    bar_y = y + (h - bar_h) // 2
    bar_w = int(w * 0.7)
    bar_x = x + (w - bar_w) // 2
    p.setPen(QPen(QColor("#444"), 1))
    p.setBrush(QBrush(QColor("#2a2a2a")))
    p.drawRoundedRect(int(bar_x), int(bar_y), int(bar_w), int(bar_h), 2, 2)


def draw_fiber_port(p: QPainter, cx, cy, r=5):
    """Optical fiber port (LC duplex style)."""
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#0a0a0a")))
    p.drawRoundedRect(int(cx-r), int(cy-r), r*2, r*2, 2, 2)
    p.setPen(QPen(QColor("#0088ff"), 0.8))
    p.drawEllipse(int(cx-2), int(cy-2), 4, 4)


def faceplate_base(p: QPainter, x, y, w, h, slot):
    """Draw the base panel background, always call first."""
    color = QColor(slot.effective_color)
    p.fillRect(int(x), int(y), int(w), int(h), color.darker(200))
    p.setPen(QPen(color.darker(120), 1))
    p.drawRect(int(x), int(y), int(w), int(h))
    # Left color stripe
    p.fillRect(int(x), int(y), 5, int(h), color)


# ── FACEPLATE RENDERERS ───────────────────────────────────────────────────────

def fp_generic(p, x, y, w, h, slot):
    faceplate_base(p, x, y, w, h, slot)
    draw_corner_screws(p, x, y, w, h)
    # LED
    draw_led(p, x + w - 18, y + h//2, 3, C_LED_G)
    # Name centered
    draw_label(p, slot.name, x+8, y, w-30, h, size=8, bold=True)


def fp_media_server_generic(p, x, y, w, h, slot):
    """Generic PC/media server 4U."""
    faceplate_base(p, x, y, w, h, slot)
    draw_corner_screws(p, x, y, w, h)
    mid_y = y + h//2

    # Drive bays (top half)
    bay_w, bay_h = 38, max(8, (h//2 - 10))
    for i in range(3):
        bx = x + 18 + i * (bay_w + 5)
        by = y + 6
        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(QBrush(QColor("#111")))
        p.drawRect(int(bx), int(by), int(bay_w), int(bay_h))
        p.setPen(QPen(C_GREY, 0.5))
        p.drawLine(int(bx+4), int(by+bay_h-3), int(bx+bay_w-4), int(by+bay_h-3))

    # Power button
    pw_x = x + w - 40
    pw_y = y + 10
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#1a1a1a")))
    p.drawEllipse(int(pw_x), int(pw_y), 14, 14)
    draw_led(p, pw_x+7, pw_y+7, 4, C_LED_G)

    # USB ports
    for i in range(2):
        ux = x + 18 + i * 18
        uy = mid_y + 6
        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(QBrush(QColor("#111")))
        p.drawRect(int(ux), int(uy), 10, 7)

    # Name + brand
    draw_label(p, slot.name, x + 8, mid_y + 4, w//2, h//2 - 8, size=7, bold=True)


def fp_disguise_gx(p, x, y, w, h, slot):
    """Disguise GX generic — 4U."""
    # Dark aluminium look
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#141414"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))

    # Left handle zone
    handle_w = 60
    p.fillRect(int(x), int(y), int(handle_w), int(h), QColor("#0f0f0f"))
    p.setPen(QPen(QColor("#333"), 1))
    p.drawLine(int(x+handle_w), int(y), int(x+handle_w), int(y+h))

    # Handle grip
    grip_h = int(h * 0.5)
    grip_y = y + (h - grip_h)//2
    p.setPen(QPen(QColor("#3a3a3a"), 2))
    p.setBrush(QBrush(QColor("#1e1e1e")))
    p.drawRoundedRect(int(x+8), int(grip_y), int(handle_w-16), int(grip_h), 4, 4)
    for i in range(3):
        ly = grip_y + grip_h//4 + i * grip_h//4
        p.setPen(QPen(QColor("#444"), 1))
        p.drawLine(int(x+14), int(ly), int(x+handle_w-14), int(ly))

    # VFC slot labels
    vfc_x = x + handle_w + 10
    vfc_w = 55
    vfc_h = int(h * 0.35)
    for i in range(2):
        vx = vfc_x + i * (vfc_w + 8)
        vy = y + (h - vfc_h)//2
        p.setPen(QPen(QColor("#2a2a2a"), 1))
        p.setBrush(QBrush(QColor("#0d0d0d")))
        p.drawRect(int(vx), int(vy), int(vfc_w), int(vfc_h))
        draw_label(p, f"VFC {i+1}", vx, vy, vfc_w, vfc_h, size=6, color=C_GREY)

    # Right section: LEDs + logo
    rx = x + w - 120
    ry = y + 6
    draw_label(p, "disguise", rx, ry, 100, 14, size=7, color=C_AMBER, bold=True)

    # Status LEDs
    for i, (label, col) in enumerate([("PWR", C_LED_G), ("SSD", C_LED_B), ("NET", C_LED_G)]):
        lx = rx + 8 + i * 32
        ly = ry + 20
        draw_led(p, lx, ly, 3, col)
        draw_label(p, label, lx-8, ly+5, 20, 10, size=5, color=C_GREY)

    # Name
    draw_label(p, slot.name, x+handle_w+10, y+h-18, w-handle_w-130, 14, size=7, bold=True)

    draw_corner_screws(p, x, y, w, h, r=3)


def fp_pixera_four(p, x, y, w, h, slot):
    """Pixera Four Gen2 — 4U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#111111"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))
    draw_corner_screws(p, x, y, w, h)

    # Left: power button + logo
    pw_r = 10
    pw_cx = x + 24
    pw_cy = y + h//2
    p.setPen(QPen(QColor("#333"), 1))
    p.setBrush(QBrush(QColor("#1a1a1a")))
    p.drawEllipse(int(pw_cx-pw_r), int(pw_cy-pw_r), pw_r*2, pw_r*2)
    draw_led(p, pw_cx, pw_cy, 5, C_LED_B)

    # PIXERA wordmark
    draw_label(p, "PIXERA", x+45, y+6, 80, 16, size=9, color=C_WHITE, bold=True)
    draw_label(p, "four Gen2", x+45, y+22, 80, 14, size=6, color=C_GREY)

    # Center: display
    disp_x = x + 140
    disp_y = y + 8
    disp_w = w - 280
    disp_h = int(h * 0.5)
    draw_display(p, disp_x, disp_y, disp_w, disp_h, "PIXERA", C_LED_B)

    # GPU / IO indicators
    for i in range(4):
        lx = disp_x + 10 + i * 20
        ly = disp_y + disp_h + 8
        draw_led(p, lx, ly, 3, C_LED_B if i < 2 else C_LED_G)

    # Right: I/O ports
    io_x = x + w - 120
    io_y = y + 10
    draw_label(p, "I/O", io_x, io_y, 30, 10, size=6, color=C_GREY)
    for i in range(4):
        draw_hdmi_port(p, io_x + 8 + i * 20, io_y + 20)
    for i in range(2):
        draw_rj45_port(p, io_x + 10 + i * 24, io_y + 40)

    draw_label(p, slot.name, x+8, y+h-14, 120, 12, size=6, color=C_GREY)


def fp_novastar_r5(p, x, y, w, h, slot):
    """Novastar MCTRL R5 — 1U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#101010"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))

    cx = x + 4

    # Power button
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#1a1a1a")))
    p.drawEllipse(int(cx+2), int(y+h//2-5), 10, 10)
    draw_led(p, cx+7, y+h//2, 3, C_LED_G)
    cx += 18

    # LCD display
    disp_w = 55
    draw_display(p, cx, y+3, disp_w, h-6, "MCTRL R5", C_LED_G)
    cx += disp_w + 6

    # Knob
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#222")))
    p.drawEllipse(int(cx), int(y+h//2-6), 12, 12)
    cx += 18

    # USB
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#111")))
    p.drawRect(int(cx), int(y+h//2-4), 8, 7)
    cx += 14

    # Input ports: SDI, HDMI, DVI label
    draw_label(p, "IN", cx, y+2, 30, 8, size=5, color=C_GREY)
    draw_bnc_port(p, cx+5, y+h//2)    # SDI
    draw_hdmi_port(p, cx+20, y+h//2)   # HDMI
    cx += 38

    # 8x EtherCON outputs
    draw_label(p, "ETH OUT", cx, y+2, 80, 8, size=5, color=C_GREY)
    for i in range(8):
        draw_ethercon_port(p, cx + 8 + i*18, y+h//2, r=6)
    cx += 8 * 18 + 12

    # 2x Fiber
    draw_label(p, "OPT", cx, y+2, 30, 8, size=5, color=C_GREY)
    for i in range(2):
        draw_fiber_port(p, cx+6+i*14, y+h//2)


def fp_novastar_mctrl4k(p, x, y, w, h, slot):
    """Novastar MCTRL4K — 2U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#0f0f0f"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))
    draw_corner_screws(p, x, y, w, h)

    mid = y + h//2
    cx = x + 8

    # Power + LED
    p.setBrush(QBrush(QColor("#1a1a1a")))
    p.setPen(QPen(C_BORDER, 1))
    p.drawEllipse(int(cx), int(y+8), 14, 14)
    draw_led(p, cx+7, y+15, 4, C_LED_G)
    cx += 22

    # LCD display — top half
    disp_w = 70
    draw_display(p, cx, y+5, disp_w, h//2-8, "MCTRL 4K", C_LED_G)
    cx += disp_w + 8

    # Knob
    p.setBrush(QBrush(QColor("#222")))
    p.setPen(QPen(C_BORDER, 1))
    p.drawEllipse(int(cx), int(y+6), 16, 16)
    cx += 24

    # Inputs: DP, HDMI, 2x DVI
    draw_label(p, "INPUTS", cx, y+3, 80, 10, size=5, color=C_GREY)
    for i, lbl in enumerate(["DP", "HDMI"]):
        px = cx + 6 + i*22
        draw_hdmi_port(p, px, y+18)
        draw_label(p, lbl, px-6, y+26, 16, 8, size=4, color=C_GREY)
    for i in range(2):
        px = cx + 52 + i*22
        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(QBrush(QColor("#111")))
        p.drawRect(int(px-8), int(y+12), 16, 12)
        draw_label(p, "DVI", px-8, y+26, 16, 8, size=4, color=C_GREY)
    cx += 100

    # 16x EtherCON — bottom row
    eth_y = mid + 4
    draw_label(p, "ETHERNET OUT (16×)", cx, eth_y-10, 200, 10, size=5, color=C_GREY)
    for i in range(16):
        draw_ethercon_port(p, cx + 8 + i*18, eth_y+8, r=6)
    cx += 16*18 + 16

    # 4x Fiber
    draw_label(p, "OPT×4", cx, eth_y-10, 50, 10, size=5, color=C_GREY)
    for i in range(4):
        draw_fiber_port(p, cx+6+i*14, eth_y+8)

    # Genlock
    cx2 = x + 8
    draw_label(p, "GENLOCK", cx2, mid+4, 50, 10, size=5, color=C_GREY)
    draw_bnc_port(p, cx2+8, mid+18)
    draw_bnc_port(p, cx2+24, mid+18)


def fp_colorlight_z6(p, x, y, w, h, slot):
    """Colorlight Z6 — 2U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#101010"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))
    draw_corner_screws(p, x, y, w, h)

    mid = y + h//2
    cx = x + 10

    # Brand + power
    draw_label(p, "Colorlight", cx, y+4, 70, 12, size=7, color=C_AMBER, bold=True)
    draw_label(p, "Z6", cx, y+16, 70, 12, size=9, color=C_WHITE, bold=True)
    draw_led(p, cx+55, y+10, 4, C_LED_G)
    cx += 80

    # Display
    disp_w = 80
    draw_display(p, cx, y+5, disp_w, h//2-8, "Z6", C_LED_G)
    cx += disp_w + 10

    # Inputs
    draw_label(p, "IN", cx, y+3, 60, 10, size=5, color=C_GREY)
    draw_hdmi_port(p, cx+8, y+18)
    draw_label(p, "HDMI", cx+2, y+26, 20, 8, size=4, color=C_GREY)
    for i in range(2):
        bx = cx + 30 + i*16
        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(QBrush(QColor("#111")))
        p.drawRect(int(bx-7), int(y+12), 14, 10)
        draw_label(p, "DVI", bx-8, y+26, 16, 8, size=4, color=C_GREY)
    cx += 65

    # EtherCON outputs — top row
    eth_count = 12
    draw_label(p, "ETH OUT", cx, y+3, 130, 10, size=5, color=C_GREY)
    for i in range(eth_count):
        draw_ethercon_port(p, cx + 8 + i*18, y+18, r=6)
    cx += eth_count*18 + 16

    # Bottom row
    draw_label(p, "ETH OUT (cont.)", x+80, mid+3, 150, 10, size=5, color=C_GREY)
    for i in range(4):
        draw_ethercon_port(p, x+80 + 8 + i*18, mid+16, r=6)

    # Fiber
    draw_label(p, "OPT", x+w-50, mid+3, 40, 10, size=5, color=C_GREY)
    for i in range(2):
        draw_fiber_port(p, x+w-44+i*14, mid+16)


def fp_novastar_cvt(p, x, y, w, h, slot):
    """Novastar CVT (fiber converter) — 1U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#0f0f0f"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))

    cx = x + 10
    draw_label(p, "NovaStar", cx, y+2, 70, 12, size=6, color=C_AMBER, bold=True)
    draw_label(p, "CVT", cx, y+h//2-4, 40, 10, size=8, color=C_WHITE, bold=True)
    cx += 75

    # Status LEDs
    for label, col in [("PWR", C_LED_G), ("LINK", C_LED_B), ("ACT", C_LED_G)]:
        draw_led(p, cx+4, y+h//2, 3, col)
        draw_label(p, label, cx, y+h//2+5, 20, 8, size=4, color=C_GREY)
        cx += 22

    cx += 10
    draw_label(p, "FIBER IN/OUT", cx, y+3, 80, 10, size=5, color=C_GREY)
    draw_fiber_port(p, cx+10, y+h//2)
    draw_fiber_port(p, cx+26, y+h//2)
    cx += 50

    draw_label(p, "ETH", cx, y+3, 50, 10, size=5, color=C_GREY)
    draw_ethercon_port(p, cx+10, y+h//2, r=6)


def fp_lightware_mx2_8x8(p, x, y, w, h, slot):
    """Lightware MX2 8x8 HDMI — 1U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#111111"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))

    cx = x + 8
    # Logo
    draw_label(p, "LIGHTWARE", cx, y+2, 70, 10, size=5, color=C_WHITE, bold=True)
    draw_label(p, "MX2  8×8  HDMI", cx, y+h//2-4, 90, 10, size=6, color=C_AMBER)
    cx += 95

    # Jog dial
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#1e1e1e")))
    p.drawEllipse(int(cx), int(y+h//2-8), 16, 16)
    p.setPen(QPen(C_GREY, 0.8))
    p.drawEllipse(int(cx+4), int(y+h//2-4), 8, 8)
    cx += 24

    # Display
    draw_display(p, cx, y+3, 55, h-6, "8x8", C_LED_B)
    cx += 62

    # 8 inputs
    draw_label(p, "IN (×8 HDMI)", cx, y+2, 110, 9, size=4, color=C_GREY)
    for i in range(8):
        draw_hdmi_port(p, cx + 8 + i*18, y+h//2)
        draw_label(p, str(i+1), cx+3+i*18, y+h//2+8, 12, 8, size=4, color=C_GREY)
    cx += 8*18 + 12

    # 8 outputs
    draw_label(p, "OUT (×8 HDMI)", cx, y+2, 110, 9, size=4, color=C_GREY)
    for i in range(8):
        draw_hdmi_port(p, cx + 8 + i*18, y+h//2)
        draw_label(p, str(i+1), cx+3+i*18, y+h//2+8, 12, 8, size=4, color=C_GREY)
    cx += 8*18 + 12

    # Status
    draw_led(p, cx+4, y+h//2, 3, C_LED_G)
    draw_label(p, "PWR", cx, y+h//2+5, 20, 8, size=4, color=C_GREY)


def fp_lightware_mx2_16x16(p, x, y, w, h, slot):
    """Lightware MX2 16x16 HDMI — 2U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#111111"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))
    draw_corner_screws(p, x, y, w, h)

    mid = y + h//2
    cx = x + 10

    draw_label(p, "LIGHTWARE", cx, y+4, 80, 12, size=6, color=C_WHITE, bold=True)
    draw_label(p, "MX2  16×16  HDMI 2.0", cx, y+18, 120, 12, size=6, color=C_AMBER)
    draw_led(p, cx+130, y+10, 4, C_LED_G)
    cx += 150

    # Jog
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#1e1e1e")))
    p.drawEllipse(int(cx), int(y+6), 20, 20)
    p.setPen(QPen(C_GREY, 0.8))
    p.drawEllipse(int(cx+4), int(y+10), 12, 12)
    cx += 30

    # Display
    draw_display(p, cx, y+4, 70, h//2-8, "16x16", C_LED_B)
    cx += 80

    # 16 inputs (top row)
    draw_label(p, "INPUTS ×16", cx, y+3, 200, 10, size=5, color=C_GREY)
    for i in range(16):
        draw_hdmi_port(p, cx + 8 + i*18, y+18)
        draw_label(p, str(i+1), cx+3+i*18, y+28, 12, 8, size=4, color=C_GREY)

    # 16 outputs (bottom row)
    draw_label(p, "OUTPUTS ×16", cx, mid+2, 200, 10, size=5, color=C_GREY)
    for i in range(16):
        draw_hdmi_port(p, cx + 8 + i*18, mid+16)
        draw_label(p, str(i+1), cx+3+i*18, mid+26, 12, 8, size=4, color=C_GREY)


def fp_eaton_5p(p, x, y, w, h, slot):
    """Eaton 5P UPS — 1U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#1a1a1a"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))

    cx = x + 8
    # Eaton logo area
    p.fillRect(int(cx), int(y+2), 50, int(h-4), QColor("#0f0f0f"))
    draw_label(p, "EATON", cx, y+2, 50, h//2, size=7, color=C_AMBER, bold=True)
    draw_label(p, "5P", cx, y+h//2, 50, h//2-2, size=6, color=C_WHITE)
    cx += 58

    # LCD display
    draw_display(p, cx, y+3, 80, h-6, "100%  AC", C_LED_G)
    cx += 88

    # Battery indicator bar
    bar_w = 60
    bar_h = 10
    bar_y = y + (h-bar_h)//2
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#111")))
    p.drawRect(int(cx), int(bar_y), int(bar_w), int(bar_h))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(C_LED_G))
    p.drawRect(int(cx+1), int(bar_y+1), int(bar_w*0.85-2), int(bar_h-2))
    draw_label(p, "BATT", cx, bar_y-10, bar_w, 10, size=4, color=C_GREY)
    cx += bar_w + 10

    # Status LEDs
    for label, col in [("ON LINE", C_LED_G), ("BATT", C_LED_O), ("FAULT", C_LED_R)]:
        draw_led(p, cx+4, y+h//2, 3, col)
        draw_label(p, label, cx, y+h//2+5, 30, 8, size=4, color=C_GREY)
        cx += 36

    # Outlets strip (right side)
    draw_label(p, "OUTPUTS", cx, y+2, 80, 10, size=5, color=C_GREY)
    for i in range(5):
        ox = cx + 6 + i*20
        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(QBrush(QColor("#111")))
        p.drawEllipse(int(ox), int(y+h//2-6), 12, 12)
        p.setPen(QPen(C_GREY, 0.8))
        p.drawLine(int(ox+4), int(y+h//2-2), int(ox+8), int(y+h//2-2))
        p.drawLine(int(ox+6), int(y+h//2-4), int(ox+6), int(y+h//2+4))


def fp_eaton_9px(p, x, y, w, h, slot):
    """Eaton 9PX UPS — 2U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#161616"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))
    draw_corner_screws(p, x, y, w, h)

    mid = y + h//2
    cx = x + 8

    # Logo
    p.fillRect(int(cx), int(y+4), 65, int(h-8), QColor("#0f0f0f"))
    draw_label(p, "EATON", cx, y+4, 65, h//3, size=8, color=C_AMBER, bold=True)
    draw_label(p, "9PX", cx, y+h//3+4, 65, h//3, size=10, color=C_WHITE, bold=True)
    draw_label(p, "ONLINE UPS", cx, y+2*h//3+4, 65, h//3-4, size=5, color=C_GREY)
    cx += 72

    # LCD
    draw_display(p, cx, y+4, 100, h-8, "ONLINE\n100%", C_LED_G)
    cx += 108

    # Capacity bar x2
    for i, label in enumerate(["LOAD", "BATT"]):
        bar_w, bar_h = 80, 10
        bx = cx
        by = y + 8 + i*(bar_h+10)
        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(QBrush(QColor("#111")))
        p.drawRect(int(bx), int(by), int(bar_w), int(bar_h))
        fill = 0.6 if i==0 else 0.9
        col = C_LED_O if i==0 else C_LED_G
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(col))
        p.drawRect(int(bx+1), int(by+1), int(bar_w*fill-2), int(bar_h-2))
        draw_label(p, label, bx, by-9, bar_w, 9, size=4, color=C_GREY)
    cx += 88

    # Status LEDs
    for label, col in [("AC IN", C_LED_G), ("DC OUT", C_LED_G), ("BYPASS", C_LED_O), ("FAULT", C_LED_R)]:
        draw_led(p, cx+5, y+h//4 + (["AC IN","DC OUT","BYPASS","FAULT"].index(label)) * h//4, 3, col)
        draw_label(p, label, cx+12, y+h//4-4 + (["AC IN","DC OUT","BYPASS","FAULT"].index(label)) * h//4, 36, 10, size=4, color=C_GREY)
    cx += 55

    # Outlets
    draw_label(p, "IEC C13 OUTPUTS", cx, y+3, 130, 10, size=5, color=C_GREY)
    for i in range(6):
        ox = cx + 6 + i*20
        oy = y + h//2 - 8
        p.setPen(QPen(C_BORDER, 1))
        p.setBrush(QBrush(QColor("#111")))
        p.drawRoundedRect(int(ox), int(oy), 14, 16, 2, 2)
        p.setPen(QPen(C_GREY, 0.8))
        p.drawEllipse(int(ox+5), int(oy+4), 4, 4)


def fp_drawmer_da6(p, x, y, w, h, slot):
    """Drawmer DA6 Audio Distribution Amp — 1U."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#111111"))
    p.setPen(QPen(QColor("#2a2a2a"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))

    cx = x + 8
    # Logo
    draw_label(p, "DRAWMER", cx, y+2, 60, 12, size=6, color=C_WHITE, bold=True)
    draw_label(p, "DA6", cx, y+h//2-2, 50, 12, size=8, color=C_AMBER, bold=True)
    cx += 65

    # Input section
    draw_label(p, "INPUT", cx, y+2, 40, 10, size=5, color=C_GREY)
    draw_xlr_port(p, cx+10, y+h//2, 7)   # XLR in
    draw_label(p, "XLR", cx+4, y+h//2+8, 16, 8, size=4, color=C_GREY)
    cx += 26

    # Gain knob
    p.setPen(QPen(C_BORDER, 1))
    p.setBrush(QBrush(QColor("#1e1e1e")))
    p.drawEllipse(int(cx), int(y+h//2-8), 16, 16)
    draw_label(p, "GAIN", cx-2, y+h//2+9, 20, 8, size=4, color=C_GREY)
    cx += 24

    # Level meter (6 segment)
    draw_label(p, "LEVEL", cx, y+2, 50, 10, size=5, color=C_GREY)
    segs = [C_LED_G]*4 + [C_LED_O] + [C_LED_R]
    seg_h = max(2, (h-10)//6)
    for i, col in enumerate(segs):
        sy = y + h - 5 - (i+1)*seg_h
        p.setPen(Qt.PenStyle.NoPen)
        active_col = col if i < 4 else QColor("#111")
        p.setBrush(QBrush(active_col))
        p.drawRect(int(cx+2), int(sy), 14, seg_h-1)
    cx += 24

    # 6x XLR outputs
    draw_label(p, "OUTPUTS (×6 XLR)", cx, y+2, 130, 10, size=5, color=C_GREY)
    for i in range(6):
        draw_xlr_port(p, cx + 12 + i*24, y+h//2, 7)
        draw_label(p, str(i+1), cx+7+i*24, y+h//2+8, 14, 8, size=4, color=C_GREY)
    cx += 6*24 + 8

    # Power LED
    draw_led(p, cx+4, y+h//2, 3, C_LED_G)
    draw_label(p, "PWR", cx, y+h//2+5, 20, 8, size=4, color=C_GREY)


def fp_patch_panel(p, x, y, w, h, slot):
    """Patch panel — connector type and count from slot notes or snapshot."""
    faceplate_base(p, x, y, w, h, slot)

    snap = slot.device_snapshot
    conn_type = snap.get("patch_connector", "XLR")
    conn_count = int(snap.get("patch_count", 24))

    draw_fn = {
        "XLR": draw_xlr_port, "BNC": draw_bnc_port,
        "RJ45": draw_rj45_port, "EtherCON": draw_ethercon_port,
        "HDMI": draw_hdmi_port, "Fiber": draw_fiber_port,
    }.get(conn_type, draw_xlr_port)

    label_area = 50
    available_w = w - label_area - 10
    spacing = min(22, available_w // max(1, conn_count))
    start_x = x + label_area

    draw_label(p, f"{conn_type} × {conn_count}", x+8, y+2, label_area-4, 10, size=5, color=C_GREY)
    draw_label(p, slot.name, x+8, y+h//2-4, label_area-4, 10, size=6, bold=True)

    for i in range(conn_count):
        cx2 = start_x + 10 + i * spacing
        if cx2 + spacing > x + w - 4:
            break
        draw_fn(p, cx2, y + h//2)
        draw_label(p, str(i+1), cx2-4, y+h-10, 12, 9, size=4, color=C_GREY)


def fp_blank(p, x, y, w, h, slot):
    """Blank panel."""
    p.fillRect(int(x), int(y), int(w), int(h), QColor("#161616"))
    p.setPen(QPen(QColor("#222"), 1))
    p.drawRect(int(x), int(y), int(w), int(h))
    # Subtle brushed metal lines
    p.setPen(QPen(QColor("#1c1c1c"), 1))
    for i in range(0, h, 4):
        p.drawLine(int(x+1), int(y+i), int(x+w-1), int(y+i))
    draw_corner_screws(p, x, y, w, h)


# ── Registry ──────────────────────────────────────────────────────────────────

FACEPLATE_REGISTRY = {
    "generic":              fp_generic,
    "media_server_generic": fp_media_server_generic,
    "disguise_gx":          fp_disguise_gx,
    "pixera_four":          fp_pixera_four,
    "novastar_r5":          fp_novastar_r5,
    "novastar_mctrl4k":     fp_novastar_mctrl4k,
    "colorlight_z6":        fp_colorlight_z6,
    "novastar_cvt":         fp_novastar_cvt,
    "lightware_mx2_8x8":    fp_lightware_mx2_8x8,
    "lightware_mx2_16x16":  fp_lightware_mx2_16x16,
    "eaton_5p":             fp_eaton_5p,
    "eaton_9px":            fp_eaton_9px,
    "drawmer_da6":          fp_drawmer_da6,
    "patch_panel":          fp_patch_panel,
    "blank_panel":          fp_blank,
}

FACEPLATE_LABELS = {
    "generic":              "Generic device",
    "media_server_generic": "Media server (generic)",
    "disguise_gx":          "Disguise GX (generic)",
    "pixera_four":          "Pixera Four Gen2",
    "novastar_r5":          "Novastar MCTRL R5",
    "novastar_mctrl4k":     "Novastar MCTRL4K",
    "colorlight_z6":        "Colorlight Z6",
    "novastar_cvt":         "Novastar CVT",
    "lightware_mx2_8x8":    "Lightware MX2 8×8",
    "lightware_mx2_16x16":  "Lightware MX2 16×16",
    "eaton_5p":             "Eaton 5P UPS (1U)",
    "eaton_9px":            "Eaton 9PX UPS (2U)",
    "drawmer_da6":          "Drawmer DA6",
    "patch_panel":          "Patch panel (custom)",
    "blank_panel":          "Blank panel",
}


def draw_faceplate(painter, x, y, w, h, slot):
    """Main entry point. Dispatches to the correct faceplate renderer."""
    key = slot.device_snapshot.get("faceplate", "generic")
    fn = FACEPLATE_REGISTRY.get(key, fp_generic)
    from PyQt6.QtCore import QRect
    painter.save()
    painter.setClipRect(QRect(int(x), int(y), int(w), int(h)))
    try:
        fn(painter, x, y, w, h, slot)
    except Exception:
        fp_generic(painter, x, y, w, h, slot)
    finally:
        painter.restore()
