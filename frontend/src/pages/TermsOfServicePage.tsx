import { Link } from "react-router-dom";

// DRAFT legal content, not yet reviewed by a lawyer — Ramin must have this
// reviewed before real (non-beta) users rely on it.
//
// Deliberately NOT i18n'd for the same reason as PrivacyPolicyPage.tsx:
// one authoritative English text until legal review happens.
//
// Honest-to-the-codebase claims worth preserving if this gets rewritten:
// - There is genuinely NO password reset/recovery mechanism (an accepted
//   limitation in CLAUDE.md) — the accounts section tells users so plainly
//   rather than hiding it. Remove that sentence if/when password reset ships.
// - Guest sessions are browser-local and unrecoverable (matches the login
//   page's own guest warning).
// - "Free during beta" and "data may be reset during beta" reflect the
//   actual pre-launch state.
export function TermsOfServicePage() {
  return (
    <div className="card" style={{ maxWidth: 720, margin: "24px auto" }}>
      <h1>Terms of Service</h1>
      <p className="muted">
        Draft for the Lingo² beta — last updated 10 July 2026. These terms may
        be revised during the beta; changes will be posted on this page.
      </p>

      <h2>1. Acceptance</h2>
      <p>
        By creating an account, starting a guest session, or otherwise using
        Lingo², you agree to these terms and to the{" "}
        <Link to="/privacy">Privacy Policy</Link>. If you don't agree, please
        don't use the app.
      </p>

      <h2>2. Beta service</h2>
      <p>
        Lingo² is in beta. Features and lesson content may change, break, or
        be removed without notice, and there is no guarantee of availability.
        In rare cases, beta data (including learning progress) may need to be
        reset. We'll try to avoid that, but you accept the possibility by
        using a beta product.
      </p>

      <h2>3. Your account</h2>
      <p>
        You are responsible for keeping your password safe and for what
        happens under your account. Please be aware that{" "}
        <strong>there is currently no password reset</strong>: if you forget
        your password, you will lose access to the account and its progress.
        Don't reuse a password from another service.
      </p>
      <p>
        Guest sessions exist only in your browser. If you clear your browser
        data or switch devices, a guest session and its progress cannot be
        recovered. Register with an email to keep progress permanently.
      </p>
      <p>
        You can delete your account at any time from your Profile page;
        deletion is immediate and permanent.
      </p>

      <h2>4. Acceptable use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>
          interfere with or disrupt the service, or probe or test its security
          other than through responsible disclosure via the feedback button;
        </li>
        <li>
          scrape, bulk-download, or redistribute the lesson content or expose
          it through another service;
        </li>
        <li>
          submit abusive, unlawful, or deliberately misleading content through
          feedback or issue reports;
        </li>
        <li>
          access or attempt to access other users' accounts or data.
        </li>
      </ul>

      <h2>5. Content and ownership</h2>
      <p>
        The app and its lesson content (including material adapted from
        public-domain language courses) are provided for your personal,
        non-commercial learning use. You may not resell or redistribute them.
      </p>
      <p>
        If you send feedback, suggestions, or issue reports, you allow us to
        use them freely to improve the app, without obligation or
        compensation.
      </p>

      <h2>6. Not professional instruction</h2>
      <p>
        Lessons, translations, grading, and speech transcription are provided
        on a best-effort basis and may contain errors. Lingo² is a learning
        aid, not certified language instruction, and its content should not be
        relied on where an accurate translation matters (legal, medical,
        official documents, and the like).
      </p>

      <h2>7. Price</h2>
      <p>Lingo² is free of charge during the beta.</p>

      <h2>8. Termination</h2>
      <p>
        You may stop using the app or delete your account at any time. We may
        suspend or terminate accounts that violate these terms or harm the
        service or other users.
      </p>

      <h2>9. Disclaimer and limitation of liability</h2>
      <p>
        The service is provided "as is" and "as available," without warranties
        of any kind, express or implied. To the maximum extent permitted by
        law, the operator is not liable for any indirect, incidental, or
        consequential damages, or for loss of data or progress, arising from
        your use of a free beta service.
      </p>

      <h2>10. Changes to these terms</h2>
      <p>
        We may update these terms during the beta. Material changes will be
        posted on this page with an updated date. Continuing to use the app
        after a change means you accept the updated terms.
      </p>

      <h2>11. Contact</h2>
      <p>
        Questions about these terms? Use the in-app "Give feedback" button —
        it works on every page, including when you are logged out.
      </p>

      <p className="muted" style={{ marginTop: 24 }}>
        See also the <Link to="/privacy">Privacy Policy</Link>.
      </p>
    </div>
  );
}
