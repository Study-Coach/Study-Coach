# AI Study Coach

Python only 기반 학습 코치 프로젝트입니다. Kivy 앱과 NiceGUI 웹이 같은 `core` 모듈과 SQLite 데이터베이스를 공유합니다.

## 구조

```text
app_kivy/main.py       Kivy 앱 실행 파일
web_nicegui/main.py    NiceGUI 웹 실행 파일
core/                  AI, DB, 분석 공통 로직
data/study_coach.db    SQLite 데이터베이스
```

## 설치

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

AI API를 쓰려면 `.env.example`을 참고해서 `.env` 파일을 만들고 API 키를 넣습니다. API 키가 없거나 호출에 실패해도 fallback 문제, 피드백, 추천이 생성됩니다.

## Kivy 앱 실행

```powershell
.\.venv\Scripts\python.exe .\app_kivy\main.py
```

## NiceGUI 웹 실행

```powershell
.\.venv\Scripts\python.exe .\web_nicegui\main.py
```

실행 후 브라우저에서 표시되는 주소로 접속합니다. 기본 흐름은 학습 입력, 문제 풀이, 결과 확인, 대시보드 확인입니다.

## 주요 기능

- 과목, 공부 시간, 집중도, 공부 내용, 어려웠던 점 입력
- 오늘 공부한 내용 기반 복습 문제 5개 생성
- 답변별 점수와 짧은 피드백 생성
- 평균 점수와 복습률 계산
- Python 규칙 기반 분석 후 내일 학습 계획 추천
- SQLite 저장 및 최근 기록 조회
- NiceGUI 대시보드에서 과목별 공부 시간, 날짜별 복습률 그래프 확인
