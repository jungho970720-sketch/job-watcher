# Job Watcher

매일 사람인·워크넷·잡다·잡코리아에서 채용공고를 모아 `dashboard.html`로 필터링해 보여주는 도구.

## 설치

1. Python 3.12+ 설치 (https://www.python.org/downloads/, "Add python.exe to PATH" 체크)
2. `pip install -r requirements.txt`
3. `playwright install chromium`
4. `config/secrets.json.example`을 `config/secrets.json`으로 복사하고 API 키 입력
   - 사람인 access-key: https://oapi.saramin.co.kr/join 에서 이용신청 후 발급
   - 워크넷 authKey: https://openapi.work.go.kr 에서 회원가입 후 발급

## 필터 조건 수정

`config/filters.json`을 텍스트 편집기로 열어 배열 항목을 추가/삭제:
- `job_keywords`: 제목에 하나 이상 포함되어야 함
- `regions`: 근무지에 하나 이상 포함되어야 함 (근무지 정보가 없는 공고는 통과)
- `experience_max_years`: 요구 경력 상한 (신입 포함, 경력 정보 없는 공고는 통과)
- `exclude_keywords`: 제목에 포함되면 제외

## 수동 실행

```bash
python main.py
```

`dashboard.html`이 생성/갱신됨. 브라우저로 열어서 확인.

## 매일 자동 실행

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
```

Windows 작업 스케줄러에 매일 오전 9시 실행되는 `JobWatcher` 작업이 등록됨. 등록 확인: `Get-ScheduledTask -TaskName "JobWatcher"`.
