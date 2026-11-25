"""뉴스 모으기·기사 저장 도우미 (feedparser + trafilatura + RapidFuzz)

사용법
  1) 최근 기사 목록(RSS) 모으기 + 비슷한 제목끼리 묶기
       python3 fetch_news.py rss --hours 24 --out out/날짜/rss.json
     → 언론사 여러 곳이 함께 다룬 주제(묶음)가 위에 나온다. 교차 보도 후보 찾기용.
  2) 기사 하나를 내려받아 본문·작성 날짜 저장 (trafilatura)
       python3 fetch_news.py article 기사주소 --issue 1 --source 연합뉴스 --dir out/날짜/research
  3) 직접 읽은 기사 저장 (네트워크가 막혀 2)가 안 될 때. 본문은 표준입력으로.
     WebFetch도 막히면 웹 검색 결과에 나온 그 기사 내용·인용문을 넣는다)
       python3 fetch_news.py save --issue 1 --source KBS --url 기사주소 --date 2026-11-25 --title "제목" --dir out/날짜/research < 본문.txt

저장된 기사(research 폴더)는 check_cards.py가 교차 보도·날짜·베끼기 검사에 쓴다.
클라우드 예약 작업 환경에서는 언론사 사이트 접속이 막혀 있을 수 있다(403). 그때는 1)·2) 대신
웹 검색·WebFetch로 읽고 3)으로 저장한다.
"""
import argparse, json, os, re, sys, time
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# 언론사 RSS 주소. 주소가 바뀌거나 막히면 그 언론사만 건너뛴다.
FEEDS = {
    "연합뉴스": "https://www.yna.co.kr/rss/news.xml",
    "한겨레": "https://www.hani.co.kr/rss/",
    "매일경제": "https://www.mk.co.kr/rss/30000001/",
    "조선일보": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
    "경향신문": "https://www.khan.co.kr/rss/rssdata/total_news.xml",
    "동아일보": "https://rss.donga.com/total.xml",
    "SBS": "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER",
}


def cmd_rss(a):
    import feedparser
    from rapidfuzz import fuzz
    import urllib.request

    cutoff = datetime.now(timezone.utc) - timedelta(hours=a.hours)
    items, failed = [], []
    for src, url in FEEDS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-card-bot)"})
            raw = urllib.request.urlopen(req, timeout=10).read()
        except Exception as e:
            failed.append(f"{src}: {e}")
            continue
        for e in feedparser.parse(raw).entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if not t:
                continue  # 날짜 없는 기사는 오늘 기사인지 알 수 없으니 뺀다
            pub = datetime(*t[:6], tzinfo=timezone.utc)
            if pub < cutoff:
                continue
            items.append({"source": src, "title": e.get("title", "").strip(),
                          "link": e.get("link", ""), "published": pub.astimezone(KST).isoformat()})

    # 비슷한 제목끼리 묶기: 언론사가 다르면서 제목이 비슷하면 같은 주제로 본다
    groups = []
    for it in items:
        for g in groups:
            if fuzz.token_set_ratio(it["title"], g[0]["title"]) >= a.similar:
                g.append(it)
                break
        else:
            groups.append([it])
    groups.sort(key=lambda g: -len({x["source"] for x in g}))
    result = {"made_at": datetime.now(KST).isoformat(), "hours": a.hours, "failed_feeds": failed,
              "groups": [{"sources": sorted({x["source"] for x in g}), "items": g} for g in groups]}
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump(result, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"기사 {len(items)}개, 주제 묶음 {len(groups)}개 (RSS 실패 {len(failed)}곳)")
    for f in failed:
        print("  실패:", f)
    for g in result["groups"][:a.top]:
        print(f"[{len(g['sources'])}곳: {', '.join(g['sources'])}] {g['items'][0]['title']}")
    if not items:
        print("RSS를 하나도 못 읽었어요. 웹 검색으로 조사하고 'save'로 기사를 저장하세요.")
        sys.exit(2)


def _save(a, text, date, title):
    os.makedirs(a.dir, exist_ok=True)
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", a.source)[:20]
    path = os.path.join(a.dir, f"issue{a.issue}_{slug}_{int(time.time() * 1000) % 100000}.json")
    json.dump({"issue": a.issue, "source": a.source, "url": a.url, "date": date, "title": title,
               "text": text}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"저장: {path} (본문 {len(text)}자, 날짜 {date or '모름'})")


def cmd_article(a):
    import trafilatura
    html = trafilatura.fetch_url(a.url)
    if not html:
        print("기사를 내려받지 못했어요(접속 막힘 등). WebFetch로 읽고 'save'로 저장하세요.")
        sys.exit(2)
    meta = trafilatura.extract_metadata(html)
    text = trafilatura.extract(html) or ""
    if len(text) < 100:
        print("본문을 뽑지 못했어요. WebFetch로 읽고 'save'로 저장하세요.")
        sys.exit(2)
    _save(a, text, (meta.date if meta else "") or "", (meta.title if meta else "") or "")


def cmd_save(a):
    text = sys.stdin.read().strip()
    if len(text) < 30:
        print("내용이 너무 짧아요. 기사 본문(또는 웹 검색 결과에 나온 그 기사 내용)을 넣어 주세요.")
        sys.exit(2)
    _save(a, text, a.date, a.title)


def main():
    p = argparse.ArgumentParser(description="뉴스 모으기·기사 저장 도우미")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rss")
    r.add_argument("--hours", type=int, default=24)
    r.add_argument("--out")
    r.add_argument("--top", type=int, default=15)
    r.add_argument("--similar", type=int, default=55, help="제목 비슷함 기준(0~100)")
    for name in ("article", "save"):
        s = sub.add_parser(name)
        if name == "article":
            s.add_argument("url")
        else:
            s.add_argument("--url", required=True)
            s.add_argument("--date", required=True, help="기사 작성 날짜 예) 2026-11-25")
            s.add_argument("--title", default="")
        s.add_argument("--issue", type=int, required=True, help="몇 번째 이슈 카드에 쓰는 기사인지(1~3)")
        s.add_argument("--source", required=True, help="언론사 이름")
        s.add_argument("--dir", required=True, help="저장 폴더 예) out/날짜/research")
    a = p.parse_args()
    {"rss": cmd_rss, "article": cmd_article, "save": cmd_save}[a.cmd](a)


if __name__ == "__main__":
    main()
