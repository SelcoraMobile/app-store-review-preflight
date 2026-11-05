# Metadata, review notes and process

The store listing and the submission form are rejection surfaces of their own. "Metadata
Rejected" outcomes are fixed without a new build, but they still stop the release. Check
every rule against this run's live text.

Contents:

1. [Listing checks (2.3.x)](#1-listing-checks-23x)
2. [Age rating (2.3.6)](#2-age-rating-236)
3. [Review notes (2.3.1(a))](#3-review-notes-231a)
4. [Demo access (2.1(a))](#4-demo-access-21a)
5. [Rejections, timing, appeals](#5-rejections-timing-appeals)

## 1. Listing checks (2.3.x)

Read the live values (store-state.md), not only the repository drafts.

**Accuracy (2.3, 2.3.1(a))**

- Check every claim in the description, subtitle, screenshots and previews against the code.
  Flag claims that have no implementation behind them:
  - "3D model" for a 2D effect
  - "reveal your baby" for an AI imagination
  - "thousands of users" without numbers
  - "AI-powered" with no model call
- Misleading marketing, "whether within or outside of the App Store", is grounds for
  removal under 2.3.1(a).

**In-app purchases (2.3.2)**

- The description, screenshots and previews must show which features need a purchase.

**Screenshots (2.3.3)**

- They "should show the app in use, and not merely the title art, login page, or splash
  screen".
- Apple's 2.3.3 help page (https://developer.apple.com/help/app-review/guideline-reference/2-3-3-screenshots,
  checked 2026-11-05): App Review "will approve only those submissions where more than half
  of screenshots show the app in use", per device set.
- The same page asks for screenshots updated with each version to match the current
  interface.
- From April 2027, submissions must include iPhone Duo screenshots (Apple news,
  2026-10-05).

**Previews (2.3.4)**

- They "may only use video screen captures of the app itself".
- Narration and text overlays are allowed. Footage that is not the app is not (hands
  holding a device, marketing animation).

**Category (2.3.5)**

- A clearly wrong category may be changed by Apple.

**Name, subtitle and keywords (2.3.7)**

- Names are limited to 30 characters.
- No pricing, other apps' names or trademarks, or irrelevant phrases in names or keywords.
- Subtitles "should not include inappropriate content, reference other apps, or make
  unverifiable product claims".
- Naming a service the app genuinely integrates with is not a violation.

**All-audiences metadata (2.3.8)**

- Icons, screenshots and previews must meet 4+ even when the app is rated higher.
- "For Kids" and "For Children" are reserved for the Kids Category.

**Rights (2.3.9, 5.2.1)**

- Use no images, brands, celebrities or other apps' material without rights.
- Use fictional account data in screenshots.

**Other platforms (2.3.10)**

- No names, icons or imagery of other mobile platforms or alternative marketplaces.

**What's New (2.3.12)**

- "Apps must clearly describe new features and product changes in their 'What's New'
  text."
- Bug-fix-only updates may use generic text; significant changes must be listed.

**Creative assets (2.3.14)**

- These are the product page header and search-result assets, kept in the Asset Library.
- Live text: they "must pertain to your app's content and functionality or overarching
  brand, follow standard metadata guidelines, and be appropriate for all audiences" and
  "should not include inappropriate content, references to other apps with an intent to
  mislead, unverifiable product claims, or specific or discounted pricing information."
- Apple's asset best practices (https://developer.apple.com/app-store/asset-best-practices/,
  checked 2026-11-05) add:
  - no website URLs or copyright symbols
  - no awards or recognition the app has not received
  - no logos or references to other platforms or marketplaces
  - no Apple-designated recognitions (Editor's Choice, App of the Day, Apple Design Award)
  - a 4+ rating for every asset
- If none are configured, say so in one line.

**Links**

- The support URL, marketing URL and privacy policy URL must answer (2.1(a): "fully
  functional URLs").
- For auto-renewable subscriptions, check the Terms of Use link
  (payments-and-subscriptions.md section 3).

## 2. Age rating (2.3.6)

"Answer the age rating questions in App Store Connect honestly." Compare the answers with
the features found in Steps 2-8.

**How the questionnaire has changed** (Apple news):

| Date | Change |
|---|---|
| 2025-07-24 | Overhaul: tiers 4+, 9+, 13+, 16+, 18+; new questions about capabilities, medical and wellness topics, and violent themes; AI assistants and chatbots must be considered. |
| 2026-01-31 | Deadline to answer the new questions for every app. |
| 2026-07-09 | Social media questions added: redistribute, amplify or interact with user-generated content through a social feed. |
| 2026-11-16 | Two new descriptors when submitting an update: **Shared Location** and **Dating and Relationships**. Dating and Relationships gives a minimum rating of 18+. All apps must answer by 2027-01-12. |
| 2026 | Regional changes: Australia and Vietnam (from 2026-06-18), Republic of Korea (from 2026-08-12). |

**Real mismatches to flag:**

- **Ads without the capability:** an ads SDK that shows ads, but the "Advertising" answer
  is no.
- **Missing chat or UGC answers:**
  - Chat or messaging in code but "Messaging and Chat" is no.
  - A public feed but no social media / UGC answer.
  - Messaging and Chat, User-Generated Content and Social Media are separate capabilities.
    Chat alone does not require a UGC answer.
- **Unrestricted web access:** a general-purpose browser or web view exists but the answer
  is no.
- **Medical or treatment information** shown without being declared, or "Health or Wellness
  Topics" undeclared while the app gives self-care or lifestyle recommendations. Apple's
  definition mentions calorie tracking, diet and exercise advice.
- **Gambling, contests or loot boxes** in code but not declared.

## 3. Review notes (2.3.1(a))

**Live text:** "All new features, functionality, and product changes must be described with
specificity in the Notes for Review section of App Store Connect (generic descriptions will
be rejected) and accessible for review."

Good notes cover what a reviewer cannot learn from the binary in a few minutes. Short is
fine; technical jargon is not needed.

- **Access:** "No account is required", or demo credentials for every role (section 4).
- **Where to find core features:** for example "the AI tools are in the Studio tab", plus
  any setup steps.
- **What is new in this version,** in specific terms.
- **Server-driven behavior the reviewer may meet,** in plain words:
  - onboarding variants
  - several paywall designs (same plans and terms)
  - free uses or rewarded ads for non-subscribers
  - ads
  - region- or date-dependent content

  2.5.19 wants functionality that is "clear to end users and App Review".
- **Products not visible in the reviewed flow,** and why (2.1(b)).
- **Data handling the reviewer will ask about:**
  - AI providers and consent
  - face data: what, why, who, where, how long, and the policy section
  - account deletion path
- **Hardware or regional needs:** required hardware, location-only features, licences for
  regulated categories, regulatory documentation (the "Before You Submit" section of the
  guidelines).
- **A short screen recording** attached when a flow is hard to reach.

## 4. Demo access (2.1(a))

The live text asks for "demo account info (and turn on your back-end service!) if your app
includes a login".

- A working demo account for every login-gated flow and role, with realistic content, not
  an empty state.
- Credentials tested on a clean device shortly before submission.
- No 2FA or one-time codes the reviewer cannot receive, or the code supplied in the notes.
- The backend, staging environment and third-party services stay up throughout the review.
- A built-in demo mode instead of an account needs "prior approval by Apple".

## 5. Rejections, timing, appeals

**Outcomes**

- **"Metadata Rejected":** only the listing or review information needs to change. Fix and
  resubmit the same build.
- **A rejection fixed in metadata, review information, demo access or the backend:** can
  usually go back on the same build.
- **Binary fixes and Invalid Binary:** need a new build.
- Reply in App Store Connect's message thread for the submission.

**Timing.** Apple's App Review page (https://developer.apple.com/distribute/app-review/,
checked 2026-11-05) says App Review typically reviews "at least 50% of submissions in less
than 24 hours and 90% in less than 48 hours". Never promise a turnaround.

**What Apple says goes wrong most.** The same page: "On average, over 40% of unresolved
issues are related to guideline 2.1: App Completeness". That covers crashes, placeholder
content and incomplete information.

**Expedited review**

- For a critical bug fix in a live app, or a time-sensitive event:
  https://developer.apple.com/help/app-review/after-submitting-for-review/request-expedited-review
- Routine releases do not qualify.

**Appeals**

- The App Review Board takes appeals:
  https://developer.apple.com/help/app-review/after-submitting-for-review/appeal-to-the-app-review-board
- Argue specific compliance. For a bug-fix submission, Apple may let the fix through and
  defer unrelated issues:
  https://developer.apple.com/help/app-review/after-submitting-for-review/bug-fix-submissions
