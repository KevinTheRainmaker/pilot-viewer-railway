from pathlib import Path
import unittest


class ExpViewerConditionSurveyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path('exp_viewer.html').read_text(encoding='utf-8')

    def test_records_all_five_system_guidance_responses(self):
        for field in [
            'system_content_reading',
            'system_guidance_reflection',
            'predecided_action',
            'system_guidance_influence',
            'system_guidance_immediate_action',
        ]:
            self.assertIn(field, self.text)

    def test_names_the_intervention_popup_in_every_survey_question(self):
        questions = [
            '시스템 개입(팝업)이 제시한 내용을 주의 깊게 읽었다.',
            '시스템 개입(팝업)이 제시한 안내는 내가 하려던 행동을 한 번 더 돌아보게 만들었다.',
            '시스템 개입(팝업)이 제시한 내용을 읽기 전에, 이미 어떻게 행동할지 결정한 경우가 많았다.',
            '시스템 개입(팝업)이 제시한 안내는 나의 다음 행동에 영향을 주었다.',
            '시스템 개입(팝업)이 제시한 안내는 내가 깊이 생각하기보다 바로 행동하도록 만들었다.',
        ]
        for question in questions:
            self.assertIn(question, self.text)

    def test_uses_seven_point_difficulty_scale_with_requested_copy(self):
        self.assertIn('이번 문제를 해결하는 과정은 나에게 얼마나 어려웠나요?', self.text)
        self.assertIn('1: 매우 쉬움 - 7: 매우 어려움', self.text)
        self.assertIn('for (let v=1; v<=7; v++)', self.text)

    def test_shows_condition_form_instruction_after_each_three_task_set(self):
        self.assertIn("'1번째 조건'", self.text)
        self.assertIn("'2번째 조건'", self.text)
        self.assertIn("'3번째 조건'", self.text)
        self.assertIn("'4번째 조건'", self.text)
        self.assertIn("'조건 비교' 설문", self.text)
        self.assertIn("pos_in_set === 3", self.text)


if __name__ == '__main__':
    unittest.main()
