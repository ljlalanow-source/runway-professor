"""교수 프로그램들이 함께 쓰는 도구: 설정·진도표 읽고 쓰기, 텔레그램 부르기."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
CONFIG_PATH = HERE / "config.json"
PROGRESS_PATH = HERE / "progress.json"
KST = timezone(timedelta(hours=9))


def today():
    return datetime.now(KST).date()


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_progress():
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    return {"last_update_id": 0, "subjects": {}}


def save_progress(progress):
    PROGRESS_PATH.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def subject_progress(progress, key):
    """과목 진도가 없으면 새로 만든다."""
    return progress["subjects"].setdefault(key, {
        "next_lesson": 1,
        "waiting": None,          # 마지막으로 보낸 강의와 퀴즈
        "reminded": False,
        "learned": [],            # 배운 개념
        "review": [],             # 틀려서 다시 낼 문제
        "questions": [],          # 톡으로 받은 질문
        "history": [],            # 강의마다 퀴즈 결과
    })


def pick_subject(config, argv):
    subjects = config["subjects"]
    if len(argv) < 2 or argv[1] not in subjects:
        sys.exit(f"과목을 골라 주세요: {', '.join(subjects)}")
    return argv[1], subjects[argv[1]]


def target(config, subject):
    """보낼 곳: 토픽 그룹이 있으면 그 과목 탭, 없으면 1:1 대화방."""
    if config.get("chat_id"):
        fields = {"chat_id": config["chat_id"]}
        if subject.get("thread_id"):
            fields["message_thread_id"] = subject["thread_id"]
        return fields
    return {"chat_id": os.environ["TELEGRAM_CHAT_ID"]}


def call(method, **fields):
    token = os.environ["TELEGRAM_TOKEN"]
    data = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
            for k, v in fields.items() if v is not None}
    body = urllib.parse.urlencode(data).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data=body, timeout=30) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        res = json.loads(e.read().decode("utf-8") or "{}")
    if not res.get("ok"):
        sys.exit(f"{method} 실패: {res.get('description', res)}")
    return res["result"]
