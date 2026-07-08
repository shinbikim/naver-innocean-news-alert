# 뉴스 이슈 레이더

네이버 뉴스에서 지정 키워드의 신규 기사를 1시간마다 감지해 Microsoft Teams 채널로 자동 공유하는 뉴스 모니터링 자동화 도구입니다.

## 한줄 소개

지정 키워드의 신규 뉴스 발생 여부를 주기적으로 확인하고, 새롭게 발견된 기사만 Teams 채널로 공유해주는 이슈 모니터링 봇입니다.

## 기획 의도

광고대행사 업무 특성상 회사뿐 아니라 다수의 클라이언트와 관련된 대내외 주요 이슈를 상시 파악하는 것이 중요합니다. 특히 부정 이슈나 위기성 보도가 발생했을 경우, 초기 인지 속도와 내부 공유 속도가 대응 품질을 좌우합니다.

이에 따라 특정 키워드로 신규 뉴스를 주기적으로 확인하고, 새롭게 감지된 기사만 팀 협업 채널에 자동 공유되는 구조를 기획했습니다.

현재는 `이노션`을 키워드로 설정했지만, 향후 클라이언트명, 브랜드명, 캠페인명, 주요 임원명 등 다양한 키워드로 확장해 PR, 위기관리, 클라이언트 이슈 모니터링 업무에 활용할 수 있습니다.

## 주요 기능

- 네이버 뉴스 검색 API 기반 키워드 모니터링
- 1시간 단위 신규 기사 확인
- 이전에 전송한 기사와 비교해 중복 알림 방지
- 신규 기사 발생 시 Microsoft Teams 채널로 자동 공유
- 신규 기사가 없을 경우 알림 미발송
- GitHub Actions 기반 자동 실행으로 PC를 켜둘 필요 없음
- 팀 단위 공유가 필요한 경우 Teams 채널에 팀원을 초대해 함께 확인 가능

## 사용법

이 자동화는 GitHub Actions를 통해 1시간마다 자동 실행됩니다.

사용자는 별도로 프로그램을 실행할 필요가 없으며, 신규 기사가 발견되면 지정된 Microsoft Teams 채널에 알림이 발송됩니다.

Teams 알림에는 아래 정보가 포함됩니다.

- 기사 제목
- 기사 요약
- 발행일
- 기사 링크

신규 기사가 없을 경우에는 불필요한 알림을 보내지 않습니다.

## 작동 방식

1. GitHub Actions가 매시간 5분에 자동 실행됩니다.
2. `monitor.py`가 네이버 뉴스 검색 API를 호출해 지정 키워드의 최신 뉴스를 조회합니다.
3. 이전에 확인한 기사 링크 목록인 `state.json`과 비교합니다.
4. 새롭게 발견된 기사만 Microsoft Teams 채널로 전송합니다.
5. 전송한 기사 링크는 `state.json`에 저장해 중복 알림을 방지합니다.
6. `state.json`이 변경되면 GitHub Actions가 자동으로 커밋합니다.

## 파일 구성

- `monitor.py`  
  뉴스 조회, 신규 기사 판별, Teams 전송 로직을 담당합니다.

- `requirements.txt`  
  Python 실행에 필요한 외부 라이브러리 목록입니다.

- `.github/workflows/news-alert.yml`  
  1시간마다 자동 실행되는 GitHub Actions 워크플로우입니다.

- `state.json`  
  이전에 확인한 기사 링크를 저장해 중복 알림을 방지합니다.

## GitHub Secrets

API Key와 Teams Webhook URL은 코드에 직접 저장하지 않고 GitHub Secrets로 관리합니다.

필요한 Secret은 아래 3개입니다.

| Secret 이름 | 설명 |
| --- | --- |
| `NAVER_CLIENT_ID` | 네이버 오픈 API 애플리케이션 Client ID |
| `NAVER_CLIENT_SECRET` | 네이버 오픈 API 애플리케이션 Client Secret |
| `TEAMS_WEBHOOK_URL` | Microsoft Teams 채널 Webhook URL |

실제 인증 정보는 GitHub Secrets에만 저장되며, Repository 코드에는 노출되지 않습니다.

## 실행 방법

### 자동 실행

GitHub Actions 워크플로우에 따라 매시간 5분에 자동 실행됩니다.

```yaml
cron: "5 * * * *"
