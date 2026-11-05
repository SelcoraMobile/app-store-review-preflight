# Lumen Photo 2.4.0 (57): App Store review preflight

2026-11-05 · skill app-store-review-preflight 1.2.0 · guidelines "Last Updated: 2026-10-20"
Scope: repository main @ 3f2c1ab (uncommitted changes: no), App Store Connect read via a
signed-in browser session. This is a risk assessment, not a guarantee of approval.

## Summary
AI photo editor with accounts, auto-renewable subscriptions, ads (AdMob), tracking (ATT)
and a backend that forwards photos to a third-party image model. iOS and iPadOS audited.
Two items block submission today; the paywall and the privacy answers are the main review
risks.
Top three: 1. yearly subscription is `MISSING_METADATA` 2. iPad orientations 3. third-party AI consent

## Findings
| # | Guideline | Finding | Confidence | Needs new build |
|---|---|---|---|---|
| 1 | 2.1(b) | Yearly plan cannot be submitted | validator-certain | no |
| 2 | Upload: iPad orientations | iPad multitasking needs all four orientations | review-risk (validator-blocking if shipped as-is; needs build verification) | yes |
| 3 | 5.1.2(i) | Photos go to a third-party AI without consent | review-risk | yes |
| 4 | 4.3(a) | Differentiation from other filter apps | judgment-call | no |

### [2.1(b)] Yearly plan cannot be submitted
- **Confidence:** validator-certain
- **Evidence:** App Store Connect > Subscriptions > `com.lumen.yearly`: MISSING_METADATA, no
  review screenshot. Sold by `Paywall/PaywallView.swift:88`.
- **Why it matters:** 2.1(b) asks that in-app purchases are "complete, visible to the
  reviewer, and functional".
- **Fix:** add the review screenshot and localization, then attach the product to version
  2.4.0. New build: no.

### [Upload: iPad orientations] iPad multitasking needs all four orientations
- **Confidence:** review-risk (validator-blocking if shipped as-is; needs build verification)
- **Evidence:** `Info.plist` sets `UISupportedInterfaceOrientations~ipad` to portrait only,
  which overrides `INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad`.
- **Why it matters:** uploads without `UIRequiresFullScreen` must support all four.
- **Fix:** list all four orientations in `Info.plist`. New build: yes (57 → 58).

### [5.1.2(i)] Photos go to a third-party AI without consent
Confidence: review-risk
Evidence: `Services/Upload.swift:41` posts photos to `api.lumen.app/v1/edit`, which forwards
them to a hosted image model. Profile text says "<script>alert('x')</script> all on device".
Why it matters: 5.1.2(i) requires that the app "clearly disclose where personal data will be
shared with third parties, including with third-party AI".
Fix: show a consent sheet before the first upload; see
[the docs](https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage)
and do not use [this link](javascript:alert(1)). New build: yes.

### [4.3(a)] Differentiation from other filter apps
- **Confidence:** judgment-call
- **Evidence:** onboarding and the first three screenshots show generic filters.
- **Fix:** lead the screenshots with the AI relighting feature.

## Previous issues
| Earlier item | Source | Status now |
|---|---|---|
| 2.3.2 IAP disclosure in description | rejection 2026-10-30 | fixed in App Store Connect |

## Submission checklist (App Store Connect, before Submit)
- [ ] Build 2.4.0 (58) uploaded, processed and attached to the version
- [x] Export compliance answered
- [ ] Yearly subscription ready and added to the version
- [ ] Review notes updated (AI consent flow, demo account)

## Clean areas
- Account deletion: present in Settings > Account (`Settings/AccountView.swift:120`).
- Sign in with Apple: offered next to Google.

## Not checked
- Runtime behavior, crashes, live purchase and restore flows

## Verification note
- Guidelines fetched in full on 2026-11-05 (Last Updated 2026-10-20)

```text
python3 -I fetch_apple.py guidelines --out /tmp/g.txt
```
