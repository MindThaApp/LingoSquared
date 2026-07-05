from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User

bearer=HTTPBearer(auto_error=False)
def current_user(auth:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    try: user=db.get(User,decode_token(auth.credentials)) if auth else None
    except Exception: user=None
    if not user: raise HTTPException(401,detail={"code":"invalid_token","message":"Invalid or expired access token"})
    return user
def optional_current_user(auth:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    if not auth: return None
    try: user=db.get(User,decode_token(auth.credentials))
    except Exception: user=None
    if not user: raise HTTPException(401,detail={"code":"invalid_token","message":"Invalid or expired access token"})
    return user
def admin_user(user:User=Depends(current_user)):
    if not user.is_admin: raise HTTPException(403,detail={"code":"admin_required","message":"Administrator access required"})
    return user
