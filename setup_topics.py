#!/usr/bin/env python3
"""토픽 그룹을 찾아 과목마다 탭(토픽)을 만들고, 그룹 번호와 탭 번호를 config.json 에 적는다.

준비: 텔레그램에서 그룹을 만들고 토픽을 켠 뒤, 교수 봇을 관리자로 지정(토픽 관리 권한)하고 그룹에 아무 말이나 보낸다.
사용법: python3 setup_topics.py          (설정할 때 한 번만)
과목 탭은 config.json 의 subjects 순서대로 만든다.
"""
import sys

import tg

config = tg.load_config()


def find_forum_group():
    """봇이 받은 소식 중에서 토픽이 켜진 그룹을 찾는다. (토픽을 켜면 그룹 번호가 바뀌므로 최신 번호를 쓴다)"""
    found = {}
    for u in tg.call("getUpdates"):
        for key in ("message", "my_chat_member", "chat_member"):
            chat = (u.get(key) or {}).get("chat")
            if chat and chat.get("type") == "supergroup":
                found[chat["id"]] = chat.get("title", "")
        migrate = (u.get("message") or {}).get("migrate_to_chat_id")
        if migrate:
            found[migrate] = u["message"]["chat"].get("title", "")
    for chat_id, title in reversed(list(found.items())):
        if tg.call("getChat", chat_id=chat_id).get("is_forum"):
            return chat_id, title
    return None, None


if not config.get("chat_id"):
    chat_id, title = find_forum_group()
    if not chat_id:
        sys.exit("토픽이 켜진 그룹을 못 찾았어요. 그룹에서 토픽을 켜고, 교수 봇을 관리자로 지정한 뒤, 그룹에 아무 말이나 보내 주세요.")
    print(f"그룹을 찾았어요: {title} ({chat_id})")
    config["chat_id"] = chat_id

for key, subject in config["subjects"].items():
    if subject.get("thread_id"):
        print(f"{subject['title']}: 이미 있어요 (탭 번호 {subject['thread_id']})")
        continue
    made = tg.call("createForumTopic", chat_id=config["chat_id"], name=subject["title"])
    subject["thread_id"] = made["message_thread_id"]
    hour = config.get("time", "08:00")
    tg.call("sendMessage", chat_id=config["chat_id"], message_thread_id=subject["thread_id"],
            text=f"{subject['title']} 수업 방이에요. 매일 아침 {hour}에 5분 강의와 퀴즈로 만나요.\n퀴즈를 풀어야 다음 강의가 와요. 궁금한 건 언제든 여기에 남겨 주세요.")
    print(f"{subject['title']}: 탭을 만들었어요 (탭 번호 {subject['thread_id']})")

tg.save_config(config)
print("config.json 에 저장했어요")
