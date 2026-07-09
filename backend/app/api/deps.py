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
def lenient_current_user(auth:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    # Unlike optional_current_user, a present-but-invalid token here never
    # 401s -- it just resolves to anonymous. Needed for POST /feedback:
    # the frontend may send this app's normal access_token to a DIFFERENT
    # centrally-configured feedback backend (see VITE_FEEDBACK_API_URL /
    # docs/CONTRACT.md's "General app/page feedback"), whose signing key
    # won't recognize a token minted by some other install's backend --
    # that must degrade to an anonymous report, not a hard error.
    if not auth: return None
    try: return db.get(User,decode_token(auth.credentials))
    except Exception: return None
def admin_user(user:User=Depends(current_user)):
    if not user.is_admin: raise HTTPException(403,detail={"code":"admin_required","message":"Administrator access required"})
    return user
