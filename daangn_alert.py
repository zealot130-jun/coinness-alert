#!/usr/bin/env python3
"""당근 중고거래에 노트북용 DDR5 8GB 램이 10만원 이하로 올라오면 휴대폰으로 알림을 보냅니다.

알림 채널은 coinness_alert.py와 같습니다 (NTFY_TOPIC 또는 TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID).

설정 (환경변수)
  DAANGN_REGIONS   검색 기준 동네(쉼표로 여러 개). 기본값은 서울/대전 몇 곳.
                   전국 바로구매 매물은 어느 동네에서 검색해도 같이 나오므로
                   지역은 크게 상관없습니다. in= 값(예: 합정동-231)이나 동네 이름.
  DAANGN_ONLY_DIRECT  1(기본)이면 바로구매(택배/안전결제) 매물만 알림, 0이면 전부
  DAANGN_MAX_PRICE 최대 가격(원), 기본 100000

실행
  python3 daangn_alert.py --once   # 한 번 확인 (GitHub Actions용)
  python3 daangn_alert.py --test   # 지금 조건에 맞는 매물만 출력, 알림 안 보냄
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from coinness_alert import post  # 알림 전송은 코인니스 알림과 같은 함수를 씀

BASE = "https://www.daangn.com"
STATE_FILE = os.environ.get("DAANGN_STATE_FILE", "daangn_seen.json")
MAX_PRICE = int(os.environ.get("DAANGN_MAX_PRICE") or "100000")
DEFAULT_REGIONS = "합정동-231,강남구-386,도룡동-5820"
ONLY_DIRECT = (os.environ.get("DAANGN_ONLY_DIRECT") or "1") != "0"
SEARCH_WORDS = ["DDR5 8GB", "노트북 램 DDR5", "DDR5 8기가"]

# 제목+본문에 반드시 있어야 하는 것
MUST = [
    re.compile(r"DDR\s*5", re.I),
    re.compile(r"(?<!\d)8\s*(GB|G|기가)(?![A-Za-z])", re.I),
]
# 제목에 있으면 제외 (구매글, 데스크톱용, 노트북 본체 등)
EXCLUDE_TITLE = re.compile(
    r"삽니다|구매합니다|구합니다|매입|데스크\s*[탑톱]|UDIMM|PC\s*용|본체|"
    r"16\s*G|32\s*G|i[3579]-?\d|라이젠|ryzen|그램|갤럭시\s*북|맥북|씽크패드|thinkpad|게이밍\s*노트북",
    re.I,
)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/json", "Accept-Language": "ko-KR,ko;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def find_key(obj, key):
    """중첩된 JSON 안에서 key에 해당하는 값을 처음 찾은 것으로 돌려줌."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        obj = obj.values()
    if isinstance(obj, (list, tuple, type({}.values()))):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    return None


def resolve_region(value):
    """'역삼동-6035' 형식이면 그대로, 동네 이름이면 당근 지역 검색으로 id를 찾음."""
    value = value.strip()
    if re.search(r"-\d+$", value):
        return value
    data = get_json(f"{BASE}/kr/api/v1/regions/keyword?keyword={urllib.parse.quote(value)}")
    candidates = []

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and "name" in o:
                candidates.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    exact = [c for c in candidates if value in (c.get("name"), c.get("name3"), c.get("name2"))]
    pick = (exact or candidates or [None])[0]
    if not pick:
        raise RuntimeError(f"동네 '{value}'를 당근에서 찾지 못했어요. 웹 검색 주소의 in= 값을 넣어 주세요.")
    return f"{pick['name']}-{pick['id']}"


def get_text(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/json", "Accept-Language": "ko-KR,ko;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.headers.get("Content-Type", ""), r.read().decode("utf-8", "replace")


def articles_from_html(html):
    """검색 페이지 HTML 안에 들어 있는 데이터에서 매물 목록을 찾음."""
    for pat in (r"window\.__remixContext\s*=\s*(\{.*?\});\s*</script>",
                r'<script id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>'):
        m = re.search(pat, html, re.S)
        if m:
            try:
                found = find_key(json.loads(m.group(1)), "fleamarketArticles")
                if found:
                    return found
            except ValueError:
                pass
    # 검색엔진용 JSON-LD(상품 목록)에서 최소 정보만이라도 뽑기
    items = []
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for el in (data.get("itemListElement") or []) if isinstance(data, dict) else []:
            it = el.get("item", el) if isinstance(el, dict) else {}
            offers = it.get("offers") or {}
            url = it.get("url") or ""
            aid = re.search(r"/buy-sell/([^/?]+)", url)
            items.append({"id": aid.group(1) if aid else url, "href": url, "title": it.get("name") or "",
                          "content": it.get("description") or "", "price": offers.get("price"), "ld_json": True})
    return items


_logged = set()


def search(region, word):
    q = urllib.parse.urlencode({
        "in": region, "search": word, "only_on_sale": "true",
        "_data": "routes/kr.buy-sell._index",
    })
    ctype, body = get_text(f"{BASE}/kr/buy-sell/?{q}")
    try:
        found = find_key(json.loads(body), "fleamarketArticles")
        if found:
            return found
    except ValueError:
        pass
    # _data 방식이 안 되면 일반 검색 페이지 HTML에서 찾기
    q = urllib.parse.urlencode({"in": region, "search": word, "only_on_sale": "true"})
    ctype2, html = get_text(f"{BASE}/kr/buy-sell/?{q}")
    found = articles_from_html(html)
    if "diag" not in _logged:  # 응답 형식 확인용 로그 (한 번만)
        _logged.add("diag")
        print(f"[진단] _data 응답: {ctype} {len(body)}자, 앞부분 {body[:200]!r}")
        print(f"[진단] HTML 응답: {ctype2} {len(html)}자, 찾은 매물 {len(found)}건, "
              f"remix={'__remixContext' in html} next={'__NEXT_DATA__' in html} "
              f"ldjson={html.count('application/ld+json')} fleamarket={'fleamarketArticles' in html}")
    return found


def price_of(article):
    raw = article.get("price")
    if raw in (None, ""):
        return None
    try:
        return int(float(str(raw).replace(",", "")))
    except ValueError:
        return None


def article_id(a):
    return str(a.get("id") or a.get("href") or a.get("title"))


def article_url(a):
    href = a.get("href") or ""
    if href.startswith("http"):
        return href
    if href:
        return BASE + href
    return f"{BASE}/kr/buy-sell/{a.get('id')}/"


DIRECT_KEY = re.compile(r"direct|instant|buy_?now|purchase|parcel|delivery|shipping", re.I)
DIRECT_VALUE = re.compile(r"direct|instant|buy_?now|parcel|delivery|shipping|바로\s*구매|택배", re.I)


def direct_purchase(a):
    """바로구매 매물이면 True, 아니면 False, 응답에 그런 정보가 아예 없으면 None.

    당근 웹 응답에서 바로구매 표시 필드 이름이 공개돼 있지 않아서,
    이름에 direct/purchase/parcel/delivery 등이 들어간 필드를 넓게 봅니다.
    """
    seen_flag = False
    for k, v in a.items():
        if DIRECT_KEY.search(k):
            seen_flag = True
            if v is True or (isinstance(v, str) and DIRECT_VALUE.search(v)) or \
               (isinstance(v, (dict, list)) and v and re.search(r"true|" + DIRECT_VALUE.pattern, json.dumps(v, ensure_ascii=False), re.I)):
                return True
        elif isinstance(v, str) and k not in ("title", "content") and \
                re.search(r"바로\s*구매|direct_?purchase|buy_?now", v, re.I):
            return True
    return False if seen_flag else None


def is_match(a):
    title = a.get("title") or ""
    text = f"{title}\n{a.get('content') or ''}"
    status = str(a.get("status") or "").lower()
    if status and status not in ("ongoing", "onsale", "on_sale"):
        return False
    price = price_of(a)
    if price is None or price > MAX_PRICE:
        return False
    if EXCLUDE_TITLE.search(title):
        return False
    if ONLY_DIRECT and direct_purchase(a) is False:
        return False
    return all(p.search(text) for p in MUST)


def notify(a):
    price = price_of(a)
    region = a.get("region")
    region = region.get("name") if isinstance(region, dict) else (region or "")
    tag = "바로구매 " if direct_purchase(a) else ""
    title = f"[당근 {tag}{price:,}원] {a.get('title') or ''}".strip()
    body = (a.get("content") or "").strip()
    if len(body) > 300:
        body = body[:300] + "…"
    body = f"{region}\n{body}".strip() or title
    link = article_url(a)

    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        post(os.environ.get("NTFY_SERVER", "https://ntfy.sh"), {
            "topic": topic, "title": title[:250], "message": body, "click": link,
            "priority": 4, "tags": ["carrot"],
        })
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat:
        post(f"https://api.telegram.org/bot{token}/sendMessage", {
            "chat_id": chat, "text": f"{title}\n\n{body}\n\n{link}",
            "disable_web_page_preview": True,
        })


def load_seen():
    try:
        with open(STATE_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, ValueError):
        return None


def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(seen)[-2000:], f, ensure_ascii=False)


def main():
    args = set(sys.argv[1:])
    dry_run = "--test" in args
    regions = [r for r in (os.environ.get("DAANGN_REGIONS") or DEFAULT_REGIONS).split(",") if r.strip()]

    seen = load_seen()
    first_run = seen is None  # 첫 실행은 지금 있는 매물을 '본 것'으로만 기록 (알림 폭탄 방지)
    seen = seen or set()
    errors, found = 0, {}
    for r in regions:
        try:
            region = resolve_region(r)
        except Exception as e:
            print(f"동네 확인 실패 ({r}): {e}", file=sys.stderr)
            errors += 1
            continue
        for word in SEARCH_WORDS:
            try:
                for a in search(region, word):
                    found[article_id(a)] = a
            except Exception as e:
                print(f"검색 실패 ({region}, {word}): {e}", file=sys.stderr)
                errors += 1

    total_calls = len(regions) * (1 + len(SEARCH_WORDS))
    print(f"검색 결과 {len(found)}건 확인")
    if found:
        # 바로구매 필드 이름 확인용: 매물 하나의 필드 목록을 로그에 남김
        sample = next(iter(found.values()))
        print("매물 필드:", ", ".join(f"{k}={str(v)[:40]!r}" for k, v in sample.items()))
        flags = [direct_purchase(a) for a in found.values()]
        print(f"바로구매 {flags.count(True)}건 / 아님 {flags.count(False)}건 / 판별불가 {flags.count(None)}건")
    for aid, a in found.items():
        if not dry_run and aid in seen:
            continue
        seen.add(aid)
        if not is_match(a):
            continue
        print(f"{price_of(a):>7,}원  {a.get('title')}  {article_url(a)}", flush=True)
        if dry_run or first_run:
            continue
        try:
            notify(a)
        except Exception as e:
            print(f"  알림 전송 실패: {e}", file=sys.stderr)

    if not dry_run and (found or not first_run):
        save_seen(seen)
    if errors and errors >= total_calls:
        sys.exit(1)  # 전부 실패하면 Actions에서 실패로 보이게


if __name__ == "__main__":
    main()
