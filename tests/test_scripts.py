"""Offline tests for the skill's scripts. Run from the repository root:

    python3 -m unittest discover -s tests -v
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "app-store-review-preflight", "scripts")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_apple = load("fetch_apple")
guideline_sections = load("guideline_sections")
inventory = load("inventory")
check_links = load("check_links")


class FetchAppleTests(unittest.TestCase):
    def test_html_to_text_drops_scripts_and_keeps_blocks(self):
        with open(os.path.join(FIXTURES, "page.html"), encoding="utf-8") as fh:
            text = fetch_apple.html_to_text(fh.read())
        self.assertIn("## Upcoming Requirements", text)
        self.assertIn("must be built with Xcode 26 or later.", text)
        self.assertIn("• Second & last", text)
        self.assertNotIn("skip me", text)
        self.assertNotIn("color:red", text)
        self.assertNotIn("no js", text)

    def test_docc_term_list_keeps_each_definition_with_its_term(self):
        with open(os.path.join(FIXTURES, "docc_reasons.json"), encoding="utf-8") as fh:
            text = fetch_apple.docc_to_text(json.load(fh))
        lines = text.splitlines()
        ca = lines.index("- CA92.1")
        self.assertIn("only the app itself", lines[ca + 1])
        c56 = lines.index("- C56D.1")
        self.assertIn("third-party SDKs", lines[c56 + 1])
        self.assertIn("Privacy manifest files", text)

    def test_doc_json_url_accepts_paths_and_urls(self):
        expected = "https://developer.apple.com/tutorials/data/documentation/bundleresources/privacy_manifest_files.json"
        self.assertEqual(fetch_apple.doc_json_url("bundleresources/privacy_manifest_files"), expected)
        self.assertEqual(fetch_apple.doc_json_url("https://developer.apple.com/documentation/BundleResources/privacy_manifest_files/"), expected)

    def test_parse_rss_filters_by_date(self):
        with open(os.path.join(FIXTURES, "news.rss"), "rb") as fh:
            items = fetch_apple.parse_rss(fh.read(), since=date(2026, 10, 15))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["date"], "2026-11-02")
        self.assertIn("content descriptors", items[0]["text"])

    def test_fetch_refuses_non_apple_hosts(self):
        with self.assertRaises(SystemExit):
            fetch_apple.fetch("https://example.com/")
        with self.assertRaises(SystemExit):
            fetch_apple.fetch("http://developer.apple.com/")


class GuidelineSectionTests(unittest.TestCase):
    def setUp(self):
        self.lines, self.sections = guideline_sections.load_sections(os.path.join(FIXTURES, "guidelines.txt"))

    def numbers(self):
        return [n for n, _, _ in self.sections]

    def test_sections_found(self):
        self.assertEqual(self.numbers(), ["1", "1.2", "1.2.1", "2", "2.1", "2.3.1"])

    def run_cmd(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = guideline_sections.main([os.path.join(FIXTURES, "guidelines.txt"), *argv])
        return code, buf.getvalue()

    def test_show_includes_lettered_items_and_stops_at_next_number(self):
        code, out = self.run_cmd("show", "2.1")
        self.assertEqual(code, 0)
        self.assertIn("(b) If you offer in-app purchases", out)
        self.assertNotIn("2.3.1", out)

    def test_show_children(self):
        _, out = self.run_cmd("show", "1.2")
        self.assertNotIn("Creator Content", out)
        _, out = self.run_cmd("show", "1.2", "--children")
        self.assertIn("Creator Content", out)

    def test_last_section_stops_before_footer(self):
        _, out = self.run_cmd("show", "2.3.1")
        self.assertIn("Notes for Review", out)
        self.assertNotIn("Last Updated", out)

    def test_grep_reports_section_numbers(self):
        _, out = self.run_cmd("grep", "AI content creation")
        self.assertTrue(out.startswith("[1.2]"))


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        out_json = os.path.join(cls.tmp, "inv.json")
        out_md = os.path.join(cls.tmp, "inv.md")
        with redirect_stdout(io.StringIO()):
            inventory.main([os.path.join(FIXTURES, "SampleApp"), "--json", out_json, "--md", out_md])
        with open(out_json, encoding="utf-8") as fh:
            cls.inv = json.load(fh)
        with open(out_md, encoding="utf-8") as fh:
            cls.md = fh.read()
        cls.flags = "\n".join(cls.inv["flags"])

    def test_parse_openstep_handles_comments_and_quotes(self):
        data = inventory.parse_openstep('// !$*UTF8*$!\n{ a = "x y"; /* c */ b = ( 1, two, ); c = { d = e; }; }')
        self.assertEqual(data["a"], "x y")
        self.assertEqual(data["b"], ["1", "two"])
        self.assertEqual(data["c"]["d"], "e")

    def test_targets_and_merged_settings(self):
        targets = {t["name"]: t for t in self.inv["projects"][0]["targets"]}
        self.assertEqual(set(targets), {"SampleApp", "SampleWidget"})
        app = targets["SampleApp"]
        self.assertEqual(app["configurations"]["Release"]["IPHONEOS_DEPLOYMENT_TARGET"], "17.0")  # from project level
        self.assertEqual(app["infoPlist"]["NSCameraUsageDescription"], "Take a photo of your plant to identify it.")
        self.assertIn("GoogleMobileAds", app["packageProducts"])

    def test_upload_flags(self):
        # The build setting lists all four iPad orientations, but the Info.plist file lists
        # three and the file's value is the one that ships.
        self.assertIn("missing UIInterfaceOrientationPortraitUpsideDown", self.flags)
        self.assertIn("UISupportedInterfaceOrientations~ipad is set in both the Info.plist file", self.flags)
        self.assertIn("SampleWidget: CURRENT_PROJECT_VERSION 2 differs from the app's 3", self.flags)
        self.assertIn("ITSAppUsesNonExemptEncryption not set", self.flags)

    def test_purpose_string_flags(self):
        self.assertIn("'location' API used", self.flags)
        self.assertIn("NSUserTrackingUsageDescription missing", self.flags)
        self.assertNotIn("'camera' API used", self.flags)

    def test_background_mode_without_use(self):
        self.assertIn("UIBackgroundModes has 'audio'", self.flags)

    def test_privacy_manifest_gap(self):
        self.assertIn("NSPrivacyAccessedAPICategorySystemBootTime not declared", self.flags)
        self.assertNotIn("NSPrivacyAccessedAPICategoryUserDefaults not declared", self.flags)

    def test_debug_hooks(self):
        outside = self.inv["sources"]["processEnvironmentOutsideDebug"]
        self.assertEqual(len(outside), 1)
        self.assertIn("UNLOCK_PRO", outside[0])

    def test_sdks_ids_and_ai(self):
        names = {s["name"] for s in self.inv["sdks"]}
        self.assertIn("Google Mobile Ads (AdMob)", names)
        self.assertNotIn("AppsFlyer", names)  # only inside a block comment
        self.assertIn("1234567890", self.inv["sources"]["appStoreIds"])
        self.assertIn("ai_endpoint", self.inv["sources"]["signals"])
        self.assertIn("rr_user_defaults", self.inv["sources"]["signals"])

    def test_localized_purpose_strings(self):
        self.assertEqual(self.inv["infoPlistLocalizations"].get("NSCameraUsageDescription"), ["en"])

    def test_markdown_summary(self):
        self.assertIn("## Mechanical flags", self.md)
        self.assertIn("com.example.sample", self.md)

    def test_debug_mask(self):
        mask = inventory.debug_mask(["a", "#if DEBUG", "b", "#else", "c", "#endif", "#if !DEBUG", "d", "#else", "e", "#endif"])
        self.assertEqual(mask, [False, False, True, False, False, False, False, False, False, True, False])


class CheckLinksTests(unittest.TestCase):
    def test_skips_templates_and_private_hosts(self):
        self.assertEqual(check_links.check_url("https://apps.apple.com/app/id\\(…)")[1], "skipped (template)")
        self.assertEqual(check_links.check_url("http://localhost:3001/api")[1], "skipped (private or local host)")
        self.assertEqual(check_links.check_url("http://192.168.1.2/x")[1], "skipped (private or local host)")

    def test_api_detection(self):
        self.assertTrue(check_links.is_api_url("https://api.example.org/"))
        self.assertTrue(check_links.is_api_url("https://example.org/api/v1/items"))
        self.assertFalse(check_links.is_api_url("https://example.org/privacy-policy"))

    def test_scripts_run_isolated(self):
        out = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "guideline_sections.py"),
                              os.path.join(FIXTURES, "guidelines.txt"), "list"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("2.3.1", out.stdout)


if __name__ == "__main__":
    unittest.main()
