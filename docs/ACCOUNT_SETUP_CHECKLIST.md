# Developer-account setup checklist (Ramin's manual tasks)

These require your identity and payment details — no AI session can or
should do them. Each section ends with exactly what to hand back to the
engineering side. Nothing here blocks current development: the OAuth
backend is being built against env-var placeholders and degrades
gracefully until real IDs exist.

## 1. Apple Developer Program — $99/year

Needed for: publishing the iOS app AND "Sign in with Apple" (which Apple
REQUIRES the moment an iOS app offers any other third-party login, i.e.
our Google sign-in makes Apple sign-in mandatory on iOS).

1. Go to https://developer.apple.com/programs/enroll/ and enroll with
   your personal Apple ID (or create a dedicated one for the business —
   recommended if you may ever sell/transfer the app).
2. Choose Individual (simpler, publishes under your personal name) or
   Organization (needs a D-U-N-S number, publishes under a company name).
   Individual is fine to start; you can migrate later.
3. Pay the $99/year fee, wait for approval (usually <48h).
4. Once approved, in https://developer.apple.com/account → Certificates,
   Identifiers & Profiles → Identifiers:
   - Create an App ID (bundle ID, e.g. `com.raminazizi.lingosquared`)
     with the "Sign in with Apple" capability checked.
   - Create a Services ID (e.g. `com.raminazizi.lingosquared.web`) for
     the WEB sign-in flow, also with Sign in with Apple enabled; its
     return URL will be the app's real web origin (decide together with
     the CORS-origin question — can be updated later).

**Hand back:** the bundle ID and the Services ID (these become the
`APPLE_AUDIENCE_IDS` env value). No secrets involved for basic ID-token
verification.

## 2. Google Play Console — $25 one-time

Needed for: publishing the Android app.

1. Go to https://play.google.com/console/signup with your Google account.
2. Pay the $25 one-time fee, complete identity verification (Google now
   requires ID verification for new personal accounts; can take a few days).
3. No further engineering inputs needed until we upload the first build.

**Hand back:** just confirm the account exists.

## 3. Google OAuth client IDs — free, uses your existing Google Cloud project

Needed for: "Continue with Google" login (web + Android + iOS).

1. In https://console.cloud.google.com (the same project that already has
   the TTS service account), go to APIs & Services → OAuth consent screen:
   - User type External, app name Lingo², your support email, publish it
     (the unverified-app warning is fine while scopes are just
     openid/email/profile).
2. APIs & Services → Credentials → Create Credentials → OAuth client ID:
   - One **Web application** client (authorized JS origins: the dev
     origins `http://localhost:5173`/`5174` now; the real domain later).
   - Later, one **Android** client (needs the Play signing SHA-1) and one
     **iOS** client (needs the bundle ID) — skip until the mobile app is
     real.
3. Copy the Web client ID (ends in `.apps.googleusercontent.com`).

**Hand back:** the Web client ID string (becomes `GOOGLE_OAUTH_CLIENT_IDS`;
Android/iOS client IDs get appended to the same comma-separated var later).
The client SECRET is not needed for ID-token verification — don't share it.

## 4. Where the values go

`backend/.env` (dev) and the live server's `.env` (deploy day):
```
GOOGLE_OAUTH_CLIENT_IDS=<web-client-id>[,<android-id>,<ios-id>]
APPLE_AUDIENCE_IDS=<bundle-id>,<services-id>
```
Until set, `POST /auth/social` returns 503 for that provider and nothing
else in the app is affected.

## 5. Related open decisions (previously flagged, still yours)

- The app's real public origin (needed for live CORS_ORIGINS, the Apple
  Services ID return URL, and Google's authorized origins).
- `VITE_FEEDBACK_API_URL` — the one stable feedback-collector URL.
- Live-server `ADMIN_EMAILS` must be your real email before any beta invite.
