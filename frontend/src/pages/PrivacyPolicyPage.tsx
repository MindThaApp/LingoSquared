import { Link } from "react-router-dom";

// DRAFT legal content, not yet reviewed by a lawyer — Ramin must have this
// reviewed before real (non-beta) users rely on it.
//
// Deliberately NOT i18n'd: legal text needs a single authoritative version,
// and machine-translating a draft policy into fa/nl/prs would create
// diverging "official" texts before the English one is even lawyer-reviewed.
// Revisit translation only after legal review of the English original.
//
// Every claim below was verified against the actual codebase on 2026-07-10:
// - DELETE /me (backend/app/api/router.py) hard-deletes the account and
//   cascades learning data — the deletion section reflects that.
// - GET /me/export SHIPPED (backend/app/api/router.py) and is exposed in-app
//   via the Profile page's "Download data" button (ProfilePage.tsx) — the
//   export section reflects the self-serve tool.
// - No analytics/ad-tracking/telemetry code exists anywhere in frontend or
//   backend (grepped for gtag/mixpanel/posthog/segment/etc.) — the "what we
//   don't do" section depends on that staying true.
// - STT: client-side Whisper (audio never leaves the device); server
//   fallback POST /stt/transcribe processes audio in memory and never
//   writes/logs it (backend/app/services/stt.py's own docstring).
export function PrivacyPolicyPage() {
  return (
    <div className="card" style={{ maxWidth: 720, margin: "24px auto" }}>
      <h1>Privacy Policy</h1>
      <p className="muted">
        Draft for the Auvel beta — last updated 10 July 2026. This policy may
        be revised during the beta; changes will be posted on this page.
      </p>

      <h2>Who we are</h2>
      <p>
        Auvel is a language-learning app currently in private beta, operated
        by its developer. There is no company entity behind it yet. You can
        reach the operator any time via the in-app "Give feedback" button
        (available on every page, even when logged out).
      </p>

      <h2>What data we collect</h2>
      <p>
        <strong>Account information.</strong> When you register we store your
        email address, an optional display name, and your password. Passwords
        are stored only in hashed form — we never store or see your actual
        password. Your browser also sends us your time zone (e.g.
        "Europe/Amsterdam") so daily streaks and goals line up with your local
        day; we store that with your account.
      </p>
      <p>
        <strong>Guest sessions.</strong> If you continue as a guest, we store
        only the name you pick — no email, no password. A guest session lives
        in your browser; if you clear your browser data, it cannot be
        recovered.
      </p>
      <p>
        <strong>Learning activity.</strong> We store the answers you submit to
        exercises, practice items, reviews, and checkpoints, along with your
        progress: lessons completed, XP, streaks, achievements, quest
        completions, and the per-word spaced-repetition scheduling data that
        decides when you review vocabulary.
      </p>
      <p>
        <strong>Feedback and issue reports.</strong> When you report a content
        issue or send general feedback, we store the text you write, the page
        or exercise it refers to, and — if you are signed in — which account
        sent it. Feedback also works while logged out, in which case it is not
        tied to an account.
      </p>

      <h2>Microphone audio and speaking exercises</h2>
      <p>
        The microphone is used only in speaking exercises, and only if you
        have chosen microphone mode (there is a per-device toggle to answer by
        keyboard instead). How your recording is handled depends on which
        transcription path your device supports:
      </p>
      <ul>
        <li>
          <strong>On-device (the normal path):</strong> your speech is
          transcribed directly in your browser using a locally-running speech
          recognition model. The raw audio never leaves your device. The first
          time you use this, your browser downloads the model files (a
          one-time download of roughly 150&nbsp;MB) from Hugging Face's
          content delivery network — that is a file download only; no audio or
          personal data is sent there.
        </li>
        <li>
          <strong>Server fallback:</strong> if on-device transcription is not
          available on your device, the recording is sent to our own server
          and transcribed there by self-hosted software. We never send your
          voice to any third-party or cloud speech service. The audio is
          processed in memory, never written to disk or to logs, and is
          discarded as soon as transcription finishes.
        </li>
      </ul>
      <p>
        In both cases, only the resulting <em>text</em> transcript is kept —
        as your answer to that exercise, exactly like a typed answer. No raw
        audio recording is stored anywhere.
      </p>

      <h2>Third-party services</h2>
      <p>
        <strong>Text-to-speech.</strong> To play lesson audio, our server
        sends the text to be spoken (lesson words and sentences, plus your
        chosen voice and speed settings) to Google Cloud Text-to-Speech or
        Microsoft Azure Speech and returns the generated audio to you. Your
        account details and your microphone recordings are never sent to these
        providers.
      </p>
      <p>
        <strong>Speech-model download.</strong> As described above, on-device
        speech recognition fetches its model files from Hugging Face's CDN.
      </p>
      <p>We use no other third-party services that receive any data.</p>

      <h2>What we don't do</h2>
      <ul>
        <li>No advertising and no ad tracking of any kind.</li>
        <li>No analytics or telemetry services.</li>
        <li>We never sell or share your personal data with anyone.</li>
        <li>
          No tracking cookies — in fact, no cookies at all. Your login session
          is kept as a token in your browser's local storage.
        </li>
      </ul>

      <h2>Data stored on your device</h2>
      <p>
        Your browser's local storage holds your login token, a cached copy of
        your profile, and per-device preferences (voice choice, speech speed,
        microphone/keyboard mode, level selections). Clearing your browser
        data removes all of these — and permanently ends any guest session.
      </p>

      <h2>Where feedback goes</h2>
      <p>
        The app can be run on different servers (including self-hosted
        copies). So that bug reports actually reach the developer, feedback
        submitted through the "Give feedback" button may be sent to a central
        feedback server operated by the app's developer, rather than only to
        the server hosting your copy of the app. What is sent is the same
        data described above: your message, the page it was sent from, and
        your account reference if you were signed in.
      </p>

      <h2>Deleting your account</h2>
      <p>
        You can delete your account yourself at any time from your Profile
        page ("Delete account"). Deletion is immediate and permanent: your
        account and your learning data are removed from the server and cannot
        be recovered.
      </p>

      <h2>Getting a copy of your data</h2>
      <p>
        You can download a copy of the data associated with your account at any
        time from your Profile page, using the "Download data" button. If you
        have any trouble, you can also request a copy via the in-app "Give
        feedback" button and the operator will provide it.
      </p>

      <h2>Data retention and security</h2>
      <p>
        We keep your data for as long as your account exists, and delete it
        when you delete your account. Passwords are stored only as hashes.
        Please note this is beta software run on the developer's own
        infrastructure — treat it accordingly and don't reuse a password you
        use anywhere else.
      </p>

      <h2>Children</h2>
      <p>Auvel is not directed at children under 13.</p>

      <h2>Contact</h2>
      <p>
        There is no dedicated privacy contact address yet. For any privacy
        question or request, use the in-app "Give feedback" button — it works
        on every page, including when you are logged out.
      </p>

      <p className="muted" style={{ marginTop: 24 }}>
        See also the <Link to="/terms">Terms of Service</Link>.
      </p>
    </div>
  );
}
