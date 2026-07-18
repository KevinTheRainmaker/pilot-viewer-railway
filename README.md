# Pilot Task Viewer

파일럿 실험용 과제 뷰어 + 코드 실행 서버. 로컬과 Railway 겸용.

## 로컬 실행

```
pip install -r requirements.txt
python run_viewer.py
```

브라우저가 자동으로 열립니다. 토큰 불필요 (localhost 한정).

## Railway 배포

1. 이 폴더를 GitHub 레포로 push
2. Railway → New Project → Deploy from GitHub repo
3. **Variables에 `RUN_TOKEN` 설정 (필수)** — 임의의 긴 문자열
   - 미설정 시 서버가 스스로 종료합니다 (공개 코드 실행 엔드포인트 방지)
4. Settings → Networking → Generate Domain
5. 참가자 접속 URL:

```
https://<도메인>/pilot_viewer.html?token=<RUN_TOKEN>
```

실험 뷰어를 열려면 기존 URL에 `&viewer=exp`를 추가하세요. 토큰은 그대로
전달되므로 코드 실행과 결과 저장은 동일한 Railway Python 서버를 사용합니다.

```
https://<도메인>/pilot_viewer.html?token=<RUN_TOKEN>&viewer=exp
```

## 결과 수집

세션 종료 시 `results/<참가자ID>_<timestamp>.json`으로 서버에 자동 저장되고,
참가자 브라우저에도 백업 JSON이 다운로드됩니다.

- 저장 목록 확인: `GET /results` (X-Run-Token 헤더 필요)
- **주의: Railway 컨테이너 파일시스템은 재배포/재시작 시 초기화됩니다.**
  결과를 유지하려면 Railway Volume을 붙이고 환경변수 `RESULTS_DIR=/data`를
  설정하세요 (Settings → Volumes → mount path `/data`).
  Volume 없이 운영한다면 참가자 세션이 끝날 때마다 results를 회수하세요.

## 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/ping` | 실행기 상태 |
| POST | `/run` | 코드 실행 `{code, stdin, timeout}` |
| POST | `/submit` | 세션 결과 저장 |
| GET | `/results` | 저장된 결과 목록 |

`/run`, `/submit`, `/results`는 `RUN_TOKEN` 설정 시 `X-Run-Token` 헤더 필요.
토큰 미설정 시(로컬) localhost 접근만 허용됩니다.
