# App Store Connect state: what to read and how

App Review judges the binary **and** what App Store Connect holds: the listing,
products, privacy answers, review notes and availability. Read all of it before judging.
Read only: no writes during the audit.

## Fields to collect

| Area | Fields | Feeds |
|---|---|---|
| App | name, bundle ID, primary locale, content rights declaration | 2.3.7, 5.2 |
| Version being submitted | version string, state, attached build (number and processing state), release type | upload, 2.1 |
| Builds | last uploads per version: build number, processing state, expired | build-number collisions, which build ships |
| Localizations (per locale) | description, keywords, promotional text, What's New, support URL, marketing URL | 2.3.x, 2.3.12, 3.1.2 metadata links |
| App info (per locale) | name, subtitle, privacy policy URL, privacy choices URL | 2.3.7, 5.1.1(i) |
| Age rating | the full questionnaire answers and resulting rating | 2.3.6 |
| Category | primary and secondary | 2.3.5 |
| Review information | notes, demo account required, demo name and password present (never the password itself), contact details complete, attachments | 2.1(a), 2.3.1(a) |
| Subscriptions and IAP | product ID, type, state, period, group level, localizations, price set, App Review screenshot present, review note, introductory offers, whether attached to this version | 2.1(b), 3.1.2 |
| License agreement | standard Apple EULA or custom EULA text | 3.1.2 metadata links |
| App Privacy | every data-type row (category, purpose, linked / not linked / tracking) and publish state | 5.1.2(i), 2.3 |
| Availability | territories where the app is sold, new-territory setting | Section 5 introduction |
| Creative assets | product page header and search-result assets, if any | 2.3.14 |
| Screenshots and previews | per device set: count and order, previews present | 2.3.3, 2.3.4 |

## Ways to read it (in order of preference)

1. **The App Store Connect API through a tool the user already has.** Examples are the
   `asc` CLI, fastlane (`fastlane deliver download_metadata` writes the listing as files) or
   their own scripts with an API key. Use read commands only. Never ask the user to paste a
   private key or give you their credentials. The public API has no App Privacy endpoint;
   get those answers another way.
2. **A browser session where the user is signed in to App Store Connect.**
   - Paste `scripts/asc_snapshot.js` into the page with a "run JavaScript" action, then:
     ```js
     const s = await ascSnapshot('<numeric Apple ID of the app>');
     JSON.stringify(s.subscriptions)   // print one part at a time; tools truncate long output
     ```
   - The script calls the same-origin API the web UI uses (`/iris/v1`, `/iris/v2`). Its
     resource names mirror the public API. It is unofficial and may change.
   - It sends GET requests only. It returns no passwords and strips query strings from
     URLs, because some tools refuse to print URLs that carry query strings.
   - If a part fails, read that page in the UI instead (`get_page_text` or a screenshot).
3. **Ask the user** to paste exactly the fields you could not read. If they decline, mark
   those checks "not audited".

The app's numeric Apple ID is under App Store Connect > App Information > Apple ID. It is
also the `id` in `apps.apple.com/.../id<number>`.

## Reading the states

**Version states** (`appStoreState` or `appVersionState`):

- Editable: `PREPARE_FOR_SUBMISSION`, `DEVELOPER_REJECTED`, `REJECTED`, `METADATA_REJECTED`.
- In flight: `WAITING_FOR_REVIEW`, `IN_REVIEW`, `PENDING_DEVELOPER_RELEASE`.
- Live: `READY_FOR_SALE` or `READY_FOR_DISTRIBUTION`.

**Build `processingState`:** `PROCESSING`, `VALID`, `INVALID`, `FAILED`.

- `VALID` means upload validation passed.
- An `INVALID` build is the validator-certain evidence for an upload blocker.
- A build number already used for a version cannot be uploaded again.

**Subscription and IAP `state`:**

| State | What it means for the submission |
|---|---|
| `MISSING_METADATA` | Cannot be submitted. Usually the App Review screenshot, a localization or the price is missing. In sandbox it typically does not load, so a paywall that sells it shows nothing for that plan. |
| `READY_TO_SUBMIT` | Complete. It still has to be added to the version's "In-App Purchases and Subscriptions" section to be reviewed with this submission. An app's first IAP must go with a new app version. |
| `WAITING_FOR_REVIEW`, `IN_REVIEW` | Under review. |
| `DEVELOPER_ACTION_NEEDED`, `REJECTED` | Needs changes before review. |
| `APPROVED` | Can be sold once the app version that uses it is live. |
| `REMOVED_FROM_SALE`, `DEVELOPER_REMOVED_FROM_SALE` | No longer for sale. |

**App Privacy rows:** each row has a data category, a purpose and a protection.

- Categories and purposes use upper snake case. Categories observed:
  `PHOTOS_OR_VIDEOS`, `CRASH_DATA`, `PURCHASE_HISTORY`, `SENSITIVE_INFO`. Purposes
  observed: `ANALYTICS`, `APP_FUNCTIONALITY`.
- Protection is `DATA_LINKED_TO_YOU`, `DATA_NOT_LINKED_TO_YOU` or `DATA_USED_TO_TRACK_YOU`.
- A row with an empty purpose and `DATA_USED_TO_TRACK_YOU` declares that this category is
  used for tracking.
- No rows at all with a published state means "Data Not Collected". Check that against the
  SDK inventory.

**Age rating:**

- The 2025 questionnaire covers content, capabilities and in-app controls. Capabilities
  include messaging and chat, user-generated content, advertising, unrestricted web access
  and age assurance.
- Social media questions were added on 2026-07-09.
- From 2026-11-16, updates must also answer two new descriptors: Shared Location, and
  Dating and Relationships. All apps must answer them by 2027-01-12.
- See `recent-changes.md`.

## Comparing drafts with what is live

Repositories often hold the intended metadata: `fastlane/metadata/<locale>/*.txt`, markdown
metadata files, release-notes files. For each field compare the draft with App Store
Connect. Report:

- **A draft that never reached App Store Connect**, for example a new description written
  for this version while the live one is still the previous version's. Judge the live text
  (that is what gets reviewed) and use the draft as the fix.
- **Locales that exist in App Store Connect but have no draft**, and the reverse.
- **Live text that contradicts the current app.** Examples: features removed, a different
  pricing model, "3D model" claims for a 2D effect.
