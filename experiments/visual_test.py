"""[실험] 위쪽 절반은 그래픽(실제 숫자로 그린 차트), 아래쪽 절반은 작은 글씨 뉴스 카드.
본 디자인(make_cards.py)은 건드리지 않는 테스트용 파일이다.
사용법: python3 experiments/visual_test.py 출력파일.jpg
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

S = 2  # 2배로 그린 뒤 줄여서 선을 매끄럽게
W, H = 1080, 1350
PAPER = (248, 246, 241); CARD = (255, 255, 255); INK = (18, 26, 46); SUB = (64, 74, 96)
LINE = (214, 210, 200); BLUE = (30, 64, 140); GOLD = (176, 138, 60); LABEL = (112, 118, 132)
UP = (196, 54, 48)     # 한국 증시 관례: 오름=빨강
DOWN = (36, 92, 196)   # 내림=파랑
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
SERIF_B, SANS_B, SANS_M = (os.path.join(FD, f) for f in
                           ("NotoSerifKR-Bold.otf", "NotoSansKR-Bold.otf", "NotoSansKR-Medium.otf"))
_c = {}


def F(p, size):
    k = (p, size)
    if k not in _c:
        _c[k] = ImageFont.truetype(p, size * S)
    return _c[k]


def s(*v):
    return tuple(int(x * S) for x in v)


# ---- 데이터 (한국경제·뉴스1·이투데이·세계일보 보도 수치) ----
# 11/24 종가 = 4,697.51 + 308.52 = 5,006.03 / 11/23 종가 = 5,006.03 - 297.49 = 4,708.54
DAYS = [("11/23 (월)", 4708.54), ("11/24 (화)", 5006.03), ("11/25 (수)", 4697.51)]
REF = ("1월 13일 종가 4,692.64", 4692.64)

TEXT = {
    "tag": "#경제",
    "title": "코스피 6% 폭락, 전날 상승분 반납",
    "rows": [
        ("무슨 일", ["25일 코스피가 308.52포인트 내려 4,697.51에 마감했어요."]),
        ("왜 중요한가", ["종가 기준 1월 이후 약 10개월 만에 가장 낮아요.",
                       "외국인이 약 1.9조 원어치를 팔았고, 개인은 1.4조 원을 샀어요."]),
        ("앞으로", ["반도체주와 외국인 매도 흐름이 관건이에요."]),
    ],
    "source": "한국경제 · 뉴스1 · 이투데이",
}


def text_w(d, t, f):
    return d.textlength(t, font=f)


def wrap(d, t, f, maxw):
    out, cur = [], ""
    for w in t.split(" "):
        test = (cur + " " + w).strip()
        if text_w(d, test, f) <= maxw * S:
            cur = test
        else:
            out.append(cur); cur = w
    return out + [cur] if cur else out


def dashed(d, x0, x1, y, color, width, dash=10, gap=8):
    x = x0
    while x < x1:
        d.line(s(x, y, min(x + dash, x1), y), fill=color, width=width * S)
        x += dash + gap


def main(path):
    im = Image.new("RGB", s(W, H), PAPER)
    d = ImageDraw.Draw(im)
    # 머리띠 (본 디자인과 같음)
    d.line(s(80, 96, W - 80, 96), fill=INK, width=4 * S)
    d.text(s(80, 112), "오늘의 핵심 뉴스", font=F(SERIF_B, 34), fill=INK)
    d.text(s(W - 80 - 92, 120), "01 / 03", font=F(SANS_M, 28), fill=SUB)
    d.line(s(80, 172, W - 80, 172), fill=LINE, width=2 * S)

    # ---- 위쪽 절반: 그래픽 ----
    top, bot = 200, 740
    d.rectangle(s(80, top, W - 80, bot), fill=CARD)
    d.text(s(116, top + 30), "코스피 종가", font=F(SANS_B, 28), fill=LABEL)
    d.text(s(116, top + 66), "-6.16%", font=F(SERIF_B, 96), fill=DOWN)
    hx = 116 + text_w(d, "-6.16%", F(SERIF_B, 96)) / S + 24
    d.text(s(hx, top + 100), "4,697.51", font=F(SANS_B, 44), fill=INK)
    d.text(s(hx, top + 156), "하루 만에 -308.52p", font=F(SANS_M, 26), fill=SUB)

    # 차트 영역
    cx0, cx1, cy0, cy1 = 160, W - 160, top + 260, bot - 70
    lo, hi = 4600, 5100
    ys = lambda v: cy1 - (v - lo) / (hi - lo) * (cy1 - cy0)
    xs = [cx0 + i * (cx1 - cx0) / (len(DAYS) - 1) for i in range(len(DAYS))]
    for g in (4700, 4900, 5100):  # 옅은 눈금
        d.line(s(cx0 - 30, ys(g), cx1 + 30, ys(g)), fill=(236, 234, 228), width=1 * S)
    dashed(d, cx0 - 30, cx1 + 30, ys(REF[1]), GOLD, 2)
    d.text(s(cx0 - 30, ys(REF[1]) + 8), REF[0], font=F(SANS_M, 22), fill=GOLD)
    # 선: 오른 구간 빨강, 내린 구간 파랑
    for i in range(len(DAYS) - 1):
        a, b = DAYS[i][1], DAYS[i + 1][1]
        d.line(s(xs[i], ys(a), xs[i + 1], ys(b)), fill=UP if b > a else DOWN, width=5 * S)
        mx, my = (xs[i] + xs[i + 1]) / 2, (ys(a) + ys(b)) / 2
        lab = f"{'+' if b > a else '-'}{abs(b - a) / a * 100:.2f}%"
        f = F(SANS_B, 26)
        lw = text_w(d, lab, f) / S
        # 선과 겹치지 않게: 오른 구간은 선의 왼쪽 위, 내린 구간은 선의 오른쪽 위
        lx = mx - lw - 18 if b > a else mx + 18
        d.text(s(lx, my - 54), lab, font=f, fill=UP if b > a else DOWN)
    for (lab, v), x in zip(DAYS, xs):
        r = 9
        d.ellipse(s(x - r, ys(v) - r, x + r, ys(v) + r), fill=CARD, outline=INK, width=4 * S)
        val = f"{v:,.0f}"
        d.text(s(x - text_w(d, val, F(SANS_B, 24)) / S / 2, ys(v) - 46), val, font=F(SANS_B, 24), fill=INK)
        d.text(s(x - text_w(d, lab, F(SANS_M, 22)) / S / 2, cy1 + 26), lab, font=F(SANS_M, 22), fill=SUB)

    # ---- 아래쪽 절반: 작은 글씨 본문 ----
    y = bot + 34
    ft = F(SANS_B, 26)
    tw = text_w(d, TEXT["tag"], ft) / S
    d.rectangle(s(80, y, 80 + tw + 32, y + 44), outline=BLUE, width=3 * S)
    d.text(s(96, y + 4), TEXT["tag"], font=ft, fill=BLUE)
    y += 64
    d.text(s(80, y), TEXT["title"], font=F(SERIF_B, 50), fill=INK)
    y += 84
    fl, fb = F(SANS_B, 26), F(SANS_M, 29)
    for k, (label, items) in enumerate(TEXT["rows"]):
        d.line(s(80, y - 14, W - 80, y - 14), fill=LINE, width=1 * S)
        d.text(s(80, y), label, font=fl, fill=GOLD if k == 1 else BLUE)
        yy = y - 2
        for t in items:
            for li, ln in enumerate(wrap(d, t, fb, W - 80 - 250)):
                if len(items) > 1 and li == 0:
                    d.text(s(232, yy), "·", font=fb, fill=GOLD)
                d.text(s(250, yy), ln, font=fb, fill=INK)
                yy += 44
        y = yy + 22
    if y > H - 140:
        raise SystemExit(f"본문이 너무 길어요 (y={y})")
    # 바닥
    d.line(s(80, H - 130, W - 80, H - 130), fill=LINE, width=2 * S)
    d.text(s(80, H - 100), "@onul_ns", font=F(SANS_M, 28), fill=INK)
    src = f"출처: {TEXT['source']}"
    d.text(s(W - 80 - text_w(d, src, F(SANS_M, 26)) / S, H - 98), src, font=F(SANS_M, 26), fill=LABEL)

    im.resize((W, H), Image.LANCZOS).save(path, "JPEG", quality=92)
    print(path, "본문 끝 y =", y)


if __name__ == "__main__":
    main(sys.argv[1])
