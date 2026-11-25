"""@onul_ns 카드뉴스 이미지 생성기 (밝은 격식체 디자인)
사용법: python3 make_cards.py cards.json 출력폴더
→ 1080x1350 JPEG(표지 + 이슈 카드 + 마무리)와 휴대폰 크기 미리보기(preview_phone.jpg)
"""
import json, sys, os, random
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
PAPER = (248, 246, 241)
CARD = (255, 255, 255)
INK = (18, 26, 46)
SUB = (64, 74, 96)
LINE = (214, 210, 200)
BLUE = (30, 64, 140)
GOLD = (176, 138, 60)
SKY = (226, 230, 238)
TINT = (236, 241, 250)
LABEL = (112, 118, 132)

# 글꼴: 이 파일 옆 fonts 폴더의 Noto 한국어 글꼴 사용(무료 글꼴, SIL OFL)
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
SERIF_B = os.path.join(FONT_DIR, "NotoSerifKR-Bold.otf")
SANS_B = os.path.join(FONT_DIR, "NotoSansKR-Bold.otf")
SANS_M = os.path.join(FONT_DIR, "NotoSansKR-Medium.otf")
_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, size)
    return _cache[key]


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
            continue
        if cur:
            lines.append(cur)
        cur = ""
        for ch in word:
            if draw.textlength(cur + ch, font=fnt) <= max_w:
                cur += ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def draw_lines(draw, xy, text, fnt, fill, max_w, gap=1.35):
    x, y = xy
    for line in wrap(draw, text, fnt, max_w):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * gap)
    return y


def background():
    random.seed(11)
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    base = H - 150
    x = 40
    while x < W - 40:
        bw = random.randint(50, 110)
        bh = random.randint(60, 230)
        if x + bw > W - 40:
            bw = W - 40 - x
            if bw < 30:
                break
        d.rectangle((x, base - bh, x + bw, base), outline=SKY, width=3)
        for wy in range(base - bh + 20, base - 10, 34):
            d.line((x + 14, wy, x + bw - 14, wy), fill=SKY, width=2)
        x += bw + random.randint(6, 18)
    d.line((40, base, W - 40, base), fill=LINE, width=2)
    return im


BG = None
SKY_TOP = H - 150 - 230  # 스카이라인 그림에서 가장 높은 건물의 윗선


class TooLong(Exception):
    pass


def page(plain=False):
    global BG
    if plain:
        im = Image.new("RGB", (W, H), PAPER)
        return im, ImageDraw.Draw(im)
    if BG is None:
        BG = background()
    im = BG.copy()
    return im, ImageDraw.Draw(im)


def masthead(dr, d, right_text):
    dr.line((80, 96, W - 80, 96), fill=INK, width=4)
    dr.text((80, 112), "오늘의 핵심 뉴스", font=font(SERIF_B, 34), fill=INK)
    fs = font(SANS_M, 28)
    dr.text((W - 80 - dr.textlength(right_text, font=fs), 120), right_text, font=fs, fill=SUB)
    dr.line((80, 172, W - 80, 172), fill=LINE, width=2)


def footer(dr, handle, right=""):
    f = font(SANS_M, 28)
    dr.line((80, H - 130, W - 80, H - 130), fill=LINE, width=2)
    left = f"@{handle}" if handle else "오늘의 핵심 뉴스"
    dr.text((80, H - 100), left, font=f, fill=INK)
    if right:
        fr = font(SANS_M, 26)
        dr.text((W - 80 - dr.textlength(right, font=fr), H - 98), right, font=fr, fill=LABEL)


def cover(d, total):
    im, dr = page()
    masthead(dr, d, d["date"])
    dr.text((80, 220), "TODAY'S BRIEFING", font=font(SANS_B, 30), fill=GOLD)
    dr.text((80, 262), "오늘의", font=font(SERIF_B, 104), fill=INK)
    dr.text((80, 386), f"핵심 뉴스 {len(d['keywords'])}", font=font(SERIF_B, 104), fill=BLUE)
    y = 580
    few = len(d["keywords"]) <= 3
    fk, fn = (font(SANS_M, 48), font(SERIF_B, 48)) if few else (font(SANS_M, 43), font(SERIF_B, 43))
    step = 100 if few else 76
    for i, kw in enumerate(d["keywords"], 1):
        kl = wrap(dr, kw, fk, W - 260)
        if len(kl) > 1:
            raise TooLong(f"표지 키워드 {i}이(가) 한 줄을 넘습니다. 키워드를 줄이세요: {kw}")
        dr.text((80, y), f"{i:02d}", font=fn, fill=GOLD)
        dr.text((170, y), kl[0], font=fk, fill=INK)
        y += step
        ly = y - (22 if few else 10)
        dr.line((80, ly, W - 80, ly), fill=LINE, width=2)
    footer(dr, d.get("handle"))
    return im


def rich_words(text):
    out = []
    for i, part in enumerate(text.split("**")):
        if i % 2 == 1:  # 강조 숫자(예: "1조 원")는 줄바꿈으로 쪼개지 않게 한 덩어리로
            if part.strip():
                out.append((part.strip(), True))
            continue
        for w in part.split(" "):
            if w:
                out.append((w, False))
    plain = text.replace("**", "")
    merged, pos = [], 0
    for w, e in out:
        idx = plain.find(w, pos)
        if merged and idx == pos and plain[pos - 1] != " ":
            merged[-1].append((w, e))
        else:
            merged.append([(w, e)])
        pos = idx + len(w)
    return merged


def wrap_rich(draw, text, fn, fe, max_w):
    def wlen(word):
        return sum(draw.textlength(t, font=fe if e else fn) for t, e in word)
    space = draw.textlength(" ", font=fn)
    lines, cur, cur_w = [], [], 0
    for word in rich_words(text):
        ww = wlen(word)
        add = ww if not cur else cur_w + space + ww
        if add <= max_w or not cur:
            cur.append(word)
            cur_w = add
        else:
            lines.append(cur)
            cur, cur_w = [word], ww
    if cur:
        lines.append(cur)
    return lines


def draw_rich_line(draw, x, y, line, fn, fe, color, ecolor):
    space = draw.textlength(" ", font=fn)
    for word in line:
        for t, e in word:
            f = fe if e else fn
            draw.text((x, y), t, font=f, fill=ecolor if e else color)
            x += draw.textlength(t, font=f)
        x += space


def issue(d, it, idx, n_issues, total):
    im, dr = page(plain=True)
    masthead(dr, d, f"{idx:02d} / {n_issues:02d}")
    ft = font(SANS_B, 30)
    tag = it["tag"]
    tw = dr.textlength(tag, font=ft)
    dr.rectangle((80, 214, 80 + tw + 40, 266), outline=BLUE, width=3)
    dr.text((100, 220), tag, font=ft, fill=BLUE)
    labels = ["무슨 일", "왜 중요한가", "앞으로"]
    sections = [b if isinstance(b, list) else [b] for b in it["lines"]]
    limit = H - 160
    fitted = False
    for ts, bs in [(72, 40), (68, 39), (64, 38), (60, 37), (58, 36)]:
        ftitle, fb, fe = font(SERIF_B, ts), font(SANS_M, bs), font(SANS_B, bs)
        tl = wrap(dr, it["title"], ftitle, W - 160)
        lh = int(bs * 1.5)
        wrapped = []
        h = 300 + len(tl) * int(ts * 1.3) + 36
        for items in sections:
            bullet = len(items) > 1
            maxw = W - 240 - (34 if bullet else 0)
            ws = [wrap_rich(dr, t, fb, fe, maxw) for t in items]
            wrapped.append(ws)
            h += 66 + sum(len(w) for w in ws) * lh + (len(items) - 1) * 12 + 24 + 22
        if h <= limit:
            fitted = True
            break
    if not fitted:
        raise TooLong(f"이슈 {idx} 카드 글이 너무 깁니다. 제목이나 문장을 줄이세요.")
    y = draw_lines(dr, (80, 300), it["title"], ftitle, INK, W - 160, 1.3) + 36
    fl = font(SANS_B, 30)
    for k, (label, ws) in enumerate(zip(labels, wrapped)):
        bullet = len(ws) > 1
        box_h = 66 + sum(len(w) for w in ws) * lh + (len(ws) - 1) * 12 + 24
        key = (k == 1)
        dr.rectangle((80, y, W - 80, y + box_h), fill=TINT if key else CARD)
        dr.rectangle((80, y, 86, y + box_h), fill=GOLD if key else BLUE)
        dr.text((114, y + 20), label, font=fl, fill=GOLD if key else BLUE)
        yy = y + 66
        for w in ws:
            for li, line in enumerate(w):
                x = 114
                if bullet:
                    if li == 0:
                        dr.text((114, yy), "·", font=fe, fill=GOLD)
                    x = 148
                draw_rich_line(dr, x, yy, line, fb, fe, INK, BLUE)
                yy += lh
            yy += 12
        y += box_h + 22
    src = it.get("source")
    footer(dr, d.get("handle"), f"출처: {src}" if src else "")
    return im


def outro(d, total):
    im, dr = page()
    masthead(dr, d, d["date"])
    dr.text((80, 300), "오늘의 한 줄", font=font(SANS_B, 32), fill=GOLD)
    y = draw_lines(dr, (80, 352), d["outro_line"], font(SERIF_B, 68), INK, W - 160, 1.35)
    dr.line((80, y + 40, 200, y + 40), fill=BLUE, width=5)
    cta = d.get("cta", "매일 아침, 핵심 뉴스를 정리해 드립니다")
    y = draw_lines(dr, (80, y + 80), cta, font(SANS_M, 40), SUB, W - 160, 1.4)
    if d.get("handle"):
        dr.text((80, y + 20), f"@{d['handle']}", font=font(SANS_B, 46), fill=BLUE)
        y += 20 + int(46 * 1.35)
    if y > SKY_TOP:
        raise TooLong("마무리 한 줄(outro_line)이 너무 깁니다. 문장을 줄이세요.")
    footer(dr, d.get("handle"), "AI가 요약하고 사람이 확인했습니다")
    return im


def main(src, out):
    d = json.load(open(src, encoding="utf-8"))
    os.makedirs(out, exist_ok=True)
    n = len(d["issues"])
    total = n + 2
    pages = [cover(d, total)] + [issue(d, it, i, n, total) for i, it in enumerate(d["issues"], 1)] + [outro(d, total)]
    for i, p in enumerate(pages, 1):
        path = os.path.join(out, f"card_{i:02d}.jpg")
        p.save(path, "JPEG", quality=92)
        print(path)
    pw, ph = 390, int(390 * H / W)
    sheet = Image.new("RGB", (len(pages) * (pw + 12), ph), (200, 200, 200))
    for i, p in enumerate(pages):
        sheet.paste(p.resize((pw, ph), Image.LANCZOS), (i * (pw + 12), 0))
    prev = os.path.join(out, "preview_phone.jpg")
    sheet.save(prev, "JPEG", quality=90)
    print(prev)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
