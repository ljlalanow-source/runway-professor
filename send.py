#!/usr/bin/env python3
"""표준 입력으로 받은 글을 그 과목 탭으로 보낸다.

사용법:
  python3 send.py <과목> < lesson.md            강의 · 주간 정리
  python3 send.py <과목> --remind < message.txt  사흘째 알림 (보낸 뒤 '알렸음'으로 적어 둔다)
"""
import sys

import tg

config = tg.load_config()
key, subject = tg.pick_subject(config, sys.argv)
text = sys.stdin.read().strip()
if not text:
    sys.exit("보낼 내용이 없어요")

# 텔레그램 한 메시지는 4096자까지라, 길면 빈 줄 기준으로 나눠 보낸다
parts, buf = [], ""
for block in text.split("\n\n"):
    if buf and len(buf) + len(block) > 3800:
        parts.append(buf)
        buf = ""
    buf = f"{buf}\n\n{block}" if buf else block
parts.append(buf)

for part in parts:
    tg.call("sendMessage", text=part, disable_web_page_preview="true", **tg.target(config, subject))

if "--remind" in sys.argv:
    progress = tg.load_progress()
    tg.subject_progress(progress, key)["reminded"] = True
    tg.save_progress(progress)
print(f"{subject['title']} 탭으로 보냈어요")
