# Upload and build blockers

Upload validation runs on the built product when it reaches App Store Connect. A failure
there costs a new build, and often a new build number, before review even starts. These
checks come from the repository and from App Store Connect's build list.

**Confidence:** report a finding as validator-certain only with evidence from what ships:

- an archive, `.app` or `.ipa`
- target-resolved build settings
- an `INVALID` build in App Store Connect

From source alone, use `review-risk (validator-blocking if shipped as-is; needs build
verification)`.

**ITMS codes:** the codes below are the ones Apple prints in upload errors for these
problems. Report the problem by name; the code is for orientation.

## Getting evidence from what ships

- **Resolved build settings:**
  `xcodebuild -showBuildSettings -project <X.xcodeproj> -target <App> -configuration Release`
  (or `-workspace … -scheme …`). This resolves `.xcconfig` files and inheritance, which
  `inventory.py` does not.
  - It is not strictly read-only. It can resolve Swift packages over the network and write
    to DerivedData or `.swiftpm` folders. Ask the user before running it.
  - When the target has no `.xcconfig` (the inventory lists them) and the setting is a
    literal with no `$(…)`, the `project.pbxproj` value from `inventory.py` is already the
    resolved value. It counts as validator-certain evidence without running Xcode.
- **Built product:** `plutil -p <App>.app/Info.plist` for the merged Info.plist, and
  `codesign -d --entitlements :- <App>.app` for the entitlements as signed.
- **Without uploading:** Xcode Organizer's "Validate App" runs the server-side validation.
- **App Store Connect builds list:** a build in `INVALID` state, or an upload error, is the
  validator's verdict.

## Version and build number

- **Duplicate build number.** A build number (`CFBundleVersion`) already uploaded for a
  version cannot be uploaded again for that version.
  - Compare the release `CURRENT_PROJECT_VERSION` in the working tree with App Store
    Connect's build list, not with git history.
  - Uncommitted project changes count: Xcode's target editor can silently rewrite the build
    number.
  - Report the number the next upload needs.
- **Version must increase (ITMS-90062).** The version (`CFBundleShortVersionString`) must
  be higher than the last approved version.
- **Extensions must match the app.** App extensions (widgets, notification service
  extensions) must carry the same version and build number as the app. Upload reports a
  mismatch otherwise.
- **Which build ships:**
  - Find the build attached to the version in App Store Connect. If none is attached, the
    submission cannot go ahead.
  - Compare its upload time with the commits.
    - App Store Connect dates carry a UTC offset, for example `2026-11-05T03:46:09-08:00`.
    - Run `git log --since=<that time> --format='%h %cI %s'`.
    - Every fix committed after the upload, or still uncommitted, is missing from that
      build and needs the next one.
  - `inventory.py` flags uncommitted edits to `CURRENT_PROJECT_VERSION` and
    `MARKETING_VERSION` in project files. Xcode's target editor makes these silently.

## SDK and deployment target minimums

Verified on 2026-11-05 from https://developer.apple.com/news/upcoming-requirements/:

- Since April 28, 2026, uploads must be built with Xcode 26 or later, using the iOS 26 /
  iPadOS 26 SDK.
- Since September 9, 2026, iOS and iPadOS apps must target iOS 13 or later.

Re-read that page each run; the minimums move every year.

## Info.plist

- **Missing purpose string (ITMS-90683).**
  - Triggers: a permission-gated API is referenced, including from a linked SDK, and the
    matching `NS…UsageDescription` key is missing or empty.
  - Where keys live: in the Info.plist file or in `INFOPLIST_KEY_*` build settings when
    `GENERATE_INFOPLIST_FILE = YES`.
  - Localized `InfoPlist.strings` override the text but do not replace the base key.
- **iPad multitasking orientations (ITMS-90474).**
  - Applies when `TARGETED_DEVICE_FAMILY` includes 2 (iPad) and `UIRequiresFullScreen` is
    not YES.
  - The iPad orientation list (`UISupportedInterfaceOrientations~ipad`, or the generic key)
    must contain Portrait, PortraitUpsideDown, LandscapeLeft and LandscapeRight.
  - Trap: when a key is set both in the Info.plist file and as `INFOPLIST_KEY_…`, the
    file's value is the one that ships (observed in practice). A stale file value can
    undo a change made in Xcode's target editor. `inventory.py` flags such conflicts.
- **Background modes (2.5.4, review).**
  - Every `UIBackgroundModes` entry needs matching use. Examples: `audio` with audible
    background playback, `location` with background location, `voip` with PushKit/CallKit,
    `remote-notification` with push (a push SDK counts), `fetch` and `processing` with
    BGTaskScheduler.
  - Reviewers reject unused modes. This is not an upload block but a common rejection.
- **Launch screen and icon.** A launch screen (`UILaunchScreen` or a storyboard) and a
  complete app icon set are required; uploads without them are refused.
- **Export compliance.** `ITSAppUsesNonExemptEncryption` missing means App Store Connect
  asks the encryption questions for each build. That is a submission step, not a
  rejection. See static-checks.md section 5 before suggesting a value.

## Privacy manifests

- **Missing API declaration (ITMS-91053).**
  - Triggers: a required-reason API is used and the privacy manifest that covers that code
    does not declare it.
  - Who declares: the app's own code, and package code compiled from source into the app
    target without its own `PrivacyInfo.xcprivacy` resource, is covered by the app's
    manifest. SDKs that ship a manifest cover themselves.
  - Categories: UserDefaults, FileTimestamp, SystemBootTime, DiskSpace, ActiveKeyboards.
    Fetch the approved reason codes with `fetch_apple.py doc` (see static-checks.md
    section 2).
- **Missing privacy manifest (ITMS-91061) / missing signature (ITMS-91065).**
  - SDKs on Apple's commonly used SDK list must include their own privacy manifest.
  - SDKs added as binary dependencies must also be signed.
  - Old SDK versions predate this. Check versions against the vendor's release notes and
    Apple's list at https://developer.apple.com/support/third-party-SDK-requirements/.
  - A lockfile entry names the dependency; it does not prove what ends up in the bundle.

## Code and entitlements

- **UIWebView (ITMS-90809).** Any reference in the binary blocks upload. Use `WKWebView`.
  A match in source or an old dependency is a build-verification item.
- **Push entitlement (ITMS-90078).** Push registration code without an `aps-environment`
  entitlement gets a warning ("Missing Push Notification Entitlement"), and push does not
  work.
  - `aps-environment = development` in the `.entitlements` file is normal: export for App
    Store distribution signs with the distribution profile's production value. Do not
    report it.
- **Private API (2.5.1).** A reliable scan needs the compiled binary. From source, flag
  only clear cases (private selectors, `dlopen` of system private frameworks).

## Upload checklist for the report

Put the items that apply into the report's submission checklist:

1. **Next build number:** say which one the upload needs, and whether the working tree is
   set to it.
2. **Fixes in a build:** a new build is needed for any fix in code or Info.plist.
3. **Attached build:** the build is attached to the version.
4. **Export compliance** is answered, or `ITSAppUsesNonExemptEncryption` is set after the
   questionnaire is understood.
5. **Products:** every product sold in the new build is in a submittable state and added
   to the version (payments-and-subscriptions.md).
