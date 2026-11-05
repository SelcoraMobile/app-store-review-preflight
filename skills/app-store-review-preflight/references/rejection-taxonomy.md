# Where rejections come from

Use this to decide where to spend attention, not to rank findings. A finding's place in the
report follows its **severity**: what happens if it ships as-is. How often its cluster
appears does not decide it.

## Numbers Apple publishes (verified 2026-11-05)

**App Store Transparency Report, 2025 edition**
(https://www.apple.com/legal/app-store/transparency/2025/). 9,100,620 submissions reviewed;
2,093,244 rejected (about 23%); 387,087 approved after rejection. Rejections by guideline
section (one submission can count in several):

| Section | Rejections | Share of rejected submissions |
|---|---|---|
| Performance (2) | 1,354,418 | 64.7% |
| Legal (5) | 495,673 | 23.7% |
| Design (4) | 415,532 | 19.9% |
| Business (3) | 283,820 | 13.6% |
| Safety (1) | 151,159 | 7.2% |

**App Review page** (https://developer.apple.com/distribute/app-review/): "On average, over
40% of unresolved issues are related to guideline 2.1: App Completeness". That covers
crashes, placeholder content and incomplete information.

Apart from that 2.1 figure, Apple publishes no per-guideline frequencies. Do not repeat
figures like "guideline X causes N% of rejections" or "N% of appeals succeed" from blogs or
forums.

## Clusters, in a sensible default order

This ordering is editorial: Apple's numbers plus recurring developer reports.

1. **Completeness (2.1):** crashes, broken links, placeholder content, demo access,
   products the reviewer cannot buy (2.1(b)), unanswered information requests. The one
   cluster Apple quantifies. The store-side part (products, demo access, notes) is fully
   auditable.
2. **Privacy and data use (5.1.1, 5.1.2):**
   - App Privacy answers against the SDKs
   - ATT consistency
   - third-party AI disclosure
   - purpose strings
   - privacy policy links and content
   - account deletion
3. **Spam and minimum functionality (4.2, 4.3):** template apps, web wrappers, saturated
   categories. Since 2026-06 this is also a removal ground for shipped apps.
4. **Payments (3.1.1, 3.1.2):** digital goods outside IAP, restore, paywall disclosure,
   billed-amount prominence, EULA link in metadata.
5. **Metadata (2.3):** inaccurate claims, screenshots not showing the app in use, missing
   IAP disclosure, subtitle claims, creative assets.
6. **Hidden features (2.5.19):** rare but account-level. Reviewer detection and
   obfuscated feature code go to the top of the report whenever found.
7. **UGC and AI generation (1.2):** moderation set, reporting, nonconsensual imagery;
   expanded on 2025-11-13, 2026-02-06 and 2026-10-16.
8. **Login services (4.8):** social login without a qualifying alternative.
9. **Special categories:** kids, medical, gambling, VPN, crypto, finance. Low volume, but
   near-certain rejections when missed.
