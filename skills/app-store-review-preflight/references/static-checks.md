# Static checks: what the repository can prove

Checks decided from source, build settings, plists, entitlements and lockfiles.
`inventory.py` collects the signals. This file says how to judge them. Guideline numbers
were checked against the live text on 2026-11-05; re-check them against this run's fetch
before citing.

Contents:

1. [Permission purpose strings](#1-permission-purpose-strings)
2. [Privacy manifest](#2-privacy-manifest)
3. [Entitlements](#3-entitlements)
4. [Login services (4.8)](#4-login-services-48)
5. [Export compliance](#5-export-compliance)
6. [Account creation and deletion (5.1.1(v))](#6-account-creation-and-deletion-511v)
7. [Web wrappers (4.2)](#7-web-wrappers-42)
8. [Dynamic code, private and deprecated APIs (2.5.1, 2.5.2)](#8-dynamic-code-private-and-deprecated-apis-251-252)
9. [Hidden, dormant and undocumented features (2.5.19)](#9-hidden-dormant-and-undocumented-features-2519)
10. [Hardcoded App Store IDs and links](#10-hardcoded-app-store-ids-and-links)
11. [Server-driven behavior inventory](#11-server-driven-behavior-inventory)

## 1. Permission purpose strings

- **Validation:** a referenced permission-gated API without its purpose string fails upload
  validation (ITMS-90683). That includes APIs referenced only by a linked SDK.
- **Text quality:** a present but empty or boilerplate string passes validation and is
  still a 5.1.1(ii) review risk. The live text says: "Ensure your purpose strings clearly
  and completely describe your use of the data".
- **Localization:** check that the purpose strings are localized for every language the app
  ships in, so the reviewer reads one in the app's language.

| Info.plist key | Triggered by |
|---|---|
| `NSCameraUsageDescription` | `AVCaptureDevice`, `AVCaptureSession`, `UIImagePickerController` with the camera source |
| `NSMicrophoneUsageDescription` | recording: `AVAudioRecorder`, record or playAndRecord session categories, audio taps for speech |
| `NSPhotoLibraryUsageDescription` | direct PhotoKit reads: `PHAsset.fetch…`, `PHImageManager`, `requestAuthorization(for: .readWrite)` |
| `NSPhotoLibraryAddUsageDescription` | write-only: `requestAuthorization(for: .addOnly)`, `PHAssetCreationRequest`, `UIImageWriteToSavedPhotosAlbum` |
| `NSLocationWhenInUseUsageDescription` (+ `NSLocationAlwaysAndWhenInUseUsageDescription` for always) | `CLLocationManager` authorization requests |
| `NSContactsUsageDescription` | `CNContactStore` |
| `NSCalendarsFullAccessUsageDescription`, `NSCalendarsWriteOnlyAccessUsageDescription`, `NSRemindersFullAccessUsageDescription` | EventKit |
| `NSHealthShareUsageDescription`, `NSHealthUpdateUsageDescription` | HealthKit |
| `NSBluetoothAlwaysUsageDescription` | CoreBluetooth managers |
| `NSFaceIDUsageDescription` | LocalAuthentication with Face ID |
| `NSSpeechRecognitionUsageDescription` | `SFSpeechRecognizer` |
| `NSMotionUsageDescription` | `CMMotionActivityManager`, `CMPedometer` (plain `CMMotionManager` device motion needs no permission) |
| `NSLocalNetworkUsageDescription` (+ `NSBonjourServices`) | local network discovery and connections |
| `NFCReaderUsageDescription` | Core NFC sessions |
| `NSAppleMusicUsageDescription` | media library access |
| `NSUserTrackingUsageDescription` | `ATTrackingManager.requestTrackingAuthorization`, and IDFA reads through SDKs configured to use it |

**No permission needed (do not flag a missing key):**

- `PHPickerViewController` and SwiftUI `PhotosPicker`, which run out of process.
- `UIImagePickerController` with the photo-library source.

5.1.1(iii) prefers the out-of-process picker over full library access. Flag full-library
reads where a picker would do.

## 2. Privacy manifest

Since May 1, 2024, uploads need approved reasons for "required reason" APIs. The
categories are:

- `NSPrivacyAccessedAPICategoryUserDefaults`
- `NSPrivacyAccessedAPICategoryFileTimestamp`
- `NSPrivacyAccessedAPICategorySystemBootTime`
- `NSPrivacyAccessedAPICategoryDiskSpace`
- `NSPrivacyAccessedAPICategoryActiveKeyboards`

**Who declares what.** A privacy manifest describes the code in its own bundle:

- The app's `PrivacyInfo.xcprivacy` covers the app's code, plus any package or vendored
  code compiled into the app target that does not ship its own manifest.
- An SDK that ships a manifest covers itself.
- So check the app manifest against the API use found in app code and in manifest-less
  source packages. `inventory.py` scans both, minus tests and example apps.

**Reason codes.** Never validate codes from memory. Fetch the current list:

```bash
python3 -I <skill>/scripts/fetch_apple.py doc bundleresources/app-privacy-configuration/nsprivacyaccessedapitypes/nsprivacyaccessedapitypereasons
```

As of 2026-11-05, the UserDefaults codes are:

| Code | Meaning | Who may declare it |
|---|---|---|
| `CA92.1` | Data only the app itself reads and writes | The usual app reason |
| `1C8F.1` | Data shared within the same App Group (app, extensions, App Clips) | The app |
| `C56D.1` | A third-party SDK wraps UserDefaults for the app | "may only be declared by third-party SDKs". Never suggest it for app code |
| `AC6B.1` | Managed app configuration from MDM | The app |

For system boot time, `35F9.1` covers measuring elapsed time between in-app events.

**Tracking keys:**

- `NSPrivacyTracking` true with an empty `NSPrivacyTrackingDomains` is inconsistent.
- A tracking SDK being present does **not** make the app manifest's
  `NSPrivacyTracking: false` wrong when that SDK ships its own manifest declaring tracking.
  The app's file speaks for the app's own code.
- Flag the app manifest only when the app's own code tracks, or when a tracking SDK has no
  manifest of its own.

**No manifest at all** is a gap only when the app's own code uses required-reason APIs.

## 3. Entitlements

Read `*.entitlements`, or the signed entitlements of a built product
(`codesign -d --entitlements :- App.app`).

- **Push:** push registration code without `aps-environment` gets a warning at upload. An
  `aps-environment` with no push code is cleanup, low severity. A `development` value in
  the file is normal (see upload-validation.md).
- **Unused capabilities:** capabilities the code never uses (App Groups, iCloud, Sign in
  with Apple, Siri, App Attest, HealthKit) are cleanup items. A HealthKit entitlement
  invites 5.1.3 questions, so remove it if unused.
- **Signing-generated keys:** ignore keys code signing adds, such as
  `application-identifier`, `team-identifier`, `get-task-allow` and `beta-reports-active`.
- **Multi-platform projects:** attribute shared entitlements to the right target before
  judging them.

## 4. Login services (4.8)

**When it applies:** the app uses a third-party or social login (Google, Facebook, X,
LinkedIn, Amazon, WeChat and similar) for the user's **primary** account.

**What it requires:** the app must also offer a login service that:

- limits data collection to name and email
- lets users keep their email private
- does not collect interactions for advertising without consent

Sign in with Apple qualifies, but it is not the only option. Word findings as "needs a
privacy-protecting login option".

**Signal:** a social-login SDK plus login UI, with no `ASAuthorizationAppleIDProvider` and
no other qualifying service. Before flagging, check the exemptions in the live 4.8 text:

- apps that use only their own account system
- education and enterprise apps
- government or industry-backed ID
- clients for a specific third-party service

## 5. Export compliance

`ITSAppUsesNonExemptEncryption`:

- **Missing:** App Store Connect asks the export questions for each build. That is a
  submission step, low severity.
- **Framework names prove nothing.** HTTPS/TLS, CryptoKit and CommonCrypto are
  OS-provided and generally exempt.
- **What matters:** proprietary or bundled cryptography, such as a custom algorithm or
  bundled OpenSSL. That is what the questionnaire is about.
- **Do not prescribe the value.** Point the user to the questionnaire and to the difference
  between OS-provided and proprietary cryptography.

## 6. Account creation and deletion (5.1.1(v))

**Live text:** "If your app supports account creation, you must also offer account deletion
within the app."

**What counts:**

- Deactivation alone is not enough.
- Support-email routes are acceptable only in highly regulated industries.
- Details: https://developer.apple.com/support/offering-account-deletion-in-your-app/

**Signals:** an auth SDK or signup flow (Firebase Auth, Supabase, Cognito, custom register
endpoints) with no deletion path (UI plus a backend call that removes the account and its
data).

5.1.1(v) also says apps that lack significant account-based features should let people use
them without a login.

**Apps without accounts:** "delete my data" for local data is good practice, but the
deletion rule does not apply. Report it as a clean area.

## 7. Web wrappers (4.2)

Live 4.2: "Your app should include features, content, and UI that elevate it beyond a
repackaged website."

**Fingerprint:**

- one `WKWebView` filling the root view
- content loaded from one remote URL
- no native navigation
- no offline handling
- no meaningful native framework use

Report which native capabilities exist and which are missing. Whether the native layer is
enough is decided in the semantic pass.

## 8. Dynamic code, private and deprecated APIs (2.5.1, 2.5.2)

- **2.5.2:** apps may not download or execute code that changes their features after
  review. Ordinary web content in a web view is fine. Embedded mini apps, mini games and
  chatbot plug-ins fall under 4.7 and its conditions.
- **Signals:** `dlopen`/`dlsym` on downloaded or bundled paths, `NSClassFromString` or
  `NSSelectorFromString` with runtime-built names, `performSelector`, JavaScript bridges
  (`evaluateScript`) that change app behavior.
- **Benign uses:** a test harness check such as `NSClassFromString("XCTestCase")`, or SDK
  feature detection.
- **UIWebView:** see upload-validation.md (ITMS-90809).
- **Private API (2.5.1):** needs the binary to scan reliably. From source, flag only clear
  cases.

## 9. Hidden, dormant and undocumented features (2.5.19)

**Live text (added October 16, 2026; confirm in this run's fetch):** "Don't include any
hidden, dormant, or undocumented features in your app; your app's functionality should be
clear to end users and App Review. Attempting to hide undocumented features in your app
binary, such as through code obfuscation or other methods, is grounds for removal of your
app from the App Store and termination of your developer account."

**Where to cite what:**

- Cite 2.5.19 for hidden features.
- Cite 2.3.1(a) for missing review-notes disclosure: new features must be "described with
  specificity in the Notes for Review section … and accessible for review".

**How to read it:**

- The text names neither remote configuration nor A/B testing.
- Remote changes to *data* in code that shipped (copy, prices, ordering) read as outside
  the rule.
- A screen, tab or capability that exists only after a server switch reads as inside it.
- That reading is an inference. Label findings that rest on it.

**Signals, each with evidence:**

- **Reviewer or sandbox detection** (review-risk, account-level exposure):
  - What to look for: names like `isReview`, `reviewMode`, `appReview`; Apple IP ranges
    (17.0.0.0/8) or Cupertino geofences; date gates that open after a review window.
  - The real signal is StoreKit environment checks (`sandboxReceipt`,
    `AppTransaction.environment`) whose result changes views or features. Using the
    environment for receipt validation or server choice is legitimate.
  - Together with obfuscated feature code, report this at the top regardless of how often
    it happens.
- **Debug hooks that ship:**
  - Shake handlers, secret gestures and debug menus outside `#if DEBUG`.
  - Environment-variable or launch-argument reads outside `#if DEBUG`: `inventory.py` lists
    them under `processEnvironmentOutsideDebug`.
  - Check each one. A test-run detector (for example `XCTestConfigurationFilePath`) is
    benign. A hook that grants premium or unlocks features in Release is a finding.
- **Dark-shipped features:** a remote flag (or a local default that is off) that gates a
  whole screen, tab or capability, with nothing in the review notes about how to reach it.
  Read the default values (`setDefaults`, bundled defaults, `@AppStorage` defaults).
- **Obfuscated feature code:** selectors and class names built from decoded strings,
  base64/XOR blobs turned into symbols, obfuscator build phases. Encrypting an API key is
  not feature hiding; the finding needs a feature behind the obfuscation.
- **Server-side review targeting:**
  - What to look for: backend fields or columns that mark Apple, reviewers or test devices
    (`is_apple`, `isReviewer`, test-device lists), Apple IP ranges, region or date
    switches.
  - App side: a flag decoded into a response model and never read is a cleanup note.
    Remove it, because its name invites the wrong reading.
  - Server side: a flag that changes features, prices or paywalls for reviewers is
    reviewer detection.
- **Post-review payment swaps** (review-risk, also cite 3.1.1):
  - A remote toggle that replaces IAP with web checkout.
  - A hard paywall, or a removal of free uses, that can be switched on after review. See
    payments-and-subscriptions.md.

## 10. Hardcoded App Store IDs and links

Rate, share and "more apps" links often carry an App Store ID copied from a template or
another app.

- **IDs:** `inventory.py` lists every ID it finds. `check_links.py --inventory` looks each
  one up and compares its bundle ID with the app's.
- **Severity:** a rate or share link that opens a different app is a 2.1(a) problem (the
  reviewer taps these rows) and a real bug for users. Report it as review-risk with the
  correct ID as the fix. The ID is in App Store Connect > App Information > Apple ID.
- **Other links:** check that privacy policy, terms, support and marketing links in the app
  answer. 2.1(a) asks for "fully functional URLs".

## 11. Server-driven behavior inventory

Build a short table of everything the server or a remote config decides:

- the key or flag
- its local default
- what it gates (screen, paywall design, access mode, ad unit, endpoint)
- whether the review notes mention it

Sources: Firebase Remote Config keys and `setDefaults`, flag SDKs, paywall SDK placements
and experiments, onboarding variant tests, ad unit IDs fetched at run time.

- **No review notes supplied:** report the table as a review-notes to-do (judgment-call),
  not as a finding.
- **Where it feeds:** the table drives the 2.5.19 and 2.3.1(a) judgment and the "Not
  checked" section. The audit cannot see what the server serves on the day of review.
