"""이슈 카드 위쪽 절반 그래픽 그리기 (실제 숫자·사실로 그리는 신문식 그래픽)

종류(cards.json 이슈의 "visual")
  line      숫자 흐름(주가·환율 등)      points, ref(선택), updown(선택)
  bars      숫자 비교(올해 vs 작년 등)   bars, unit(선택), highlight(선택)
  timeline  일정·절차                    steps, now(선택)
  versus    쟁점의 양측 입장(정치 등)     left, right
공통(선택): label(왼쪽 위 작은 제목), big(큰 숫자/글자), big_color(up/down/blue/ink), big_side([굵은 줄, 작은 줄])

draw_panel(v, w, h, progress) → PIL 이미지. progress 0~1은 영상용(선이 그려지는 정도). 사진·AI 그림은 쓰지 않는다.
"""
import os
from PIL import Image, ImageDraw, ImageFont

S = 2  # 2배로 그린 뒤 줄여서 선을 매끄럽게
CARD = (255, 255, 255); INK = (18, 26, 46); SUB = (64, 74, 96); LINE = (214, 210, 200)
BLUE = (30, 64, 140); GOLD = (176, 138, 60); LABEL = (112, 118, 132); GRID = (236, 234, 228)
MUTED = (200, 206, 220)
UP = (196, 54, 48)    # 한국 증시 관례: 오름=빨강
DOWN = (36, 92, 196)  # 내림=파랑
COLORS = {"up": UP, "down": DOWN, "blue": BLUE, "ink": INK, "gold": GOLD}

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
SERIF_B = os.path.join(FD, "NotoSerifKR-Bold.otf")
SANS_B = os.path.join(FD, "NotoSansKR-Bold.otf")
SANS_M = os.path.join(FD, "NotoSansKR-Medium.otf")
_fc = {}
TYPES = ("line", "bars", "timeline", "versus")


class VisualError(Exception):
    pass


def F(p, size):
    k = (p, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(p, int(size * S))
    return _fc[k]


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class P:
    """1배 좌표로 그리면 내부에서 2배로 바꿔 그리는 도우미"""

    def __init__(self, w, h):
        self.im = Image.new("RGB", (w * S, h * S), CARD)
        self.d = ImageDraw.Draw(self.im)

    def tw(self, t, f):
        return self.d.textlength(t, font=f) / S

    def text(self, x, y, t, f, fill):
        self.d.text((x * S, y * S), t, font=f, fill=fill)

    def ctext(self, cx, y, t, f, fill):
        self.text(cx - self.tw(t, f) / 2, y, t, f, fill)

    def line(self, x0, y0, x1, y1, fill, width):
        self.d.line((x0 * S, y0 * S, x1 * S, y1 * S), fill=fill, width=int(width * S))

    def rect(self, x0, y0, x1, y1, **k):
        if "width" in k:
            k["width"] = int(k["width"] * S)
        self.d.rectangle((x0 * S, y0 * S, x1 * S, y1 * S), **k)

    def dot(self, x, y, r, fill, outline, width):
        self.d.ellipse(((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S), fill=fill, outline=outline,
                       width=int(width * S))

    def dashed(self, x0, x1, y, fill, width, dash=10, gap=8):
        x = x0
        while x < x1:
            self.line(x, y, min(x + dash, x1), y, fill, width)
            x += dash + gap

    def wrap(self, t, f, maxw):
        out, cur = [], ""
        for w in t.split(" "):
            test = (cur + " " + w).strip()
            if self.tw(test, f) <= maxw or not cur:
                cur = test
            else:
                out.append(cur)
                cur = w
        return out + ([cur] if cur else [])


def header(p, v, pad):
    """왼쪽 위 작은 제목 + (있으면) 큰 숫자. 그래픽이 시작할 y를 돌려준다."""
    y = pad
    if v.get("label"):
        p.text(pad, y, v["label"], F(SANS_B, 28), LABEL)
        y += 44
    if v.get("big"):
        fb = F(SERIF_B, 92)
        col = COLORS.get(v.get("big_color", "blue"), BLUE)
        p.text(pad, y - 8, v["big"], fb, col)
        x = pad + p.tw(v["big"], fb) + 26
        side = v.get("big_side", [])
        if len(side) > 0:
            p.text(x, y + 22, side[0], F(SANS_B, 42), INK)
        if len(side) > 1:
            p.text(x, y + 76, side[1], F(SANS_M, 26), SUB)
        y += 130
    return y + 10


def draw_line(p, v, w, h, y0, t):
    pts = v["points"]
    if len(pts) < 2:
        raise VisualError("line: points가 2개 이상 필요해요")
    vals = [float(b) for _, b in pts] + ([float(v["ref"][1])] if v.get("ref") else [])
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    lo, hi = lo - span * 0.25, hi + span * 0.35
    cx0, cx1, cy0, cy1 = 80, w - 80, y0 + 50, h - 78
    ys = lambda val: cy1 - (val - lo) / (hi - lo) * (cy1 - cy0)
    xs = [cx0 + i * (cx1 - cx0) / (len(pts) - 1) for i in range(len(pts))]
    for k in range(3):
        gy = cy0 + k * (cy1 - cy0) / 2
        p.line(cx0 - 40, gy, cx1 + 40, gy, GRID, 1)
    if v.get("ref"):
        p.dashed(cx0 - 40, cx1 + 40, ys(float(v["ref"][1])), GOLD, 2)
        p.text(cx0 - 40, ys(float(v["ref"][1])) + 8, v["ref"][0], F(SANS_M, 22), GOLD)
    dec = int(v.get("decimals", 0))
    unit = v.get("unit", "")
    updown = v.get("updown", False)
    segs = len(pts) - 1
    prog = ease(t) * segs
    for i in range(segs):
        part = max(0.0, min(1.0, prog - i))
        if part <= 0:
            break
        a, b = float(pts[i][1]), float(pts[i + 1][1])
        col = (UP if b > a else DOWN) if updown else BLUE
        x1 = xs[i] + (xs[i + 1] - xs[i]) * part
        y1 = ys(a) + (ys(b) - ys(a)) * part
        p.line(xs[i], ys(a), x1, y1, col, 5)
        if part >= 1 and updown:
            lab = f"{'+' if b > a else '-'}{abs(b - a) / a * 100:.2f}%"
            f = F(SANS_B, 26)
            mx, my = (xs[i] + xs[i + 1]) / 2, (ys(a) + ys(b)) / 2
            lx = mx - p.tw(lab, f) - 18 if b > a else mx + 18
            p.text(lx, my - 54, lab, f, col)
    for i, ((lab, val), x) in enumerate(zip(pts, xs)):
        if prog < i - 0.001:
            break
        val = float(val)
        p.dot(x, ys(val), 9, CARD, INK, 4)
        s = f"{val:,.{dec}f}{unit}"
        p.ctext(x, ys(val) - 46, s, F(SANS_B, 24), INK)
    for (lab, _), x in zip(pts, xs):
        p.ctext(x, cy1 + 28, lab, F(SANS_M, 22), SUB)


def draw_bars(p, v, w, h, y0, t):
    bars = v["bars"]
    if not 2 <= len(bars) <= 6:
        raise VisualError("bars: 막대는 2~6개")
    unit = v.get("unit", "")
    dec = int(v.get("decimals", 0))
    hl = v.get("highlight", len(bars) - 1)
    top = max(float(b) for _, b in bars) or 1
    cx0, cx1, cy0, cy1 = 80, w - 80, y0 + 50, h - 78
    n = len(bars)
    slot = (cx1 - cx0) / n
    bw = min(120, slot * 0.55)
    p.line(cx0 - 20, cy1, cx1 + 20, cy1, LINE, 2)
    for i, (lab, val) in enumerate(bars):
        val = float(val)
        g = ease(t * 1.3 - i * 0.12)
        bh = (cy1 - cy0) * (val / top) * g
        cx = cx0 + slot * (i + 0.5)
        col = BLUE if i == hl else MUTED
        if bh > 0:
            p.rect(cx - bw / 2, cy1 - bh, cx + bw / 2, cy1, fill=col)
        if g >= 0.98:
            p.ctext(cx, cy1 - bh - 40, f"{val:,.{dec}f}{unit}", F(SANS_B, 26), INK)
        p.ctext(cx, cy1 + 22, lab, F(SANS_M, 22), SUB)


def draw_timeline(p, v, w, h, y0, t):
    steps = v["steps"]
    if not 2 <= len(steps) <= 5:
        raise VisualError("timeline: 단계는 2~5개")
    now = v.get("now", 0)
    n = len(steps)
    lx0, lx1 = 100, w - 100
    ly = y0 + max(70, (h - y0) / 2 - 60)  # 남는 공간 가운데쯤
    xs = [lx0 + i * (lx1 - lx0) / (n - 1) for i in range(n)]
    shown = ease(t) * (n - 1)
    p.line(lx0, ly, lx0 + (lx1 - lx0) * min(1, shown / (n - 1)), ly, LINE, 4)
    maxw = (lx1 - lx0) / (n - 1) - 16 if n > 1 else 300
    for i, ((date, txt), x) in enumerate(zip(steps, xs)):
        if shown < i - 0.001:
            break
        here = i == now
        p.dot(x, ly, 14 if here else 10, BLUE if here else CARD, BLUE, 4)
        if here:
            p.ctext(x, ly - 64, "지금", F(SANS_B, 26), BLUE)
        p.ctext(x, ly + 32, date, F(SANS_B, 34), BLUE if here else INK)
        yy = ly + 88
        for ln in p.wrap(txt, F(SANS_M, 28), maxw):
            p.ctext(x, yy, ln, F(SANS_M, 28), INK if here else SUB)
            yy += 40
        if yy > h - 10:
            raise VisualError("timeline: 일정 설명이 너무 길어요. 줄이세요")


def draw_versus(p, v, w, h, y0, t):
    sides = [v.get("left"), v.get("right")]
    if not all(s and s.get("name") and s.get("points") for s in sides):
        raise VisualError("versus: left/right 모두 name과 points가 필요해요")
    colw = (w - 80 * 2 - 60) / 2
    xs = [80, 80 + colw + 60]
    p.ctext(w / 2, y0 + 70, "VS", F(SERIF_B, 34), LABEL)
    p.line(w / 2, y0 + 120, w / 2, h - 50, LINE, 2)
    # 나타나는 순서: 왼쪽 이름 → 오른쪽 이름 → 왼쪽 입장1 → 오른쪽 입장1 → … (양쪽을 번갈아 똑같이)
    npts = max(len(s["points"][:3]) for s in sides)
    slots = 2 + 2 * npts
    def shown(k):
        return ease((t * slots - k) * 1.4)
    for k, (s, x) in enumerate(zip(sides, xs)):
        a = shown(k)
        if a <= 0:
            continue
        y = y0 + 40 + (1 - a) * 24
        p.text(x, y, s["name"], F(SANS_B, 34), INK)
        p.line(x, y + 54, x + (colw * a), y + 54, INK, 3)
    for k, (s, x) in enumerate(zip(sides, xs)):
        y = y0 + 116
        for j, pt in enumerate(s["points"][:3]):
            lines = p.wrap(pt, F(SANS_M, 27), colw - 26)
            a = shown(2 + j * 2 + k)
            if a > 0:
                yy = y + (1 - a) * 24
                p.text(x, yy, "·", F(SANS_B, 27), GOLD)
                for li, ln in enumerate(lines):
                    p.text(x + 22, yy + li * 40, ln, F(SANS_M, 27), INK)
            y += len(lines) * 40 + 14
            if y > h - 16:
                raise VisualError("versus: 입장 문장이 너무 길어요. 줄이세요")


def draw_panel(v, w, h, progress=1.0):
    typ = v.get("type")
    if typ not in TYPES:
        raise VisualError(f"visual type은 {', '.join(TYPES)} 중 하나여야 해요 (지금: {typ})")
    p = P(w, h)
    y0 = header(p, v, 36)
    {"line": draw_line, "bars": draw_bars, "timeline": draw_timeline, "versus": draw_versus}[typ](
        p, v, w, h, y0, progress)
    return p.im.resize((w, h), Image.LANCZOS)
