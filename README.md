# open-go-kr-parser

한국 정부 원문정보공개 포털(open.go.kr)의 문서 공개 현황을 모니터링하고 텔레그램으로 알림을 보내는 서비스입니다.

## 기능

- 지정된 기관의 원문정보공개 문서 조회
- 텔레그램 봇을 통한 일일 알림 발송
- GitHub Actions를 통한 자동 스케줄링 (평일 09:00 KST)
- YAML 설정 파일을 통한 모니터링 기관 관리

## 요구사항

- Python 3.14+
- Telegram Bot Token ([BotFather](https://t.me/botfather)에서 생성)
- Telegram Chat ID

## 설치

```bash
# 저장소 클론
git clone https://github.com/kadragon/open-go-kr-parser.git
cd open-go-kr-parser

# 의존성 설치
pip install -e .

# 개발 의존성 포함 설치
pip install -e ".[dev]"
```

## 설정

### 1. 환경 변수

다음 환경 변수를 설정해야 합니다:

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### 2. 모니터링 기관 설정

`config/agencies.yaml` 파일에서 모니터링할 기관을 설정합니다:

```yaml
agencies:
  - code: "1342000"
    name: "교육부"
  - code: "1741000"
    name: "행정안전부"
  - code: "1721000"
    name: "과학기술정보통신부"
```

기관 코드 확인 방법:
1. https://www.open.go.kr/othicInfo/infoList/orginlInfoList.do 접속
2. 기관 검색 팝업에서 원하는 기관 검색
3. 네트워크 요청에서 `insttCd` 값 확인

## 사용법

### 로컬 실행

```bash
# 기본 실행 (오늘 날짜 기준)
open-go-kr

# 특정 날짜 지정
open-go-kr --dates "2025-12-28"

# 여러 날짜 지정
open-go-kr --dates "2025-12-27,2025-12-28"
```

### GitHub Actions

저장소에 다음 Secrets를 설정합니다:
- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID`: 알림을 받을 채팅 ID

워크플로우는 평일 09:00 KST에 자동 실행되며, Actions 탭에서 수동 실행도 가능합니다.

## 개발

```bash
# 테스트 실행
pytest

# 코드 린팅
ruff check src tests

# 타입 체크
mypy src
```

## 프로젝트 구조

```
open-go-kr-parser/
├── src/
│   ├── client.py      # open.go.kr API 클라이언트
│   ├── notifier.py    # 텔레그램 알림 전송
│   ├── config.py      # 설정 로더
│   └── main.py        # 진입점
├── config/
│   └── agencies.yaml  # 모니터링 기관 목록
├── tests/             # 테스트 코드
└── .github/workflows/
    ├── ci.yml         # CI 파이프라인
    └── daily-notify.yml  # 일일 알림 스케줄러
```

## 라이선스

MIT License
