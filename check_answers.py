#!/usr/bin/env python3
"""매일 아침 맨 먼저 돈다. 퀴즈 답과 질문 톡을 읽어 진도표에 적고, 과목마다 오늘 할 일을 정해 JSON으로 출력한다.

오늘 할 일(`할_일`)
- "강의": 첫날이거나 지난 퀴즈를 다 풀었다 → 오늘 강의를 보낸다
- "기다림": 아직 안 풀었다 → 아무것도 보내지 않는다
- "알림": 사흘째 안 풀었고 아직 안 알렸다 → 짧게 한 번만 알린다
- "주간정리": 일요일. 이번 주에 들은 강의가 있으면 정리만 보낸다 (퀴즈 없음)
- "쉼": 일요일인데 이번 주에 들은 강의가 없다

사용법: python3 check_answers.py
"""
import json
import sys
from datetime import date, timedelta

import tg

REMIND_AFTER_DAYS = 3


def grade(sp, poll_id, chosen, now):
    """답 하나를 채점해서 복습 목록을 고친다. 맞으면 True."""
    poll = sp["waiting"]["polls"][poll_id]
    poll["chosen"] = chosen
    right = chosen == poll["correct"]
    item = {k: poll[k] for k in ("question", "options", "correct", "explanation") if k in poll}
    if poll.get("kind") == "review":
        old = next((r for r in sp["review"] if r["question"] == poll["question"]), None)
        if old:
            if right and old["stage"] >= 2:
                sp["review"].remove(old)                       # 3일 뒤, 7일 뒤 두 번 다 맞혔다 → 졸업
            elif right:
                old.update(stage=2, due=str(now + timedelta(days=7)))
            else:
                old.update(stage=1, due=str(now + timedelta(days=3)))
    elif not right:
        sp["review"].append({**item, "lesson": sp["waiting"]["lesson"], "stage": 1, "due": str(now + timedelta(days=3))})
    return right


def main():
    config, progress = tg.load_config(), tg.load_progress()
    now = tg.today()
    thread_to_key = {s.get("thread_id"): k for k, s in config["subjects"].items() if s.get("thread_id")}
    poll_to_key = {pid: k for k, sp in progress["subjects"].items()
                   for pid in ((sp.get("waiting") or {}).get("polls") or {})}

    updates = tg.call("getUpdates", offset=progress.get("last_update_id", 0) + 1,
                      allowed_updates=["message", "poll_answer"])
    new_answers, new_questions = [], []
    for u in updates:
        progress["last_update_id"] = max(progress.get("last_update_id", 0), u["update_id"])
        if "poll_answer" in u:
            pa = u["poll_answer"]
            key = poll_to_key.get(pa["poll_id"])
            if key and pa.get("option_ids"):
                sp = tg.subject_progress(progress, key)
                right = grade(sp, pa["poll_id"], pa["option_ids"][0], now)
                new_answers.append({"과목": key, "맞음": right})
        elif "message" in u:
            m = u["message"]
            text = (m.get("text") or "").strip()
            if not text or m.get("from", {}).get("is_bot"):
                continue
            key = thread_to_key.get(m.get("message_thread_id"))
            if key is None and not config.get("chat_id") and len(config["subjects"]) == 1:
                key = next(iter(config["subjects"]))            # 1:1 대화방에 과목이 하나면 그 과목 질문
            if key:
                tg.subject_progress(progress, key)["questions"].append(text)
                new_questions.append({"과목": key, "질문": text})
    if updates:
        tg.call("getUpdates", offset=progress["last_update_id"] + 1)   # 읽음 처리

    result = {"오늘": str(now), "요일": "월화수목금토일"[now.weekday()], "과목": {}, "새로_받은_답": new_answers,
              "새로_받은_질문": new_questions}
    for key, subject in config["subjects"].items():
        sp = tg.subject_progress(progress, key)
        w = sp.get("waiting")
        polls = (w or {}).get("polls") or {}
        all_done = bool(w) and all("chosen" in p for p in polls.values())
        if w and all_done and not w.get("recorded"):
            lesson_polls = [p for p in polls.values() if p.get("kind") != "review"]
            sp["history"].append({"lesson": w["lesson"], "date": w["sent_on"],
                                  "correct": sum(p["chosen"] == p["correct"] for p in lesson_polls),
                                  "total": len(lesson_polls)})
            w["recorded"] = True

        days = (now - date.fromisoformat(w["sent_on"])).days if w else 0
        week_ago = str(now - timedelta(days=6))
        if now.weekday() == 6:
            todo = "주간정리" if any(h["date"] >= week_ago for h in sp["history"]) else "쉼"
        elif not w or all_done:
            todo = "강의"
        elif days >= REMIND_AFTER_DAYS and not sp.get("reminded"):
            todo = "알림"
        else:
            todo = "기다림"

        result["과목"][key] = {
            "제목": subject["title"],
            "할_일": todo,
            "다음_강의": sp["next_lesson"],
            "기다리는_강의": w["lesson"] if w and not all_done else None,
            "안_푼_날수": days if w and not all_done else 0,
            "오늘_복습할_문제": [r for r in sp["review"] if r["due"] <= str(now)],
            "답할_질문": sp["questions"],
            "배운_개념": sp["learned"],
            "최근_결과": sp["history"][-5:],
        }

    tg.save_progress(progress)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
