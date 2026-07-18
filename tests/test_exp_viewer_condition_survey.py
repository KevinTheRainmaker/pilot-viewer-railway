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
