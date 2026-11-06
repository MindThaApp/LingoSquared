"""Imports the e2e fixture courses (de-ar.json, en-prs.json) through the importer."""
import json

from app.content.service import import_content
from app.db.session import SessionLocal
from app.schemas.api import ImportRequest

for name in ("de-ar", "en-prs"):
    with open(f"/fixtures/{name}.json", encoding="utf-8") as fh:
        payload = json.load(fh)
    with SessionLocal() as db:
        count, errors, counters = import_content(db, ImportRequest.model_validate(payload))
    if errors and not counters:
        raise SystemExit(f"fixture import failed for {name}: {errors}")
    print(f"fixtures imported: {name}: {count} course(s)")
