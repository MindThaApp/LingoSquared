# Content-Security-Policy (web app)

Set in `backend/nginx.web.conf` (server level, `always`). Enforcing since the WS5 change of 2026-11-04; before that it was Report-Only. There is no report endpoint, so there are no violation logs: the policy was derived from the built bundle, the source and the old Report-Only policy. Verify with `scripts/csp_check.sh` (headers via the real nginx config in a throwaway container, plus a static check of `index.html`). A real browser pass is still advised before the deploy: open the app with DevTools, start a speaking exercise (downloads the on-device whisper model), play audio, trigger a Sentry test event.

| Directive | Value | Why |
|---|---|---|
| default-src | 'self' | baseline |
| script-src | 'self' 'wasm-unsafe-eval' https://cdn.jsdelivr.net | Vite bundle (no inline scripts); ONNX wasm needs wasm-unsafe-eval; `@huggingface/transformers` loads onnxruntime-web `.mjs` from jsDelivr (default `wasmPaths`, the whisper worker does not override it) |
| style-src | 'self' 'unsafe-inline' | React `style` props |
| img-src | 'self' data: blob: http://*:8010 https: | icons, API media on LAN :8010 |
| media-src | 'self' blob: data: http://*:8010 https: | TTS audio from API, recorded blobs |
| font-src | 'self' data: | fonts are bundled (`public/fonts`) |
| connect-src | 'self' http(s)://*:8010 https://*.ingest.de.sentry.io https://huggingface.co https://*.huggingface.co https://*.hf.co https://cdn.jsdelivr.net data: blob: | API, Sentry EU ingest, model download, ort wasm fetch |
| worker-src / child-src | 'self' blob: | whisper worker, service worker |
| manifest-src | 'self' | PWA manifest |
| object-src 'none', base-uri 'self', form-action 'self', frame-ancestors 'none' | | hardening |

## Known trade-offs
- `cdn.jsdelivr.net` in script-src is a third-party script origin. Removing it needs the app to self-host onnxruntime-web: copy `ort-wasm-simd-threaded*.{mjs,wasm}` into `public/` and set `env.backends.onnx.wasm.wasmPaths = "/ort/"` in `src/workers/whisperWorker.ts` (frontend change, not done here). Then drop jsDelivr from both directives.
- `style-src 'unsafe-inline'` stays until inline styles are removed.
- `img-src https:` / `media-src https:` are broad on purpose (content may link external images); tighten if none are used.

## Not enabled (dormant features)
Social sign-in buttons only render when `VITE_GOOGLE_CLIENT_ID` / `VITE_APPLE_*` are set at build time. If enabled, add: script-src `https://accounts.google.com https://appleid.cdn-apple.com`; connect-src `https://accounts.google.com https://appleid.apple.com`; frame-src `https://accounts.google.com`; and Apple needs form-action to its redirect target. Test in a browser first.

## Rollback
Re-add the old `Content-Security-Policy-Report-Only` header or change the header name; `nginx -s reload` (or recreate the `web` container).
