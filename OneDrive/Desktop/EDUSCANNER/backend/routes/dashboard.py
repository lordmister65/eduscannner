from pathlib import Path
from fastapi import APIRouter,Request,Depends
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.security import get_current_user
from backend.models import Classroom,AnswerCard,ScanSession

BASE_DIR=Path(__file__).resolve().parents[2]
templates=Jinja2Templates(directory=BASE_DIR/"frontend/templates")
router=APIRouter()

@router.get("/dashboard",response_class=HTMLResponse)
def dashboard(request:Request,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    if not user:return RedirectResponse("/login",303)
    classrooms=db.query(Classroom).filter_by(teacher_id=user.id).all()
    cards=db.query(AnswerCard).filter_by(teacher_id=user.id).all()
    scans=db.query(ScanSession).join(Classroom).filter(Classroom.teacher_id==user.id).order_by(ScanSession.created_at.desc()).limit(5).all()
    student_total=sum(len(c.students) for c in classrooms)
    return templates.TemplateResponse("dashboard.html",{"request":request,"user":user,"classrooms":classrooms,"cards":cards,"scans":scans,"student_total":student_total})
