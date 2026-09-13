from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

def build_class_pdf(classroom, scans):
    buf=BytesIO()
    c=canvas.Canvas(buf,pagesize=A4)
    w,h=A4
    c.setTitle(f"EDUSCANNER - {classroom.name}")
    c.setFont("Helvetica-Bold",18)
    c.drawString(20*mm,h-20*mm,"EDUSCANNER")
    c.setFont("Helvetica",11)
    c.drawString(20*mm,h-28*mm,f"Turma: {classroom.name}")
    y=h-42*mm
    for scan in scans:
        if y<35*mm:
            c.showPage(); y=h-20*mm
        sid=scan.student.student_code if scan.student else "-"
        name=scan.student.name if scan.student else "Aluno não identificado"
        c.setFont("Helvetica-Bold",10)
        c.drawString(20*mm,y,f"ID: {sid}    Nome: {name}    Turma: {classroom.name}")
        y-=6*mm
        c.setFont("Helvetica",8.5)
        for a in sorted(scan.answers,key=lambda x:x.question_number):
            status="acerto" if a.correct is True else "errou" if a.correct is False else "em branco"
            c.drawString(24*mm,y,f"Questão {a.question_number}: {status}")
            y-=4.5*mm
            if y<15*mm:
                c.showPage(); y=h-20*mm
        c.setFont("Helvetica-Bold",9)
        c.drawString(24*mm,y,f"Total: {scan.correct_count} acertos | {scan.wrong_count} erros | {scan.blank_count} em branco")
        y-=9*mm
    c.save(); buf.seek(0); return buf
