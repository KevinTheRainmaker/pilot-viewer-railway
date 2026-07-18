"""Convert the private adapted-task package into the participant-safe viewer catalog."""

import json
import re
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


def load_markdown_contexts(path):
    """Return participant-safe contextual titles and bodies keyed by task ID."""
    markdown = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^### (S\d-[ADB]) · (.+)$", markdown, re.MULTILINE))
    contexts = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        section = markdown[match.end():end]
        section = section.split("<details>", 1)[0]
        section = re.sub(
            r"\n\*\*제공 코드\*\*\n```python\n.*?\n```\s*$", "", section, flags=re.DOTALL
        )
        section = re.sub(r"^- 유형:.*$\n?", "", section, flags=re.MULTILINE)
        section = re.sub(r"^- 목표:.*$\n?", "", section, flags=re.MULTILINE)
        contexts[match.group(1)] = {"title": match.group(2), "body": section.strip()}
    return contexts


def to_viewer_task(task, context=None):
    title = context["title"] if context else task["title"]
    body = context["body"] if context else problem_body(task)
    return {
        "id": task["id"],
        "source": SOURCE_BY_CATEGORY[task["category"]],
        "group": task["category"],
        "difficulty": "junior_ai_10min",
        "title": title,
        "title_ko": title,
        "meta": f"origin={task['origin']};estimated_minutes={task['estimated_minutes']}",
        "body": body,
        "body_ko": body,
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
    context_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    package = json.loads(source.read_text(encoding="utf-8"))
    contexts = load_markdown_contexts(context_path) if context_path else {}
    tasks = [to_viewer_task(task, contexts.get(task["id"])) for task in package["tasks"]]
    destination.write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
