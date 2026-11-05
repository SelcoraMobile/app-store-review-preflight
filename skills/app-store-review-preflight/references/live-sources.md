# Live sources: what to fetch, how, and how to cite it

The audit quotes primary sources fetched during the run. This file lists them and says how
to read each one reliably. URLs were checked on 2026-11-05.

## Fetch methods

| Source type | Method |
|---|---|
| App Review Guidelines | `fetch_apple.py guidelines --out FILE`, then `guideline_sections.py FILE show|grep|list` |
| Apple Developer News | `fetch_apple.py news --since YYYY-MM-DD [--full]` (RSS: `https://developer.apple.com/news/rss/news.rss`) |
| `developer.apple.com/documentation/...` pages | `fetch_apple.py doc <path or URL>`. These pages render client-side; the script reads the DocC JSON at `https://developer.apple.com/tutorials/data/documentation/<path>.json`, which is what the page itself loads |
| Other Apple pages (support, help, app-store) | `fetch_apple.py page <URL> --out FILE` |
| App Store IDs | `fetch_apple.py lookup <id> [--country cc]` (iTunes Lookup API) or `check_links.py --appstore-id` |

Why not a summarizing fetch tool: such tools pass the page through a model and may return a
summary, paraphrase or a truncated tail. The guidelines page is long (about 100 KB of
text); its last sections (5.x) are the first to get lost. If you must use one, ask for
verbatim text section by section and record in the verification note that quotes may be
paraphrased.

## Primary sources

**Rules and requirements**

- App Review Guidelines: https://developer.apple.com/app-store/review/guidelines/ ("Last
  Updated" line at the bottom).
- Upcoming requirements (SDK minimums, deadlines): https://developer.apple.com/news/upcoming-requirements/
- App Review overview (published review-time figure): https://developer.apple.com/distribute/app-review/
- Completing a review submission (review notes, demo accounts, regional differences):
  https://developer.apple.com/help/app-review/before-submitting-for-review/complete-review

**Privacy**

- App Privacy details (label definitions): https://developer.apple.com/app-store/app-privacy-details/
- User privacy and data use (ATT): https://developer.apple.com/app-store/user-privacy-and-data-use/
- Required-reason API codes (DocC):
  `bundleresources/app-privacy-configuration/nsprivacyaccessedapitypes/nsprivacyaccessedapitypereasons`
- Third-party SDK requirements (manifests, signatures, the SDK list):
  https://developer.apple.com/support/third-party-SDK-requirements/
- Account deletion: https://developer.apple.com/support/offering-account-deletion-in-your-app/

**Payments and EU terms**

- Auto-renewable subscriptions guidance: https://developer.apple.com/app-store/subscriptions/
- EU DMA terms: https://developer.apple.com/support/dma-and-apps-in-the-eu/

**Store listing and ratings**

- Age ratings reference: https://developer.apple.com/help/app-store-connect/reference/age-ratings/
- Screenshot specifications: https://developer.apple.com/help/app-store-connect/reference/screenshot-specifications/
- App preview specifications: https://developer.apple.com/help/app-store-connect/reference/app-preview-specifications/
- Creative asset rules: https://developer.apple.com/app-store/asset-best-practices/

**Transparency data**

- App Store Transparency Report (2025 edition): https://www.apple.com/legal/app-store/transparency/2025/

The Apple Developer Program License Agreement and its Schedule 2 sit behind sign-in.
3.1.2(c) points to Schedule 2 for subscription disclosure. Cite the guideline and
Apple's public subscriptions page, not the agreement text, unless the user supplies it.

## Citing

- Quote the live guideline wording in English, with the section number.
- When a fact comes from a non-guideline Apple page, name the page.
- When a fact could not be confirmed from a primary source during the run, write "not
  verified this run". Use that label for vendor behavior, laws in other countries, and
  Apple process details. Do not drop the point silently, and do not present memory as
  fact.
- Apple forum answers from Apple staff are secondary sources. Label them as such.
