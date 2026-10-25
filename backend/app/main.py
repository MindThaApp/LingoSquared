import logging
import re
import secrets
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import router
from app.core.config import get_settings
from app.core.security import decode_token
from app.core.sentry import init_sentry
from app.services.push_scheduler import push_scheduler_enabled, run_push_scheduler_once

# Basic logging configuration so app.* loggers actually emit to stdout.
# uvicorn only configures its own "uvicorn"/"uvicorn.error"/"uvicorn.access"
# loggers — the root logger has no handler under uvicorn's default config,
# so without this every logger.info()/logger.exception() in app code was
# silently dropped. basicConfig is a no-op when a root handler already
# exists, so this never clobbers an outer/production logging setup.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("app.main")

def validate_startup_settings(settings):
    if settings.jwt_secret == "development-only-secret" and settings.app_env.lower() not in {"dev", "development", "test"}:
        raise RuntimeError(
            "Refusing to start with the built-in JWT secret; set JWT_SECRET to a strong secret or set APP_ENV=dev/test for local development and tests."
        )

s=get_settings()
validate_startup_settings(s)
init_sentry(s)  # no-op unless SENTRY_DSN is set
async def _push_scheduler_loop():
    while True:
        try:
            await asyncio.to_thread(run_push_scheduler_once)
        except Exception:
            logger.exception("push reminder scheduler iteration failed")
        await asyncio.sleep(15 * 60)


@asynccontextmanager
async def lifespan(_app):
    task = asyncio.create_task(_push_scheduler_loop()) if push_scheduler_enabled() else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app=FastAPI(title=s.app_name,version="1.0.0",description="Local-first language learning API",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=s.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

# Accept a client-supplied X-Request-ID only if it's a short, safe token —
# anything else (too long, control chars, log-injection attempts) gets a
# fresh server-generated id instead.
_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID", "")
    rid = incoming if _REQUEST_ID_RE.fullmatch(incoming) else secrets.token_hex(6)
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response

def _user_id_for_log(request: Request):
    """Best-effort user id from the bearer token, for log correlation only.

    Deliberately never touches the DB and never raises — a missing,
    malformed, or expired token just correlates as None. This is NOT an
    auth check; it only labels log lines.
    """
    auth = request.headers.get("Authorization", "")
    if auth[:7].lower() == "bearer ":
        try:
            return decode_token(auth[7:].strip())
        except Exception:
            return None
    return None

@app.exception_handler(HTTPException)
async def http_error(request:Request,exc:HTTPException):
    detail=exc.detail if isinstance(exc.detail,dict) and "code" in exc.detail else {"code":"http_error","message":str(exc.detail)}
    return JSONResponse(status_code=exc.status_code,content={"error":detail})
@app.exception_handler(RequestValidationError)
async def validation_error(request:Request,exc:RequestValidationError):
    return JSONResponse(status_code=422,content={"error":{"code":"validation_error","message":"; ".join(f"{'.'.join(map(str,e['loc']))}: {e['msg']}" for e in exc.errors())}})
@app.exception_handler(Exception)
async def internal_error(request:Request,exc:Exception):
    rid = getattr(request.state, "request_id", None)
    logger.exception(
        "unhandled exception request_id=%s method=%s path=%s user_id=%s",
        rid, request.method, request.url.path, _user_id_for_log(request),
        exc_info=exc,
    )
    # Starlette's ServerErrorMiddleware invokes this handler OUTSIDE the
    # request-id middleware (which only wraps the inner app), so the
    # X-Request-ID header must be attached here explicitly — the
    # middleware never sees this response.
    return JSONResponse(
        status_code=500,
        content={"error":{"code":"internal_error","message":"An unexpected server error occurred"}},
        headers={"X-Request-ID": rid} if rid else None,
    )
@app.get("/health")
def health(): return {"status":"ok"}
from app.review.api import router as review_router
router.include_router(review_router)
app.include_router(router, prefix="/v1")
app.include_router(router, include_in_schema=False)
