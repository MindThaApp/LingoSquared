import { execSync } from 'node:child_process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { sentryVitePlugin } from '@sentry/vite-plugin'

// Release name shared by the runtime SDK and the source-map upload:
// VITE_SENTRY_RELEASE if set, else the short git sha, else unset.
function resolveRelease(): string | undefined {
  if (process.env.VITE_SENTRY_RELEASE) return process.env.VITE_SENTRY_RELEASE
  try {
    return execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString()
      .trim()
  } catch {
    return undefined
  }
}

// https://vite.dev/config/
export default defineConfig(() => {
  const release = resolveRelease()
  const uploadMaps = Boolean(process.env.SENTRY_AUTH_TOKEN)
  return {
    plugins: [
      react(),
      // Optional step: runs ONLY when SENTRY_AUTH_TOKEN is set, uploading the
      // hidden source maps and then deleting them from dist. Without the token
      // the build is unchanged (maps are still emitted, hidden). See
      // docs/SENTRY.md.
      ...(uploadMaps
        ? [
            sentryVitePlugin({
              org: 'mindtheapp',
              project: 'lingosquared-web',
              url: 'https://de.sentry.io',
              authToken: process.env.SENTRY_AUTH_TOKEN,
              release: { name: release },
              sourcemaps: { filesToDeleteAfterUpload: ['./dist/**/*.map'] },
              telemetry: false,
            }),
          ]
        : []),
    ],
    build: {
      // "hidden": maps are written next to the bundles but no
      // //# sourceMappingURL comment points browsers at them.
      sourcemap: 'hidden' as const,
    },
    define: {
      'import.meta.env.VITE_SENTRY_RELEASE': JSON.stringify(release ?? ''),
    },
  }
})
