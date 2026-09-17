import tempfile
import unittest
from pathlib import Path
from lab.core import Bundle, Config
from lab.workflow import run_stage, STAGES


TEST_TMP = Path(__file__).resolve().parents[1] / "build/tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class WorkflowTests(unittest.TestCase):
    def test_resume_does_not_repeat_completed_action(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), True)
            count = []
            run_stage(b, "one", lambda: count.append(1))
            run_stage(b, "one", lambda: count.append(2))
            self.assertEqual(count, [1])

    def test_failed_stage_retry_and_durable_state(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), True)

            def fail():
                raise ValueError("SYNTHETIC failure")

            self.assertFalse(run_stage(b, "four", fail))
            self.assertEqual(
                Bundle.open(b.path).metadata["stages"]["four"]["status"], "FAIL"
            )
            self.assertTrue(run_stage(b, "four", lambda: None))
            self.assertEqual(b.metadata["stages"]["four"]["status"], "PASS")

    def test_human_observation_stages_exist(self):
        self.assertEqual(len(STAGES), 10)
        self.assertIn("06-flatscreen", STAGES)


class RetryTests(unittest.TestCase):
    def test_retry_clears_only_related_observations(self):
        from lab.workflow import reset_stage

        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), False)
            b.write(
                "android/observations.json",
                {
                    "video_visible": "FAIL",
                    "pointer": "FAIL",
                    "clear_video": "PASS",
                    "audio": "PASS",
                },
            )
            reset_stage(b, "06-flatscreen")
            self.assertEqual(
                b.read("android/observations.json"),
                {"clear_video": "PASS", "audio": "PASS"},
            )

    def test_declined_service_stage_persists_skip(self):
        from lab.workflow import decline_service

        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), False)
            calls = []
            decline_service(b)
            run_stage(b, "09-service", lambda: calls.append(1))
            self.assertEqual(calls, [])
