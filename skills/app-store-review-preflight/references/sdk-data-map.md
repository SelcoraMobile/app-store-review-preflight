# SDK to App Privacy map

What common SDKs typically collect, and therefore what the App Privacy answers usually need.
This is a starting map, not a verdict. Collection depends on SDK version, configuration and
consent settings.

- **Confirm with the vendor's disclosure page** before telling the user to add or remove a
  row.
- **Name the vendor page in the finding** when you rely on it.
- **"Typical" means not verified this run** unless you fetched the page.

Purposes use Apple's names: Third-Party Advertising, Developer's Advertising or Marketing,
Analytics, Product Personalization, App Functionality, Other Purposes.

## Vendor disclosure pages (reachable on 2026-11-05)

| SDK | Page |
|---|---|
| Google Mobile Ads (AdMob) | https://developers.google.com/admob/ios/privacy/data-disclosure |
| Firebase (Analytics, Crashlytics, Remote Config, Messaging…) | https://firebase.google.com/docs/ios/app-store-data-collection |
| RevenueCat | https://www.revenuecat.com/docs/platform-resources/apple-platform-resources/apple-app-privacy |
| Adapty | https://adapty.io/docs/apple-app-privacy |
| Sentry | https://docs.sentry.io/platforms/apple/data-management/apple-privacy-manifest/ |

To read a vendor page, run `python3 -I <skill>/scripts/check_links.py --text <url>` (works
for any public page) or use a fetch tool. Cite what you read. For other vendors, search
their documentation for "App Store privacy" or "privacy nutrition label". Do not cite a URL
you have not opened.

## Typical collection

| SDK (inventory name) | Data types usually involved | Usual purposes | Tracking? |
|---|---|---|---|
| Google Mobile Ads (AdMob) | Device ID (advertising identifier or other app- or developer-bounded IDs), Advertising Data, Product Interaction, Coarse Location (IP), Crash Data, Performance Data | Third-Party Advertising, Analytics | Yes when the IDFA is used for personalized ads (needs ATT). Google's page (fetched 2026-11-05) lists IP address, crash logs, performance data, device ID, advertising data and user product interactions |
| Google UMP (consent) | Consent state stored on device | App Functionality | No |
| Firebase Analytics | Device ID (app instance ID; IDFA only with the IDFA-support product or AdSupport and ATT authorization), Product Interaction, Other Usage Data, Coarse Location | Analytics (plus advertising if linked to Google Ads) | When the IDFA is collected or the data is linked for ads |
| Firebase Analytics IDFA support | Adds IDFA collection to Analytics | as above | Yes, with ATT |
| Firebase Crashlytics | Crash Data, Device ID (installation ID), Other Diagnostic Data | App Functionality, Analytics | No |
| Firebase Remote Config | Device ID (installation ID) | App Functionality | No |
| Firebase Cloud Messaging, OneSignal | Device ID (push token, SDK user or device ID), Product Interaction (opens); OneSignal can also collect email, phone and location when those features are used | App Functionality, Analytics, Developer's Advertising (marketing pushes) | No by default |
| RevenueCat, Adapty, Qonversion, Apphud, Superwall | Purchase History, User ID / Device ID, Product Interaction (paywall events) | App Functionality, Analytics | No by default; attribution integrations can change that |
| AppsFlyer, Adjust, Branch, Singular, Kochava, TikTok Business SDK, Meta (Facebook) SDK | Device ID (IDFA/IDFV), Advertising Data, Product Interaction, Purchase History, Coarse Location | Third-Party Advertising, Analytics | Yes when the IDFA or cross-app matching is used |
| Mixpanel, Amplitude, PostHog, Segment, TelemetryDeck | Product Interaction, User ID / Device ID, Coarse Location (IP), Other Usage Data | Analytics (Product Personalization if used for it) | No unless forwarded to ad networks |
| Sentry, Bugsnag, Datadog | Crash Data, Performance Data, Other Diagnostic Data, Device ID | App Functionality, Analytics | No |
| Braze, Intercom | Name, Email, User ID, Product Interaction, Customer Support (Intercom) | App Functionality, Developer's Advertising or Marketing | No by default |
| AppLovin, ironSource/LevelPlay, Unity Ads, Vungle/Liftoff, Meta Audience Network, Pangle, Chartboost, InMobi | Device ID, Advertising Data, Product Interaction, Coarse Location, Diagnostics | Third-Party Advertising, Analytics | Yes when personalized |
| Google Sign-In, Facebook Login, Sign in with Apple | Name, Email, User ID | App Functionality | No by default |

## Your own backend counts too

What the app's server receives and keeps is collection, whoever wrote the SDK. List it from
the networking code and the backend:

- **User content:** photos, audio, free text → Photos or Videos, Audio Data, Other User
  Content.
- **Profile fields:** name, due date, preferences → Name, Health, Other Data Types as fits.
- **Identifiers:** device or install IDs sent as headers → Device ID; accounts → User ID.
- **Server logs** that keep IP addresses → Coarse Location if kept and used.
- **Third-party AI providers** behind the server: the data is shared with them. The App
  Privacy answers describe collection, and 5.1.2(i) requires disclosure and consent for
  the sharing.

## Reading the result

- **The answers must cover the union of all rows above** that apply to the binary. A
  "Data Not Collected" listing is only possible when none apply.
- **Tracking is one switch for the whole data type in App Store Connect.** If any SDK
  tracks with Device ID, Device ID is "used to track you".
- **Ad SDKs and the age rating:** they also mean the age-rating questionnaire's
  "Advertising" capability is Yes. Ads must suit the app's rating.
