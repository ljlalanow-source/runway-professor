#!/usr/bin/env python3
"""quiz.json 의 문제를 텔레그램 퀴즈 투표로 보내고, 진도표에 '이 퀴즈를 기다리는 중'으로 적는다.
강의를 보낸 직후에 부른다. 이걸 부르면 그 과목의 강의 번호가 하나 올라간다.

사용법: python3 quiz.py <과목> [--concept "배운 개념"]

quiz.json 모양 (복습 문제를 먼저, 오늘 강의 문제를 뒤에):
[
  {"kind": "review", "question": "…", "options": ["…", "…"], "correct": 1, "explanation": "…"},
  {"question": "…", "options": ["…", "…", "…"], "correct": 0, "explanation": "…"}
]
제한: 질문 300자, 보기 2~10개(각 100자), 해설 200자. correct 는 0부터 센다.
"""
import json
import sys

import tg

config = tg.load_config()
key, subject = tg.pick_subject(config, sys.argv)
quizzes = json.loads((tg.HERE / "quiz.json").read_text(encoding="utf-8"))
if not quizzes:
    sys.exit("quiz.json 이 비어 있어요")

for q in quizzes:
    problems = []
    if len(q["question"]) > 300: problems.append("질문이 300자를 넘어요")
    if not 2 <= len(q["options"]) <= 10: problems.append("보기는 2~10개여야 해요")
    if any(len(o) > 100 for o in q["options"]): problems.append("보기가 100자를 넘어요")
    if len(q.get("explanation", "")) > 200: problems.append("해설이 200자를 넘어요")
    if not 0 <= q["correct"] < len(q["options"]): problems.append("correct 번호가 보기 범위를 벗어나요")
    if problems:
        sys.exit(f"고쳐 주세요 — {q['question'][:30]}…: {', '.join(problems)}")

progress = tg.load_progress()
sp = tg.subject_progress(progress, key)
lesson = sp["next_lesson"]
polls = {}
for q in quizzes:
    prefix = "🔁 복습 · " if q.get("kind") == "review" else f"{lesson}강 퀴즈 · "
    msg = tg.call("sendPoll", question=(prefix + q["question"])[:300], options=q["options"], type="quiz",
                  is_anonymous="false", correct_option_id=q["correct"], explanation=q.get("explanation"),
                  **tg.target(config, subject))
    polls[msg["poll"]["id"]] = {**q, "kind": q.get("kind", "lesson")}

sp["waiting"] = {"lesson": lesson, "sent_on": str(tg.today()), "polls": polls}
sp["next_lesson"] = lesson + 1
sp["reminded"] = False
sp["questions"] = []          # 오늘 강의에서 답했으니 비운다
if "--concept" in sys.argv:
    concept = sys.argv[sys.argv.index("--concept") + 1]
    if concept not in sp["learned"]:
        sp["learned"].append(concept)
tg.save_progress(progress)
print(f"{subject['title']} {lesson}강 퀴즈 {len(polls)}개를 보냈어요. 풀면 다음에 {lesson + 1}강이 가요")
