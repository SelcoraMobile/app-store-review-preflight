# app-store-review-preflight

An Agent Skill that checks an iOS or iPadOS app for App Store review problems before you
submit it. It reads three things:

- **Your Xcode project:** code, build settings, Info.plist, entitlements, privacy
  manifests, SDKs.
- **Your App Store Connect state:** listing, subscriptions, App Privacy answers, builds,
  availability.
- **The live App Review Guidelines.**

It then tells you what is likely to be rejected or refused at upload. Every finding has a
guideline number, evidence (file and line, or App Store Connect field), a concrete fix and
an honest confidence level.

Made by [Selcora Mobile](https://github.com/selcoramobile). Built on the open
[Agent Skills](https://agentskills.io) format, so it works in Claude Code and other agents
that read `SKILL.md` skills.

## Why another review checker

It started from [dabodamjan/app-store-rejection-checker](https://github.com/dabodamjan/app-store-rejection-checker)
(MIT). We used that skill on a real submission, compared every claim with Apple's live
pages, and rebuilt it around what we found. In short:

- **It reads App Store Connect, not only the repo.**
  - Repo-only audits miss two of the most common real problems: subscriptions the paywall
    sells but App Store Connect cannot submit (`MISSING_METADATA`), and App Privacy answers
    that leave out the SDKs in the binary.
  - Store descriptions that never received the update you wrote also slip through.
  - The skill reads these through the App Store Connect API, a signed-in browser session
    (GET-only snippet) or pasted fields.
- **Deterministic sources.**
  - Bundled scripts download the whole guidelines page, so quotes are exact and the last
    sections are never cut off.
  - They read Apple's client-rendered documentation through its DocC JSON instead of
    giving up on an empty page.
  - They verify App Store IDs with Apple's lookup API.
- **Corrected facts.**
  - The upstream example `C56D.1` is a UserDefaults reason that only third-party SDKs may
    declare; apps use `CA92.1`.
  - Apple's published review time is "at least 50% … in less than 24 hours and 90% in less
    than 48 hours", not 90% in 24 hours.
  - An app's privacy manifest does not need `NSPrivacyTracking: true` because an ad SDK
    with its own manifest tracks.
- **New checks.**
  - Product readiness (2.1(b)), and the App Privacy answers compared with an SDK data map.
  - ATT consistency in both directions, and face data (5.1.2(vi)).
  - Hardcoded App Store IDs that point at another app, and links that do not answer.
  - The iPad multitasking orientation trap where the Info.plist file overrides a build
    setting.
  - Unused background modes, SDK and deployment-target minimums, and build-number
    collisions with uploads.
  - Server-driven variants that the review notes should mention.
  - Calibrated 1.2 rules for AI generators, prediction features, and local-law questions
    for the countries you sell in.
- **Safer by default.**
  - The skill pre-approves only read tools (no blanket shell access).
  - Scripts are read-only and stdlib-only, and their network access is limited.
  - Fixes in App Store Connect happen only after the report, one at a time, with your
    go-ahead.

## Install

**Claude Code, as a plugin:**

```
/plugin marketplace add selcoramobile/app-store-review-preflight
/plugin install app-store-review-preflight@selcoramobile
```

**Claude Code, as a plain skill:**

```bash
git clone https://github.com/selcoramobile/app-store-review-preflight.git
mkdir -p ~/.claude/skills
cp -R app-store-review-preflight/skills/app-store-review-preflight ~/.claude/skills/
```

Use `<repo>/.claude/skills/` instead to install it for one project only.

**Other agents** (Cursor, Codex CLI, Gemini CLI and others that support Agent Skills): copy
`skills/app-store-review-preflight/` to the folder your agent reads skills from.

## Use

Inside your app's repository:

```
Run an App Store review preflight on this app.
```

You can also invoke `/app-store-review-preflight`. Give it the app's Apple ID if you want
App Store Connect checked through a signed-in browser.

The skill works through ten steps:

1. Live sources
2. Repository inventory
3. App Store Connect state
4. Upload blockers
5. Static checks
6. Privacy and tracking
7. Payments
8. Semantic review
9. Report
10. Offer fixes

The report is saved as `APP_REVIEW_PREFLIGHT.md`, in the language you use, with a findings
table and a submission checklist.

## What it checks

| Area | Examples |
|---|---|
| Upload blockers | build number already uploaded, iPad multitasking orientations (and Info.plist-vs-build-setting conflicts), purpose strings, privacy manifest reasons, SDK manifests and signatures, UIWebView, Xcode and SDK minimums, extension version mismatch |
| Completeness (2.1) | products the paywall sells but App Store Connect cannot submit, broken links, wrong App Store IDs, demo access, placeholder and test ads |
| Metadata (2.3) | description and subtitle claims against the code, IAP disclosure, screenshots (more than half in use), previews, What's New, creative assets, repo drafts that never reached App Store Connect |
| Hidden features (2.5.19) | reviewer or sandbox detection, debug hooks that ship in Release, features shipped dark behind a remote switch, obfuscation, server-driven variants to document |
| Payments (3.1) | product states, paywall disclosure (billed amount, trial and offer terms, links), restore, EULA link in metadata, rewarded ads and free uses, external links (live text) |
| Design (4.x) | web wrappers, template apps, saturated categories, iPad layout, marketing push without opt-in, login services |
| Privacy (5.1) | App Privacy answers against SDKs, ATT consistency, pre-permission screens, analytics consent, third-party AI disclosure and consent, face data, privacy policy link and content, account deletion |
| Special categories | AI generators (1.2), face and body images, prediction features, pregnancy, health, kids, gambling, VPN, crypto, finance, dating, local law where the app is sold |

## Scripts

All scripts are Python 3 standard library only, read-only, and run as `python3 -I <script>`.

| Script | What it does |
|---|---|
| `fetch_apple.py` | Fetches the whole guidelines page, Apple Developer News since a date, `developer.apple.com/documentation` pages through their DocC JSON, other Apple pages, and App Store ID lookups. HTTPS to Apple hosts only. |
| `guideline_sections.py` | Lists, prints or greps guideline sections by number from the fetched text. |
| `inventory.py` | Inventories the repository: targets, merged release settings, generated Info.plist keys, purpose-string localizations, entitlements, privacy manifests, packages and pods, SDK detection, source signals, App Store IDs, hosts, git state, and mechanical flags. |
| `check_links.py` | Checks that URLs answer and that App Store IDs belong to the app's bundle ID. Skips private hosts. Its `--text` mode prints a page as text, for privacy policies. |
| `asc_snapshot.js` | GET-only App Store Connect snapshot for a signed-in browser tab: versions, builds, localizations, review info, age rating, subscriptions, App Privacy answers, availability, EULA. Never returns passwords. |

The skill's `allowed-tools` line pre-approves only Read, Grep, Glob, WebFetch and
WebSearch. Your agent asks before running the scripts. To skip those prompts, allow
`python3 -I <path to the skill>/scripts/` commands in your agent's permission settings.

## Honest limits

- **Runtime is not checked.** It cannot see crashes, live purchases, what a remote config
  or paywall panel serves on review day, or links behind a login. The report lists those
  under "Not checked".
- **Findings are risk assessments.** App Review is done by people, and no tool can
  guarantee approval. This one never estimates approval odds.
- **Laws are not verified.** Local-law notes are questions to check with counsel, labeled
  as unverified unless a primary source was read during the run.
- **Not affiliated with Apple.** App Store, App Store Connect, Xcode and related marks
  belong to Apple Inc.

## Development

```bash
python3 -m unittest discover -s tests -v   # offline tests for the scripts
claude plugin validate --strict .          # plugin and marketplace manifests
```

**Reference files** carry the date they were last checked against Apple's live pages.

**To release:**

1. Re-verify `references/recent-changes.md`.
2. Bump the version in `SKILL.md`, `.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json` and `CHANGELOG.md`.
3. Tag `v<version>`.

Issues and pull requests are welcome. Please include the Apple page or rejection text that
backs a new check.

## Credits and license

MIT, see [LICENSE](LICENSE). Portions are derived from
[app-store-rejection-checker](https://github.com/dabodamjan/app-store-rejection-checker) by
Damjan Dabo (MIT); its copyright notice is kept in the license.
