# Privacy, tracking and data flows

Section 5.1 is the second-largest source of rejections in Apple's own counts (Legal: 495,673
of 2,093,244 rejected submissions in the 2025 Transparency Report). The checks here compare
three things that must agree:

- what the binary collects (code plus SDKs)
- what App Store Connect declares (App Privacy answers, ATT)
- what the user is told (purpose strings, consent screens, privacy policy)

Contents:

1. [App Privacy answers ("privacy labels")](#1-app-privacy-answers-privacy-labels)
2. [App Tracking Transparency, both directions](#2-app-tracking-transparency-both-directions)
3. [Permission requests and pre-prompts (5.1.1(ii)-(iv))](#3-permission-requests-and-pre-prompts-511ii-iv)
4. [Analytics consent (5.1.1(ii))](#4-analytics-consent-511ii)
5. [Third-party AI (5.1.2(i))](#5-third-party-ai-512i)
6. [Face data (5.1.2(vi))](#6-face-data-512vi)
7. [Privacy policy (5.1.1(i))](#7-privacy-policy-511i)
8. [EU consent for ads and analytics](#8-eu-consent-for-ads-and-analytics)

## 1. App Privacy answers ("privacy labels")

**Live text, 2.3:** "make sure all your app metadata, including privacy information, your app
description, screenshots, and previews accurately reflect the app's core experience".

**Apple's definitions** (https://developer.apple.com/app-store/app-privacy-details/, fetch
it for exact wording):

- The answers cover data collected by the app **and by third-party partners whose code is
  in the app**.
- "Collect" means the data leaves the device and is kept longer than needed to serve the
  request in real time.
- Each data type carries:
  - purposes (Third-Party Advertising, Developer's Advertising or Marketing, Analytics,
    Product Personalization, App Functionality, Other)
  - whether it is linked to the user
  - whether it is used for tracking

**Method:**

1. Read the published answers (store-state.md: the browser snapshot is the only route to
   them).
2. List every SDK and data flow in the binary (`inventory.py` SDKs, plus your own backend:
   what it receives and keeps).
3. Map each SDK to the data types it collects (sdk-data-map.md), and confirm with the
   vendor's disclosure page for the configured features.
4. Compare. Report:
   - An ads, attribution or analytics SDK with no matching data types declared (Identifiers
     > Device ID, Usage Data > Product Interaction or Advertising Data, Location > Coarse,
     Diagnostics). **Review-risk.**
   - "Data Not Collected" published while any analytics, ads, crash or attribution SDK
     ships. **Review-risk.**
   - Answers last published before a new SDK or data flow was added. The publish date sits
     in the snapshot's `privacy.publish`.
   - Categories declared for data the app does not collect. Cleanup, but it misinforms
     users.

**Fix:** list the exact rows to add, as category / purposes / linked / tracking. Note that
publishing the answers takes effect immediately, not with the version.

## 2. App Tracking Transparency, both directions

**Live text, 5.1.2(i):** "You must receive explicit permission from users via the App
Tracking Transparency APIs to track their activity." It also forbids requiring users to
enable tracking "in order to access functionality, content, use the app, or receive
monetary or other compensation".

**Tracking** (Apple's definition, on the user-privacy page): linking user or device data
from your app with data from other companies' apps, websites or offline properties for
targeted advertising or advertising measurement, or sharing it with data brokers.

**Consistency checks:**

- **The app (or an SDK it hosts) calls `requestTrackingAuthorization`.**
  - The App Privacy answers must declare at least one data type used for tracking.
  - The purpose string must describe what is actually tracked.
  - An ATT prompt with no tracking declared, or the reverse, is a recurring rejection
    pattern.
- **Tracking declared, but no ATT request in the code or SDK configuration.** Review-risk.
- **IDFA read before the user answers.** IDFA-based tracking initialized before the ATT
  result is known is a review-risk. With ATT denied the IDFA is zeros, but device
  fingerprinting is not allowed either way.
- **SDK that owns the prompt.** When an SDK (attribution, paywall or engagement SDK) shows
  ATT, confirm in its code or configuration when the prompt appears and that the ad SDK
  starts afterwards. Do not assume.
- **EU.** Apple announced (news, 2026-09-16) an alternative ATT system prompt from iOS and
  iPadOS 27.2 in the EU, the only one available in Germany, France, Italy, Poland and
  Romania. When permission is required is unchanged; no code change is implied.

## 3. Permission requests and pre-prompts (5.1.1(ii)-(iv))

- **Live text, 5.1.1(iv):** apps "must respect the user's permission settings and not
  attempt to manipulate, trick, or force people to consent to unnecessary data access".
- **Pre-prompts.** A screen before the system dialog is allowed if:
  - the user always reaches the real system dialog
  - it does not mimic a system alert
  - it does not reward consent or punish refusal
  - it does not leave out a way to decline

  Report a pre-prompt that pressures (for example a single "Allow" path with no decline,
  or an incentive for allowing) as a review-risk under 5.1.1(iv). Report ATT-specific
  pressure under 5.1.2(i).
- **Purpose strings** must "clearly and completely describe your use of the data"
  (5.1.1(ii)). Check the text in each shipped language.
- **Data minimization (5.1.1(iii)):** prefer the out-of-process picker or share sheet over
  full Photos or Contacts access.
- **No gating (5.1.2(i)):** do not require push, location or tracking to use the app.

## 4. Analytics consent (5.1.1(ii))

**Live text:** "Apps that collect user or usage data must secure user consent for the
collection, even if such data is considered to be anonymous at the time of or immediately
following collection." The same subsection requires "an easily accessible and
understandable way to withdraw consent". It also allows collection "for a legitimate
interest without consent by relying on the terms of the European Union's General Data
Protection Regulation ("GDPR") or similar statute", provided the app complies with all
terms of that law.

**Calibration**, kept from the upstream skill because it matches how enforcement behaves:

- **The pattern:** an analytics SDK collecting from launch, with no consent gate and no
  consent screen.
- **Rate it judgment-call by default.** Apple rarely enforces this sentence against plain
  first-party analytics; enforcement attention goes to ATT.
- **Raise it to review-risk** when:
  - the analytics carry sensitive or identifying data, or
  - the privacy answers or policy claim nothing is collected, or
  - the UI misstates what happens. For example, a settings toggle that reads as "off"
    while collection runs. Check the default the toggle actually reads, including
    `register(defaults:)` and `@AppStorage` defaults, before calling it a misstatement.
- **Legitimate interest declared** (usually in the privacy policy): note it, state that
  GDPR compliance was not and cannot be verified here, and flag any contradiction with the
  actual data flows.

## 5. Third-party AI (5.1.2(i))

**Live text (added November 2025):** "You must clearly disclose where personal data will be
shared with third parties, including with third-party AI, and obtain explicit permission
before doing so."

**Scope:**

- Personal data sent to an external LLM, image or ML provider.
- That includes a provider behind the app's own backend: if the server forwards a user's
  photo to an AI provider, the app is sharing it with third-party AI. Find out what the
  backend forwards (Step 2).
- Free-form text, photos, audio, face images and health data are personal data in
  practice.
- Inputs that carry no personal data, such as a style choice or a list of preferences, are
  outside the sentence. Judge each flow and say which side it falls on.

**What a passing flow looks like:**

1. Before the first send, the app says **what** is sent and **to whom** (the provider names
   or a clear description).
2. It asks for explicit permission: an affirmative action, not a line buried in the terms.
3. It links the privacy policy.
4. Permission can be withdrawn later, for example in Settings.
5. For photos of other people, the user confirms they have that person's permission.
6. The App Privacy answers and the privacy policy cover the same flow (for example Photos
   or Videos, Other User Content, Audio).

**Ratings:** no consent flow is a **review-risk**. The wording is explicit, and reviewers
have rejected AI photo apps on it together with 2.1 information requests. Consent that
exists for some tools but not others is a review-risk for the uncovered ones.

## 6. Face data (5.1.2(vi))

**Live text:** "Data gathered from the HomeKit API, HealthKit, Clinical Health Records API,
MovementDisorder APIs, ClassKit or from depth and/or facial mapping tools (such as ARKit,
Camera APIs, or Photo APIs) may not be used for marketing, advertising or use-based data
mining, including by third parties."

**When it applies:** apps that process faces, such as face swaps, "future baby" or ageing
generators, beauty filters and face-based AI portraits.

**What reviewers ask.** These apps often get a 2.1 "Information Needed" message about face
data. It is a recurring request seen in practice; confirm the current wording if a
rejection is at hand. It typically asks:

- what face data the app collects
- what it is used for
- whether it is shared, and with whom
- where it is stored
- how long it is kept
- which section of the privacy policy covers it

**How to prepare:**

- **Privacy policy:** a specific face-data section that answers those points.
- **Review notes:** a short summary of the same answers.
- **Code:** confirm that no face-derived data reaches ad or analytics SDKs (5.1.2(vi)).

**Rating:** missing face-data disclosure in an app that sends faces to a server is a
review-risk.

## 7. Privacy policy (5.1.1(i))

**Live text:** "All apps must include a link to their privacy policy in the App Store
Connect metadata field and within the app in an easily accessible manner." The policy must
"clearly and explicitly":

- identify what data is collected, how it is collected, and all uses
- confirm that third parties who receive user data give the same or equal protection
- explain retention and deletion, and how a user can revoke consent or request deletion

**Checks:**

1. The URL field in App Store Connect is filled for every locale (snapshot `appInfo`).
2. The app shows the link where users can find it: settings, paywall, consent screens.
3. The page answers (`check_links.py`).
4. Read the page (`check_links.py --text <url>`) and compare it with the inventory. Every
   SDK category and every AI provider should appear, plus retention and deletion and how to
   withdraw consent.

## 8. EU consent for ads and analytics

Outside App Review but often confused with it:

- **GDPR and ePrivacy** consent for ads and analytics in the EEA and UK.
- **Google's EU user consent policy** for AdMob and Firebase. Google documents its User
  Messaging Platform or a certified CMP for this; check Google's current pages.

Report gaps here, such as a consent SDK linked but never called, as a compliance note, not
as an App Review rejection risk. 5.1.1(ii) still applies to consent for collection; see
section 4.
