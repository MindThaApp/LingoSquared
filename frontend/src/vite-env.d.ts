/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  // Social sign-in (docs/SOCIAL_SIGN_IN.md). Unset = button hidden.
  readonly VITE_AUDIO_BASE_URL?: string;
  readonly VITE_PRERENDERED_AUDIO?: string;
  readonly VITE_GOOGLE_CLIENT_ID?: string;
  readonly VITE_APPLE_CLIENT_ID?: string;
  readonly VITE_APPLE_REDIRECT_URI?: string;
  // Sentry crash reporting. Unset DSN = Sentry fully off.
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_SENTRY_RELEASE?: string;
  readonly VITE_SENTRY_ENVIRONMENT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
