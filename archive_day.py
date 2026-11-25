"""그날 결과를 저장소의 archive/날짜/ 폴더에 정리하고 목차(archive/README.md)에 한 줄 추가한다.

사용법: python3 archive_day.py cards.json out/2026-11-26
  → archive/2026-11-26/card_01.jpg … card_07.jpg, archive/2026-11-26/README.md
  → archive/README.md 맨 위(최신순)에 그날 줄 추가(같은 날짜가 있으면 바꿈)

cards.json에 "caption", "why"([{title, kind, reason}]), "factcheck"(글) 칸이 있으면 함께 적는다.
실패한 날 기록: python3 archive_day.py --failed 2026-11-26 "어느 단계에서 무슨 오류"
"""
import json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(ROOT, "archive")
INDEX = os.path.join(ARCH, "README.md")
HEAD = """# 카드뉴스 보관함

매일 아침 예약 작업이 만든 @onul_ns 카드뉴스를 날짜별로 모아 둔 곳이에요. 날짜를 누르면 카드 7장, 캡션, 고른 이유, 사실 확인 결과가 나와요.

| 날짜 | 표지 | 뉴스 | 상태 |
|---|---|---|---|
<!-- rows -->
"""
WEEK = "월화수목금토일"


def md(t):
    """표 칸에 넣을 글: | 와 줄바꿈 정리"""
    return str(t).replace("|", "\\|").replace("\n", " ")


def index_row(date, row):
    os.makedirs(ARCH, exist_ok=True)
    text = open(INDEX, encoding="utf-8").read() if os.path.exists(INDEX) else HEAD
    if "<!-- rows -->" not in text:
        text = HEAD
    head, rows = text.split("<!-- rows -->", 1)
    lines = [ln for ln in rows.strip("\n").split("\n") if ln.strip() and not ln.startswith(f"| [{date}]")]
    lines.append(row)
    lines.sort(reverse=True)  # 날짜 최신순 (행이 "| [YYYY-MM-DD]"로 시작)
    open(INDEX, "w", encoding="utf-8").write(head + "<!-- rows -->\n" + "\n".join(lines) + "\n")


def day_label(date):
    import datetime
    y, m, d = map(int, date.split("-"))
    return f"{m}월 {d}일 ({WEEK[datetime.date(y, m, d).weekday()]})"


def archive_ok(cards_json, outdir):
    d = json.load(open(cards_json, encoding="utf-8"))
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", d.get("date", ""))
    if not m:
        sys.exit("cards.json의 date에서 날짜를 못 읽었어요")
    date = f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}"
    dst = os.path.join(ARCH, date)
    os.makedirs(dst, exist_ok=True)
    cards = sorted(f for f in os.listdir(outdir) if re.fullmatch(r"card_\d\d\.jpg", f))
    if not cards:
        sys.exit(f"{outdir}에 card_XX.jpg가 없어요")
    for f in cards:
        shutil.copyfile(os.path.join(outdir, f), os.path.join(dst, f))
    issues = d.get("issues", [])
    out = [f"# {day_label(date)} 오늘의 핵심 뉴스", "", "[← 보관함 목차](../README.md)", ""]
    out += ["## 카드", ""] + [f"![{i + 1}번 카드]({f})" for i, f in enumerate(cards)] + [""]
    if d.get("caption"):
        out += ["## 캡션 (그대로 복사)", "", "```", d["caption"].strip(), "```", ""]
    why = d.get("why") or []
    out += ["## 왜 이 뉴스인가 (게시용 아님)", ""]
    for i, it in enumerate(issues):
        w = why[i] if i < len(why) and isinstance(why[i], dict) else {}
        kind = f" ({w['kind']})" if w.get("kind") else ""
        reason = f": {w['reason']}" if w.get("reason") else ""
        out.append(f"{i + 1}. **{it.get('title', '')}**{kind}{reason} · 출처 {it.get('source', '')}")
    out.append("")
    if d.get("factcheck"):
        out += ["## 사실 확인 결과 (게시용 아님)", "", d["factcheck"].strip(), ""]
    open(os.path.join(dst, "README.md"), "w", encoding="utf-8").write("\n".join(out))
    titles = " · ".join(md(it.get("title", "")) for it in issues)
    index_row(date, f"| [{date}]({date}/README.md) | <img src=\"{date}/{cards[0]}\" width=\"90\"> | {titles} | ✅ {len(issues)}개 |")
    print(f"보관 완료: archive/{date}/ (카드 {len(cards)}장)")


def archive_failed(date, reason):
    dst = os.path.join(ARCH, date)
    os.makedirs(dst, exist_ok=True)
    open(os.path.join(dst, "README.md"), "w", encoding="utf-8").write(
        f"# {day_label(date)} 카드뉴스 실패\n\n[← 보관함 목차](../README.md)\n\n{reason.strip()}\n")
    index_row(date, f"| [{date}]({date}/README.md) | | {md(reason)[:80]} | ❌ 실패 |")
    print(f"실패 기록: archive/{date}/")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--failed":
        archive_failed(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3:
        archive_ok(sys.argv[1], sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
