import os
import json
import re
import html
from pathlib import Path

import requests


NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"
STATE_FILE = Path("state.json")
QUERY = "이노션"


def clean_text(text: str) -> str:
    """네이버 뉴스 API 응답에 포함된 HTML 태그를 제거합니다."""
    text = html.unescape(text or "")
    text = re.sub(r"<.*?>", "", text)
    return text.strip()


def load_state() -> dict:
    """이미 전송한 기사 링크 목록을 불러옵니다."""
    if not STATE_FILE.exists():
        return {
            "initialized": False,
            "seen_links": []
        }

    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    """이미 전송한 기사 링크 목록을 저장합니다."""
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_naver_news() -> list[dict]:
    """네이버 뉴스 검색 API에서 최신 뉴스를 가져옵니다."""
    client_id = os.environ["NAVER_CLIENT_ID"]
    client_secret = os.environ["NAVER_CLIENT_SECRET"]

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    params = {
        "query": QUERY,
        "display": 100,
        "start": 1,
        "sort": "date",
    }

    response = requests.get(
        NAVER_API_URL,
        headers=headers,
        params=params,
        timeout=15,
    )

    if response.status_code >= 400:
        print("Naver API failed")
        print("Status code:", response.status_code)
        print("Response body:", response.text[:1000])

    response.raise_for_status()
    return response.json().get("items", [])


def normalize_article(item: dict) -> dict:
    """네이버 뉴스 API 응답을 사용하기 쉬운 형태로 정리합니다."""
    title = clean_text(item.get("title"))
    description = clean_text(item.get("description"))
    link = item.get("originallink") or item.get("link")
    naver_link = item.get("link")
    pub_date = item.get("pubDate")

    return {
        "title": title,
        "description": description,
        "link": link,
        "naver_link": naver_link,
        "pubDate": pub_date,
    }


def send_teams_message(article: dict) -> None:
    """신규 기사를 Microsoft Teams 채널로 전송합니다."""
    webhook_url = os.environ["TEAMS_WEBHOOK_URL"]

    title = article.get("title", "")
    description = article.get("description", "")
    pub_date = article.get("pubDate", "")
    link = article.get("link") or article.get("naver_link") or ""

    adaptive_card = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
            {
                "type": "TextBlock",
                "text": "📰 [이노션] 신규 뉴스",
                "weight": "Bolder",
                "size": "Medium",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": title,
                "weight": "Bolder",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": description,
                "wrap": True
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "발행일",
                        "value": pub_date or "-"
                    }
                ]
            }
        ]
    }

    if link.startswith("http"):
        adaptive_card["actions"] = [
            {
                "type": "Action.OpenUrl",
                "title": "기사 보기",
                "url": link
            }
        ]

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": adaptive_card
            }
        ]
    }

    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if response.status_code >= 400:
        print("Teams webhook failed")
        print("Status code:", response.status_code)
        print("Response body:", response.text[:1000])

    response.raise_for_status()


def main() -> None:
    state = load_state()
    seen_links = set(state.get("seen_links", []))

    raw_items = fetch_naver_news()
    articles = [normalize_article(item) for item in raw_items]

    current_links = [
        article["link"]
        for article in articles
        if article.get("link")
    ]

    new_articles = [
        article
        for article in articles
        if article.get("link") and article["link"] not in seen_links
    ]

    # 최초 실행 시에는 기존 기사 폭탄 알림을 막기 위해 저장만 하고 종료합니다.
    if not state.get("initialized"):
        state["initialized"] = True
        state["seen_links"] = list(dict.fromkeys(current_links))
        save_state(state)
        print("Initialized state. No Teams alerts sent on first run.")
        return

    # 오래된 기사부터 순서대로 전송합니다.
    for article in reversed(new_articles):
        send_teams_message(article)

    if new_articles:
        updated_links = list(dict.fromkeys(current_links + list(seen_links)))
        state["seen_links"] = updated_links[:500]
        save_state(state)
        print(f"Sent {len(new_articles)} new article(s) to Teams.")
    else:
        print("No new articles.")


if __name__ == "__main__":
    main()
