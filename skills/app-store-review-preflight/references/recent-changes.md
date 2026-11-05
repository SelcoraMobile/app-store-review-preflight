# Recent changes (verified 2026-11-05)

Rules and requirements that changed in 2024-2026, newest first. Each entry was checked
against Apple's news feed (`fetch_apple.py news`), the live guidelines, or the page named in
the entry, on 2026-11-05.

**During an audit:** run `fetch_apple.py news --since 2026-11-05` and add anything newer to
the verification note.

| Date | Change | Audit impact |
|---|---|---|
| 2026-11-16 (announced 2026-11-02) | Age rating: new **Shared Location** and **Dating and Relationships** descriptors. Required when submitting an update or editing the questionnaire. All apps by **2027-01-12**. Dating and Relationships means a minimum of 18+. Brazil: A16 for Shared Location, A18 for Dating. | Submission checklist: answer both. Flag dating or companion features (1.2, 2.3.6). |
| 2026-11-04 | Retention messages for subscriptions in App Store Connect. | Not a rule. |
| 2026-10-29 | Taiwan storefront commission becomes 26% from 2026-10-31. | Business only. |
| 2026-10-22 | Multiseat subscription purchases (Volume Purchasing, Group Purchases). | Business only. |
| 2026-10-16 | Guidelines revision (Apple news `92th7e5i`, companion post `vvzx6cul`), detailed in the list below. | static-checks.md 9, special-categories.md 1, metadata-and-review-notes.md 1. |
| 2026-10-13 | License agreement update: Group Purchases, Volume Purchasing, tax reporting. | Behind sign-in; not audited. |
| 2026-10-05 | iPhone Duo; creative assets, Asset Library and preview tool in App Store Connect. **iPhone Duo screenshots required for all submissions from April 2027.** | Submission checklist (from April 2027); 2.3.14. |
| 2026-09-16 | **EU ATT:** an alternative ATT system prompt from iOS and iPadOS 27.2. It is the only option in Germany, France, Italy, Poland and Romania. When permission is needed is unchanged. Also subscriptions for iOS 27 (Bundles and Suites; StoreKit 2 encouraged). | privacy-and-tracking.md 2. |
| 2026-09-09 | Minimum deployment target: iOS and iPadOS apps must target iOS 13 or later (upcoming-requirements page). | upload-validation.md. |
| 2026-08-18 | EU business terms: single set of terms; Core Technology Commission (5% on digital sales in apps distributed outside the App Store) replaces the Core Technology Fee; key changes effective 2026-10-01. | Only for apps using EU alternative distribution or external purchase links; read the DMA page live. |
| 2026-08-12 | Republic of Korea age ratings: GRAC official ratings can override; more changes later in 2026. | 2.3.6 for games and entertainment in Korea. |
| 2026-07-09 | Age rating questionnaire adds **social media** questions (redistribute, amplify or interact with UGC through a feed); a Social Media descriptor and Time Allowances category. | 2.3.6. |
| 2026-06-18 (announced 2026-05-21) | Australia: 15+ removed, some apps moved to 16+. Vietnam: region-specific ratings. | 2.3.6. |
| 2026-06-08 | Guidelines and license agreement revision. The live 4.3(b) now includes: "We may remove these apps from the App Store going forward if they are not updated, improved, or do not attract customers." That turns 4.3(b) into a removal ground for shipped apps too. | 4.3 judgment. |
| 2026-04-28 | **SDK minimum:** uploads built with Xcode 26 or later and the iOS 26 / iPadOS 26 SDK (upcoming-requirements page). | upload-validation.md. |
| 2026-02-06 | Random or anonymous chat explicitly subject to 1.2. | special-categories.md 5. |
| 2026-01-31 | Deadline to answer the 2025 age rating questions for every app. | 2.3.6. |
| 2025-11-13 | Guidelines revision, detailed in the list below. | Several. |
| 2025-07-24 | Age ratings overhaul: 4+, 9+, 13+, 16+, 18+; new questions about capabilities, medical and wellness topics, and violent themes; AI assistant and chatbot impact must be considered. | 2.3.6. |
| 2024-05-01 | Privacy manifests: approved reasons for required-reason APIs needed to upload (app code and third-party SDKs); SDK manifests and signatures for listed SDKs. | upload-validation.md, static-checks.md 2. |
| 2024 (January) | 4.8 Login Services no longer requires Sign in with Apple specifically; any login option with the 4.8 privacy properties qualifies. | static-checks.md 4. |
| 2022-06-30 | In-app account deletion required when the app supports account creation (5.1.1(v)). | static-checks.md 6. |

**2026-10-16 guidelines revision, in detail:**

- 1.2 explicitly covers "AI content creation apps" and nonconsensual intimate imagery, and
  adds a remediation-after-notice clause.
- 2.3.14 (new) covers creative assets.
- 2.5.19 (new) covers hidden, dormant and undocumented features, moved from 2.3.1. It names
  obfuscation and account termination.
- 3.1.1(a): links go to "a permitted destination".
- Section 5 introduction: apps facilitating trafficking or child exploitation are removed
  and blocked from alternative distribution.

**2025-11-13 guidelines revision, in detail:**

- 1.2.1(a) creator apps: age restriction based on verified or declared age.
- 2.5.10 removed (empty or test ad banners).
- 3.2.2(ix): loan apps limited to 36% APR, and no full repayment in 60 days or less.
- 4.1(c): no other developer's icon, brand or name without approval.
- 4.7: HTML5 and JavaScript mini apps and games in scope.
- 5.1.2(i) gained the third-party AI sentence: "You must clearly disclose where personal
  data will be shared with third parties, including with third-party AI, and obtain
  explicit permission before doing so." It is present in the live text.

**Still moving:**

- **External purchase links in the US and EU** (3.1.1(a), DMA terms): read the live text
  and https://developer.apple.com/support/dma-and-apps-in-the-eu/ during the run. Never
  rely on a cached summary.
