"""Shared structured-HTTP-error helper.

Historically defined inline in app/api/router.py; extracted 2026-07-10 so
the grading module (app/review/grading.py) can raise the same structured
error envelope without importing the router (which itself imports the
grading module - a circular import). Function body moved verbatim.
"""
from fastapi import HTTPException


def fail(status,code,message,**details):
    raise HTTPException(
        status,
        detail={"code":code,"message":message,**details},
    )
