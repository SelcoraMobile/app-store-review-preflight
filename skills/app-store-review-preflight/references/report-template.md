# Report template

Write the report in the user's language and keep guideline quotes in English. Save it as
markdown (default `APP_REVIEW_PREFLIGHT.md` in the repository root, or where the user
wants it) and post the summary and the findings table in chat. Then render it as an
interactive page with `scripts/render_report.py` (default `APP_REVIEW_PREFLIGHT.html`, see
SKILL.md Step 9). Do not commit either file unless asked. Do not pad: clean areas get one
line each.

**What the HTML page reads.** Translate headings and labels freely. Keep these parts as
they are, because the page keys on them:

- each finding's `### [guideline] title` heading
- the identifiers `validator-certain`, `review-risk` and `judgment-call`
- the findings table: one row per finding, in the same order or numbered by the `#`
  column, with "Needs new build" as the last column (`yes`/`no` or the same words in the
  report's language)
- checklist items written as `- [ ]` (or `- [x]` when already done)

```markdown
# <App name> <version> (<build>): App Store review preflight

<date> · skill app-store-review-preflight <version> · guidelines "Last Updated: <date>"
Scope: repository <branch @ commit, uncommitted changes y/n>, App Store Connect <read via …
| not audited>. This is a risk assessment, not a guarantee of approval.

## Summary
<Classification in one or two lines: accounts, payments, ads, tracking, AI, UGC, data
types, special categories, platforms audited.>
<Risk picture in two or three sentences.>
Top three: 1. … 2. … 3. …

## Findings
| # | Guideline | Finding | Confidence | Needs new build |
|---|---|---|---|---|
| 1 | 2.1(b) | … | review-risk | no |

### [2.1(b)] <short title>
- **Confidence:** review-risk
- **Evidence:** <file:line / build setting / App Store Connect field and value>
- **Why it matters:** "<live guideline quote>"
- **Fix:** <concrete change>. <New build: yes/no.>

… (ordered by severity, then confidence)

## Previous issues (only when a rejection or an earlier report exists)
| Earlier item | Source | Status now (commit / in uploaded build / App Store Connect / open) |
|---|---|---|

## Submission checklist (App Store Connect, before Submit)
- [ ] Build <version (build)> uploaded, processed and attached to the version
- [ ] Every product the build sells is approved, or ready and added to the version
- [ ] Age rating questionnaire up to date (new descriptors: …)
- [ ] Export compliance answered
- [ ] Review notes updated (…)
- [ ] App Privacy answers published to match the SDKs

## Compliance notes (outside App Review)
- <for example: EU consent for ads and analytics (GDPR, Google's policy): status>

## Clean areas
- <Area>: no findings (<one-line reason>).

## Not checked
- Runtime behavior, crashes, live purchase and restore flows
- What remote configuration or server panels serve on review day: <keys found>
- <anything the tools could not read>

## Verification note
- Guidelines fetched in full on <date> (Last Updated <date>) / via a summarizing tool
  (quotes may be paraphrased; sections not confirmed: …)
- News checked since <date>: <items that apply>; others: <titles, one line>
- Facts not verified this run: <list>
```

## Writing each finding

- **One guideline (or upload validation) per finding.** If two apply, cite both in the
  heading, for example `[2.5.19, 3.1.1]`.
- **Evidence must be checkable:** `Features/Profile/ProfileView.swift:72`,
  `INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad`, "App Store Connect >
  Subscriptions > com.example.yearly: MISSING_METADATA, no review screenshot".
- **Quote, don't paraphrase,** the guideline sentence the finding rests on. Label inference
  as inference ("the text names neither remote configuration nor A/B testing; this reading
  is an inference").
- **The fix is the smallest change that removes the risk.** Say whether it needs a new
  build, an App Store Connect change, or review notes.
- **Never estimate approval odds.**

## Example

```markdown
### [2.1(a)] Rate App and Recommend open a different app
- **Confidence:** review-risk
- **Evidence:** `Constant/Config.swift:9` builds `https://apps.apple.com/app/id6760262151`;
  iTunes Lookup returns "Sentra AI: Dating Coach & Rizz" (bundle com.sentraai.app), not this
  app (com.example.app). Used by Profile > Rate App (`?action=write-review`) and Profile >
  Recommend.
- **Why it matters:** 2.1(a) asks for "fully functional URLs" and rejects binaries that
  "exhibit obvious technical problems"; reviewers tap settings rows.
- **Fix:** use this app's Apple ID (App Store Connect > App Information > Apple ID).
  New build: yes.
```
