"""Build a participant-facing assignment manifest without answers or test cases."""

import json
import re
import sys
from pathlib import Path


CONDITION_MODES = {"C1": "Ded-Us", "C2": "Ded-Sys", "C3": "Dir-Us", "C4": "Dir-Sys"}
PARTICIPANT_PLANS = {
    "G1V1": [("C1", 1), ("C2", 2), ("C4", 3), ("C3", 4)],
    "G1V2": [("C1", 2), ("C2", 3), ("C4", 4), ("C3", 1)],
    "G1V3": [("C1", 3), ("C2", 4), ("C4", 1), ("C3", 2)],
    "G1V4": [("C1", 4), ("C2", 1), ("C4", 2), ("C3", 3)],
    "G2V1": [("C2", 1), ("C3", 2), ("C1", 3), ("C4", 4)],
    "G2V2": [("C2", 2), ("C3", 3), ("C1", 4), ("C4", 1)],
    "G2V3": [("C2", 3), ("C3", 4), ("C1", 1), ("C4", 2)],
    "G2V4": [("C2", 4), ("C3", 1), ("C1", 2), ("C4", 3)],
    "G3V1": [("C3", 1), ("C4", 2), ("C2", 3), ("C1", 4)],
    "G3V2": [("C3", 2), ("C4", 3), ("C2", 4), ("C1", 1)],
    "G3V3": [("C3", 3), ("C4", 4), ("C2", 1), ("C1", 2)],
    "G3V4": [("C3", 4), ("C4", 1), ("C2", 2), ("C1", 3)],
    "G4V1": [("C4", 1), ("C1", 2), ("C3", 3), ("C2", 4)],
    "G4V2": [("C4", 2), ("C1", 3), ("C3", 4), ("C2", 1)],
    "G4V3": [("C4", 3), ("C1", 4), ("C3", 1), ("C2", 2)],
    "G4V4": [("C4", 4), ("C1", 1), ("C3", 2), ("C2", 3)],
}


def section(body, heading, next_heading=None):
    start = body.find(heading)
    if start == -1:
        return ""
    start += len(heading)
    end = body.find(next_heading, start) if next_heading else len(body)
    return body[start:end if end != -1 else len(body)].strip()


def task_info(task):
    body = task["body_ko"]
    description = section(body, "", "**함수 규격**")
    signature = re.search(r"```python\s*\n(.*?)\n```", section(body, "**함수 규격**", "**제약**"), re.DOTALL)
    return {
        "problem_id": task["id"],
        "title": task["title_ko"],
        "source": task["source"],
        "category": task["group"],
        "origin": task["origin"],
        "estimated_minutes": task["estimated_minutes"],
        "description": description,
        "function_signature": signature.group(1).strip() if signature else "",
        "constraints": section(body, "**제약**", "**예시**"),
    }


def main():
    exp_path, output_path = map(Path, sys.argv[1:3])
    exp_tasks = json.loads(exp_path.read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in exp_tasks}
    manifest = {
        "schema_version": "1.0",
        "scope": "참가자 ID별 컨디션·문제 세트 배정",
        "condition_modes": CONDITION_MODES,
        "participants": [],
    }
    for participant_id, plan in PARTICIPANT_PLANS.items():
        assignments = []
        for order, (condition_code, set_number) in enumerate(plan, 1):
            task_ids = (f"S{set_number}-A", f"S{set_number}-D", f"S{set_number}-B")
            assignments.append({
                "presentation_order": order,
                "condition_code": condition_code,
                "condition_mode": CONDITION_MODES[condition_code],
                "set_id": f"S{set_number}",
                "problems": [task_info(by_id[task_id]) for task_id in task_ids],
            })
        manifest["participants"].append({
            "participant_id": participant_id,
            "group": participant_id[:2],
            "assignments": assignments,
        })
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
