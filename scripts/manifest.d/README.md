# Per-group manifests

One file per entry so parallel direction agents never touch the same file.
Readers must glob `scripts/manifest.d/<kind>/*.txt` in sorted (LC_ALL=C) order; `scripts/manifest.py` does it for Python.

- `content/<course_name>.txt`: one line `course_name|realization files|overlay files`. Realizations and overlays must be in
  matching unit order (compiler flags are position-matched, not name-matched; see CLAUDE.md).
- `practice/<pack_name>.txt`: one line `pack_name|pack files`. Update when a new practice pack is authored and validated.

The file name must equal the first field. `derive_direction.py inject` writes these files.
