"""
Testes de turmas e alunos (Seção 8) e isolamento entre professores
(Seção 6: um professor não pode acessar dados de outro).
"""

from tests.conftest import register_and_login, login


def _create_class(client, name="Turma Original 8A", school="Escola X"):
    r = client.post("/turmas", data={"name": name, "school": school})
    assert r.status_code == 200
    return r


def test_create_classroom(client):
    register_and_login(client)
    _create_class(client)
    r = client.get("/turmas")
    assert "Turma Original 8A" in r.text
    assert "Escola X" in r.text


def test_edit_classroom(client):
    register_and_login(client)
    _create_class(client)
    client.post("/turmas/1/editar", data={"name": "Turma Renomeada 8B", "school": "Escola Y"})
    r = client.get("/turmas")
    assert "Turma Renomeada 8B" in r.text
    assert "Turma Original 8A" not in r.text


def test_delete_classroom(client):
    register_and_login(client)
    _create_class(client)
    client.post("/turmas/1/excluir")
    r = client.get("/turmas")
    assert "Turma Original 8A" not in r.text


def test_add_student_to_classroom(client):
    register_and_login(client)
    _create_class(client)
    client.post("/turmas/1/alunos", data={"student_code": "001", "name": "João Silva"})
    r = client.get("/turmas")
    assert "João Silva" in r.text
    assert "001" in r.text


def test_edit_student(client):
    register_and_login(client)
    _create_class(client)
    client.post("/turmas/1/alunos", data={"student_code": "001", "name": "João Silva"})
    client.post("/turmas/1/alunos/1/editar", data={"student_code": "002", "name": "João S. Silva"})
    r = client.get("/turmas")
    assert "João S. Silva" in r.text
    assert "002" in r.text


def test_remove_student(client):
    register_and_login(client)
    _create_class(client)
    client.post("/turmas/1/alunos", data={"student_code": "001", "name": "João Silva"})
    client.post("/turmas/1/alunos/1/excluir")
    r = client.get("/turmas")
    assert "João Silva" not in r.text


def test_deleting_classroom_removes_its_students_from_the_database(client):
    """Cascade: excluir a turma remove os alunos dela do banco, não só
    da tela (Seção 8)."""
    register_and_login(client)
    _create_class(client)
    client.post("/turmas/1/alunos", data={"student_code": "001", "name": "João Silva"})
    client.post("/turmas/1/excluir")

    from backend.db import SessionLocal
    from backend.models import Student

    db = SessionLocal()
    assert db.query(Student).count() == 0
    db.close()


def test_teacher_cannot_see_another_teachers_classroom(client):
    """Seção 6: um professor NÃO pode acessar turmas de outro professor."""
    register_and_login(client, email="ana@escola.com")
    _create_class(client, name="Turma da Ana")
    client.get("/logout")

    register_and_login(client, name="Prof Beto", email="beto@escola.com")
    r = client.get("/turmas")
    assert "Turma da Ana" not in r.text


def test_teacher_cannot_edit_another_teachers_classroom(client):
    register_and_login(client, email="ana@escola.com")
    _create_class(client, name="Turma da Ana")
    client.get("/logout")

    register_and_login(client, name="Prof Beto", email="beto@escola.com")
    client.post("/turmas/1/editar", data={"name": "Turma Sequestrada", "school": ""})

    client.get("/logout")
    login(client, email="ana@escola.com")
    r = client.get("/turmas")
    assert "Turma da Ana" in r.text
    assert "Turma Sequestrada" not in r.text
