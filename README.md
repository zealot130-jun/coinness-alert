# 코인니스 관심 코인 속보 알림

코인니스 속보(https://coinness.com/news) 중 아래 소식만 골라 휴대폰 푸시로 보냅니다.

- 관심 코인: NEAR, HBAR(헤데라), ONDO, ALGO(알고랜드), LINK(체인링크), AVAX(아발란체), SUI, DOGE
- 상장폐지 관련: 상장폐지, 상폐, 거래지원 종료, 유의종목 지정, 디리스팅

코인 판별은 코인니스가 속보마다 붙이는 코인 코드를 우선 쓰고, 제목·본문의 티커/코인 이름도 함께 봅니다.
코인을 바꾸려면 `coinness_alert.py`의 `COINS`, 키워드는 `DELIST_KEYWORDS`를 고치면 됩니다.

## 1. 휴대폰 알림 받기 (ntfy, 가입 불필요)

1. 앱스토어/플레이스토어에서 **ntfy** 설치
2. 앱에서 `+` → 토픽 이름 입력 (남이 못 맞히게 길게, 예: `coinness-pro-7x9k2q`) → 구독
3. 이 토픽 이름이 `NTFY_TOPIC` 값입니다.

텔레그램을 원하면 @BotFather로 봇을 만들어 토큰을 받고, 봇에게 아무 메시지나 보낸 뒤
`https://api.telegram.org/bot<토큰>/getUpdates`에서 `chat.id`를 확인해 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`로 씁니다.

## 2-A. GitHub Actions로 실행 (PC 꺼져 있어도 동작, 무료)

1. GitHub에 새 저장소를 만들고 이 폴더의 파일(`.github` 폴더 포함)을 올립니다.
   공개(public) 저장소면 실행 시간 무제한 무료, 비공개면 월 2,000분 무료 한도(5분마다 실행 시 초과 가능)라 공개를 권장합니다. 토픽/토큰은 코드가 아니라 Secrets에 들어가므로 노출되지 않습니다.
2. 저장소 Settings → Secrets and variables → Actions → New repository secret 에서 `NTFY_TOPIC` 추가
3. Actions 탭 → coinness-alert → Run workflow 로 한 번 실행해 확인
4. 이후 5분마다 자동 실행됩니다. (GitHub 스케줄은 몇 분씩 늦어질 수 있음)

## 2-B. 내 PC/서버에서 상시 실행 (1분 간격, 더 빠름)

```bash
NTFY_TOPIC=coinness-pro-7x9k2q python3 coinness_alert.py
```

Python 3.8+ 표준 라이브러리만 사용합니다. `python3 coinness_alert.py --test` 는 최근 속보 중 걸러지는 것만 출력합니다(알림 없음).

## 알림 테스트

Actions 탭 → coinness-alert → Run workflow 에서 **테스트 알림만 보내기**를 체크하고 실행하면 휴대폰에 테스트 알림이 1개 옵니다.

---

# 당근 노트북 DDR5 8GB 램 바로구매 알림 (`daangn_alert.py`)

당근 중고거래에 **노트북용 DDR5 8GB 램이 10만원 이하, 바로구매(택배/안전결제)** 로 올라오면 같은 ntfy 토픽으로 알림이 옵니다. 지역은 상관없고 10분마다 확인합니다. 알림을 누르면 매물로 가서 바로 구매하면 됩니다(자동 구매는 하지 않음).

- 당근은 검색할 때 내 동네 매물과 함께 **전국 바로구매 매물**을 같이 보여 줍니다. 그래서 몇몇 동네(기본: 합정동, 강남구, 대전 도룡동)를 기준으로 검색하고 그중 바로구매 매물만 고릅니다.
- 검색어: `DDR5 8GB`, `노트북 램 DDR5`, `DDR5 8기가` (판매중 매물만)
- 제목+본문에 DDR5와 8GB(8G, 8기가)가 모두 있어야 함
- 제외: 구매글(삽니다/구합니다), 데스크톱용, 16GB/32GB, 노트북 본체(i5, 라이젠, 그램, 갤럭시북 등)
- 처음 실행할 때는 이미 올라와 있던 매물은 알림 없이 기록만 하고, 그 뒤 새로 올라온 것만 알립니다.
- 바로구매 여부를 당근 웹 응답에서 판별할 수 없는 매물은 일단 알림을 보냅니다(놓치지 않도록). 실행 로그의 `바로구매 N건 / 아님 N건 / 판별불가 N건` 줄로 확인할 수 있어요.

## 설정 (모두 선택)

저장소 Settings → Secrets and variables → Actions → **Variables** 탭

- `DAANGN_REGIONS`: 검색 기준 동네, 쉼표 구분. 당근 웹 검색 주소의 `in=` 값(예: `합정동-231`)이나 동네 이름
- `DAANGN_MAX_PRICE`: 최대 가격, 기본 `100000`
- `DAANGN_ONLY_DIRECT`: `0`이면 바로구매가 아닌 매물도 알림

조건을 바꾸려면 `daangn_alert.py`의 `SEARCH_WORDS`, `MUST`, `EXCLUDE_TITLE`을 고치면 됩니다.
