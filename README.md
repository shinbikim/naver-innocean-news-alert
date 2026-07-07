# 네이버 뉴스 모니터링 (이노션)

네이버 뉴스 검색 API로 "이노션" 키워드의 신규 기사를 주기적으로 확인하고,
새로 발견된 기사만 Microsoft Teams 채널로 알려주는 GitHub Actions 기반 봇입니다.

## 동작 방식

1. `monitor.py`가 네이버 뉴스 검색 API(`https://openapi.naver.com/v1/search/news.json`)를
   `query=이노션`, `display=100`, `sort=date` 조건으로 호출합니다.
2. 이전에 보낸 기사 링크 목록은 `state.json`에 저장되어 있습니다.
   - `state.json`이 없는 **최초 실행**에서는 현재 검색 결과를 모두 `state.json`에 저장만 하고,
     Teams 알림은 보내지 않습니다. (과거 기사가 한꺼번에 쏟아지는 것을 방지)
   - 이후 실행부터는 `state.json`에 없는 **새 기사만** Teams로 전송하고, 전송한 링크를
     `state.json`에 추가합니다.
3. 새 기사가 없으면 아무 메시지도 보내지 않습니다.
4. GitHub Actions 워크플로우가 실행될 때마다 `state.json`이 변경되면 자동으로 커밋됩니다.

## 파일 구성

- `monitor.py` : 뉴스 조회, 신규 기사 판별, Teams 전송 로직
- `requirements.txt` : 의존성 목록 (표준 라이브러리만 사용하므로 실질적으로 비어 있음)
- `.github/workflows/news-alert.yml` : 매시간 5분에 실행되는 GitHub Actions 워크플로우
- `state.json` : 이전에 전송한 기사 링크 저장소 (최초 실행 시 자동 생성, 자동 커밋됨)

## 사전 준비: GitHub Secrets

저장소 `Settings > Secrets and variables > Actions`에 아래 3개가 이미 등록되어 있어야 합니다.

| Secret 이름            | 설명                                  |
| ---------------------- | ------------------------------------- |
| `NAVER_CLIENT_ID`      | 네이버 오픈 API 애플리케이션 Client ID |
| `NAVER_CLIENT_SECRET`  | 네이버 오픈 API 애플리케이션 Client Secret |
| `TEAMS_WEBHOOK_URL`    | Teams 채널의 Incoming Webhook URL      |

## 실행 방법

### 자동 실행

`.github/workflows/news-alert.yml`에 정의된 대로 **매시간 5분**(`cron: "5 * * * *"`)에
자동으로 실행됩니다.

### 수동 실행

GitHub 저장소의 **Actions** 탭 > `Naver News Alert (이노션)` 워크플로우 > **Run workflow**
버튼으로 언제든 수동 실행할 수 있습니다 (`workflow_dispatch`).

### 로컬 실행 (테스트용)

```bash
pip install -r requirements.txt

export NAVER_CLIENT_ID="..."
export NAVER_CLIENT_SECRET="..."
export TEAMS_WEBHOOK_URL="..."

python monitor.py
```

로컬에서 실행하면 현재 디렉터리에 `state.json`이 생성/갱신됩니다.

## Teams 메시지 내용

새 기사가 발견되면 아래 항목을 포함한 메시지가 Teams 채널로 전송됩니다.

- 제목
- 요약
- 발행일
- 기사 링크

## 커스터마이징

- 검색 키워드를 바꾸려면 `monitor.py`의 `QUERY` 값을 수정하세요.
- 실행 주기를 바꾸려면 `.github/workflows/news-alert.yml`의 `cron` 표현식을 수정하세요.
- 저장하는 링크 개수 상한(`MAX_SEEN_LINKS`, 기본 1000개)은 `monitor.py`에서 조정할 수 있습니다.

## 주의 사항

- 이 워크플로우는 `contents: write` 권한으로 `state.json`을 저장소에 직접 커밋합니다.
  브랜치 보호 규칙으로 인해 봇의 푸시가 막혀 있다면 예외를 허용해야 합니다.
- 네이버 뉴스 검색 API는 최대 100건(`display=100`)까지만 반환하므로, 한 번의 실행 주기
  동안 100건을 초과하는 새 기사가 쏟아지면 일부가 누락될 수 있습니다.
