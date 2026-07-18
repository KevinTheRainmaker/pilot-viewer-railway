# 실험 뷰어 조건별 설문 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 각 과제의 난이도 평정 화면에서 시스템 안내 관련 5개 1~7점 문항을 저장하고, 조건별 세 문제 완료 후 외부 설문 안내를 표시한다.

**Architecture:** `exp_viewer.html`의 기존 단일 페이지 상태 전환에 조건 완료 화면을 추가한다. 평정 상태는 문제 결과 객체에 병합하고, 마지막 과제의 `pos_in_set`이 3이면 다음 과제로 전환하기 전에 안내 화면을 거치게 한다.

**Tech Stack:** 정적 HTML, CSS, 브라우저 JavaScript, Python unittest.

## Global Constraints

- `rating`은 기존 난이도 1~5점 정수로 유지한다.
- 시스템 안내 문항 5개는 모두 1~7점 정수이며 모두 선택해야 진행할 수 있다.
- 조건 순서는 `set_position` 1~4를 사용하며, 4번째 안내에는 조건 비교 설문을 명시한다.
- 기존 JSON/CSV/`submit` 결과 배열 계약은 보존한다.

---

### Task 1: 설문 데이터와 조건 종료 흐름의 회귀 검사

**Files:**
- Create: `tests/test_exp_viewer_condition_survey.py`
- Modify: `exp_viewer.html`

**Interfaces:**
- Consumes: `exp_viewer.html`의 결과 객체와 `nextTask()` 전환 흐름
- Produces: 5개 저장 필드와 4개 조건 안내 사본을 검증하는 unittest

- [ ] **Step 1: 실패하는 정적 회귀 테스트 작성**

```python
def test_condition_survey_fields_and_copy_are_present():
    text = Path('exp_viewer.html').read_text(encoding='utf-8')
    for field in [
        'system_content_reading', 'system_guidance_reflection',
        'predecided_action', 'system_guidance_influence',
        'system_guidance_immediate_action',
    ]:
        self.assertIn(field, text)
    self.assertIn("'1번째 조건'", text)
    self.assertIn("'4번째 조건'", text)
    self.assertIn("'조건 비교' 설문", text)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m unittest tests.test_exp_viewer_condition_survey -v`

Expected: 설문 필드 또는 안내 문구가 없어 실패.

- [ ] **Step 3: 최소 구현 작성**

`exp_viewer.html`에 설문 상태, 1~7점 렌더링 헬퍼, 결과 병합, `scr-condition-complete` 화면과 그 다음 단계 전환을 추가한다.

- [ ] **Step 4: 단위 테스트 통과 확인**

Run: `python -m unittest tests.test_exp_viewer_condition_survey -v`

Expected: PASS.

### Task 2: 전체 뷰어 회귀 검증과 작업 기록

**Files:**
- Modify: `tasks/todo.md`
- Modify: `tasks/lessons.md`
- Modify: `exp_viewer.html`

**Interfaces:**
- Consumes: Task 1의 설문 및 조건 전환 구현
- Produces: 검토 결과가 기록된 작업 목록과 JavaScript 문법이 유효한 뷰어

- [ ] **Step 1: JavaScript 문법 검사 실행**

Run: `node --check exp_viewer.html` 대신 스크립트 블록을 임시 `.js` 파일로 추출해 `node --check`를 실행한다.

Expected: exit code 0.

- [ ] **Step 2: 전체 Python 테스트 실행**

Run: `python -m unittest discover -s tests -v`

Expected: 모든 테스트 PASS.

- [ ] **Step 3: 작업 및 교훈 기록**

`tasks/todo.md`에 완료 항목과 실제 검증 결과를 추가하고, `tasks/lessons.md`에 조건 단위 설문은 문제 결과와 별도 상태를 갖되 결과 행에 병합한다는 교훈을 추가한다.

- [ ] **Step 4: 변경 검토**

Run: `git diff --check; git diff -- exp_viewer.html tests/test_exp_viewer_condition_survey.py tasks/todo.md tasks/lessons.md`

Expected: 공백 오류가 없고, 변경이 설문·안내·검증 기록으로 한정됨.
