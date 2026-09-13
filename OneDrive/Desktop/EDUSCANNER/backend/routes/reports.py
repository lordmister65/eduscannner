from pathlib import Path
from datetime import datetime
from io import StringIO,BytesIO
import csv
from fastapi import APIRouter,Request,Depends
from fastapi.responses import StreamingResponse,RedirectResponse,HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.security import get_current_user
from backend.models import Classroom,ScanSession,Student,AnswerCard
from backend.services.pdf_report import build_class_pdf

BASE_DIR=Path(__file__).resolve().parents[2]
templates=Jinja2Templates(directory=BASE_DIR/"frontend/templates")
router=APIRouter()

@router.get("/relatorios",response_class=HTMLResponse)
def results_page(request:Request,classroom_id:int=None,student_id:int=None,card_id:int=None,
                  date_from:str=None,date_to:str=None,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    if not user:return RedirectResponse("/login",303)

    classrooms=db.query(Classroom).filter_by(teacher_id=user.id).all()
    cards=db.query(AnswerCard).filter_by(teacher_id=user.id).all()

    query=db.query(ScanSession).join(Classroom).filter(Classroom.teacher_id==user.id)
    if classroom_id:query=query.filter(ScanSession.classroom_id==classroom_id)
    if student_id:query=query.filter(ScanSession.student_id==student_id)
    if card_id:query=query.filter(ScanSession.card_id==card_id)
    if date_from:
        try:query=query.filter(ScanSession.created_at>=datetime.fromisoformat(date_from))
        except ValueError:pass
    if date_to:
        try:query=query.filter(ScanSession.created_at<=datetime.fromisoformat(date_to+"T23:59:59"))
        except ValueError:pass
    scans=query.order_by(ScanSession.created_at.desc()).limit(200).all()

    students=[]
    if classroom_id:
        students=db.query(Student).filter_by(classroom_id=classroom_id).all()

    return templates.TemplateResponse("results.html",{
        "request":request,"user":user,"classrooms":classrooms,"cards":cards,"students":students,
        "scans":scans,
        "filters":{"classroom_id":classroom_id,"student_id":student_id,"card_id":card_id,
                   "date_from":date_from or "","date_to":date_to or ""},
    })

@router.get("/relatorios/{class_id}/pdf")
def pdf(request:Request,class_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    classroom=db.query(Classroom).filter_by(id=class_id,teacher_id=user.id).first() if user else None
    if not classroom:return RedirectResponse("/turmas",303)
    scans=db.query(ScanSession).filter_by(classroom_id=class_id).order_by(ScanSession.created_at.asc()).all()
    return StreamingResponse(build_class_pdf(classroom,scans),media_type="application/pdf",
        headers={"Content-Disposition":f'attachment; filename="EDUSCANNER_{classroom.name}.pdf"'})

@router.get("/relatorios/{class_id}/csv")
def csv_report(request:Request,class_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    classroom=db.query(Classroom).filter_by(id=class_id,teacher_id=user.id).first() if user else None
    if not classroom:return RedirectResponse("/turmas",303)
    scans=db.query(ScanSession).filter_by(classroom_id=class_id).order_by(ScanSession.created_at.asc()).all()
    s=StringIO();w=csv.writer(s);w.writerow(["ID","Nome","Turma","Questão","Resultado"])
    for scan in scans:
        sid=scan.student.student_code if scan.student else "";name=scan.student.name if scan.student else ""
        for a in sorted(scan.answers,key=lambda x:x.question_number):
            result="acerto" if a.correct is True else "errou" if a.correct is False else "em branco"
            w.writerow([sid,name,classroom.name,a.question_number,result])
    return StreamingResponse(BytesIO(s.getvalue().encode("utf-8-sig")),media_type="text/csv",
        headers={"Content-Disposition":f'attachment; filename="EDUSCANNER_{classroom.name}.csv"'})
