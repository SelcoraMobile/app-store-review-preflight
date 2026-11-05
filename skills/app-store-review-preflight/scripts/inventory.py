#!/usr/bin/env python3
"""Inventory an iOS/iPadOS repository for an App Store review preflight.

Read-only and stdlib-only. It parses the Xcode project (targets, merged build
settings, generated Info.plist keys), Info.plist and InfoPlist.strings files,
entitlements, privacy manifests, Swift package / CocoaPods lockfiles, and scans
source for the API, SDK and configuration signals the review checks depend on.

Usage:
  python3 -I inventory.py REPO_ROOT [--json OUT.json] [--md OUT.md] [--max-hits N]

Without --md the markdown summary goes to stdout. Everything it reports is a
*signal* with file:line evidence, not a verdict: confirm in code before citing.
Build settings come from project.pbxproj (project level overlaid by target level);
values set only in .xcconfig files are listed separately and not merged, so use
`xcodebuild -showBuildSettings` when a finding depends on an exact resolved value.
"""
import argparse
import json
import os
import plistlib
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict

SKIP_DIRS = {".git", "Pods", "Carthage", "DerivedData", ".build", "build", "node_modules", ".swiftpm",
             "xcuserdata", "vendor", ".venv", "venv", "fastlane", "Tests", "UITests", "Examples",
             "Example", "Demo", "Samples", "Sample", "Fixtures", "fixtures", "Preview Content"}
SOURCE_EXT = {".swift", ".m", ".mm", ".h", ".c", ".cc", ".cpp"}
APP_PRODUCT = "com.apple.product-type.application"

# ---------------------------------------------------------------- OpenStep plist (project.pbxproj)

_TOKEN = re.compile(r"[A-Za-z0-9_$/:.\-+<>]+")


def parse_openstep(text):
    """Parse the old-style (OpenStep) property list used by project.pbxproj."""
    pos = 0
    n = len(text)

    def skip():
        nonlocal pos
        while pos < n:
            ch = text[pos]
            if ch in " \t\r\n":
                pos += 1
            elif text.startswith("/*", pos):
                end = text.find("*/", pos + 2)
                pos = n if end < 0 else end + 2
            elif text.startswith("//", pos):
                end = text.find("\n", pos)
                pos = n if end < 0 else end + 1
            else:
                break

    def value():
        nonlocal pos
        skip()
        ch = text[pos]
        if ch == "{":
            pos += 1
            result = OrderedDict()
            while True:
                skip()
                if text[pos] == "}":
                    pos += 1
                    return result
                key = value()
                skip()
                if text[pos] != "=":
                    raise ValueError(f"expected '=' at {pos}")
                pos += 1
                val = value()
                skip()
                if text[pos] != ";":
                    raise ValueError(f"expected ';' at {pos}")
                pos += 1
                result[key] = val
        if ch == "(":
            pos += 1
            items = []
            while True:
                skip()
                if text[pos] == ")":
                    pos += 1
                    return items
                items.append(value())
                skip()
                if text[pos] == ",":
                    pos += 1
        if ch == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == "\\":
                    pos += 1
                    esc = text[pos]
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
                else:
                    buf.append(text[pos])
                pos += 1
            pos += 1
            return "".join(buf)
        match = _TOKEN.match(text, pos)
        if not match:
            raise ValueError(f"unexpected {text[pos]!r} at {pos}")
        pos = match.end()
        return match.group(0)

    return value()


# ---------------------------------------------------------------- helpers

def rel(path, root):
    return os.path.relpath(path, root)


def walk(root, exts=None, names=None):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith((".xcassets", ".xcframework", ".framework", ".bundle", ".lproj")) or d.endswith(".lproj")]
        for fn in filenames:
            if names and fn in names:
                yield os.path.join(dirpath, fn)
            elif exts and os.path.splitext(fn)[1] in exts:
                yield os.path.join(dirpath, fn)


def load_plist(path):
    try:
        with open(path, "rb") as fh:
            return plistlib.load(fh)
    except Exception as err:  # noqa: BLE001 - report and continue
        return {"__error__": str(err)}


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=20)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def list_value(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [v for v in re.split(r"[\s,]+", value.strip()) if v and v != "$(inherited)"]
    return []


# ---------------------------------------------------------------- Xcode project

def read_projects(root):
    projects = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for d in list(dirnames):
            if d.endswith(".xcodeproj"):
                pbx = os.path.join(dirpath, d, "project.pbxproj")
                if os.path.exists(pbx):
                    projects.append(pbx)
                dirnames.remove(d)
    result = []
    for pbx in projects:
        try:
            with open(pbx, encoding="utf-8") as fh:
                data = parse_openstep(fh.read())
        except Exception as err:  # noqa: BLE001
            result.append({"path": rel(pbx, root), "error": f"could not parse: {err}"})
            continue
        result.append(project_summary(pbx, data, root))
    return result


def config_settings(objs, list_id):
    configs = {}
    for cid in objs.get(list_id, {}).get("buildConfigurations", []):
        cfg = objs.get(cid, {})
        configs[cfg.get("name", cid)] = {
            "settings": dict(cfg.get("buildSettings", {})),
            "xcconfig": objs.get(cfg.get("baseConfigurationReference", ""), {}).get("path"),
        }
    return configs


def project_summary(pbx, data, root):
    objs = data.get("objects", {})
    project_dir = os.path.dirname(os.path.dirname(pbx))
    proj_obj = next((o for o in objs.values() if o.get("isa") == "PBXProject"), {})
    proj_cfgs = config_settings(objs, proj_obj.get("buildConfigurationList", ""))
    packages = []
    for o in objs.values():
        if o.get("isa") == "XCRemoteSwiftPackageReference":
            packages.append({"kind": "remote", "url": o.get("repositoryURL"), "requirement": dict(o.get("requirement", {}))})
        elif o.get("isa") == "XCLocalSwiftPackageReference":
            packages.append({"kind": "local", "path": o.get("relativePath")})
    targets = []
    for oid, o in objs.items():
        if o.get("isa") != "PBXNativeTarget":
            continue
        t_cfgs = config_settings(objs, o.get("buildConfigurationList", ""))
        merged = {}
        for name, cfg in t_cfgs.items():
            base = dict(proj_cfgs.get(name, {}).get("settings", {}))
            base.update(cfg["settings"])
            merged[name] = base
        products = [objs.get(p, {}).get("productName") for p in o.get("packageProductDependencies", [])]
        deps = [objs.get(objs.get(d, {}).get("target", ""), {}).get("name") for d in o.get("dependencies", [])]
        targets.append({
            "name": o.get("name"),
            "productType": o.get("productType"),
            "configurations": merged,
            "xcconfigs": sorted({c["xcconfig"] for c in t_cfgs.values() if c.get("xcconfig")}
                                | {c["xcconfig"] for c in proj_cfgs.values() if c.get("xcconfig")}),
            "packageProducts": [p for p in products if p],
            "dependencies": [d for d in deps if d],
        })
    return {"path": rel(pbx, root), "projectDir": project_dir, "packages": packages, "targets": targets}


def release_settings(target):
    cfgs = target["configurations"]
    for name in ("Release", "release", "AppStore", "Production"):
        if name in cfgs:
            return name, cfgs[name]
    if cfgs:
        name = sorted(cfgs)[-1]
        return name, cfgs[name]
    return None, {}


def resolve_path(value, project_dir, target_name):
    value = value.replace("$(SRCROOT)/", "").replace("${SRCROOT}/", "").replace("$(PROJECT_DIR)/", "")
    value = value.replace("$(TARGET_NAME)", target_name or "").replace("${TARGET_NAME}", target_name or "")
    return os.path.normpath(os.path.join(project_dir, value))


def merged_info_plist(target, project_dir, conflicts=None):
    """Release Info.plist as the build would produce it.

    Keys from INFOPLIST_KEY_* build settings come first; a key that is also in the
    INFOPLIST_FILE keeps the file's value (observed in practice: the file wins, which
    can silently undo a setting changed in Xcode's target editor). Keys defined in both
    places with different values are reported through `conflicts`.
    """
    cfg_name, settings = release_settings(target)
    info = {}
    generated = {}
    if str(settings.get("GENERATE_INFOPLIST_FILE", "")).upper() == "YES":
        for key, val in settings.items():
            if key.startswith("INFOPLIST_KEY_"):
                # Build settings spell the iPad variant "_iPad" where the plist uses "~ipad".
                plist_key = key[len("INFOPLIST_KEY_"):].replace("UISupportedInterfaceOrientations_iPad", "UISupportedInterfaceOrientations~ipad")
                generated[plist_key] = val
    info.update(generated)
    source = None
    if settings.get("INFOPLIST_FILE"):
        source = resolve_path(settings["INFOPLIST_FILE"], project_dir, target["name"])
        if os.path.exists(source):
            loaded = load_plist(source)
            if isinstance(loaded, dict):
                for key, val in loaded.items():
                    if key in generated and conflicts is not None and list_value(val) != list_value(generated[key]) and str(val) != str(generated[key]):
                        conflicts.append((key, val, generated[key]))
                    info[key] = val
    return cfg_name, source, info, sorted(generated)


# ---------------------------------------------------------------- source signals

SIGNALS = OrderedDict([
    # permission-gated APIs: (regex, required Info.plist keys)
    ("camera", (r"AVCaptureDevice|\.sourceType\s*=\s*\.camera|UIImagePickerController\.SourceType\.camera|AVCaptureSession", ["NSCameraUsageDescription"])),
    ("microphone", (r"AVAudioRecorder|requestRecordPermission|setCategory\(\.(playAndRecord|record)\b|installTap\(onBus|SFSpeechAudioBufferRecognitionRequest", ["NSMicrophoneUsageDescription"])),
    ("photo_library_read", (r"PHAsset\.fetch|PHPhotoLibrary\.requestAuthorization\((?!for: \.addOnly)|PHPhotoLibrary\.authorizationStatus\((?!for: \.addOnly)|PHImageManager", ["NSPhotoLibraryUsageDescription"])),
    ("photo_library_add_only", (r"requestAuthorization\(for: \.addOnly\)|PHAssetCreationRequest|UIImageWriteToSavedPhotosAlbum|PHAssetChangeRequest", ["NSPhotoLibraryAddUsageDescription"])),
    ("photo_picker_no_permission", (r"PhotosPicker|PHPickerViewController", [])),
    ("location", (r"CLLocationManager|requestWhenInUseAuthorization|requestAlwaysAuthorization|CLLocationUpdate", ["NSLocationWhenInUseUsageDescription"])),
    ("contacts", (r"CNContactStore|CNContactPickerViewController", ["NSContactsUsageDescription"])),
    ("calendars", (r"EKEventStore", ["NSCalendarsFullAccessUsageDescription|NSCalendarsWriteOnlyAccessUsageDescription|NSCalendarsUsageDescription"])),
    ("health", (r"HKHealthStore", ["NSHealthShareUsageDescription|NSHealthUpdateUsageDescription"])),
    ("bluetooth", (r"CBCentralManager|CBPeripheralManager", ["NSBluetoothAlwaysUsageDescription"])),
    ("speech", (r"SFSpeechRecognizer", ["NSSpeechRecognitionUsageDescription"])),
    ("face_id", (r"LAContext|evaluatePolicy", ["NSFaceIDUsageDescription"])),
    ("motion_activity", (r"CMMotionActivityManager|CMPedometer", ["NSMotionUsageDescription"])),
    ("nfc", (r"NFCNDEFReaderSession|NFCTagReaderSession|NFCReaderSession", ["NFCReaderUsageDescription"])),
    ("media_library", (r"MPMediaLibrary|MPMediaQuery", ["NSAppleMusicUsageDescription"])),
    ("local_network", (r"NWBrowser|NetService\b|NWConnection\(host|Bonjour", ["NSLocalNetworkUsageDescription"])),
    ("tracking_request", (r"requestTrackingAuthorization", ["NSUserTrackingUsageDescription"])),
    ("idfa_read", (r"advertisingIdentifier|ASIdentifierManager", ["NSUserTrackingUsageDescription"])),
    ("notifications_request", (r"requestAuthorization\(options:|registerForRemoteNotifications", [])),
    # required-reason API categories (privacy manifest)
    ("rr_user_defaults", (r"UserDefaults|NSUserDefaults|@AppStorage", ["NSPrivacyAccessedAPICategoryUserDefaults"])),
    ("rr_system_boot_time", (r"systemUptime|mach_absolute_time|kern\.boottime", ["NSPrivacyAccessedAPICategorySystemBootTime"])),
    ("rr_file_timestamp", (r"\.creationDate\b|\.modificationDate\b|contentModificationDateKey|creationDateKey|attributesOfItem|\bfstat\(|\blstat\(|\bstat\(|getattrlist", ["NSPrivacyAccessedAPICategoryFileTimestamp"])),
    ("rr_disk_space", (r"volumeAvailableCapacity|systemFreeSize|systemSize|\bstatfs\(|\bstatvfs\(|volumeTotalCapacity", ["NSPrivacyAccessedAPICategoryDiskSpace"])),
    ("rr_active_keyboards", (r"activeInputModes", ["NSPrivacyAccessedAPICategoryActiveKeyboards"])),
    # review prompts and store links
    ("review_prompt_api", (r"SKStoreReviewController|requestReview|AppStore\.requestReview", [])),
    ("write_review_link", (r"action=write-review", [])),
    # web and dynamic code
    ("wkwebview", (r"WKWebView", [])),
    ("uiwebview", (r"\bUIWebView\b", [])),
    ("safari_view", (r"SFSafariViewController", [])),
    ("dynamic_code", (r"\bdlopen\(|\bdlsym\(|NSClassFromString|NSSelectorFromString|performSelector\(|evaluateScript\(", [])),
    # payments
    ("storekit_purchase", (r"Product\.products\(|SKProductsRequest|\.purchase\(|SKPaymentQueue|Transaction\.currentEntitlements|Transaction\.updates", [])),
    ("restore_purchases", (r"AppStore\.sync\(|restoreCompletedTransactions|restorePurchases?\b|Purchases\.shared\.restore|\.restore\(\)", [])),
    ("external_payment", (r"Stripe|PayPal|Braintree|checkout\.|/checkout", [])),
    # accounts
    ("sign_in_with_apple", (r"ASAuthorizationAppleIDProvider|SignInWithAppleButton", [])),
    ("third_party_login", (r"GIDSignIn|GoogleSignIn|LoginManager\(\)|FBSDKLoginKit|FacebookLogin", [])),
    ("account_creation", (r"createUser\(|signUp\(|createAccount|Auth\.auth\(\)\.createUser|/register\b|/signup\b|\.signUp\b", [])),
    ("account_deletion", (r"deleteUser|deleteAccount|delete_account|user\.delete\(|currentUser\?\.delete|removeAccount|/account/delete", [])),
    # tracking / remote config / review detection
    ("remote_config", (r"RemoteConfig\.remoteConfig|remoteConfig\.|configValue\(forKey|LaunchDarkly|LDClient|Statsig|ConfigCat|Optimizely|GrowthBook", [])),
    ("reviewer_detection", (r"isReview|reviewMode|reviewerMode|appReview|isAppleReviewer|isReviewer|is_reviewer|isApple\b|is_apple|isTestDevice|underReview|sandboxReceipt|AppTransaction\.shared|\.environment\s*==\s*\.sandbox|17\.0\.0\.0|Cupertino", [])),
    ("ump_usage", (r"ConsentInformation|ConsentForm|requestConsentInfoUpdate|UMPConsent", [])),
    ("permission_pre_dialog", (r"preDialog|PreDialog|prePrompt|PrePrompt|primerView|PermissionPrimer|softPrompt|SoftPrompt|askPushPreDialog", [])),
    ("debug_gestures", (r"motionEnded|debugMenu|DebugMenu|secretTap|tapCount\s*>=", [])),
    ("process_environment", (r"ProcessInfo\.processInfo\.(environment|arguments)", [])),
    # background work (for UIBackgroundModes)
    ("bg_audio", (r"AVAudioSession.*\.playback|setCategory\(\.playback|AVPlayer\b|AVAudioPlayer\b", [])),
    ("bg_location", (r"allowsBackgroundLocationUpdates|startMonitoringSignificantLocationChanges", [])),
    ("bg_tasks", (r"BGTaskScheduler|BGAppRefreshTask|BGProcessingTask", [])),
    ("voip", (r"PKPushRegistry|CXProvider", [])),
    ("bluetooth_bg", (r"CBCentralManager|CBPeripheralManager", [])),
    # AI and personal data flows
    ("ai_endpoint", (r"api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com|openrouter\.ai|fal\.run|fal\.ai|replicate\.com|api\.stability\.ai|api\.together\.(xyz|ai)|api\.groq\.com|api\.mistral\.ai|api\.deepseek\.com|api\.x\.ai|api\.cohere\.(ai|com)|api-inference\.huggingface\.co|api\.elevenlabs\.io", [])),
    ("ai_sdk", (r"import (OpenAI|Anthropic|GoogleGenerativeAI|FirebaseAI|FirebaseVertexAI|MLXLLM|FoundationModels)\b", [])),
    ("ipv4_literal", (r"https?://\d{1,3}(?:\.\d{1,3}){3}\b", [])),
    ("test_ad_unit", (r"ca-app-pub-3940256099942544", [])),
    ("face_processing", (r"VNDetectFaceRectanglesRequest|VNDetectFaceLandmarksRequest|ARFaceTrackingConfiguration|faceObservation|CIDetectorTypeFace", [])),
])

BG_MODE_SIGNALS = {
    "audio": ["bg_audio"],
    "location": ["bg_location"],
    "voip": ["voip"],
    "fetch": ["bg_tasks"],
    "processing": ["bg_tasks"],
    "bluetooth-central": ["bluetooth_bg"],
    "bluetooth-peripheral": ["bluetooth_bg"],
    "remote-notification": ["notifications_request"],
}

SDKS = [
    # (name, category, regexes over the identifier corpus)
    ("Google Mobile Ads (AdMob)", "ads", [r"googlemobileads", r"google-mobile-ads", r"plist:gadapplicationidentifier"]),
    ("Google UMP (consent)", "consent", [r"usermessagingplatform", r"user-messaging-platform"]),
    ("Firebase Analytics", "analytics", [r"product:firebaseanalytics\b", r"pod:firebase/analytics", r"import:firebaseanalytics"]),
    ("Firebase Analytics IDFA support", "tracking", [r"firebaseanalyticsidentitysupport", r"googleappmeasurementidentitysupport"]),
    ("Firebase Crashlytics", "crash", [r"crashlytics"]),
    ("Firebase Remote Config", "remote-config", [r"firebaseremoteconfig", r"pod:firebase/remoteconfig"]),
    ("Firebase Cloud Messaging", "push", [r"firebasemessaging", r"pod:firebase/messaging"]),
    ("Firebase Auth", "auth", [r"firebaseauth", r"pod:firebase/auth"]),
    ("Firebase AI / Vertex AI", "ai", [r"firebaseai", r"firebasevertexai"]),
    ("OneSignal", "push", [r"onesignal"]),
    ("RevenueCat", "subscriptions", [r"revenuecat", r"purchases-ios", r"pod:purchases\b"]),
    ("Adapty", "subscriptions", [r"adapty"]),
    ("Qonversion", "subscriptions", [r"qonversion"]),
    ("Apphud", "subscriptions", [r"apphud"]),
    ("Superwall", "paywall", [r"superwall"]),
    ("AppsFlyer", "attribution", [r"appsflyer"]),
    ("Adjust", "attribution", [r"github\.com/adjust/", r"import:adjustsdk", r"pod:adjust\b", r"product:adjustsdk"]),
    ("Branch", "attribution", [r"branchmetrics", r"ios-branch", r"import:branchsdk", r"pod:branch\b"]),
    ("Singular", "attribution", [r"singular-ios", r"import:singular"]),
    ("Kochava", "attribution", [r"kochava"]),
    ("Meta (Facebook) SDK", "attribution", [r"facebook-ios-sdk", r"fbsdkcorekit", r"facebookcore", r"fbsdkloginkit", r"facebooklogin"]),
    ("TikTok Business SDK", "attribution", [r"tiktok-business", r"tiktokbusinesssdk"]),
    ("Mixpanel", "analytics", [r"mixpanel"]),
    ("Amplitude", "analytics", [r"amplitude"]),
    ("PostHog", "analytics", [r"posthog"]),
    ("Segment", "analytics", [r"segmentio", r"analytics-swift"]),
    ("TelemetryDeck", "analytics", [r"telemetrydeck"]),
    ("Sentry", "crash", [r"sentry"]),
    ("Bugsnag", "crash", [r"bugsnag"]),
    ("Datadog", "crash", [r"datadog"]),
    ("Braze", "engagement", [r"braze", r"appboy"]),
    ("Intercom", "support", [r"intercom"]),
    ("AppLovin", "ads", [r"applovin"]),
    ("ironSource / LevelPlay", "ads", [r"ironsource", r"levelplay"]),
    ("Unity Ads", "ads", [r"unityads", r"unity-ads"]),
    ("Vungle / Liftoff", "ads", [r"vungle", r"liftoff"]),
    ("Meta Audience Network", "ads", [r"audiencenetwork"]),
    ("Pangle", "ads", [r"pangle", r"bytedance"]),
    ("Chartboost", "ads", [r"chartboost"]),
    ("InMobi", "ads", [r"inmobi"]),
    ("Google Sign-In", "auth", [r"googlesignin"]),
    ("Supabase", "backend", [r"supabase"]),
    ("Stripe", "payments", [r"stripe"]),
    ("PayPal / Braintree", "payments", [r"paypal", r"braintree"]),
    ("LaunchDarkly", "flags", [r"launchdarkly"]),
    ("Statsig", "flags", [r"statsig"]),
    ("ConfigCat", "flags", [r"configcat"]),
    ("Optimizely", "flags", [r"optimizely"]),
    ("GrowthBook", "flags", [r"growthbook"]),
]

APPSTORE_ID_RE = re.compile(
    r"(?:apps|itunes)\.apple\.com/[^\s\"']*?id(\d{6,12})"
    r"|itms-apps://[^\s\"']*?id(\d{6,12})"
    r"|/id\\\((\d{6,12})\)"
    r"|\b(?:appStoreI[dD]|appleI[dD]|appI[dD]|kAppStoreID)\b\s*[:=]\s*\"?(\d{6,12})")
ALERT_RE = re.compile(r"UIAlertController\(|\.alert\(|\bAlert\(|confirmationDialog\(")
PERMISSION_RE = re.compile(r"requestAuthorization\(options:|requestTrackingAuthorization|requestWhenInUseAuthorization|requestAlwaysAuthorization|requestPushAuthorization|AVCaptureDevice\.requestAccess|requestAccess\(for")
IMPORT_RE = re.compile(r"(?:#import\s+[<\"]|@import\s+|import\s+(?:class\s+|struct\s+|enum\s+|protocol\s+|func\s+|typealias\s+)?)([A-Za-z_][A-Za-z0-9_]*)")
URL_RE = re.compile(r"https?://[A-Za-z0-9.\-]+(?::\d+)?(?:/[^\s\"'<>()\\]*)?")


def debug_mask(lines):
    """True for lines compiled only in DEBUG builds (inside #if DEBUG, or #else of #if !DEBUG)."""
    stack, mask = [], []
    for line in lines:
        s = line.strip()
        if s.startswith("#if "):
            cond = s[4:]
            negative = bool(re.search(r"!\s*\(?\s*DEBUG", cond))
            positive = "DEBUG" in cond and not negative
            stack.append([positive, negative, False])
            mask.append(False)
            continue
        if s.startswith("#elseif") or s.startswith("#else"):
            if stack:
                stack[-1][2] = True
            mask.append(False)
            continue
        if s.startswith("#endif"):
            if stack:
                stack.pop()
            mask.append(False)
            continue
        mask.append(any((p and not e) or (neg and e) for p, neg, e in stack))
    return mask


def scan_sources(root, max_hits):
    hits = defaultdict(list)
    counts = defaultdict(int)
    imports = defaultdict(int)
    appstore_ids = defaultdict(list)
    urls = defaultdict(list)
    debug_env_outside = []
    files = 0
    compiled = {name: re.compile(rx) for name, (rx, _) in SIGNALS.items()}
    for path in walk(root, exts=SOURCE_EXT):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        files += 1
        mask = debug_mask(lines)
        relpath = rel(path, root)
        joined = "\n".join(lines)
        if ALERT_RE.search(joined) and PERMISSION_RE.search(joined):
            m_alert = ALERT_RE.search(joined)
            line_no = joined[:m_alert.start()].count("\n") + 1
            counts["permission_pre_dialog"] += 1
            if len(hits["permission_pre_dialog"]) < max_hits:
                hits["permission_pre_dialog"].append(f"{relpath}:{line_no}: alert and permission request in the same file")
        in_block_comment = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("/*") and "*/" not in stripped:
                in_block_comment = True
                continue
            if stripped.startswith("//"):
                continue
            m = IMPORT_RE.match(stripped)
            if m:
                imports[m.group(1)] += 1
            for name, rx in compiled.items():
                if rx.search(line):
                    counts[name] += 1
                    if len(hits[name]) < max_hits:
                        hits[name].append(f"{relpath}:{idx + 1}: {stripped[:140]}")
                    if name == "process_environment" and not mask[idx]:
                        debug_env_outside.append(f"{relpath}:{idx + 1}: {stripped[:140]}")
            for m in APPSTORE_ID_RE.finditer(line):
                found = next(g for g in m.groups() if g)
                appstore_ids[found].append(f"{relpath}:{idx + 1}")
            for m in URL_RE.finditer(line):
                url = m.group(0).rstrip(".,;")
                if line[m.end():m.end() + 2] == "\\(":
                    url += "\\(…)"  # Swift interpolation follows: a template, not a fetchable URL
                if len(urls[url]) < 3:
                    urls[url].append(f"{relpath}:{idx + 1}")
    return {
        "files": files,
        "signals": {k: {"count": counts[k], "samples": hits[k]} for k in SIGNALS if counts[k]},
        "imports": dict(sorted(imports.items())),
        "appStoreIds": {k: v[:5] for k, v in appstore_ids.items()},
        "urls": {k: v for k, v in sorted(urls.items())},
        "processEnvironmentOutsideDebug": debug_env_outside[:max_hits * 3],
    }


# ---------------------------------------------------------------- other files

def read_lockfiles(root):
    pins, pods = [], []
    for path in walk(root, names={"Package.resolved"}):
        data = load_plist_json(path)
        if not data:
            continue
        entries = data.get("pins") or data.get("object", {}).get("pins", [])
        for p in entries:
            state = p.get("state", {})
            pins.append({
                "identity": p.get("identity") or p.get("package"),
                "location": p.get("location") or p.get("repositoryURL"),
                "version": state.get("version") or (state.get("revision") or "")[:10],
                "file": rel(path, root),
            })
    for path in walk(root, names={"Podfile.lock"}):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        section = text.split("DEPENDENCIES:")[0]
        for m in re.finditer(r"^  - ([A-Za-z0-9_\-+/.]+) \(([^)]+)\)", section, re.M):
            pods.append({"name": m.group(1), "version": m.group(2), "file": rel(path, root)})
    # de-duplicate pins (example projects often repeat them)
    seen, unique = set(), []
    for p in pins:
        key = (p["identity"], p["version"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique, pods


def load_plist_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def read_privacy_manifests(root):
    out = []
    for path in walk(root, names={"PrivacyInfo.xcprivacy"}):
        data = load_plist(path)
        if not isinstance(data, dict):
            continue
        out.append({
            "file": rel(path, root),
            "tracking": data.get("NSPrivacyTracking"),
            "trackingDomains": data.get("NSPrivacyTrackingDomains", []),
            "collectedDataTypes": [d.get("NSPrivacyCollectedDataType") for d in data.get("NSPrivacyCollectedDataTypes", [])],
            "accessedAPIs": {a.get("NSPrivacyAccessedAPIType"): a.get("NSPrivacyAccessedAPITypeReasons", [])
                             for a in data.get("NSPrivacyAccessedAPITypes", [])},
        })
    return out


def read_entitlements(root):
    out = {}
    for path in walk(root, exts={".entitlements"}):
        data = load_plist(path)
        out[rel(path, root)] = {k: v for k, v in data.items()} if isinstance(data, dict) else data
    return out


def read_infoplist_strings(root):
    localized = defaultdict(set)
    for path in walk(root, names={"InfoPlist.strings"}):
        lang = os.path.basename(os.path.dirname(path)).replace(".lproj", "")
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
            text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
        except OSError:
            continue
        for m in re.finditer(r'^\s*"?([A-Za-z0-9_~]+)"?\s*=', text, re.M):
            localized[m.group(1)].add(lang)
    for path in walk(root, names={"InfoPlist.xcstrings"}):
        data = load_plist_json(path) or {}
        for key, val in data.get("strings", {}).items():
            for lang in val.get("localizations", {}):
                localized[key].add(lang)
    return {k: sorted(v) for k, v in sorted(localized.items())}


def version_changes(root):
    """Uncommitted edits to MARKETING_VERSION / CURRENT_PROJECT_VERSION in project files."""
    diff = git(root, "diff", "-U0", "HEAD", "--", "*.pbxproj")
    if not diff:
        return []
    changes, current = [], None
    removed, added = defaultdict(list), defaultdict(list)
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        m = re.match(r"^([+-])\s*(MARKETING_VERSION|CURRENT_PROJECT_VERSION) = ([^;]+);", line)
        if m and current:
            (added if m.group(1) == "+" else removed)[(current, m.group(2))].append(m.group(3).strip('"'))
    for key in sorted(set(removed) | set(added)):
        old = sorted(set(removed.get(key, [])))
        new = sorted(set(added.get(key, [])))
        if old != new:
            changes.append({"file": key[0], "setting": key[1], "committed": old, "workingTree": new})
    return changes


def git_state(root):
    status = git(root, "status", "--porcelain")
    return {
        "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": git(root, "log", "-1", "--format=%h %ad %s", "--date=short"),
        "uncommitted": status.splitlines() if status else [],
    }


# ---------------------------------------------------------------- analysis

def detect_sdks(projects, pins, pods, imports, plist_keys):
    corpus = []
    for p in pins:
        corpus.append(f"pin:{p['identity']} {p['location']}".lower())
    for proj in projects:
        for pkg in proj.get("packages", []):
            corpus.append(f"pin:{pkg.get('url') or pkg.get('path')}".lower())
        for t in proj.get("targets", []):
            corpus.extend(f"product:{p}".lower() for p in t.get("packageProducts", []))
    corpus.extend(f"pod:{p['name']}".lower() for p in pods)
    corpus.extend(f"import:{name}".lower() for name in imports)
    corpus.extend(f"plist:{k}".lower() for k in plist_keys)
    found = []
    for name, category, patterns in SDKS:
        evidence = [c for c in corpus if any(re.search(rx, c) for rx in patterns)]
        if evidence:
            found.append({"name": name, "category": category, "evidence": sorted(set(evidence))[:4]})
    return found


def analyze(projects, scan, manifests, sdks, root):
    findings = []
    signals = scan["signals"]
    push_sdk = any(s["category"] == "push" for s in sdks)
    for proj in projects:
        for t in proj.get("targets", []):
            if t.get("productType") != APP_PRODUCT:
                continue
            conflicts = []
            cfg_name, source, info, generated = merged_info_plist(t, proj["projectDir"], conflicts)
            for key, file_val, setting_val in conflicts:
                findings.append(f"[upload] {t['name']}: {key} is set in both the Info.plist file ({json.dumps(file_val)[:80]}) and INFOPLIST_KEY_{key.replace('~ipad', '_iPad')} ({json.dumps(setting_val)[:80]}); the file's value is the one that ships")
            t["release"] = cfg_name
            t["infoPlistFile"] = rel(source, root) if source else None
            t["infoPlist"] = info
            t["generatedKeys"] = generated
            settings = t["configurations"].get(cfg_name, {})
            family = list_value(settings.get("TARGETED_DEVICE_FAMILY", "1"))
            if "2" in family and str(info.get("UIRequiresFullScreen", "NO")).upper() not in ("YES", "TRUE", "1"):
                ipad = list_value(info.get("UISupportedInterfaceOrientations~ipad") or info.get("UISupportedInterfaceOrientations"))
                need = ["UIInterfaceOrientationPortrait", "UIInterfaceOrientationPortraitUpsideDown",
                        "UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"]
                missing = [o for o in need if o not in ipad]
                if missing:
                    findings.append(f"[upload] {t['name']}: iPad multitasking needs all four orientations; missing {', '.join(missing)} (ITMS-90474) unless UIRequiresFullScreen is set")
            for name, (_, keys) in SIGNALS.items():
                if name.startswith("rr_") or not keys or name not in signals:
                    continue
                for key_alt in keys:
                    options = key_alt.split("|")
                    present = [k for k in options if str(info.get(k, "")).strip()]
                    if not present:
                        findings.append(f"[purpose string] {t['name']}: '{name}' API used ({signals[name]['samples'][0]}) but none of {options} is set")
            modes = list_value(info.get("UIBackgroundModes"))
            for mode in modes:
                needed = BG_MODE_SIGNALS.get(mode)
                if mode == "remote-notification" and push_sdk:
                    continue
                if needed and not any(n in signals for n in needed):
                    findings.append(f"[2.5.4] {t['name']}: UIBackgroundModes has '{mode}' but no matching API use was found")
            if str(info.get("ITSAppUsesNonExemptEncryption", "")).strip() == "":
                findings.append(f"[export] {t['name']}: ITSAppUsesNonExemptEncryption not set; App Store Connect will ask the export compliance question")
            for key, value in info.items():
                if key.startswith("NS") and key.endswith("UsageDescription"):
                    text = str(value).strip()
                    if not text or len(text) < 12:
                        findings.append(f"[5.1.1(ii)] {t['name']}: {key} is empty or too short to explain the use: '{text}'")
            if "NSUserNotificationsUsageDescription" in info:
                findings.append(f"[info] {t['name']}: NSUserNotificationsUsageDescription is not a documented iOS key; the notification prompt shows no custom text (harmless)")
    # extension versions must match the app
    for proj in projects:
        apps = [t for t in proj.get("targets", []) if t.get("productType") == APP_PRODUCT]
        if not apps:
            continue
        app = apps[0]
        _, app_settings = release_settings(app)
        for t in proj.get("targets", []):
            if t is app or "app-extension" not in str(t.get("productType")):
                continue
            _, s = release_settings(t)
            for key in ("MARKETING_VERSION", "CURRENT_PROJECT_VERSION"):
                if s.get(key) and app_settings.get(key) and s.get(key) != app_settings.get(key):
                    findings.append(f"[upload] {t['name']}: {key} {s.get(key)} differs from the app's {app_settings.get(key)} (extensions must match)")
    declared = set()
    for m in manifests:
        declared.update(m["accessedAPIs"].keys())
    for name, (_, keys) in SIGNALS.items():
        if name.startswith("rr_") and name in signals and keys[0] not in declared:
            findings.append(f"[privacy manifest] {keys[0]} not declared in any PrivacyInfo.xcprivacy, but used: {signals[name]['samples'][0]}")
    if scan["processEnvironmentOutsideDebug"]:
        findings.append(f"[2.5.19] {len(scan['processEnvironmentOutsideDebug'])} environment/launch-argument reads compile into Release (not inside #if DEBUG); check none unlocks features: {scan['processEnvironmentOutsideDebug'][0]}")
    if "uiwebview" in signals:
        findings.append(f"[upload] UIWebView referenced in source (ITMS-90809 if it reaches the binary): {signals['uiwebview']['samples'][0]}")
    if "tracking_request" in signals or "idfa_read" in signals:
        for proj in projects:
            for t in proj.get("targets", []):
                if t.get("productType") == APP_PRODUCT and not str(t.get("infoPlist", {}).get("NSUserTrackingUsageDescription", "")).strip():
                    findings.append(f"[5.1.2(i)] {t['name']}: ATT/IDFA used but NSUserTrackingUsageDescription missing")
    return findings


# ---------------------------------------------------------------- report

def to_markdown(inv):
    out = []
    g = inv["git"]
    out.append(f"# Inventory: {inv['root']}")
    out.append(f"git: {g.get('branch')} @ {g.get('head')}; uncommitted files: {len(g.get('uncommitted', []))}")
    for line in g.get("uncommitted", [])[:12]:
        out.append(f"  {line}")
    out.append("")
    out.append("## Targets")
    for proj in inv["projects"]:
        if proj.get("error"):
            out.append(f"- {proj['path']}: {proj['error']}")
            continue
        out.append(f"- project {proj['path']}")
        for t in proj["targets"]:
            cfg_name, s = release_settings(t)
            out.append(
                f"  - {t['name']} ({str(t['productType']).split('.')[-1]}) [{cfg_name}] "
                f"id={s.get('PRODUCT_BUNDLE_IDENTIFIER')} version={s.get('MARKETING_VERSION')} build={s.get('CURRENT_PROJECT_VERSION')} "
                f"family={s.get('TARGETED_DEVICE_FAMILY', '1')} min={s.get('IPHONEOS_DEPLOYMENT_TARGET')} "
                f"platforms={s.get('SUPPORTED_PLATFORMS', s.get('SDKROOT'))} entitlements={s.get('CODE_SIGN_ENTITLEMENTS')}")
            if t.get("xcconfigs"):
                out.append(f"    xcconfig (not merged): {', '.join(t['xcconfigs'])}")
            if t.get("packageProducts"):
                out.append(f"    package products: {', '.join(t['packageProducts'])}")
            info = t.get("infoPlist")
            if info:
                usage = {k: str(v)[:90] for k, v in info.items() if k.endswith("UsageDescription")}
                out.append(f"    Info.plist: {t.get('infoPlistFile')} + {len(t.get('generatedKeys', []))} INFOPLIST_KEY_* settings")
                for k, v in sorted(usage.items()):
                    langs = inv["infoPlistLocalizations"].get(k, [])
                    out.append(f"      {k}: \"{v}\"  (localized: {', '.join(langs) if langs else 'none'})")
                for k in ("UIBackgroundModes", "UISupportedInterfaceOrientations", "UISupportedInterfaceOrientations~ipad",
                          "UIRequiresFullScreen", "ITSAppUsesNonExemptEncryption", "GADApplicationIdentifier",
                          "NSAppTransportSecurity", "LSApplicationQueriesSchemes", "CFBundleURLTypes"):
                    if k in info:
                        val = info[k]
                        if k == "CFBundleURLTypes":
                            val = [s for t2 in val for s in t2.get("CFBundleURLSchemes", [])] if isinstance(val, list) else val
                        out.append(f"      {k}: {json.dumps(val)[:160]}")
                if "SKAdNetworkItems" in info:
                    out.append(f"      SKAdNetworkItems: {len(info['SKAdNetworkItems'])} entries")
    out.append("")
    out.append("## Entitlements")
    for path, ent in inv["entitlements"].items():
        out.append(f"- {path}: {json.dumps(ent, default=str)[:300]}")
    out.append("")
    out.append("## Privacy manifests")
    for m in inv["privacyManifests"]:
        apis = "; ".join(f"{k.replace('NSPrivacyAccessedAPICategory', '')}={','.join(v)}" for k, v in m["accessedAPIs"].items())
        out.append(f"- {m['file']}: tracking={m['tracking']} domains={len(m['trackingDomains'])} collected={len(m['collectedDataTypes'])} apis: {apis or 'none'}")
    out.append("")
    out.append("## Dependencies")
    for p in inv["packagePins"]:
        out.append(f"- {p['identity']} {p['version']}  ({p['location']})")
    for p in inv["pods"]:
        out.append(f"- pod {p['name']} {p['version']}")
    out.append("")
    out.append("## SDKs detected (verify each; presence is not proof of use)")
    for s in inv["sdks"]:
        out.append(f"- {s['name']} [{s['category']}]: {', '.join(s['evidence'])}")
    out.append("")
    out.append(f"## Source signals ({inv['sources']['files']} files)")
    for name, data in inv["sources"]["signals"].items():
        out.append(f"- {name}: {data['count']}")
        out.extend(f"    {sample}" for sample in data["samples"])
    out.append("")
    ids = inv["sources"]["appStoreIds"]
    out.append("## Hardcoded App Store IDs (check with: fetch_apple.py lookup <id>)")
    out.extend(f"- {k}: {', '.join(v)}" for k, v in ids.items()) if ids else out.append("- none found")
    out.append("")
    out.append("## Hosts referenced in code (check_links.py for status)")
    hosts = defaultdict(int)
    for url in inv["sources"]["urls"]:
        hosts[re.sub(r"^https?://", "", url).split("/")[0]] += 1
    out.append(", ".join(f"{h} ({n})" for h, n in sorted(hosts.items(), key=lambda x: -x[1])[:40]) or "none")
    out.append("")
    out.append("## Mechanical flags (signals to confirm, not verdicts)")
    out.extend(f"- {f}" for f in inv["flags"]) if inv["flags"] else out.append("- none")
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inventory an iOS repository for an App Store review preflight")
    parser.add_argument("root")
    parser.add_argument("--json")
    parser.add_argument("--md")
    parser.add_argument("--max-hits", type=int, default=3)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    projects = read_projects(root)
    pins, pods = read_lockfiles(root)
    scan = scan_sources(root, args.max_hits)
    manifests = read_privacy_manifests(root)
    strings_loc = read_infoplist_strings(root)
    plist_keys = set()
    for proj in projects:
        for t in proj.get("targets", []):
            if t.get("productType") == APP_PRODUCT and "configurations" in t:
                plist_keys.update(merged_info_plist(t, proj["projectDir"])[2].keys())
    sdks = detect_sdks(projects, pins, pods, scan["imports"], plist_keys)
    flags = analyze(projects, scan, manifests, sdks, root)
    for ch in version_changes(root):
        flags.append(f"[upload] uncommitted change in {ch['file']}: {ch['setting']} {','.join(ch['committed']) or '-'} -> {','.join(ch['workingTree']) or '-'} "
                     "(the next archive uses the working tree; compare with the builds already in App Store Connect)")
    if any(s["name"] == "Google UMP (consent)" for s in sdks) and "ump_usage" not in scan["signals"]:
        flags.append("[compliance] Google UMP is linked but never called: no consent message for EEA/UK users (Google policy, GDPR; not an App Review rule)")
    if "permission_pre_dialog" in scan["signals"]:
        flags.append(f"[5.1.1(iv)] custom pre-permission UI found; check it does not mimic a system alert or skip the system dialog: {scan['signals']['permission_pre_dialog']['samples'][0]}")
    inv = {
        "root": root,
        "git": git_state(root),
        "projects": projects,
        "packagePins": pins,
        "pods": pods,
        "entitlements": read_entitlements(root),
        "privacyManifests": manifests,
        "infoPlistLocalizations": strings_loc,
        "sources": scan,
        "sdks": sdks,
        "flags": flags,
    }
    for proj in projects:
        proj.pop("projectDir", None)
    md = to_markdown(inv)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(inv, fh, indent=1, default=str)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"inventory: {args.md}" + (f" and {args.json}" if args.json else ""))
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
