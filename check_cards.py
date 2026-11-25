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
N_ISSUES = 5         # 매일 뉴스 개수

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
    if len(kws) != N_ISSUES:
        errors.append(f"표지 키워드: {len(kws)}개 ({N_ISSUES}개여야 해요)")
    for i, k in enumerate(kws, 1):
        length(f"표지 키워드 {i}", k, LIMITS["keyword"])
    length("마무리 한 줄", d.get("outro_line", ""), LIMITS["outro"])
    if "**" in d.get("outro_line", "") + "".join(kws):
        errors.append("표지 키워드·마무리 한 줄에는 별표(**)를 쓰지 않아요")
    if not card_date(d):
        errors.append(f"date 형식이 달라요 (예: 2026년 11월 25일 (수)) → \"{d.get('date')}\"")

    issues = d.get("issues", [])
    if len(issues) != N_ISSUES:
        errors.append(f"이슈: {len(issues)}개 ({N_ISSUES}개여야 해요)")
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
    check_style(d)
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
