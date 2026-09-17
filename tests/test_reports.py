import tempfile
import unittest
from pathlib import Path
from lab.core import Bundle, Config
from lab.reports import render_report, assess_drm, classify
from lab.synthetic import populate, SCENARIOS


TEST_TMP = Path(__file__).resolve().parents[1] / "build/tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class ReportsTests(unittest.TestCase):
    def test_no_l1_from_property_or_ads(self):
        self.assertEqual(
            assess_drm({"supported": True, "properties": {"securityLevel": "L1"}})[
                "actual_session"
            ],
            "NOT TESTED",
        )

    def test_open_session_precise_api_label(self):
        d = assess_drm(
            {
                "supported": True,
                "session": {"status": "OPENED", "security_level_name": "HW_SECURE_ALL"},
            }
        )
        self.assertEqual(d["actual_session"], "HW_SECURE_ALL")
        self.assertEqual(d["protected_playback"], "NOT TESTED")

    def test_all_scenarios_render_without_real_claims(self):
        for scenario in SCENARIOS:
            with (
                self.subTest(scenario=scenario),
                tempfile.TemporaryDirectory(dir=TEST_TMP) as d,
            ):
                b = Bundle.create(Path(d), Config(), True)
                populate(b, scenario)
                r = render_report(b)
                self.assertTrue(r["synthetic"])
                self.assertIn("SYNTHETIC", (b.path / "report.md").read_text())
                self.assertEqual(len(r["services"]), 5)

    def test_classify_separates_headset_and_screenshot(self):
        self.assertIn(
            "HOST PANEL ABSENT",
            classify({"activity_rendered": "PASS", "video_visible": "FAIL"}),
        )
        self.assertIn(
            "POSSIBLE CAPTURE PROTECTION",
            classify({"video_visible": "PASS", "screenshot_video": "FAIL"}),
        )
        self.assertIn(
            "PROTECTED VIDEO BLACK",
            classify(
                {"clear_video": "PASS", "protected_video": "FAIL", "audio": "PASS"}
            ),
        )

    def test_report_redaction_and_unknowns(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), False)
            b.write(
                "services/disney.json",
                {"service": "Disney+", "notes": "sean@example.org token=TOPSECRET"},
            )
            r = render_report(b)
            self.assertEqual(r["drm"]["actual_session"], "NOT TESTED")
            txt = (b.path / "report.md").read_text()
            self.assertNotIn("TOPSECRET", txt)
            self.assertNotIn("sean@example.org", txt)


class RealSchemaTests(unittest.TestCase):
    def test_hdcp_actual_android_export_shape(self):
        d = assess_drm(
            {"connected_hdcp_level": 6, "max_hdcp_level": 6, "hdcp_error": None}
        )
        self.assertEqual(d["hdcp"]["connected_level"], 6)

    def test_real_service_and_drm_failures_are_classified(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), False)
            b.write("drm/widevine.json", {"supported": False})
            b.write("services/disney.json", {"service": "Disney+", "login": "FAIL"})
            r = render_report(b)
            self.assertIn("WIDEVINE UNSUPPORTED", r["classifications"])
            self.assertIn("LOGIN FAILED", r["service_classifications"]["Disney+"])

    def test_valid_resolution_needs_measured_evidence(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), False)
            b.write(
                "media/playback.json",
                {
                    "video_decoder": "decoder",
                    "video_actually_used": True,
                    "video_output_width": 1920,
                    "video_output_height": 1080,
                },
            )
            r = render_report(b)
            self.assertEqual(r["tested_decode"]["resolution"], "1920x1080")


class FreshMediaTests(unittest.TestCase):
    def test_old_completed_playback_cannot_describe_new_launch(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as d:
            b = Bundle.create(Path(d), Config(), False)
            b.write(
                "media/playback.json",
                {
                    "launch_id": "old",
                    "video_decoder": "old-decoder",
                    "video_actually_used": True,
                    "video_output_width": 3840,
                    "video_output_height": 2160,
                },
            )
            b.write("media/expected-launch.json", {"launch_id": "new"})
            b.write("android/observations.json", {"clear_video": "PASS"})
            r = render_report(b)
            self.assertEqual(r["tested_decode"]["resolution"], "NOT TESTED")
            self.assertNotIn("old-decoder", (b.path / "report.md").read_text())
