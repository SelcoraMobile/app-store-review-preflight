# Payments and subscriptions

Business (section 3) accounts for 283,820 of 2,093,244 rejected submissions in Apple's 2025
Transparency Report. Paywall disclosure is the most familiar part. Product setup in App
Store Connect is the part repo-only audits miss.

Contents:

1. [Product readiness in App Store Connect (2.1(b))](#1-product-readiness-in-app-store-connect-21b)
2. [Paywall disclosure (3.1.2(c))](#2-paywall-disclosure-312c)
3. [Subscription metadata: description, EULA, privacy URL](#3-subscription-metadata-description-eula-privacy-url)
4. [Restore and digital goods (3.1.1)](#4-restore-and-digital-goods-311)
5. [Alternative unlock paths and remote access modes](#5-alternative-unlock-paths-and-remote-access-modes)
6. [Other rules: value, groups, offers, loot boxes, external links](#6-other-rules)

## 1. Product readiness in App Store Connect (2.1(b))

**Live text:** "If you offer in-app purchases in your app, make sure they are complete,
up-to-date, visible to the reviewer and functional. If any configured in-app purchase items
cannot be found or reviewed in your app, explain the reason in your review notes."

**Method:**

1. List every product ID the shipping build can sell:
   - constants in code
   - paywall catalogs
   - product lists that a paywall SDK or panel serves (read its configuration or ask)
   - the `.storekit` file (that file only affects local testing)
2. Read each product in App Store Connect (store-state.md: snapshot `subscriptions`, `iap`).
3. For each product the build sells:
   - **`APPROVED`:** fine.
   - **`READY_TO_SUBMIT`:** it must be added to this version's "In-App Purchases and
     Subscriptions" section before Submit. An app's first IAP always goes with a new
     version.
   - **`MISSING_METADATA`:** it cannot be submitted, and in sandbox it typically does not
     load. Name what is missing: the App Review screenshot (most common), a localization
     (display name and description), the price, or the offer setup. Rate it review-risk;
     this is often the top finding.
   - **`DEVELOPER_ACTION_NEEDED` / `REJECTED`:** read the product's review note in App Store
     Connect and fix it first.
4. Trace what the reviewer sees when a product does not load:
   - Does the paywall drop the plan silently?
   - Does it show an empty or "unavailable" state?
   - Does the default selection point at the missing product?
   - Paywall designs chosen by a server or panel can land on a plan the reviewer cannot buy.

   Say which designs are affected.

**Fix, in order:**

1. Complete the metadata. The review screenshot shows the product on the paywall.
2. Add the products to the version.
3. Keep only fully approved or submitted products in the paywalls the reviewer can reach,
   or explain the rest in the notes.

## 2. Paywall disclosure (3.1.2(c))

**Live text:** "Before asking a customer to subscribe, you should clearly describe what the
user will get for the price." It adds: "Ensure you clearly communicate the requirements
described in Schedule 2 of the Apple Developer Program License Agreement." Schedule 2 is
behind sign-in; Apple's public page is https://developer.apple.com/app-store/subscriptions/.

**What to check on every paywall the build can show** (each server-selected design or
experiment variant counts):

- **Title and value:** what the subscription unlocks.
- **Length and price:** the length of each plan and its price per period.
- **Billed amount:** the amount actually charged is the most prominent price. A computed
  "per week" or "per day" figure, or a "free" badge, that outshines the billed amount is a
  recurring 3.1.2 rejection pattern.
- **Trials:** say how long the trial lasts, what is charged afterwards and when, and how to
  cancel before being charged.
- **Pay up front and pay as you go offers:** say what is paid today, for how long, and the
  price after the offer.
- **Auto-renewal and cancellation:** say that the plan renews automatically and how to
  cancel.
- **Links:** working links to the Terms of Use (EULA) and the Privacy Policy, close to the
  purchase button.
- **Restore:** a restore action on the paywall or in settings (section 4).
- **Match the offer:** the offer text matches the offer configured in App Store Connect
  (duration, price, eligibility). A paywall promising an offer the product does not have
  is "promoting a false price" (2.3.1(a)).
- **Dismissal:** hard paywalls are allowed. A close control that is hidden, delayed or
  disguised on a paywall that is meant to be dismissible draws reviewer complaints.
  Judgment-call.

**Rating:**

- **review-risk:** a missing element, or a billed amount that is less prominent than a
  computed figure.
- **judgment-call:** layout prominence calls.

## 3. Subscription metadata: description, EULA, privacy URL

- **Description (2.3.2).** It must say whether featured items or features require
  additional purchases. Live text: "make sure your app description, screenshots, and
  previews clearly indicate whether any featured items, levels, subscriptions, etc.
  require additional purchases."
  - Name which features are in the subscription and which are free.
  - "Optional subscription" next to a feature list that is mostly paid is weak.
- **Terms of Use link.** Apple's 3.1.2 rejection messages ask for "a functional link to the
  Terms of Use (EULA)" in the App Store metadata. Paraphrased (not verified this run), the
  two accepted forms are:
  - With Apple's standard EULA: link it in the description
    (https://www.apple.com/legal/internet-services/itunes/dev/stdeula/).
  - With a custom EULA: add it in App Store Connect's License Agreement field.

  Many apps also end the description with a "Terms of Use: URL" and "Privacy Policy: URL"
  pair. That is cheap insurance and easy to verify. Check that the links answer.
- **Privacy policy URL** set for every locale (5.1.1(i)).

## 4. Restore and digital goods (3.1.1)

**Restore.** Live text: "you should make sure you have a restore mechanism for any
restorable in-app purchases". Auto-renewable subscriptions and non-consumables need a
visible restore action, in the paywall or in settings, that calls `AppStore.sync()` or the
SDK's restore.

**Digital goods outside IAP.** Live text: "If you want to unlock features or functionality
within your app … you must use in-app purchase." The following are the classic hard
rejection:

- payment SDKs (Stripe, PayPal, Braintree) or checkout URLs that unlock digital content
- license keys, QR codes or crypto unlocks

Physical goods and services used outside the app may use other payment methods (3.1.3(e)).

## 5. Alternative unlock paths and remote access modes

Rewarded ads, a number of free uses, and free-on-first-install are common next to a
subscription. They are allowed. Check:

- **Disclosure.** Do the review notes describe them in plain words? Examples: "free users
  can unlock one result by watching a rewarded ad"; "the first generation is free".
  2.3.1(a) wants new functionality "described with specificity".
- **Stability.** Is the access mode decided remotely, and could it change after approval?
  Switching from free uses to a hard paywall, or from IAP to web checkout, right after
  review reads as the post-review change 2.5.19 targets. That is an inference; label it.
  Recommend keeping the reviewed mode, or describing the possible modes in the notes.
- **Ads.** Ads (rewarded, interstitial, app-open) mean the age-rating questionnaire's
  "Advertising" capability is Yes, and ad content must suit the app's rating.

## 6. Other rules

- **3.1.2(a), permissible uses:** the subscription must provide ongoing value; periods of at
  least seven days; available across the user's devices.
- **3.1.2(b), upgrades and downgrades:** put variants of the same service in one
  subscription group, with levels, so users cannot buy two variations of the same thing.
- **Loot boxes (3.1.1):** show the odds for each item type before purchase.
- **External purchase links (3.1.1(a)):** the rules differ by storefront and change often.
  Read the live 3.1.1(a) text during the run and do not rely on any cached summary. For
  the EU, also read https://developer.apple.com/support/dma-and-apps-in-the-eu/.
- **Non-subscription trials:** use a "XX-day Trial" non-consumable at price 0, with the
  disclosures that 3.1.1 lists.
