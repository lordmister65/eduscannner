from pathlib import Path
import json
from fastapi import APIRouter,Request,Depends,UploadFile,File,Form
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.security import get_current_user
from backend.models import AnswerCard,Classroom,Student,ScanSession,ScanAnswer
from backend.services.scanner import analyze_image
from backend.rate_limit import enforce_scanner_rate_limit

BASE_DIR=Path(__file__).resolve().parents[2]
templates=Jinja2Templates(directory=BASE_DIR/"frontend/templates")
router=APIRouter()

@router.get("/scanner",response_class=HTMLResponse)
def page(request:Request,db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    if not user:return RedirectResponse("/login",303)
    cards=db.query(AnswerCard).filter_by(teacher_id=user.id).all()
    classrooms=db.query(Classroom).filter_by(teacher_id=user.id).all()
    students=db.query(Student).join(Classroom).filter(Classroom.teacher_id==user.id).all()
    return templates.TemplateResponse("scanner.html",{"request":request,"user":user,"cards":cards,"classrooms":classrooms,"students":students})

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB — generosa para fotos de celular, evita abuso

@router.post("/api/scanner/analyze",dependencies=[Depends(enforce_scanner_rate_limit)])
async def analyze(request:Request,card_id:int=Form(...),image:UploadFile=File(...),db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    card=db.query(AnswerCard).filter_by(id=card_id,teacher_id=user.id).first() if user else None
    if not card:return JSONResponse({"ok":False,"message":"Cartão não encontrado."},404)
    raw=await image.read()
    if len(raw)>MAX_UPLOAD_BYTES:
        return JSONResponse({"ok":False,"message":"Imagem muito grande. Envie uma foto de até 15MB."},413)
    result=analyze_image(raw,card.question_count)
    if not result.ok:
        return JSONResponse({"ok":False,"message":result.debug_message},422)
    return {"ok":True,"message":result.debug_message,"question_count":card.question_count,
            "questions":[{"number":q.number,"answer":q.answer,"status":q.status,"confidence":q.confidence,"ratios":q.ratios} for q in result.questions]}

@router.post("/api/scanner/save")
async def save(request:Request,card_id:int=Form(...),classroom_id:int=Form(...),student_id:int=Form(None),answers_json:str=Form(...),db:Session=Depends(get_db)):
    user=get_current_user(request,db)
    card=db.query(AnswerCard).filter_by(id=card_id,teacher_id=user.id).first() if user else None
    classroom=db.query(Classroom).filter_by(id=classroom_id,teacher_id=user.id).first() if user else None
    if not card or not classroom:return JSONResponse({"ok":False,"message":"Dados inválidos."},400)
    answers=json.loads(answers_json); key=json.loads(card.key.answers_json)
    scan=ScanSession(classroom_id=classroom.id,student_id=student_id or None,card_id=card.id)
    db.add(scan);db.flush()
    correct=wrong=blank=0
    for item in answers:
        q=int(item["number"]);detected=item.get("answer");qstatus=item.get("status","OK");expected=key.get(str(q))
        if qstatus=="MULT":
            status=False;wrong+=1;detected="MULT"
        elif detected is None: status=None;blank+=1
        elif expected and detected==expected: status=True;correct+=1
        elif expected: status=False;wrong+=1
        else: status=None
        db.add(ScanAnswer(scan_id=scan.id,question_number=q,detected_option=detected,correct=status))
    scan.correct_count,scan.wrong_count,scan.blank_count=correct,wrong,blank
    db.commit()
    return {"ok":True,"scan_id":scan.id,"correct":correct,"wrong":wrong,"blank":blank}
