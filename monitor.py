import html
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

NAVER_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.json"
QUERY = "이노션"
DISPLAY = 100
SORT = "date"

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

# Cap on how many links we remember, so state.json doesn't grow forever.
MAX_SEEN_LINKS = 1000


def strip_html(text: str) -> str:
    """Naver API returns titles/descriptions with <b> tags and HTML entities."""
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).strip()


def fetch_news() -> list[dict]:
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 설정되어 있지 않습니다."
        )

    params = urllib.parse.urlencode(
        {
            "query": QUERY,
            "display": DISPLAY,
            "sort": SORT,
        }
    )
    url = f"{NAVER_NEWS_API_URL}?{params}"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)

    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))

    return body.get("items", [])


def load_state() -> tuple[dict, bool]:
    """Returns (state, is_first_run)."""
    if not os.path.exists(STATE_FILE):
        return {"seen_links": []}, True

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            state = {}

    if "seen_links" not in state:
        state["seen_links"] = []

    return state, False


def save_state(seen_links: list[str]) -> None:
    # Keep only the most recently seen links to bound file size.
    trimmed = seen_links[-MAX_SEEN_LINKS:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"seen_links": trimmed}, f, ensure_ascii=False, indent=2)


def send_teams_message(article: dict) -> None:
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("TEAMS_WEBHOOK_URL 환경변수가 설정되어 있지 않습니다.")

    title = strip_html(article.get("title", ""))
    summary = strip_html(article.get("description", ""))
    pub_date = article.get("pubDate", "")
    link = article.get("originallink") or article.get("link", "")

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": title,
        "themeColor": "0076D7",
        "title": title,
        "sections": [
            {
                "facts": [
                    {"name": "요약", "value": summary or "(요약 없음)"},
                    {"name": "발행일", "value": pub_date or "(알 수 없음)"},
                    {"name": "링크", "value": link},
                ],
                "markdown": True,
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "기사 보기",
                "targets": [{"os": "default", "uri": link}],
            }
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def main() -> None:
    articles = fetch_news()
    state, is_first_run = load_state()
    seen_links = set(state.get("seen_links", []))

    def article_link(article: dict) -> str:
        return article.get("originallink") or article.get("link", "")

    if is_first_run:
        print(f"최초 실행입니다. {len(articles)}건을 state.json에 저장하고 알림은 보내지 않습니다.")
        all_links = list(dict.fromkeys(article_link(a) for a in articles if article_link(a)))
        save_state(all_links)
        return

    new_articles = [a for a in articles if article_link(a) and article_link(a) not in seen_links]

    if not new_articles:
        print("새 기사가 없습니다.")
        return

    # Naver returns newest first; send oldest-of-the-new-batch first so Teams shows them in order.
    for article in reversed(new_articles):
        send_teams_message(article)
        time.sleep(1)  # avoid hitting Teams webhook rate limits

    updated_links = list(seen_links) + [article_link(a) for a in new_articles]
    save_state(list(dict.fromkeys(updated_links)))

    print(f"새 기사 {len(new_articles)}건을 Teams로 전송했습니다.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"오류 발생: {exc}", file=sys.stderr)
        sys.exit(1)
