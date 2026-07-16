#!/usr/bin/env python
"""
파일럿 뷰어 서버 — 로컬과 Railway 겸용.

[로컬]
    python run_viewer.py
    → 서버 시작 + 브라우저 자동 오픈. 실행은 이 PC의 Python 사용.

[Railway 배포]
    이 폴더(run_viewer.py, pilot_viewer.html, tasks.json, requirements.txt,
    Procfile)를 repo로 올리고 Railway에 연결.
    환경변수 RUN_TOKEN을 반드시 설정하세요 (임의의 긴 문자열).
    참가자 접속 URL:  https://<앱>.up.railway.app/pilot_viewer.html?token=<RUN_TOKEN>

엔드포인트:
    GET  /ping     실행기 확인
    POST /run      코드 실행 {code, stdin, timeout}
    POST /submit   세션 결과 저장 → ./results/<userId>_<ts>.json
    GET  /results  저장된 결과 목록(JSON) — 토큰 필요

DS-1000 실행에는 numpy/pandas 필요:  pip install numpy pandas
"""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

RUN_TIMEOUT_DEFAULT = 20  # 초
RUN_TOKEN = os.environ.get("RUN_TOKEN", "")          # 배포 시 필수
DEPLOYED = bool(os.environ.get("PORT"))              # Railway가 PORT를 주입함
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", "results"))

def free_port(preferred=8000):
    for port in [preferred] + list(range(8001, 8020)):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("사용 가능한 포트가 없습니다")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        if RUN_TOKEN:
            return self.headers.get("X-Run-Token", "") == RUN_TOKEN
        # 토큰 미설정 시 localhost에서만 허용 (배포 실수 안전장치)
        return self.client_address[0] in ("127.0.0.1", "::1")

    def do_GET(self):
        if self.path == "/ping":
            self._json(200, {"service": "pilot-runner",
                             "python": sys.version.split()[0],
                             "token_required": bool(RUN_TOKEN)})
            return
        if self.path == "/results":
            if not self._authorized():
                self._json(403, {"ok": False, "out": "invalid token"})
                return
            files = sorted(RESULTS_DIR.glob("*.json")) if RESULTS_DIR.exists() else []
            self._json(200, {"count": len(files), "files": [f.name for f in files]})
            return
        super().do_GET()

    def _handle_submit(self):
        if not self._authorized():
            self._json(403, {"ok": False, "out": "invalid token"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            uid = re.sub(r"[^A-Za-z0-9_\-]", "_", str(payload.get("user_id", "unknown")))[:40]
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            fname = RESULTS_DIR / f"{uid}_{int(time.time())}.json"
            fname.write_text(json.dumps(payload.get("results", []),
                             ensure_ascii=False, indent=2), encoding="utf-8")
            self._json(200, {"ok": True, "saved": fname.name})
        except Exception as e:
            self._json(200, {"ok": False, "out": f"저장 실패: {e}"})

    def do_POST(self):
        if self.path == "/submit":
            self._handle_submit()
            return
        if self.path != "/run":
            self._json(404, {"ok": False, "out": "unknown endpoint"})
            return
        if not self._authorized():
            self._json(403, {"ok": False, "out": "invalid token (URL의 ?token= 확인)"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            code = payload.get("code", "")
            stdin = payload.get("stdin", "")
            timeout = min(float(payload.get("timeout", RUN_TIMEOUT_DEFAULT)), 60)
        except Exception as e:
            self._json(400, {"ok": False, "out": f"bad request: {e}"})
            return

        tmp = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                             encoding="utf-8") as f:
                f.write(code)
                tmp = f.name
            proc = subprocess.run(
                [sys.executable, "-X", "utf8", tmp],
                input=stdin, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout,
                cwd=tempfile.gettempdir(),
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            self._json(200, {"ok": proc.returncode == 0, "out": out or "(출력 없음)"})
        except subprocess.TimeoutExpired:
            self._json(200, {"ok": False,
                             "out": f"(시간 초과: {timeout:.0f}초 — 무한 루프 여부를 확인하세요)"})
        except Exception as e:
            self._json(200, {"ok": False, "out": f"(실행기 오류: {e})"})
        finally:
            if tmp:
                try:
                    Path(tmp).unlink()
                except OSError:
                    pass


def main():
    here = Path(__file__).resolve().parent
    viewer = here / "pilot_viewer.html"
    if not viewer.exists():
        print(f"[오류] {viewer} 가 없습니다. 이 스크립트를 pilot_viewer.html과 같은 폴더에 두세요.")
        return

    # numpy/pandas 사전 점검 (DS-1000 실행에 필요)
    missing = []
    for pkg in ("numpy", "pandas"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[경고] {', '.join(missing)} 미설치 — DS-1000 문제 실행이 실패합니다.")
        print(f"       설치:  pip install {' '.join(missing)}")

    if DEPLOYED:
        port = int(os.environ["PORT"])
        host = "0.0.0.0"
        if not RUN_TOKEN:
            print("[치명적] 배포 환경인데 RUN_TOKEN이 없습니다. 환경변수를 설정하세요.")
            print("         토큰 없이 공개하면 임의 코드 실행 엔드포인트가 인터넷에 노출됩니다.")
            return
    else:
        port = free_port()
        host = "127.0.0.1"
    url = f"http://localhost:{port}/pilot_viewer.html"
    server = ThreadingHTTPServer((host, port), partial(QuietHandler, directory=str(here)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"서버 실행 중: {url}" + (" (배포 모드)" if DEPLOYED else ""))
    print("종료하려면 Ctrl+C")
    if not DEPLOYED:
        webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n서버 종료")
        server.shutdown()


if __name__ == "__main__":
    main()
