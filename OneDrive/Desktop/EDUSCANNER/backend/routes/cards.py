from pathlib import Path
import json
from fastapi import APIRouter,Request,Depends,Form
from fastapi.responses import HTMLResponse,RedirectResponse,StreamingResponse
from urllib.parse import quote
from pydantic import ValidationError
from backend.schemas import CardInput
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.security import get_current_user
from backend.models import AnswerCard,AnswerKey,ScanSession
from backend.services.blocks import BLOCK_QUESTION_COUNTS
from backend.services.card_generator import build_answer_card_pdf

BASE_DIR=Path(__file__).resolve().parents[2]
templates=Jinja2Templates(directory=BASE_DIR/"frontend/templates")
router=APIRouter()

@router.get("/cartoes",response_class=HTMLResponse)
def page(request:Request,erro:str=None,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    if not user:return RedirectResponse("/login",303)
    cards=db.query(AnswerCard).filter_by(teacher_id=user.id).order_by(AnswerCard.created_at.desc()).all()
    return templates.TemplateResponse("cards.html",{"request":request,"user":user,"cards":cards,"blocks":BLOCK_QUESTION_COUNTS,"erro":erro})

@router.post("/cartoes")
def create(request:Request,name:str=Form(...),block:int=Form(...),db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    if not user:return RedirectResponse("/login",303)
    try:
        data=CardInput(name=name,block=block)
    except ValidationError as exc:
        msg=quote(exc.errors()[0]["msg"])
        return RedirectResponse(f"/cartoes?erro={msg}",303)
    count=BLOCK_QUESTION_COUNTS[data.block]
    card=AnswerCard(teacher_id=user.id,name=data.name,block=data.block,question_count=count)
    db.add(card);db.flush()
    db.add(AnswerKey(card_id=card.id,answers_json=json.dumps({str(i):None for i in range(1,count+1)})))
    db.commit()
    return RedirectResponse(f"/cartoes/{card.id}/editar",303)

@router.get("/cartoes/{card_id}/editar",response_class=HTMLResponse)
def edit(request:Request,card_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    card=db.query(AnswerCard).filter_by(id=card_id,teacher_id=user.id).first() if user else None
    if not card:return RedirectResponse("/cartoes",303)
    answers=json.loads(card.key.answers_json)
    return templates.TemplateResponse("card_edit.html",{"request":request,"user":user,"card":card,"answers":answers})

@router.post("/cartoes/{card_id}/editar")
async def save(request:Request,card_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    card=db.query(AnswerCard).filter_by(id=card_id,teacher_id=user.id).first() if user else None
    if not card:return RedirectResponse("/cartoes",303)
    form=await request.form()
    answers={str(q):(form.get(f"q{q}") if form.get(f"q{q}") in {"A","B","C","D","E"} else None) for q in range(1,card.question_count+1)}
    card.key.answers_json=json.dumps(answers);db.commit()
    return RedirectResponse("/cartoes",303)

@router.get("/cartoes/{card_id}/imprimir")
def print_card(request:Request,card_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    card=db.query(AnswerCard).filter_by(id=card_id,teacher_id=user.id).first() if user else None
    if not card:return RedirectResponse("/cartoes",303)
    pdf=build_answer_card_pdf(card,teacher_name=user.name)
    return StreamingResponse(pdf,media_type="application/pdf",
        headers={"Content-Disposition":f'inline; filename="EDUSCANNER_cartao_{card.id}.pdf"'})

@router.post("/cartoes/{card_id}/excluir")
def delete_card(request:Request,card_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    card=db.query(AnswerCard).filter_by(id=card_id,teacher_id=user.id).first() if user else None
    if not card:return RedirectResponse("/cartoes",303)
    used=db.query(ScanSession).filter_by(card_id=card_id).first()
    if used:
        msg=quote("Este cartão já foi usado em correções e não pode ser excluído.")
        return RedirectResponse(f"/cartoes?erro={msg}",303)
    db.delete(card);db.commit()
    return RedirectResponse("/cartoes",303)
