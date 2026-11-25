"""카드 문구 검사기: 이미지를 만들기 전에 CLAUDE.md 규칙을 자동으로 확인한다.

사용법
  python3 check_cards.py cards.json                       # 글자 수·강조 숫자·출처 검사
  python3 check_cards.py cards.json out/날짜/research      # + 교차 보도·기사 날짜·베끼기 검사

[오류]가 하나라도 있으면 실패(종료 코드 1). 문구를 고쳐서 다시 돌린다.
[주의]는 실패는 아니지만 다시 한번 보라는 뜻이다.
"""
import glob, json, re, sys
from datetime import date, datetime

LIMITS = {"title": 20, "what": 24, "why": 36, "next": 24, "keyword": 16, "outro": 28}
COPY_LIMIT = 85      # 기사 문장과 이 점수(0~100) 이상 비슷하면 베낀 것으로 본다
MAX_AGE_DAYS = 2     # 카드 날짜보다 이만큼 넘게 오래된 기사는 오래된 기사로 본다

errors, warns = [], []


def n(s):
    """글자 수: 공백 포함, 별표 제외"""
    return len(s.replace("**", ""))


def length(where, s, limit):
    if n(s) > limit:
        errors.append(f"{where}: {n(s)}자 (최대 {limit}자) → \"{s.replace('**', '')}\"")


def stars(where, s):
    if s.count("**") % 2:
        errors.append(f"{where}: 별표(**)가 짝이 안 맞아요 → \"{s}\"")
        return 0
    hl = re.findall(r"\*\*(.+?)\*\*", s)
    for h in hl:
        if not re.search(r"\d", h):
            errors.append(f"{where}: 숫자가 아닌 말을 강조했어요 → **{h}**")
    if len(hl) > 1:
        errors.append(f"{where}: 한 문장에 강조 숫자는 1개까지예요 ({len(hl)}개)")
    return len(hl)


def card_date(d):
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", d.get("date", ""))
    return date(int(m[1]), int(m[2]), int(m[3])) if m else None


def article_date(s):
    m = re.search(r"(\d{4})[-./년\s]+(\d{1,2})[-./월\s]+(\d{1,2})", s or "")
    try:
        return date(int(m[1]), int(m[2]), int(m[3])) if m else None
    except ValueError:
        return None


def check_text(d):
    kws = d.get("keywords", [])
    if len(kws) != 3:
        errors.append(f"표지 키워드: {len(kws)}개 (3개여야 해요)")
    for i, k in enumerate(kws, 1):
        length(f"표지 키워드 {i}", k, LIMITS["keyword"])
    length("마무리 한 줄", d.get("outro_line", ""), LIMITS["outro"])
    if "**" in d.get("outro_line", "") + "".join(kws):
        errors.append("표지 키워드·마무리 한 줄에는 별표(**)를 쓰지 않아요")
    if not card_date(d):
        errors.append(f"date 형식이 달라요 (예: 2026년 11월 25일 (수)) → \"{d.get('date')}\"")

    issues = d.get("issues", [])
    if len(issues) != 3:
        errors.append(f"이슈: {len(issues)}개 (3개여야 해요)")
    for i, it in enumerate(issues, 1):
        c = f"이슈 {i}"
        length(f"{c} 제목", it.get("title", ""), LIMITS["title"])
        if "**" in it.get("title", ""):
            errors.append(f"{c} 제목: 제목에는 별표(**)를 쓰지 않아요")
        lines = it.get("lines", [])
        if len(lines) != 3:
            errors.append(f"{c}: lines는 [무슨 일, [왜 중요한가…], 앞으로] 3칸이어야 해요")
            continue
        what, why, nxt = lines
        why = why if isinstance(why, list) else [why]
        if not 1 <= len(why) <= 2:
            errors.append(f"{c} 왜 중요한가: {len(why)}개 (1~2개)")
        length(f"{c} 무슨 일", what, LIMITS["what"])
        length(f"{c} 앞으로", nxt, LIMITS["next"])
        for j, w in enumerate(why, 1):
            length(f"{c} 왜 중요한가 {j}", w, LIMITS["why"])
        total = stars(f"{c} 무슨 일", what) + stars(f"{c} 앞으로", nxt)
        total += sum(stars(f"{c} 왜 중요한가 {j}", w) for j, w in enumerate(why, 1))
        if total > 4:
            errors.append(f"{c}: 강조 숫자 {total}개 (카드 전체 4개까지)")
        elif total < 2:
            warns.append(f"{c}: 강조 숫자 {total}개. 숫자가 의미 없는 이슈(인사·판결·외교)가 아니면 2개 이상 넣어요")
        for bad in ("귀추가 주목", "논란이 됐다", "논란이 되고"):
            if bad in json.dumps(it, ensure_ascii=False):
                errors.append(f"{c}: 쓰지 말라고 한 표현 \"{bad}\"")
        src = [s for s in re.split(r"\s*[·,]\s*", it.get("source", "")) if s]
        if len(src) < 2:
            errors.append(f"{c} 출처: 언론사가 {len(src)}곳 (2곳 이상)")


def check_research(d, folder):
    from rapidfuzz import fuzz
    arts = []
    for p in sorted(glob.glob(f"{folder}/*.json")):
        try:
            arts.append(json.load(open(p, encoding="utf-8")))
        except Exception as e:
            errors.append(f"기사 파일을 못 읽었어요: {p} ({e})")
    cd = card_date(d)
    for i, it in enumerate(d.get("issues", []), 1):
        mine = [a for a in arts if a.get("issue") == i]
        outlets = sorted({a.get("source", "") for a in mine})
        if len(outlets) < 2:
            errors.append(f"이슈 {i} 교차 보도: 저장된 기사 언론사가 {len(outlets)}곳 {outlets} (서로 다른 2곳 이상 필요)")
        for a in mine:
            ad = article_date(a.get("date", ""))
            if not ad:
                warns.append(f"이슈 {i} {a.get('source')}: 기사 날짜를 모름 → 직접 확인 ({a.get('url')})")
            elif cd and (cd - ad).days > MAX_AGE_DAYS:
                errors.append(f"이슈 {i} {a.get('source')}: {ad} 기사 — 오늘 카드({cd})보다 {(cd - ad).days}일 오래됐어요 ({a.get('url')})")
            elif cd and ad > cd:
                errors.append(f"이슈 {i} {a.get('source')}: 기사 날짜 {ad}가 카드 날짜 {cd}보다 늦어요. 날짜를 확인하세요")
        # 베끼기 검사: 카드 문장마다 그 이슈 기사 본문과 비교
        lines = it.get("lines", [])
        sents = [it.get("title", "")]
        for x in lines:
            sents += x if isinstance(x, list) else [x]
        for s in sents:
            plain = s.replace("**", "")
            if len(plain) < 10:
                continue
            for a in mine:
                score = fuzz.partial_ratio(plain, a.get("text", ""))
                if score >= COPY_LIMIT:
                    errors.append(f"이슈 {i} 베끼기 의심({score:.0f}점, {a.get('source')}): \"{plain}\" → 자기 말로 다시 쓰세요")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    check_text(d)
    if len(sys.argv) > 2:
        check_research(d, sys.argv[2])
    for e in errors:
        print("[오류]", e)
    for w in warns:
        print("[주의]", w)
    if errors:
        print(f"\n오류 {len(errors)}개: 문구를 고친 뒤 다시 검사하세요.")
        sys.exit(1)
    print(f"통과 (주의 {len(warns)}개)")


if __name__ == "__main__":
    main()
