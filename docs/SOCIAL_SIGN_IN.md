# Google and Apple sign-in: setup guide

Social sign-in is built but **switched off**. Nothing changes in any deployment
until every step below has been done for a provider and the switches are set.
Do this once the app has its own domain served over HTTPS. Apple will not
work without one (see [Apple needs a real domain](#apple-needs-a-real-domain-with-https)).

## What exists

| Piece | Where |
|---|---|
| `POST /auth/social`: sign in or sign up with a Google/Apple ID token | `backend/app/api/router.py` |
| `POST /auth/social/nonce`: single-use, short-lived nonce for the next sign-in | same |
| `POST /auth/social/link`: attach Google/Apple to the signed-in account; converts a guest in place, keeping all progress; other accounts confirm their password | same |
| `POST /auth/social/unlink`: remove a linked sign-in (never the last way in) | same |
| ID-token verification against the provider's JWKS (signature, `iss`, `aud`, `azp`, `exp`, `iat`, `nonce`) | `backend/app/services/social_auth.py` |
| `user_identities` table (migration 0023) + one identity per provider per account (0033) + issued nonces (0034) | `backend/alembic/versions/` |
| "Continue with Google" / "Continue with Apple" on Log in and Register, a "Keep your progress" card for guests on Profile, and a "Sign-in methods" card (connect/disconnect, with the current password) for other accounts | `frontend/src/components/SocialSignInButtons.tsx`, `frontend/src/components/ConnectedSignIns.tsx`, `frontend/src/lib/socialSignIn.ts` |

API details are in `docs/CONTRACT.md` (Auth section).

How a sign-in works (web):

1. The browser asks the backend for a nonce (valid 10 minutes, usable once)
   and gives the provider its SHA-256 digest.
2. The provider's popup returns a signed ID token (a JWT) that contains that digest.
3. The browser sends the token and the raw nonce to the backend.
4. The backend fetches the provider's public keys (JWKS, cached 5 minutes,
   refetched at most once a minute for an unknown key id) and checks the
   signature, issuer, audience (must be one of your client IDs), authorized
   party, expiry, issue time and nonce, then uses the nonce up. A replayed
   request is refused. If the provider's keys cannot be fetched the answer
   is 503, not "invalid token".
5. The backend finds or creates the account and returns the usual
   access + refresh token pair.

Account rules:

- An existing identity → that account.
- Otherwise, an email the provider vouches for that matches an existing
  account WITHOUT a password → the identity is linked to that account.
  Apple's verified emails (including private-relay addresses) count. Google's
  count only for gmail.com/googlemail.com or when the token's `hd`
  (Workspace domain) matches, which is Google's own guidance.
- If that account has a password, nothing is linked: the answer is
  `409 account_exists` ("log in with your password, then connect from your
  profile"). Registration does not verify email addresses, so otherwise
  anyone could register a victim's address first and later share the
  victim's account once the victim continues with Google or Apple. The
  same rule covers an Apple address that has changed hands since the Apple
  ID was created.
- Otherwise a new passwordless account is created.
- Accounts are never merged. If a guest tries to link an identity or email
  that belongs to another account, they get a clear 409 instead.
- Linking from inside an account needs the current password unless the
  account is a guest. A passwordless account cannot add another sign-in from
  its profile; signing in with the second provider under the same vouched-for
  email links it instead.

## Switches and settings

All values come from environment variables. Leave them empty to keep a
provider off.

**Backend** (`backend/.env`; documented in `backend/.env.example`)

| Variable | Value |
|---|---|
| `SOCIAL_SIGN_IN_ENABLED` | `true` to turn the endpoints on (default `false` → `503 social_login_unavailable`) |
| `GOOGLE_OAUTH_CLIENT_IDS` | Comma-separated Google client IDs whose tokens are accepted: the web client, plus any iOS/Android clients later |
| `APPLE_AUDIENCE_IDS` | Comma-separated Apple audiences: the **Services ID** for the web, plus the iOS **bundle ID** later |

**Frontend** (`frontend/.env` at build time; documented in `frontend/.env.example`)

| Variable | Value |
|---|---|
| `VITE_GOOGLE_CLIENT_ID` | The Google **web** client ID. Unset = no Google button |
| `VITE_APPLE_CLIENT_ID` | The Apple **Services ID**, e.g. `com.yourdomain.web`. Unset = no Apple button |
| `VITE_APPLE_REDIRECT_URI` | The Return URL registered for that Services ID, e.g. `https://app.yourdomain.com/auth/apple/callback`. Unset = no Apple button |

These are public identifiers, not secrets. They end up in the JavaScript
bundle anyway. Nothing in the current flow needs a client secret. The Apple
private key described below is only for future features. If you create it,
keep it in the backend's environment only, never in the frontend or the repo.

After changing `backend/.env`, run `docker compose up -d` (a plain `restart`
does not reload `.env`). After changing `frontend/.env`, rebuild the frontend.
Also run `alembic upgrade head` once for migrations 0032 and 0033.

## Google (Google Cloud Console)

1. Go to <https://console.cloud.google.com/> and create a project (or pick one).
2. Open **Google Auth Platform → Branding** (older consoles: **APIs & Services →
   OAuth consent screen**). Fill in the app name, support email, logo
   (optional), home page, privacy policy and terms URLs. Add your domain
   under **Authorized domains**.
3. Under **Audience**, choose **External**. While the app is in *Testing*,
   only listed test users can sign in. Click **Publish app** when you go live.
   With only the `openid`, `email` and `profile` scopes, no Google review is
   needed.
4. Under **Data access**, the default `openid`, `.../auth/userinfo.email` and
   `.../auth/userinfo.profile` scopes are enough.
5. Open **Clients → Create client** (older: **Credentials → Create
   credentials → OAuth client ID**). Choose **Web application**.
   - **Authorized JavaScript origins**: every origin that shows the button,
     with the scheme and no path, e.g. `https://app.yourdomain.com`. For local
     testing also add `http://localhost` and `http://localhost:5173` (Google
     allows plain http only for localhost).
   - **Authorized redirect URIs**: not needed. The app uses Google's popup
     flow, which returns the ID token to the page directly. Add one only if
     you later switch to redirect mode.
6. Copy the client ID (`1234-abc.apps.googleusercontent.com`):
   - `VITE_GOOGLE_CLIENT_ID=<it>` in `frontend/.env`
   - `GOOGLE_OAUTH_CLIENT_IDS=<it>` in `backend/.env`
   - `SOCIAL_SIGN_IN_ENABLED=true` in `backend/.env`
7. Later, for the mobile apps, create an **iOS** and an **Android** client
   (bundle ID / package name + SHA-1) in the same project and append their
   IDs to `GOOGLE_OAUTH_CLIENT_IDS`.

Google works on `http://localhost` for development, so it can be tried before
the domain exists. Apple cannot.

## Apple (Apple Developer)

You need a paid Apple Developer Program membership. Everything happens in
<https://developer.apple.com/account/resources/> (Certificates, Identifiers &
Profiles). Note your **Team ID**, shown at the top right and under Membership.

1. **App ID (primary).** Go to **Identifiers → + → App IDs → App**. Enter a
   description and an explicit bundle ID, e.g. `com.yourdomain.lingosquared`.
   Under Capabilities, tick **Sign In with Apple** and keep "Enable as a
   primary App ID". The iOS app will use this one later.
2. **Services ID (the web client ID).** Go to **Identifiers → + → Services
   IDs**. Enter a description (users see it in the Apple popup, e.g. "Auvel")
   and an identifier, e.g. `com.yourdomain.lingosquared.web`. Save, open it
   again, tick **Sign In with Apple** and click **Configure**:
   - **Primary App ID**: the App ID from step 1.
   - **Domains and Subdomains**: `app.yourdomain.com` (no scheme, no path).
   - **Return URLs**: `https://app.yourdomain.com/auth/apple/callback`. It
     must be `https`, on that domain, and match `VITE_APPLE_REDIRECT_URI`
     exactly. In popup mode the result goes back to the page itself and this
     URL is never actually loaded, but Apple still validates it, so the SPA
     needs no special route.
   - Save, then **Continue → Save** on the Services ID.
3. **Domain verification.** If the portal shows a **Download** button next to
   your domain, download `apple-developer-domain-association.txt`, serve it
   at `https://app.yourdomain.com/.well-known/apple-developer-domain-association.txt`
   (for the nginx `web` service, put it under
   `web_dist/.well-known/`), then click **Verify**. Newer portal versions may
   not ask for this step; if no Download button is shown, there is nothing to
   do.
4. **Key (for later features).** Go to **Keys → +**, tick **Sign In with
   Apple**, **Configure** it with the primary App ID, then register it and
   **download the `.p8` file** (you can only download it once). Note the
   **Key ID**. The current sign-in flow verifies Apple's ID token only and does
   not use the key. The key is needed to exchange authorization codes and to
   **revoke** a user's Apple tokens, which App Store review requires when an
   iOS app with Sign in with Apple deletes an account. Keep the key out of the
   repo. When that feature is built, it will read it from backend env vars
   such as `APPLE_TEAM_ID`, `APPLE_KEY_ID` and `APPLE_PRIVATE_KEY`.
5. **Private email relay (only if you email users).** Users can hide their
   address behind `@privaterelay.appleid.com`. To deliver mail to those
   addresses, register your sending domain/addresses under **Services → Sign
   in with Apple for Email Communication** (SPF must pass).
6. Set:
   - `VITE_APPLE_CLIENT_ID=com.yourdomain.lingosquared.web` and
     `VITE_APPLE_REDIRECT_URI=https://app.yourdomain.com/auth/apple/callback`
     in `frontend/.env`
   - `APPLE_AUDIENCE_IDS=com.yourdomain.lingosquared.web` in `backend/.env`
     (append the iOS bundle ID later)
   - `SOCIAL_SIGN_IN_ENABLED=true` in `backend/.env`

Apple sends the user's name only on the **first** authorization. The web
client passes it along as `display_name`. If that first request fails, the
name is gone, and the account falls back to the email's local part.

### Apple needs a real domain with HTTPS

Apple rejects `localhost`, IP addresses (such as the LAN server
`192.168.4.4`) and plain `http` for both the domain and the Return URL. Apple
sign-in can therefore only be tested once the app is served from a real domain
with a valid certificate. For development before that, a tunnel that gives you
a stable HTTPS hostname works, as long as that hostname is registered in the
Services ID.

## Redirect URLs and origins at a glance

| Provider | Where | Value |
|---|---|---|
| Google | Authorized JavaScript origins | `https://app.yourdomain.com` (+ `http://localhost`, `http://localhost:5173` for dev) |
| Google | Authorized redirect URIs | none (popup flow) |
| Apple | Domains and Subdomains | `app.yourdomain.com` |
| Apple | Return URLs | `https://app.yourdomain.com/auth/apple/callback` (= `VITE_APPLE_REDIRECT_URI`) |
| Backend | `CORS_ORIGINS` | must include `https://app.yourdomain.com` (as for any frontend origin) |

## Going live checklist

1. Deploy the backend with `alembic upgrade head` (0032, 0033). Flags still off.
2. Set the backend env vars for one provider, then `docker compose up -d`.
3. Build the frontend with that provider's `VITE_*` values and deploy it.
4. With a fresh test account, check:
   - "Continue with …" on Log in creates an account and lands on Home.
   - Logging out and signing in again lands in the same account.
   - A guest session → Profile → "Keep your progress" → same XP and streak
     afterwards, and the guest warning is gone.
   - Signing in on a second browser lands in that converted account.
5. Repeat for the other provider.

To switch a provider off again, empty its `VITE_*` value (the button
disappears) and/or set `SOCIAL_SIGN_IN_ENABLED=false` (the backend refuses
with 503). Existing accounts keep their data, and password login is
unaffected.

## Not done yet

- Mobile app (Expo): native Google/Apple SDKs, which would post their ID
  tokens to the same endpoints with the bundle ID / Android client ID added
  to the allowlists. An iOS app that offers Google sign-in must also offer
  Sign in with Apple (App Store guideline 4.8).
- Apple token revocation on account deletion (needs the key from step 4).
- A "set a password" flow for passwordless accounts.
- Email verification at registration. Until it exists, password accounts
  are never linked by email automatically.
- An Apple address that is not a private-relay address can still be linked
  automatically into a passwordless account with the same address (for
  example one created through Google Workspace). Closing that would mean
  trusting only private-relay addresses from Apple.
- fa/prs translations of the new strings (they fall back to English).
