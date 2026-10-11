#!/usr/bin/env python3
"""뉴스 연결형 과목에서 쓴다. 최근 며칠 한국 뉴스 제목을 믿을 만한 언론사에서만 모아 JSON으로 출력한다.
교수는 이 중에서 오늘 가르칠 개념이 들어 있는 뉴스를 하나 고른다.

사용법: python3 news.py <과목> [며칠치]     (기본 7일)
설정: config.json 의 korea_sites, 그리고 과목의 korea_queries, korea_keywords
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import tg

KST = tg.KST
SKIP_KOREAN_SOURCE = re.compile(r"스포츠|연예|헬스|골프")
CONFIG = tg.load_config()


def fetch(url):
    for wait in (5, None):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (runway-professor)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception:
            if wait is None:
                raise
            time.sleep(wait)


def clean(text, limit=600):
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def parse_date(text):
    if not text:
        return None
    text = text.strip()
    try:
        d = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def korea_news(topic, days, since):
    sites = CONFIG.get("korea_sites", []) + topic.get("korea_extra_sites", [])
    if not sites or not topic.get("korea_queries"):
        return []
    keywords = re.compile(topic.get("korea_keywords", "."))
    site = " OR ".join(f"site:{s}" for s in sites)
    found = {}
    for q in topic["korea_queries"]:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": f"{q} ({site}) when:{days}d", "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
        for it in ET.fromstring(fetch(url)).iter("item"):
            source = it.findtext("source") or ""
            if SKIP_KOREAN_SOURCE.search(source):
                continue
            title = clean(it.findtext("title"), 200)
            title = re.sub(rf"\s+-\s+{re.escape(source)}$", "", title)  # 끝에 붙은 " - 언론사" 떼기
            # 검색어에 OR를 넣으면 주제와 상관없는 기사도 섞여 와서, 제목이 키워드에 맞는 것만 남긴다
            if not keywords.search(title) or not re.search(r"[가-힣]", title):
                continue
            d = parse_date(it.findtext("pubDate"))
            if d and d < since:  # 검색의 when:Nd가 오래된 기사를 섞어 줄 때가 있다
                continue
            found.setdefault(title, {
                "출처": source,
                "제목": title,
                "링크": it.findtext("link"),
                "날짜": d.astimezone(KST).strftime("%Y-%m-%d") if d else "",
            })
    return list(found.values())


def main():
    key, topic = tg.pick_subject(CONFIG, sys.argv)
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    since = datetime.now(timezone.utc) - timedelta(days=days)
    news = sorted(korea_news(topic, days, since), key=lambda x: x["날짜"], reverse=True)
    json.dump({"과목": topic["title"], "기준": f"최근 {days}일", "뉴스": news}, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
