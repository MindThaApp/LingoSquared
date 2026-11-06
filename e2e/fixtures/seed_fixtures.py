"""Imports e2e/fixtures/de-ar.json (a tiny German-speaker Arabic course) through the importer."""
import json

from app.content.service import import_content
from app.db.session import SessionLocal
from app.schemas.api import ImportRequest

with open("/fixtures/de-ar.json", encoding="utf-8") as fh:
    payload = json.load(fh)
with SessionLocal() as db:
    count, errors, counters = import_content(db, ImportRequest.model_validate(payload))
if errors and not counters:
    raise SystemExit(f"fixture import failed: {errors}")
print(f"fixtures imported: {count} course(s)")
