# Content-Security-Policy (web app)

Set in `backend/nginx.web.conf` (server level, `always`). Enforcing since the WS5 change of 2026-11-04; before that it was Report-Only. There is no report endpoint, so there are no violation logs: the policy was derived from the built bundle, the source and the old Report-Only policy. Verify with `scripts/csp_check.sh` (headers via the real nginx config in a throwaway container, plus a static check of `index.html`). Verified in a real browser (headless Chromium, Playwright) with `scripts/csp_browser_check.sh`: isolated compose stack, sign-up, login, lesson + audio, speaking exercise (whisper worker, onnxruntime-web from jsDelivr, model from Hugging Face), profile, change password, Sentry send, Privacy/Terms, RTL course and Persian UI; zero violations. Rerun it before each deploy that touches this policy or the frontend bundle.

| Directive | Value | Why |
|---|---|---|
| default-src | 'self' | baseline |
| script-src | 'self' 'wasm-unsafe-eval' blob: https://cdn.jsdelivr.net | Vite bundle (no inline scripts); ONNX wasm needs wasm-unsafe-eval (confirmed: compile is refused without it); transformers.js fetches the ort `.mjs` from jsDelivr and `import()`s it from a blob: URL inside the worker (found by the browser test: without blob: the speaking exercise breaks); `@huggingface/transformers` loads onnxruntime-web `.mjs` from jsDelivr (default `wasmPaths`, the whisper worker does not override it) |
| style-src | 'self' | Vite emits external CSS; React `style` props go through CSSOM, which strict style-src allows. Browser test: zero violations, and no `<style>`/`cssText`/`innerHTML` in the source or bundle |
| img-src | 'self' data: blob: http://*:8010 https: | icons, API media on LAN :8010 |
| media-src | 'self' blob: data: http://*:8010 https: | TTS audio from API, recorded blobs |
| font-src | 'self' data: | fonts are bundled (`public/fonts`) |
| connect-src | 'self' http(s)://*:8010 https://*.ingest.de.sentry.io https://huggingface.co https://*.huggingface.co https://*.hf.co https://cdn.jsdelivr.net data: blob: | API, Sentry EU ingest, model download, ort wasm fetch |
| worker-src / child-src | 'self' blob: | whisper worker, service worker |
| manifest-src | 'self' | PWA manifest |
| object-src 'none', base-uri 'self', form-action 'self', frame-ancestors 'none' | | hardening |

## Known trade-offs
- `cdn.jsdelivr.net` in script-src is a third-party script origin. Removing it needs the app to self-host onnxruntime-web: copy `ort-wasm-simd-threaded*.{mjs,wasm}` into `public/` and set `env.backends.onnx.wasm.wasmPaths = "/ort/"` in `src/workers/whisperWorker.ts` (frontend change, not done here). Then drop jsDelivr from both directives.
- `blob:` in script-src is needed while ort is loaded from jsDelivr; self-hosting ort (above) removes both `blob:` and jsDelivr.
- If a future dependency injects `<style>` or `style=""` attributes via HTML, `style-src` violations appear: the browser check will catch them.
- `img-src https:` / `media-src https:` are broad on purpose (content may link external images); tighten if none are used.

## Not enabled (dormant features)
Social sign-in buttons only render when `VITE_GOOGLE_CLIENT_ID` / `VITE_APPLE_*` are set at build time. If enabled, add: script-src `https://accounts.google.com https://appleid.cdn-apple.com`; connect-src `https://accounts.google.com https://appleid.apple.com`; frame-src `https://accounts.google.com`; and Apple needs form-action to its redirect target. Test in a browser first.

## Rollback
Re-add the old `Content-Security-Policy-Report-Only` header or change the header name; `nginx -s reload` (or recreate the `web` container).
