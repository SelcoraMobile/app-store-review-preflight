# Common rejection patterns and how to detect them

A checklist of patterns that recur in rejections. Use it to make sure no common surface is
skipped. The "How to detect" column says where the evidence comes from: repo, App Store
Connect (ASC), runtime, or judgment. Cite the live guideline text from this run, not this
table.

Apple's own figure (https://developer.apple.com/distribute/app-review/, checked 2026-11-05):
"On average, over 40% of unresolved issues are related to guideline 2.1: App Completeness".
Start there.

## Completeness and performance (section 2)

| Pattern | Guideline | How to detect | Typical fix |
|---|---|---|---|
| Crash or obvious bug on the reviewer's device, often on iPad or the newest OS | 2.1(a) | Runtime (not visible to this audit). Ask whether the build was tested on the latest OS and on iPad. | Test on device; fix. |
| Placeholder text, empty screens, "lorem ipsum", test ads | 2.1(a) | Repo: grep for lorem, TODO in UI strings, test ad unit IDs (`ca-app-pub-3940256099942544` is Google's test ID). | Replace before submitting. |
| Broken links: privacy, terms, support, rate/share links that open the wrong app | 2.1(a) | `check_links.py --inventory …` (URLs and App Store IDs). | Fix the URL or ID; new build if in code. |
| Login-gated app without demo access, or backend down | 2.1(a) | ASC review information; ask about server uptime. | Demo account for each role; keep services up. |
| IAP not loadable or not submitted | 2.1(b) | ASC product states against product IDs in code (payments-and-subscriptions.md). | Complete metadata, attach to the version, or explain in the notes. |
| "Information Needed" (business model, face data, AI providers, regulated features) | 2.1 | Classification (Step 2). | Answer the questions in advance in the review notes and the privacy policy. |
| Metadata does not match the app; screenshots not showing the app in use | 2.3, 2.3.1(a), 2.3.3 | ASC listing against the code; screenshot sets. | Use the accurate drafts; more than half of each device set shows the app in use. |
| Subtitle or keywords with claims, prices, other apps' names | 2.3.7 | ASC listing. | Rewrite. |
| Names or images of other platforms | 2.3.10 | ASC listing, screenshots, in-app text. | Remove. |
| Unused background modes | 2.5.4 | `inventory.py` flags. | Remove the mode or implement the use. |
| Not working on IPv6-only networks | 2.5.5 | Repo: hardcoded IPv4 literals in URLs (`inventory.py` signal `ipv4_literal`); low-level sockets. | Use hostnames and Network.framework / URLSession. |
| Ads outside the main app binary (widgets, extensions, notifications) | 2.5.18 | Repo: ad SDK imports in extension targets. | Keep ads in the main app. |
| Hidden or undocumented features, reviewer detection | 2.5.19 | static-checks.md section 9. | Remove, or document in the notes. |

## Business (section 3)

| Pattern | Guideline | How to detect | Typical fix |
|---|---|---|---|
| Digital goods sold outside IAP | 3.1.1 | Repo: payment SDKs, checkout URLs reached from paywall or unlock code. | Use IAP. |
| No restore for subscriptions or non-consumables | 3.1.1 | Repo: `restore_purchases` signal; UI. | Add Restore. |
| Paywall missing required information, or billed amount less prominent than a computed price | 3.1.2(c) | Repo: paywall views and strings for every design. | Add title, length, price, billed amount, trial terms, and Terms and Privacy links. |
| No Terms of Use (EULA) link in metadata for auto-renewable subscriptions | 3.1.2 | ASC description and license agreement. | Link Apple's standard EULA in the description or set a custom EULA; links at the end of the description. |

## Design (section 4)

| Pattern | Guideline | How to detect | Typical fix |
|---|---|---|---|
| Layout broken on iPad: iPhone apps run on iPad and reviewers check | 2.4.1, 4.0 | Repo: `TARGETED_DEVICE_FAMILY`; layout code with fixed sizes; screenshots of the iPad set. Runtime otherwise. | Fix layouts, or make the app iPhone-only (an iPhone-only app still runs on iPad in compatibility mode). |
| Copycat icon, name or brand of another developer | 4.1 (incl. 4.1(c)) | ASC listing and icon; judgment. | Your own branding. |
| Thin app, web wrapper, template output | 4.2, 4.2.6 | static-checks.md section 7; judgment. | Add native value, or do not ship. |
| Saturated category or near-duplicate | 4.3 | Judgment (4.3(b) names dating, flashlight, sound effects, wallpaper, simple timers, fortune telling). | Differentiate. |
| Marketing push notifications without explicit opt-in and in-app opt-out | 4.5.4 | Repo: push SDK plus marketing use (campaigns, offers); consent UI; settings toggle. | Opt-in text in the app and an opt-out setting. |
| Social login without a privacy-protecting alternative | 4.8 | static-checks.md section 4. | Add a qualifying login option. |

## Privacy and conduct (section 5)

| Pattern | Guideline | How to detect | Typical fix |
|---|---|---|---|
| No privacy policy link in the app or in ASC | 5.1.1(i) | ASC app info; repo: link in settings or paywall. | Add both. |
| Unclear purpose strings | 5.1.1(ii) | `inventory.py` lists them with localizations. | Say what is accessed and why. |
| Pressure before permission dialogs | 5.1.1(iv), 5.1.2(i) | Repo: pre-prompt screens before ATT, push, camera or photos. | Neutral pre-prompt, always reach the system dialog, no incentives. |
| Account creation without in-app deletion | 5.1.1(v) | static-checks.md section 6. | Add deletion. |
| Login required for features that do not need an account | 5.1.1(v) | Repo: login wall at launch. | Let people in without an account. |
| ATT prompt and App Privacy tracking answers disagree | 5.1.2(i) | privacy-and-tracking.md section 2. | Make them agree. |
| Personal data to third-party AI without disclosure and consent | 5.1.2(i) | privacy-and-tracking.md section 5. | Consent screen before the first send. |
| Face data questions unanswered | 2.1, 5.1.2(vi) | privacy-and-tracking.md section 6. | Policy section plus notes. |
| AI generator with no way to report results | 1.2 | special-categories.md section 1. | A "Report" action; mention filters in the notes. |
| Custom rating prompt instead of the system API | 5.6.1 | Repo: custom "Rate us" or "Do you like the app?" dialogs. A settings row that opens the App Store review page is fine. | Use `AppStore.requestReview` / `SKStoreReviewController`. |
