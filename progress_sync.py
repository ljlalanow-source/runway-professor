#!/usr/bin/env python3
"""진도표(progress.json)를 GitHub의 `claude/progress` 브랜치에서 불러오고, 그 브랜치에만 저장한다.

클라우드 예약은 `claude/` 로 시작하는 브랜치에만 올릴 수 있어서, 진도표를 main 대신 이 브랜치에 둔다.

사용법:
  python3 progress_sync.py load   매일 맨 처음
  python3 progress_sync.py save   매일 맨 끝
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
BRANCH = "claude/progress"
FILE = "progress.json"


def git(*args, cwd=HERE, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def load():
    if git("fetch", "origin", BRANCH, check=False).returncode != 0:
        print("진도표가 아직 없어요. 처음 시작해요")
        return
    shown = git("show", f"origin/{BRANCH}:{FILE}", check=False)
    if shown.returncode == 0:
        (HERE / FILE).write_text(shown.stdout, encoding="utf-8")
        print("진도표를 불러왔어요")
    else:
        print("진도표가 아직 없어요. 처음 시작해요")


def save():
    src = HERE / FILE
    if not src.exists():
        sys.exit("저장할 진도표가 없어요")
    tmp = Path(tempfile.mkdtemp())
    try:
        exists = git("fetch", "origin", BRANCH, check=False).returncode == 0
        if exists:
            git("worktree", "add", "-B", BRANCH, str(tmp), f"origin/{BRANCH}")
        else:
            git("worktree", "add", "--detach", str(tmp))
            git("checkout", "--orphan", BRANCH, cwd=tmp)
            git("rm", "-rf", "--quiet", ".", cwd=tmp, check=False)
        shutil.copy(src, tmp / FILE)
        git("add", "-f", FILE, cwd=tmp)
        if git("diff", "--cached", "--quiet", cwd=tmp, check=False).returncode == 0:
            print("바뀐 진도가 없어요")
            return
        git("commit", "-m", "진도표 업데이트", cwd=tmp)
        git("push", "origin", f"HEAD:{BRANCH}", cwd=tmp)
        print("진도표를 저장했어요")
    finally:
        git("worktree", "remove", "--force", str(tmp), check=False)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    {"load": load, "save": save}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
