#!/usr/bin/env python3
"""Генерирует схемы подключения USB-UART к MB90F395HA для сайта.

Две картинки (вариант A — UART0, вариант B — UART4), подписи на английском
техническом языке, чтобы одна картинка подходила обеим языковым версиям
сайта. Координаты считаются по сетке строк — провода всегда горизонтальные и
не пересекаются, подписи не наезжают друг на друга.

Usage:
    python3 tools/site/gen_uart_svg.py           # записать site/assets/img/uart-wiring-{a,b}.svg
    python3 tools/site/gen_uart_svg.py --check   # код 1, если картинки устарели
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "site" / "assets" / "img"

W = 980
BG, PANEL, BORDER = "#0f0d0a", "#1b1812", "#3a3128"
TEXT, DIM = "#ece6da", "#a99d8a"
ACCENT, DATA, PWR, GNDC = "#ff5e1a", "#ffb08a", "#e0b400", "#8fb4d6"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

ADAPTER_X0, ADAPTER_X1 = 40, 250
MCU_X0, MCU_X1 = 640, 940
ROW0, ROW_STEP, GROUP_GAP = 128, 44, 34

VARIANTS = {
    "a": {
        "title": "Variant A · UART0 (pins 5 / 7) · reported working",
        "uart": [  # (pin, name, adapter pin, direction: 'in' = adapter -> MCU)
            (5, "SOT0", "RXD", "out"),
            (7, "SIN0", "TXD", "in"),
            (16, "VSS", "GND", "gnd"),
        ],
        "mode": [
            (87, "MD2", "5v"),
            (88, "MD1", "5v"),
            (89, "MD0", "gnd"),
            (90, "RST", "button"),
            (93, "P00", "res_gnd"),
            (94, "P01", "res_gnd"),
        ],
    },
    "b": {
        "title": "Variant B · UART4 (pins 52 / 54) · per Fujitsu spec",
        "uart": [
            (47, "VSS", "GND", "gnd"),
            (52, "SIN4", "TXD", "in"),
            (54, "SOT4", "RXD", "out"),
        ],
        "mode": [
            (87, "MD2", "5v"),
            (88, "MD1", "5v"),
            (89, "MD0", "gnd"),
            (90, "RST", "button"),
            (93, "P00", "5v_wire"),
            (94, "P01", "gnd"),
        ],
    },
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=14, fill=TEXT, anchor="start", weight="normal", family=MONO):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" '
            f'dominant-baseline="middle">{esc(s)}</text>')


def line(x1, y1, x2, y2, stroke, w=2.5, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{w}" stroke-linecap="round"{d}/>')


def gnd_symbol(x, y):
    """Значок земли: провод уже подходит в точку (x, y) сверху/сбоку."""
    return "".join([
        line(x, y, x, y + 8, GNDC, 2),
        line(x - 11, y + 8, x + 11, y + 8, GNDC, 2),
        line(x - 7, y + 13, x + 7, y + 13, GNDC, 2),
        line(x - 3, y + 18, x + 3, y + 18, GNDC, 2),
    ])


def arrow(x, y, direction, color):
    """Треугольник посередине провода, direction: +1 вправо, -1 влево."""
    s = 7 * direction
    return (f'<polygon points="{x - s},{y - 6} {x + s},{y} {x - s},{y + 6}" '
            f'fill="{color}"/>')


def pill(x0, y, label, color):
    w = 58
    return (f'<rect x="{x0}" y="{y - 12}" width="{w}" height="24" rx="12" '
            f'fill="none" stroke="{color}" stroke-width="2"/>'
            + text(x0 + w / 2, y + 1, label, 13, color, "middle", "bold"))


def mode_row(y, kind):
    """Элемент слева от вывода МК; провод всегда горизонтален и короток."""
    out = []
    pad = MCU_X0
    if kind == "5v":
        out.append(line(pad, y, 560, y, PWR, 2.5))
        out.append(pill(502, y, "+5V", PWR))
        out.append(text(490, y + 1, "board pull-up, verify", 12, DIM, "end"))
    elif kind == "5v_wire":
        out.append(line(pad, y, 560, y, PWR, 2.5))
        out.append(pill(502, y, "+5V", PWR))
        out.append(text(490, y + 1, "wire to +5V", 12, DIM, "end"))
    elif kind == "gnd":
        out.append(line(pad, y, 560, y, GNDC, 2.5))
        out.append(gnd_symbol(560, y))
        out.append(text(540, y + 1, "wire to GND", 12, DIM, "end"))
    elif kind == "res_gnd":
        out.append(line(pad, y, 600, y, GNDC, 2.5))
        out.append(f'<rect x="540" y="{y - 8}" width="60" height="16" rx="3" '
                   f'fill="{PANEL}" stroke="{GNDC}" stroke-width="2"/>')
        out.append(text(570, y + 1, "10k", 11, GNDC, "middle", "bold"))
        out.append(line(540, y, 500, y, GNDC, 2.5))
        out.append(gnd_symbol(500, y))
        out.append(text(480, y + 1, "GND via ~10 kΩ", 12, DIM, "end"))
    elif kind == "button":
        out.append(line(pad, y, 600, y, GNDC, 2.5))
        out.append(f'<circle cx="596" cy="{y}" r="3.5" fill="{GNDC}"/>')
        out.append(f'<circle cx="548" cy="{y}" r="3.5" fill="{GNDC}"/>')
        out.append(line(552, y - 9, 592, y - 9, GNDC, 2))
        out.append(line(572, y - 9, 572, y - 17, GNDC, 2))
        out.append(line(548, y, 520, y, GNDC, 2.5))
        out.append(gnd_symbol(520, y))
        out.append(text(500, y + 1, "tap to GND = reset", 12, DIM, "end"))
    return "".join(out)


def render(key: str) -> str:
    v = VARIANTS[key]
    uart_rows = [ROW0 + i * ROW_STEP for i in range(len(v["uart"]))]
    mode_y0 = uart_rows[-1] + ROW_STEP + GROUP_GAP
    mode_rows = [mode_y0 + i * ROW_STEP for i in range(len(v["mode"]))]
    mcu_top, mcu_bot = ROW0 - 50, mode_rows[-1] + 34
    H = mcu_bot + 64

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" role="img">',
         f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>',
         text(40, 40, v["title"], 17, ACCENT, weight="bold")]

    # МК
    p.append(f'<rect x="{MCU_X0}" y="{mcu_top}" width="{MCU_X1 - MCU_X0}" '
             f'height="{mcu_bot - mcu_top}" rx="10" fill="{PANEL}" '
             f'stroke="{BORDER}" stroke-width="2"/>')
    p.append(text(MCU_X1 - 16, mcu_top + 22, "MB90F395HA", 15, TEXT, "end", "bold"))
    p.append(text(MCU_X1 - 16, mcu_top + 42, "LQFP-120 · pin numbers", 12, DIM, "end"))

    def pin(y, num, name, color):
        p.append(f'<rect x="{MCU_X0 - 6}" y="{y - 7}" width="16" height="14" '
                 f'rx="2" fill="{color}"/>')
        p.append(text(MCU_X0 + 22, y + 1, f"{num:>3}", 14, ACCENT, weight="bold"))
        p.append(text(MCU_X0 + 62, y + 1, name, 14, TEXT, weight="bold"))

    # Переходник
    ad_top, ad_bot = ROW0 - 50, uart_rows[-1] + 80
    p.append(f'<rect x="{ADAPTER_X0}" y="{ad_top}" width="{ADAPTER_X1 - ADAPTER_X0}" '
             f'height="{ad_bot - ad_top}" rx="10" fill="{PANEL}" '
             f'stroke="{BORDER}" stroke-width="2"/>')
    p.append(text(ADAPTER_X0 + 16, ad_top + 22, "USB-UART adapter", 15, TEXT, weight="bold"))
    p.append(text(ADAPTER_X0 + 16, ad_top + 42, "level jumper: 5V", 12, PWR))

    for y, (num, name, ad, kind) in zip(uart_rows, v["uart"]):
        color = GNDC if kind == "gnd" else DATA
        p.append(line(ADAPTER_X1, y, MCU_X0, y, color, 2.5))
        if kind != "gnd":
            p.append(arrow((ADAPTER_X1 + MCU_X0) / 2, y, 1 if kind == "in" else -1, color))
        p.append(text(ADAPTER_X1 - 16, y + 1, ad, 14, TEXT, "end", "bold"))
        p.append(f'<circle cx="{ADAPTER_X1}" cy="{y}" r="4" fill="{color}"/>')
        pin(y, num, name, color)

    vcc_y = uart_rows[-1] + 44
    p.append(text(ADAPTER_X1 - 16, vcc_y + 1, "VCC", 14, DIM, "end", "bold"))
    p.append(line(ADAPTER_X1, vcc_y, ADAPTER_X1 + 26, vcc_y, DIM, 2, "4 4"))
    p.append(text(ADAPTER_X1 + 36, vcc_y + 1, "✕ leave unconnected", 12, DIM))

    for y, (num, name, kind) in zip(mode_rows, v["mode"]):
        color = PWR if kind.startswith("5v") else GNDC
        p.append(mode_row(y, kind))
        pin(y, num, name, color)

    # Питание платы — отдельно, без проводов к переходнику
    bx0, by0 = ADAPTER_X0, mode_rows[1] - 10
    p.append(f'<rect x="{bx0}" y="{by0}" width="290" height="132" rx="10" '
             f'fill="none" stroke="{BORDER}" stroke-width="2" stroke-dasharray="6 5"/>')
    p.append(text(bx0 + 16, by0 + 24, "Cluster power (X11175)", 14, TEXT, weight="bold"))
    p.append(text(bx0 + 16, by0 + 52, "pin 9  → +12V (Kl.30)", 13, PWR))
    p.append(text(bx0 + 16, by0 + 76, "pin 18 → GND  (Kl.31)", 13, GNDC))
    p.append(text(bx0 + 16, by0 + 106, "board is NOT powered by adapter", 12, DIM))

    p.append(text(40, H - 26, "Logical diagram: rows follow pin numbers, not physical "
                  "positions on the package.", 12, DIM))
    p.append("</svg>")
    return "\n".join(p) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale = False
    for key in VARIANTS:
        out = OUT_DIR / f"uart-wiring-{key}.svg"
        content = render(key)
        if args.check:
            if not out.exists() or out.read_text(encoding="utf-8") != content:
                print(f"{out} устарел -- запустите без --check", file=sys.stderr)
                stale = True
        else:
            out.write_text(content, encoding="utf-8")
            print(f"записано {out}")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
