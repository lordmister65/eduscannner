from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter,Request,Depends,Form
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError
from backend.db import get_db
from backend.security import get_current_user
from backend.models import Classroom,Student
from backend.schemas import ClassroomInput,StudentInput

BASE_DIR=Path(__file__).resolve().parents[2]
templates=Jinja2Templates(directory=BASE_DIR/"frontend/templates")
router=APIRouter()

def _redirect_with_error(msg:str):
    return RedirectResponse(f"/turmas?erro={quote(msg)}",303)

@router.get("/turmas",response_class=HTMLResponse)
def page(request:Request,erro:str=None,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    if not user:return RedirectResponse("/login",303)
    classes=db.query(Classroom).filter_by(teacher_id=user.id).all()
    return templates.TemplateResponse("classes.html",{"request":request,"user":user,"classes":classes,"erro":erro})

@router.post("/turmas")
def create(request:Request,name:str=Form(...),school:str=Form(""),db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    if not user:return RedirectResponse("/login",303)
    try:
        data=ClassroomInput(name=name,school=school)
    except ValidationError as exc:
        return _redirect_with_error(exc.errors()[0]["msg"])
    db.add(Classroom(teacher_id=user.id,name=data.name,school=data.school));db.commit()
    return RedirectResponse("/turmas",303)

@router.post("/turmas/{class_id}/alunos")
def add(request:Request,class_id:int,student_code:str=Form(...),name:str=Form(...),db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    classroom=db.query(Classroom).filter_by(id=class_id,teacher_id=user.id).first() if user else None
    if not classroom:return RedirectResponse("/turmas",303)
    try:
        data=StudentInput(student_code=student_code,name=name)
    except ValidationError as exc:
        return _redirect_with_error(exc.errors()[0]["msg"])
    exists=db.query(Student).filter_by(classroom_id=class_id,student_code=data.student_code).first()
    if exists:
        return _redirect_with_error(f"Já existe um aluno com o ID '{data.student_code}' nesta turma.")
    db.add(Student(classroom_id=class_id,student_code=data.student_code,name=data.name));db.commit()
    return RedirectResponse("/turmas",303)

@router.post("/turmas/{class_id}/editar")
def edit_class(request:Request,class_id:int,name:str=Form(...),school:str=Form(""),db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    classroom=db.query(Classroom).filter_by(id=class_id,teacher_id=user.id).first() if user else None
    if not classroom:return RedirectResponse("/turmas",303)
    try:
        data=ClassroomInput(name=name,school=school)
    except ValidationError as exc:
        return _redirect_with_error(exc.errors()[0]["msg"])
    classroom.name=data.name;classroom.school=data.school;db.commit()
    return RedirectResponse("/turmas",303)

@router.post("/turmas/{class_id}/excluir")
def delete_class(request:Request,class_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    classroom=db.query(Classroom).filter_by(id=class_id,teacher_id=user.id).first() if user else None
    if classroom:
        db.delete(classroom);db.commit()
    return RedirectResponse("/turmas",303)

@router.post("/turmas/{class_id}/alunos/{student_id}/editar")
def edit_student(request:Request,class_id:int,student_id:int,student_code:str=Form(...),name:str=Form(...),db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    classroom=db.query(Classroom).filter_by(id=class_id,teacher_id=user.id).first() if user else None
    student=db.query(Student).filter_by(id=student_id,classroom_id=class_id).first() if classroom else None
    if not student:return RedirectResponse("/turmas",303)
    try:
        data=StudentInput(student_code=student_code,name=name)
    except ValidationError as exc:
        return _redirect_with_error(exc.errors()[0]["msg"])
    student.student_code=data.student_code;student.name=data.name;db.commit()
    return RedirectResponse("/turmas",303)

@router.post("/turmas/{class_id}/alunos/{student_id}/excluir")
def delete_student(request:Request,class_id:int,student_id:int,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    classroom=db.query(Classroom).filter_by(id=class_id,teacher_id=user.id).first() if user else None
    student=db.query(Student).filter_by(id=student_id,classroom_id=class_id).first() if classroom else None
    if student:
        db.delete(student);db.commit()
    return RedirectResponse("/turmas",303)
