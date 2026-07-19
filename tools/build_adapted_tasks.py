"""Convert the private adapted-task package into the participant-safe viewer catalog."""

import json
import re
import sys
import ast
from pathlib import Path


SOURCE_BY_CATEGORY = {
    "algorithmic": "APPS",
    "data_manipulation": "DS-1000",
    "bug_fixing": "BugsInPy",
}


def problem_body(task):
    constraints = "\n".join(f"- {constraint}" for constraint in task["constraints"])
    return "\n\n".join((
        task["description"],
        f"**함수 시그니처**\n```python\n{task['function_signature']}\n```",
        f"**제약 조건**\n{constraints}",
        "`solution` 함수를 구현하세요. 실행할 때는 터미널에 함수 매개변수 순서대로 한 줄씩 입력합니다. 리스트·딕셔너리 값은 해당 줄에 JSON 형식으로 입력합니다.",
    ))


def execution_runner(task):
    """Add a direct stdin runner that calls solution with named input variables."""
    function = ast.parse(task["function_signature"] + "\n    pass").body[0]
    arguments = [argument.arg for argument in function.args.args]
    assignments = "\n".join(f"    {name} = read_value()" for name in arguments)
    call = ", ".join(arguments)
    return "\n".join((
        "if __name__ == '__main__':",
        "    import ast",
        "    import json",
        "    def read_value():",
        "        raw = input()",
        "        try:",
        "            return json.loads(raw)",
        "        except json.JSONDecodeError:",
        "            return ast.literal_eval(raw)",
        assignments,
        f"    print(solution({call}))",
        "",
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
            r"\n\*\*예시\*\*\n.*?(?=\n\*\*제공 코드\*\*|\Z)",
            "",
            section,
            flags=re.DOTALL,
        )
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
    if task["id"] == "S2-D":
        body = body.replace(
            "결과 행에는 query의 기존 키를 유지하고 `data` 키를 추가하세요.",
            "결과 행에는 query의 `timestamp`와 `stuff` 값을 유지하고, 연결된 센서 값 `data`를 추가하세요.",
        )
        body += "\n\n각 source는 `timestamp`와 `data` 키만, 각 query는 `timestamp`와 `stuff` 키만 가집니다."
    if task["id"] == "S1-D":
        body += "\n\n각 행은 `id`와 정수형 `value` 키만 가집니다."
    body = "**사용 언어: Python**\n\n" + body
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
        "execution_runner": execution_runner(task),
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
