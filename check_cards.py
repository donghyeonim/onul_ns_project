"""카드 문구 검사기: 이미지를 만들기 전에 CLAUDE.md 규칙을 자동으로 확인한다.

사용법
  python3 check_cards.py cards.json                       # 글자 수·강조 숫자·출처 검사
  python3 check_cards.py cards.json out/날짜/research      # + 교차 보도·기사 날짜·베끼기·그래픽 숫자 검사
                                                          #   + 최근 보관함(archive/)과 비슷한 뉴스 검사

[오류]가 하나라도 있으면 실패(종료 코드 1). 문구를 고쳐서 다시 돌린다.
[주의]는 실패는 아니지만 다시 한번 보라는 뜻이다.
"""
import glob, json, re, sys
from datetime import date, datetime

LIMITS = {"title": 20, "what": 24, "why": 36, "next": 24, "keyword": 16, "outro": 28}
COPY_LIMIT = 85      # 기사 문장과 이 점수(0~100) 이상 비슷하면 베낀 것으로 본다
MAX_AGE_DAYS = 1     # 기준: 최근 24시간. 카드 날짜보다 1일 넘게 오래된 기사(그제 이전)는 오류
REPEAT_DAYS = 2      # 최근 이 날짜 수만큼의 보관함과 비교해 비슷한 뉴스를 잡는다
TAGS = ["#정치", "#경제", "#사회", "#생활/문화", "#IT/과학", "#세계"]  # 네이버 뉴스 분야와 같게
GENERIC_OUTRO = ["내일 아침에도", "내일 또 만나", "다음에 또", "핵심 뉴스로 만나"]
N_ISSUES = 5         # 매일 뉴스 개수 (확인된 뉴스가 모자라면 MIN_ISSUES까지 줄여도 됨)
MIN_ISSUES = 3

# AI 말투 (CLAUDE.md 'AI 말투 빼기', backnotprop/pstack unslop 스킬(MIT)의 한국어판)
AI_PHRASES = ["주목할 만", "눈길을 끈", "눈길을 끌", "이목이 집중", "관심이 쏠", "기대를 모", "시사하는 바", "의미가 크", "중요한 역할",
              "결론적으로", "새로운 국면", "파장이 예상", "귀추가 주목", "논란이 됐다", "논란이 되고",
              "앞으로가 기대", "지켜볼 필요", "뿐만 아니라", "에 따르면 관계자"]
HEDGES = ["예정", "알려져", "전망", "보인다", "가능성", "것으로 보"]

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
    if len(kws) != len(d.get("issues", [])):
        errors.append(f"표지 키워드: {len(kws)}개 (뉴스 개수와 같아야 해요)")
    for i, k in enumerate(kws, 1):
        length(f"표지 키워드 {i}", k, LIMITS["keyword"])
    length("마무리 한 줄", d.get("outro_line", ""), LIMITS["outro"])
    if "**" in d.get("outro_line", "") + "".join(kws):
        errors.append("표지 키워드·마무리 한 줄에는 별표(**)를 쓰지 않아요")
    if not card_date(d):
        errors.append(f"date 형식이 달라요 (예: 2026년 11월 25일 (수)) → \"{d.get('date')}\"")

    issues = d.get("issues", [])
    if not MIN_ISSUES <= len(issues) <= N_ISSUES:
        errors.append(f"이슈: {len(issues)}개 ({MIN_ISSUES}~{N_ISSUES}개여야 해요)")
    elif len(issues) < N_ISSUES:
        warns.append(f"뉴스가 {len(issues)}개예요. 확인된 뉴스가 모자란 날이면 괜찮아요. 이유를 [사실 확인 결과]에 적어요")
    from collections import Counter
    cnt = Counter(it.get("tag") for it in issues)
    for t, k in cnt.items():
        if k >= 3:
            errors.append(f"분야 {t}가 {k}개예요 (같은 분야는 2개까지)")
        elif k == 2:
            warns.append(f"분야 {t}가 2개예요. 기본은 서로 다른 분야 5개. 다른 분야에 확인된 뉴스가 없을 때만 괜찮아요")
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
        if it.get("tag") not in TAGS:
            errors.append(f"{c} 분야 태그: \"{it.get('tag')}\" → {' '.join(TAGS)} 중 하나로 써요")
        check_visual(c, it)
        src = [s for s in re.split(r"\s*[·,]\s*", it.get("source", "")) if s]
        if len(src) < 2:
            errors.append(f"{c} 출처: 언론사가 {len(src)}곳 (2곳 이상)")


def ai_style(where, text):
    for ph in AI_PHRASES:
        if ph in text:
            errors.append(f"{where}: AI 말투 \"{ph}\" → 실제 사실·숫자·일정으로 바꿔 써요")
    vague = [w for w in ("크게", "매우", "상당히", "대폭", "급격히") if w in text]
    if vague:
        warns.append(f"{where}: 꾸밈말 {', '.join(vague)} → 가능하면 숫자로 ({text.replace('**', '')})")
    if re.search("[—–]", text):
        errors.append(f"{where}: 줄표(—)는 쓰지 않아요. 쉼표나 마침표로")
    if re.search("[\U0001F300-\U0001FAFF\u2600-\u27BF]", text):
        errors.append(f"{where}: 장식 이모지는 쓰지 않아요")
    if re.search("[“”‘’]", text):
        warns.append(f"{where}: 둥근 따옴표 대신 곧은 따옴표(' \")를 써요")


def sentences(it):
    out = [("제목", it.get("title", ""))]
    lines = it.get("lines", [])
    names = ["무슨 일", "왜 중요한가", "앞으로"]
    for k, x in enumerate(lines[:3]):
        for y in (x if isinstance(x, list) else [x]):
            out.append((names[k], y))
    return out


def check_style(d):
    ai_style("마무리 한 줄", d.get("outro_line", ""))
    if any(g in d.get("outro_line", "") for g in GENERIC_OUTRO):
        warns.append("마무리 한 줄이 매일 같은 인사말이에요 → 그날 뉴스를 한 줄로 묶어 써요 (예: \"금리는 오르고, 세금 고지서도 늘었어요\")")
    for i, it in enumerate(d.get("issues", []), 1):
        for name, s in sentences(it):
            ai_style(f"이슈 {i} {name}", s)
            if sum(s.count(h) for h in HEDGES) >= 2:
                errors.append(f"이슈 {i} {name}: 얼버무림 표현이 두 번 겹쳐요 → \"{s}\"")
    cap = d.get("caption")
    if cap is None:
        warns.append("캡션(caption)이 cards.json에 없어요. 넣으면 캡션도 검사해요")
        return
    ai_style("캡션", cap)
    if "**" in cap:
        errors.append("캡션: 별표(**)를 쓰지 않아요")
    tags = re.findall(r"#\S+", cap)
    if not 8 <= len(tags) <= 15:
        errors.append(f"캡션: 해시태그 {len(tags)}개 (10개 안팎, 8~15개)")
    if "AI가 요약하고 사람이 확인했습니다" not in cap:
        errors.append("캡션: \"※ AI가 요약하고 사람이 확인했습니다\" 문구가 없어요")
    if "출처:" not in cap:
        errors.append("캡션: \"출처: 언론사명\" 줄이 없어요")


HANJA_HINT = {"美": "미국", "中": "중국", "日": "일본", "北": "북한", "韓": "한국", "與": "여당", "野": "야당",
              "尹": "윤석열", "李": "이재명", "英": "영국", "佛": "프랑스", "獨": "독일", "露": "러시아", "靑": "청와대"}


def walk_strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, list):
        for y in x:
            yield from walk_strings(y)
    elif isinstance(x, dict):
        for y in x.values():
            yield from walk_strings(y)


def check_glyphs(d):
    """카드 글꼴(fonts/)에 없는 글자는 이미지에서 네모(□)로 나온다. 캡션은 카드에 안 들어가니 제외."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        warns.append("fonttools가 없어 글꼴에 없는 글자 검사를 건너뛰었어요 (pip install fonttools)")
        return
    import os
    fd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    have = None
    for f in ("NotoSansKR-Bold.otf", "NotoSansKR-Medium.otf", "NotoSerifKR-Bold.otf"):
        cm = set(TTFont(os.path.join(fd, f)).getBestCmap())
        have = cm if have is None else have & cm
    on_card = {k: v for k, v in d.items() if k not in ("caption", "why", "factcheck")}
    bad = sorted({ch for t in walk_strings(on_card) for ch in t.replace("**", "") if ord(ch) not in have and not ch.isspace()})
    for ch in bad:
        hint = f" → \"{HANJA_HINT[ch]}\"처럼 한글로" if ch in HANJA_HINT else " → 다른 글자로 바꿔요"
        errors.append(f"카드 글꼴에 없는 글자 '{ch}'(이미지에서 네모로 나와요){hint}")


def check_visual(c, it):
    v = it.get("visual")
    if not v:
        errors.append(f"{c}: 그래픽(visual)이 없어요. line·bars·timeline·versus 중 하나를 넣어요")
        return
    t = v.get("type")
    if t not in ("line", "bars", "timeline", "versus"):
        errors.append(f"{c} 그래픽: type은 line·bars·timeline·versus 중 하나 (지금: {t})")
        return
    if v.get("big"):
        length(f"{c} 그래픽 큰 글자", v["big"], 8)
    for k, x in enumerate(v.get("big_side", []), 1):
        length(f"{c} 그래픽 옆 글자 {k}", x, 14)
    if t == "line" and len(v.get("points", [])) < 2:
        errors.append(f"{c} 그래픽(line): points가 2개 이상 필요해요")
    if t == "bars" and not 2 <= len(v.get("bars", [])) <= 6:
        errors.append(f"{c} 그래픽(bars): 막대는 2~6개")
    if t == "timeline":
        st = v.get("steps", [])
        if not 2 <= len(st) <= 5:
            errors.append(f"{c} 그래픽(timeline): 단계는 2~5개")
        for date_, txt in st:
            length(f"{c} 그래픽 일정 설명", txt, 8)
    if t == "versus":
        L, R = v.get("left") or {}, v.get("right") or {}
        if not (L.get("name") and R.get("name")):
            errors.append(f"{c} 그래픽(versus): 양쪽 이름(name)이 필요해요")
        if len(L.get("points", [])) != len(R.get("points", [])):
            errors.append(f"{c} 그래픽(versus): 양쪽 입장 개수가 달라요. 중립을 위해 똑같이 맞춰요")
        for side in (L, R):
            for x in side.get("points", []):
                length(f"{c} 그래픽 입장 문장", x, 16)
    if "정치" in it.get("tag", "") and t != "versus":
        warns.append(f"{c}: 정치 이슈는 양측 입장(versus) 그래픽을 우선 고려해요")


def fmt_num(v):
    """그래프 값 → 기사에서 찾을 글자 (54.0 → '54', 4.96 → '4.96')"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def visual_numbers(v):
    found = []
    for key in ("bars", "points"):
        for row in v.get(key, []) or []:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                found.append(fmt_num(row[1]))
    ref = v.get("ref")
    if isinstance(ref, (list, tuple)) and len(ref) >= 2:
        found.append(fmt_num(ref[1]))
    for t in [v.get("big", "")] + list(v.get("big_side", []) or []):
        t = re.sub(r"[,\s]", "", str(t))
        if re.fullmatch(r"D-\d+", t):  # D-day는 날짜 계산값이라 제외
            continue
        found += re.findall(r"\d+(?:\.\d+)?", t)
    return [x for x in dict.fromkeys(found) if x]


def recent_titles(d, days=REPEAT_DAYS):
    """archive/날짜/README.md 의 '1. **제목**' 줄에서 최근 며칠 카드 제목을 읽는다."""
    import os
    from datetime import timedelta
    cd = card_date(d)
    if not cd:
        return []
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive")
    out = []
    for k in range(1, days + 1):
        day = (cd - timedelta(days=k)).isoformat()
        p = os.path.join(root, day, "README.md")
        if os.path.exists(p):
            for m in re.finditer(r"^\d+\. \*\*(.+?)\*\*", open(p, encoding="utf-8").read(), re.M):
                out.append((day, m[1]))
    return out


STOP = {"오늘", "내일", "어제", "올해", "내년", "정부", "한국", "미국", "발표", "인상", "인하", "증가", "감소", "최고", "최저", "유지", "확정", "논란"}


def words(t):
    return {w for w in re.findall(r"[가-힣A-Za-z]{2,}", t) if w not in STOP}


def check_repeat(d):
    """최근 보관함과 같은 주제면 [주의]. 큰 변화(결정·확정, 숫자가 크게 바뀜, 새 단계)일 때만 다시 쓴다."""
    from rapidfuzz import fuzz
    prev = recent_titles(d)
    for i, it in enumerate(d.get("issues", []), 1):
        t = it.get("title", "")
        for day, pt in prev:
            shared = {w for w in words(t) & words(pt) if len(w) >= 3}
            if shared or fuzz.token_set_ratio(t, pt) >= 60:
                warns.append(f"이슈 {i} '{t}'가 {day} 카드 '{pt}'와 비슷해요 → 큰 변화(결정·확정, 숫자가 크게 바뀜, 새 단계)가 아니면 빼고, 넣으면 이유를 [사실 확인 결과]에 적어요")
                break


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
        # 숫자 대조: 강조 숫자가 저장한 기사에 나오는지 (쉼표·공백 무시)
        lines = it.get("lines", [])
        norm = lambda t: re.sub(r"[,\s]", "", t)
        texts = norm(" ".join(a.get("text", "") + " " + a.get("title", "") for a in mine))
        for x in lines:
            for y in (x if isinstance(x, list) else [x]):
                for h in re.findall(r"\*\*(.+?)\*\*", y):
                    nums = re.findall(r"\d+(?:\.\d+)?", norm(h))
                    if mine and nums and not all(n in texts for n in nums):
                        warns.append(f"이슈 {i} 숫자 '{h}'가 저장한 기사에 없어요 → 계산한 값이면 [사실 확인 결과]에 계산식, 아니면 출처를 적거나 빼요")
        # 그래픽 숫자 대조: 막대·선·기준선 값과 큰 글자 속 숫자가 저장한 기사에 나오는지
        if mine:
            for h in visual_numbers(it.get("visual") or {}):
                if h not in texts:
                    warns.append(f"이슈 {i} 그래픽 숫자 '{h}'가 저장한 기사에 없어요 → 계산한 값이면 [사실 확인 결과]에 계산식을 적고, 아니면 빼요")
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
    check_style(d)
    check_glyphs(d)
    if len(sys.argv) > 2:
        check_research(d, sys.argv[2])
        check_repeat(d)
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
