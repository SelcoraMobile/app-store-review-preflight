"""Offline tests for the skill's scripts. Run from the repository root:

    python3 -m unittest discover -s tests -v
"""
import importlib.util
import io
import json
import os
import shutil
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
render_report = load("render_report")


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

    def test_html_to_text_main_only_drops_navigation(self):
        with open(os.path.join(FIXTURES, "page.html"), encoding="utf-8") as fh:
            raw = fh.read()
        full = fetch_apple.html_to_text(raw)
        main = fetch_apple.html_to_text(raw, main_only=True)
        self.assertIn("Explore Platforms", full)
        self.assertNotIn("Explore Platforms", main)
        self.assertNotIn("Developer Footer", main)
        self.assertTrue(main.startswith("## Upcoming Requirements"))

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
        self.assertEqual(self.numbers(), ["1", "1.2", "1.2.1", "2", "2.1", "2.3.1", "3", "3.1.2", "3.1.2(a)", "3.1.2(c)", "3.1.3"])

    def test_show_includes_lettered_sections(self):
        _, out = self.run_cmd("show", "3.1.2")
        self.assertIn("3.1.2(c) Subscription Information", out)
        self.assertNotIn("3.1.3", out)

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
        _, out = self.run_cmd("show", "3.1.3")
        self.assertIn("Other Purchase Methods", out)
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

    def test_reviewer_flags_consent_sdk_and_pre_dialog(self):
        self.assertIn("reviewer_detection", self.inv["sources"]["signals"])
        self.assertIn("Google UMP is linked but never called", self.flags)
        self.assertIn("custom pre-permission UI found", self.flags)
        self.assertIn("PushPrimer.swift", self.flags)

    def test_uncommitted_build_number_change(self):
        tmp = tempfile.mkdtemp()
        repo = os.path.join(tmp, "repo")
        shutil.copytree(os.path.join(FIXTURES, "SampleApp"), repo)
        git = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(git[:3] + ["init", "-q"], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "fixture"], check=True)
        pbx = os.path.join(repo, "SampleApp.xcodeproj", "project.pbxproj")
        with open(pbx, encoding="utf-8") as fh:
            text = fh.read()
        with open(pbx, "w", encoding="utf-8") as fh:
            fh.write(text.replace("CURRENT_PROJECT_VERSION = 3;", "CURRENT_PROJECT_VERSION = 1;"))
        out_json = os.path.join(tmp, "inv.json")
        with redirect_stdout(io.StringIO()):
            inventory.main([repo, "--json", out_json, "--md", os.path.join(tmp, "inv.md")])
        with open(out_json, encoding="utf-8") as fh:
            flags = "\n".join(json.load(fh)["flags"])
        self.assertIn("CURRENT_PROJECT_VERSION 3 -> 1", flags)

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


class RenderReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FIXTURES, "report.md"), encoding="utf-8") as fh:
            cls.markdown = fh.read()
        cls.page, cls.doc = render_report.render(cls.markdown, version="test")

    def test_findings_confidence_and_new_build(self):
        cards = self.doc["cards"]
        self.assertEqual([c["guideline"] for c in cards], ["2.1(b)", "Upload: iPad orientations", "5.1.2(i)", "4.3(a)"])
        self.assertEqual([c["conf"] for c in cards], ["validator-certain", "review-risk", "review-risk", "judgment-call"])
        self.assertEqual([c["build"] for c in cards], ["no", "yes", "yes", "no"])
        self.assertEqual(cards[1]["qualifier"], "validator-blocking if shipped as-is; needs build verification")
        self.assertEqual(self.doc["overview"]["mapping"], [0, 1, 2, 3])

    def test_bold_and_plain_fields(self):
        bulleted, plain_lines = self.doc["cards"][0], self.doc["cards"][2]
        for card in (bulleted, plain_lines):
            self.assertEqual([f["kind"] for f in card["fields"]], ["confidence", "evidence", "why", "fix"])
        self.assertIn("Paywall/PaywallView.swift:88", render_report.blocks_text(bulleted["fields"][1]["blocks"]))
        self.assertIn('class="field f-fix"', self.page)

    def test_untrusted_text_is_escaped(self):
        self.assertNotIn("<script>alert", self.page)
        self.assertIn("&lt;script&gt;alert", self.page)
        self.assertNotRegex(self.page, r'href="\s*javascript:')
        self.assertIn('href="https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage"', self.page)
        self.assertEqual(render_report.safe_href("JavaScript:alert(1)"), None)
        self.assertEqual(render_report.safe_href("//evil.example/x"), None)
        self.assertNotIn("<a", render_report.render_inline("[x](data:text/html,hi)"))

    def test_page_is_self_contained_with_hash_csp(self):
        import base64, hashlib, re
        self.assertNotRegex(self.page, r"<(link|img|iframe)\b")
        self.assertNotRegex(self.page, r"\bsrc=")
        csp = re.search(r'Content-Security-Policy" content="([^"]+)"', self.page).group(1)
        self.assertIn("default-src 'none'", csp)
        for tag in ("style", "script"):
            body = re.search(r"<%s>(.*?)</%s>" % (tag, tag), self.page, re.S).group(1)
            digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode()
            self.assertIn("'sha256-%s'" % digest, csp)

    def test_checklist_becomes_checkboxes(self):
        self.assertEqual(self.page.count('type="checkbox" id="t-'), 4)
        self.assertEqual(self.page.count(" checked>"), 1)
        self.assertIn("data-progress=", self.page)

    def test_inline_markdown(self):
        out = render_report.render_inline("**Fix:** use `a|b` and *see* https://example.org/p.")
        self.assertIn("<strong>Fix:</strong>", out)
        self.assertIn("<code>a|b</code>", out)
        self.assertIn("<em>see</em>", out)
        self.assertIn('href="https://example.org/p"', out)
        self.assertEqual(render_report.render_inline("INFOPLIST_KEY_UISupported_iPad"), "INFOPLIST_KEY_UISupported_iPad")
        self.assertEqual(render_report.split_row("| 1 | `a | b` | x |"), ["1", "`a | b`", "x"])

    def test_turkish_report_without_findings_table(self):
        md = ("# Uygulama 1.0 (3): App Store inceleme ön kontrolü\n\n## Bulgular\n\n"
              "### [2.1(a)] Değerlendir bağlantısı başka uygulamayı açıyor\n"
              "Güven: review-risk\nKanıt: `Config.swift:9` başka bir App Store ID kullanıyor.\n"
              "Neden önemli: 2.1(a) \"fully functional URLs\" ister.\n"
              "Düzeltme: doğru Apple ID'yi kullanın. Yeni build: evet.\n\n"
              "## Kontrol listesi\n- [ ] Build yüklendi\n")
        page, doc = render_report.render(md, lang="tr", version="test")
        card = doc["cards"][0]
        self.assertEqual(card["conf"], "review-risk")
        self.assertEqual(card["build"], "yes")
        self.assertEqual([f["kind"] for f in card["fields"]], ["confidence", "evidence", "why", "fix"])
        self.assertIn('<html lang="tr"', page)
        self.assertIn("Bulgularda ara", page)
        self.assertIn("<h1>Uygulama 1.0 (3)</h1>", page)

    def test_cli_runs_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "report.html")
            out = subprocess.run([sys.executable, "-I", os.path.join(SCRIPTS, "render_report.py"),
                                  os.path.join(FIXTURES, "report.md"), "--out", out_path, "--lang", "tr"],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("4 findings", out.stdout)
            self.assertEqual(out.stderr, "")
            with open(out_path, encoding="utf-8") as fh:
                self.assertIn("Yeni build gerektiren", fh.read())


if __name__ == "__main__":
    unittest.main()
