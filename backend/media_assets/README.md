# Local dev media assets (Phase D scaffolding)

Provisional local-dev location for recorded human audio (fa/prs A1) per
`docs/SONNET_BUILD_PROMPT_UPGRADES.md` Phase D. One file per
`media_asset_key`, e.g. `fa.a1.audio.salam.neutral.01.mp3`.

**This directory and its final serving mechanism are scaffolding, not a
finished feature.** Session 3 (INFRA) created it so
`scripts/audio_manifest.py` has somewhere concrete to check against;
the actual serving route (`GET /media/{key}`, static-file mount vs.
nginx, upload endpoint) is Phase D3 and belongs to whoever owns
`backend/app/**` (Session 1/Codex) per the ownership map. Confirm this
path still makes sense when D3 is actually implemented — it was chosen
because `backend/`'s directory is already the one Docker mounts as a
volume, not because it's been reviewed as the final answer.

Empty on purpose right now (`.gitkeep` only) — nothing has been
recorded yet. Run `scripts/audio_manifest.py` to see what's needed.
