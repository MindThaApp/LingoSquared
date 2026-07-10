from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import router
from app.core.config import get_settings

s=get_settings(); app=FastAPI(title=s.app_name,version="1.0.0",description="Local-first language learning API")
app.add_middleware(CORSMiddleware,allow_origins=s.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.exception_handler(HTTPException)
async def http_error(request:Request,exc:HTTPException):
    detail=exc.detail if isinstance(exc.detail,dict) and "code" in exc.detail else {"code":"http_error","message":str(exc.detail)}
    return JSONResponse(status_code=exc.status_code,content={"error":detail})
@app.exception_handler(RequestValidationError)
async def validation_error(request:Request,exc:RequestValidationError):
    return JSONResponse(status_code=422,content={"error":{"code":"validation_error","message":"; ".join(f"{'.'.join(map(str,e['loc']))}: {e['msg']}" for e in exc.errors())}})
@app.exception_handler(Exception)
async def internal_error(request:Request,exc:Exception):
    return JSONResponse(status_code=500,content={"error":{"code":"internal_error","message":"An unexpected server error occurred"}})
@app.get("/health")
def health(): return {"status":"ok"}
app.include_router(router, prefix="/v1")
app.include_router(router, include_in_schema=False)
