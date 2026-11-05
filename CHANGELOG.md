# Changelog

## 1.0.0 (2026-11-05)

First release by Selcora Mobile. Based on dabodamjan/app-store-rejection-checker (MIT,
commit d8fe5fd, 2026-10-18), re-verified against Apple's live pages on 2026-11-05.

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
- **New reference files:** `upload-validation.md`, `store-state.md`,
  `privacy-and-tracking.md`, `sdk-data-map.md`, `payments-and-subscriptions.md`,
  `common-rejections.md`, `live-sources.md`, `report-template.md`.
- **New checks:**
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

**Fixed (from upstream)**

- `C56D.1` was given as an example UserDefaults reason; Apple allows it only for
  third-party SDKs. Apps use `CA92.1` (or `1C8F.1` for App Groups).
- The published review time is "at least 50% … in less than 24 hours and 90% in less than
  48 hours" (upstream: 90% in 24 hours).
- The privacy manifest tracking rule no longer flags `NSPrivacyTracking: false` in the app
  manifest when a tracking SDK ships its own manifest.
- Apple does publish one per-guideline figure: over 40% of unresolved issues relate to 2.1.

**Changed**

- `allowed-tools` pre-approves read tools only; shell commands go through normal
  permission prompts.
- The audit is read-only. App Store Connect fixes come after the report, one at a time,
  with explicit approval.
- `recent-changes.md` is updated to 2026-11-05. New entries include the age rating
  descriptors (2026-11-16), the EU ATT prompt (iOS 27.2), SDK and deployment minimums,
  social-media age-rating questions, and regional rating changes.
