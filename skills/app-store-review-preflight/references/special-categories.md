# Special categories

Apply the matching section when Step 2's classification puts the app in one of these. Missed
requirements here are rare but near-certain rejections. Re-read the matching live section
in every run; the quotes below were checked on 2026-11-05.

Contents:

1. [AI content generation (1.2)](#1-ai-content-generation-12)
2. [Face and body images](#2-face-and-body-images)
3. [Prediction and novelty features (1.1.6, 4.3(b))](#3-prediction-and-novelty-features-116-43b)
4. [Pregnancy, fertility, health and medical (1.4.1, 5.1.3)](#4-pregnancy-fertility-health-and-medical-141-513)
5. [User-generated content and chat (1.2)](#5-user-generated-content-and-chat-12)
6. [Kids (1.3, 5.1.4)](#6-kids-13-514)
7. [Gambling, contests, real-money gaming (5.3)](#7-gambling-contests-real-money-gaming-53)
8. [VPN (5.4)](#8-vpn-54)
9. [Cryptocurrency (3.1.5) and finance (3.2.1)](#9-cryptocurrency-315-and-finance-321)
10. [Dating](#10-dating)
11. [Where the app is sold: local law (section 5)](#11-where-the-app-is-sold-local-law-section-5)

## 1. AI content generation (1.2)

**Live 1.2 text:** it covers "Apps that enable users to create, generate, upload, share, or
otherwise contribute content". It adds: "This includes social media, user-generated content
platforms, and AI content creation apps. To prevent abuse, such apps must include:

- A method for filtering objectionable material from being posted to the app
- A mechanism to report offensive content and timely responses to concerns
- The ability to block abusive users from the service
- Published contact information so users can easily reach you"

Apple's October 16, 2026 announcement ties this to nonconsensual intimate imagery,
"including imagery generated using AI tools".

**Calibrate to the app's shape.** The four items are written for platforms where users
reach each other. For a single-user generator whose results stay private:

| Requirement | What to look for |
|---|---|
| Filtering | Server-side or provider safety checks on inputs and outputs (a safety-checker flag, a moderation call, a blocklist). The reviewer cannot see these, so mention them in the review notes. |
| Reporting | A "Report" action on each generated result, with a response path (an email with the result ID is enough). Missing in-app reporting is the gap most often seen. Rate it review-risk under the October 2026 text. |
| Blocking | Applies only if users can see or reach each other. Otherwise say "not applicable: no user-to-user content". |
| Contact | Published support contact in the app and on the support URL. |

Shared feeds, public galleries, chat and remixing bring in the full 1.2 set and 1.2.1.

**Remediation clause:** 1.2 also says "Developers who fail to implement appropriate
safeguards or fail to remediate identified violations after notice may be considered in
violation of the Developer Code of Conduct". That makes this account-level exposure.

**Also check:**

- The age rating considers what the generator can produce (2.3.6).
- Creative assets and screenshots show only 4+ content.
- Third-party AI disclosure and consent (privacy-and-tracking.md section 5).

## 2. Face and body images

Apps that upload faces or bodies (face swaps, "future baby", ageing, beauty or body edits,
AI portraits):

- **Face data:** 5.1.2(vi) forbids using face data for marketing, advertising or data
  mining. Reviewers often ask the standard face-data questions under 2.1. Prepare a
  privacy-policy section and notes (privacy-and-tracking.md section 6).
- **Photos of other people:** the app should ask the uploader to confirm they have
  permission. The consent text should cover it.
- **Real people and nudity:** 1.1.4 and 1.2's nonconsensual intimate imagery wording. Any
  path to undressing, sexualizing or "hot-or-not" style rating of real people is a removal
  risk. 1.2 lists "objectification of real people (such as "hot-or-not" voting)".
- **Children's images:** if outputs depict children (baby generators), make sure filters
  keep outputs clothed and non-sexual, and say so in the notes.

## 3. Prediction and novelty features (1.1.6, 4.3(b))

**1.1.6:** "False information and features, including inaccurate device data or trick/joke
functionality, such as fake location trackers. Stating that the app is "for entertainment
purposes" won't overcome this guideline."

**4.3(b)** names fortune telling among categories Apple "will not accept new submissions"
in "unless they offer a meaningfully different or improved experience".

For features like gender prediction, "what will my baby look like", compatibility scores or
horoscopes:

- **Accuracy.** Judge whether the feature claims accuracy it cannot have. A disclaimer
  alone does not fix a feature that pretends to measure or diagnose (1.1.6, 1.4.1). Honest
  framing ("an AI-imagined portrait", "a just-for-fun guess") throughout the app and
  listing reduces the risk.
- **Differentiation.** A novelty feature inside a broader app with real utility is in a
  different position from an app that is only that feature. Give the differentiation view
  as a judgment-call.

## 4. Pregnancy, fertility, health and medical (1.4.1, 5.1.3)

**1.4.1:** "Medical apps that could provide inaccurate data or information, or that could be
used for diagnosing or treating patients may be reviewed with greater scrutiny." Apps "must
clearly disclose data and methodology to support accuracy claims relating to health
measurements". Device-only measurements of blood pressure, temperature, blood glucose or
blood oxygen are "not permitted". Apps "should remind users to check with a doctor".

- **Pregnancy, fertility and baby apps:**
  - Due-date math, baby-size charts and scan interpretation need sources or a clear
    "average values, not medical advice" note.
  - Anything that reads medical images (ultrasound) must not present itself as
    diagnosis.
- **5.1.3 (HealthKit, Motion and Fitness, health research data):** no advertising or data
  mining use; never write false data to HealthKit; no personal health information in
  iCloud.
- **Regulatory clearance:** if the app has it, submit a link. "Before You Submit" now asks
  for documentation for regulated features.
- **Age rating:** answer "Medical or Treatment Information" and "Health or Wellness Topics"
  to match the content.

## 5. User-generated content and chat (1.2)

The full four-item set applies: filtering, reporting with timely response, blocking, and
published contact.

**Random or anonymous chat:**

- Apple's 2026-02-06 revision made random or anonymous chat subject to 1.2.
- 1.2 also says apps used primarily for "Chatroulette-style experiences, random or
  anonymous chat" may be removed.

**Creator apps (1.2.1(a)):** they need a way to identify content above the app's age rating
and an age restriction "based on verified or declared age".

## 6. Kids (1.3, 5.1.4)

**Kids Category (1.3):**

- No links out, purchases or other distractions unless behind a parental gate.
- No sending personal or device information to third parties.
- Third-party analytics and advertising are not allowed, except in the narrow cases 1.3
  describes.
- The obligations continue "even if you decide to deselect the category".

**5.1.4:** follow children's privacy law (COPPA, GDPR and similar). Apps not in the Kids
Category "cannot include any terms in app name, subtitle, icon, screenshots or description
that imply the main audience for the app is children".

**Static signals:**

- ad or analytics SDKs in a Kids Category app
- `SKAdNetworkItems`
- outbound links without a parental gate

## 7. Gambling, contests, real-money gaming (5.3)

- **Contests:** sweepstakes and contests are sponsored by the developer, with official rules
  in the app that make clear Apple is not a sponsor (5.3.1, 5.3.2).
- **IAP:** no IAP for credit used in real-money gaming (5.3.3).
- **Real-money gaming (5.3.4):**
  - Requires licensing in every location where the app is available.
  - Must be geo-restricted to those locations.
  - Must be free on the App Store.
- **Embedded games:** gambling-like mini games delivered as embedded software fall under
  4.7. Read it live.

## 8. VPN (5.4)

**Live text:** VPN apps "must utilize the NEVPNManager API and may only be offered by
developers enrolled as an organization". They must make "a clear declaration of what user
data will be collected and how it will be used on an app screen prior to any user action to
purchase or otherwise use the service". They "may not sell, use, or disclose to third
parties any data for any purpose, and must commit to this in their privacy policy".

Where a territory requires a VPN license, put the license information in the App Review
Notes field.

## 9. Cryptocurrency (3.1.5) and finance (3.2.1)

**Crypto (3.1.5):**

- Wallets only from organizations.
- No on-device mining.
- Exchanges only where licensed.
- ICOs and crypto securities only from approved financial institutions.
- No crypto rewards for tasks.

**Trading and money management (3.2.1):** should come from the licensed institution itself.
Read 3.2.1 and 3.2.2 live; for example, 3.2.2(ix) limits loan apps' APR and repayment
terms.

## 10. Dating

There is no dedicated guideline. Dating combines:

- the 1.2 obligations
- 4.3(b), which names dating as a saturated category
- the age rating: since 2026-11-16 the questionnaire has a Dating and Relationships
  descriptor with a minimum rating of 18+, and higher regional ratings (Brazil A18)

## 11. Where the app is sold: local law (section 5)

**Live section 5 introduction:** "Apps must comply with all legal requirements in any
location where you make them available (if you're not sure, check with a lawyer)."

Read the availability list (store-state.md) and look for features that local rules treat
specially. Examples:

- generative AI services and content labelling in some countries
- loot boxes
- real-money gaming
- VPN licensing
- prenatal sex determination
- health claims
- data localization

**Rules for this check:**

- **Facts:** state each local rule as a question to verify, not as a fact, unless you
  confirmed it from a primary source in this run. Label it "not verified this run".
- **Confidence:** these findings are judgment-calls.
- **Fix:** usually counsel, or removing the territory, or disabling the feature there.
