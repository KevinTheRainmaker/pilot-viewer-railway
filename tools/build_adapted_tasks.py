"""Convert the private adapted-task package into the participant-safe viewer catalog."""

import json
import sys
from pathlib import Path


SOURCE_BY_CATEGORY = {
    "algorithmic": "APPS",
    "data_manipulation": "DS-1000",
    "bug_fixing": "BugsInPy",
}


def problem_body(task):
    examples = "\n".join(
        f"- 입력: `{example['input']}` → 출력: `{example['output']}`"
        for example in task["examples"]
    )
    constraints = "\n".join(f"- {constraint}" for constraint in task["constraints"])
    return "\n\n".join((
        task["description"],
        f"**함수 시그니처**\n```python\n{task['function_signature']}\n```",
        f"**제약 조건**\n{constraints}",
        f"**예시**\n{examples}",
        "`solution` 함수를 구현한 뒤 「테스트 실행」으로 공개 테스트를 확인하세요.",
    ))


def to_viewer_task(task):
    return {
        "id": task["id"],
        "source": SOURCE_BY_CATEGORY[task["category"]],
        "group": task["category"],
        "difficulty": "junior_ai_10min",
        "title": task["title"],
        "title_ko": task["title"],
        "meta": f"origin={task['origin']};estimated_minutes={task['estimated_minutes']}",
        "body": problem_body(task),
        "body_ko": problem_body(task),
        "body_kind": "markdown",
        "starter_code": task["starter_code"],
        "public_tests": task["public_tests"],
        "task_set": task["set"],
        "origin": task["origin"],
        "estimated_minutes": task["estimated_minutes"],
    }


def main():
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    package = json.loads(source.read_text(encoding="utf-8"))
    tasks = [to_viewer_task(task) for task in package["tasks"]]
    destination.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
