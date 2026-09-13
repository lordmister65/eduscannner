from pathlib import Path
import os
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError
from dotenv import load_dotenv
from backend.db import get_db
from backend.models import User
from backend.security import hash_password, verify_password
from backend.schemas import RegisterInput, LoginInput
from backend.rate_limit import enforce_login_rate_limit

BASE_DIR=Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR/".env")
templates=Jinja2Templates(directory=BASE_DIR/"frontend/templates")
router=APIRouter()

@router.get("/login",response_class=HTMLResponse)
def login_page(request:Request):
    return templates.TemplateResponse("login.html",{"request":request,"error":None})

@router.post("/register",dependencies=[Depends(enforce_login_rate_limit)])
def register(request:Request,name:str=Form(...),email:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    try:
        data=RegisterInput(name=name,email=email,password=password)
    except ValidationError as exc:
        return templates.TemplateResponse("login.html",{"request":request,"error":exc.errors()[0]["msg"]})
    email=data.email.lower()
    if db.query(User).filter_by(email=email).first():
        return templates.TemplateResponse("login.html",{"request":request,"error":"Este e-mail já está cadastrado."})
    user=User(name=data.name,email=email,password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    request.session["user_id"]=user.id
    return RedirectResponse("/dashboard",303)

@router.post("/login",dependencies=[Depends(enforce_login_rate_limit)])
def do_login(request:Request,email:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    try:
        data=LoginInput(email=email,password=password)
    except ValidationError:
        return templates.TemplateResponse("login.html",{"request":request,"error":"E-mail ou senha inválidos."})
    user=db.query(User).filter_by(email=data.email.lower()).first()
    if not user or not user.password_hash or not verify_password(data.password,user.password_hash):
        return templates.TemplateResponse("login.html",{"request":request,"error":"E-mail ou senha inválidos."})
    request.session["user_id"]=user.id
    return RedirectResponse("/dashboard",303)

@router.get("/logout")
def logout(request:Request):
    request.session.clear()
    return RedirectResponse("/login",303)

@router.get("/auth/google")
async def google_login(request:Request):
    if not os.getenv("GOOGLE_CLIENT_ID"):
        return templates.TemplateResponse("login.html",{"request":request,"error":"Login Google ainda não foi configurado no .env."})
    from authlib.integrations.starlette_client import OAuth
    oauth=OAuth()
    oauth.register(name="google",client_id=os.getenv("GOOGLE_CLIENT_ID"),client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                   server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                   client_kwargs={"scope":"openid email profile"})
    redirect_uri=os.getenv("GOOGLE_REDIRECT_URI",str(request.url_for("google_callback")))
    return await oauth.google.authorize_redirect(request,redirect_uri)

@router.get("/auth/google/callback",name="google_callback")
async def google_callback(request:Request,db:Session=Depends(get_db)):
    from authlib.integrations.starlette_client import OAuth
    oauth=OAuth()
    oauth.register(name="google",client_id=os.getenv("GOOGLE_CLIENT_ID"),client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                   server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                   client_kwargs={"scope":"openid email profile"})
    token=await oauth.google.authorize_access_token(request)
    info=token.get("userinfo") or await oauth.google.userinfo(token=token)
    email=info["email"].lower()
    user=db.query(User).filter_by(email=email).first()
    if not user:
        user=User(name=info.get("name",email.split("@")[0]),email=email,google_sub=info.get("sub"))
        db.add(user); db.commit(); db.refresh(user)
    else:
        user.google_sub=info.get("sub"); db.commit()
    request.session["user_id"]=user.id
    return RedirectResponse("/dashboard",303)
