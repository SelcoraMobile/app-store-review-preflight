# Changelog

## 1.2.0 (2026-11-05)

**Added**

- **HTML report:** `scripts/render_report.py` renders `APP_REVIEW_PREFLIGHT.md` as
  `APP_REVIEW_PREFLIGHT.html`, one self-contained interactive page:
  - counts per confidence level, filters for confidence and "needs a new build", search
  - one card per finding with a copy-as-markdown button
  - the submission checklist as checkboxes whose ticks stay in the browser
  - table of contents, light and dark themes, print layout
  - page controls in English or Turkish (`--lang`), any other language with `--labels`
- **Safety of the page:** it makes no network requests, all report text is escaped, links
  work only for http, https and mailto, and a hash-based Content-Security-Policy allows
  only the page's own style and script.
- Offline tests for the renderer.

**Changed**

- Finding fields are now `- **Label:** value` list items, so they show as separate lines in
  any markdown viewer. Plain `Label: value` lines from older reports still render.
- `SKILL.md` Step 9 renders the HTML page after the markdown and reads the renderer's
  warnings. Step 10 re-renders it after fixes that change the report.
- `report-template.md` lists the parts the page keys on: `### [guideline] title`
  headings, the confidence identifiers, the findings table's last column and `- [ ]`
  checklist items.

## 1.1.0 (2026-11-05)

Fixes from a field test: a fresh agent ran the skill on a real app (an AI photo app with
subscriptions, ads and a backend) and reported what slowed it down or was missing.

**Added**

- **Step 0:** start from a rejection message or an earlier preflight report. The report
  gets a "Previous issues" section with each item's status now.
- **Which build gets reviewed:** compare the attached build's upload time (in UTC) with
  later commits. `inventory.py` flags uncommitted edits to `CURRENT_PROJECT_VERSION` and
  `MARKETING_VERSION`, which Xcode's target editor makes silently.
- **Server-side review targeting:** `is_apple`-style flags, test-device lists, Apple IP
  ranges, and switches based on region or date.
- **`inventory.py`:**
  - reviewer-flag names (`isApple`, `isTestDevice`, `isReviewer`…)
  - "Google UMP is linked but never called"
  - a `permission_pre_dialog` signal (custom and SDK-owned pre-permission dialogs)
  - every kept sample per signal in the markdown
- **Report:** a "Compliance notes (outside App Review)" section.
- **`store-state.md`:** unanswered (`null`) age rating answers, custom EULA content (the
  snapshot returns its first 300 characters), and UTC offsets on App Store Connect dates.

**Fixed**

- `guideline_sections.py show 3.1.2` now includes 3.1.2(a)-(c). Lettered parts that are
  numbered lines of their own were dropped before.
- `fetch_apple.py page` keeps only the page's `<main>` content, without site navigation;
  `--keep-nav` restores the full page.
- `SKILL.md` defines `<tmp>` and explains how `allowed-tools` pre-approval relates to the
  shell-run scripts.
- **validator-certain evidence:** literal `project.pbxproj` values count as resolved when
  the target has no `.xcconfig`. `xcodebuild -showBuildSettings` can resolve packages and
  write files, so the skill now says to ask first.
- **Vendor privacy pages:** they can be read with `check_links.py --text`, and the
  `compatibility` field mentions them.

## 1.0.0 (2026-11-05)

First release by Selcora Mobile, checked against Apple's live pages on 2026-11-05.

**Added**

- **App Store Connect state checks:** listing, subscriptions and IAP states, App Privacy
  answers, builds, age rating, availability and EULA. Read through the API, a GET-only
  browser snippet (`scripts/asc_snapshot.js`) or pasted fields. Repository drafts are
  compared with the live listing.
- **Deterministic source scripts:** `fetch_apple.py` fetches the whole guidelines page,
  news since a date, DocC JSON for client-rendered documentation, and App Store ID lookups.
  `guideline_sections.py` prints sections by number.
- **`inventory.py`:** OpenStep `project.pbxproj` parser, merged release settings,
  generated Info.plist keys (where the file's value wins and conflicts are flagged), SDK
  detection, source signals with `#if DEBUG` awareness, App Store IDs, hosts and mechanical
  flags.
- **`check_links.py`:** URL status, App Store ID ownership against the bundle ID, and page
  text for privacy policies.
- **Reference files:** `upload-validation.md`, `store-state.md`,
  `privacy-and-tracking.md`, `sdk-data-map.md`, `payments-and-subscriptions.md`,
  `common-rejections.md`, `live-sources.md`, `report-template.md`.
- **Checks:**
  - product readiness (2.1(b))
  - App Privacy answers compared with the SDKs, and ATT in both directions
  - face data (5.1.2(vi))
  - wrong App Store IDs
  - iPad orientations, including the Info.plist override trap
  - unused background modes, SDK and deployment-target minimums, build-number collisions,
    extension version mismatches
  - pre-permission pressure (5.1.1(iv)), marketing push (4.5.4), custom review prompts
    (5.6.1), ads in extensions (2.5.18), IPv6 literals, test ad units
  - AI generator calibration (1.2), prediction and novelty features, local law where the
    app is sold
- **Offline unit tests** and CI.

**Facts checked against Apple's pages**

- `C56D.1` is a UserDefaults reason Apple allows only for third-party SDKs. Apps use
  `CA92.1` (or `1C8F.1` for App Groups).
- The published review time is "at least 50% … in less than 24 hours and 90% in less than
  48 hours".
- The privacy manifest tracking rule does not flag `NSPrivacyTracking: false` in the app
  manifest when a tracking SDK ships its own manifest.
- Apple publishes one per-guideline figure: over 40% of unresolved issues relate to 2.1.

**Design**

- `allowed-tools` pre-approves read tools only; shell commands go through normal
  permission prompts.
- The audit is read-only. App Store Connect fixes come after the report, one at a time,
  with explicit approval.
- `recent-changes.md` is current as of 2026-11-05. Entries include the age rating
  descriptors (2026-11-16), the EU ATT prompt (iOS 27.2), SDK and deployment minimums,
  social-media age-rating questions, and regional rating changes.
