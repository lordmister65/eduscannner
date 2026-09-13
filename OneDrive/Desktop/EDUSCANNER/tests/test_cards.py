"""
Testes de cartões-resposta (Seções 9, 10, 18, 25) e isolamento entre
professores.
"""

from tests.conftest import register_and_login


def _create_card(client, name="Prova de Matemática", block=2):
    r = client.post("/cartoes", data={"name": name, "block": block})
    assert r.status_code == 200
    card_id = int(r.url.path.strip("/").split("/")[1])
    return card_id


def test_creating_card_sets_question_count_from_block_for_every_block(client):
    """Seção 9: o professor nunca escolhe a quantidade de questões —
    ela vem sempre do bloco."""
    register_and_login(client)
    expected = {1: 20, 2: 30, 3: 20, 4: 30, 5: 30, 6: 30, 7: 45, 8: 45}

    from backend.db import SessionLocal
    from backend.models import AnswerCard

    for block, count in expected.items():
        card_id = _create_card(client, name=f"Cartão bloco {block}", block=block)
        db = SessionLocal()
        card = db.get(AnswerCard, card_id)
        assert card.question_count == count
        db.close()


def test_creating_card_by_block_2_yields_30_questions(client):
    register_and_login(client)
    card_id = _create_card(client, block=2)
    r = client.get(f"/cartoes/{card_id}/editar")
    assert r.status_code == 200
    # 30 seletores de questão (q1..q30) devem existir no formulário
    assert 'name="q30"' in r.text
    assert 'name="q31"' not in r.text


def test_card_appears_in_listing(client):
    register_and_login(client)
    _create_card(client, name="Prova de Inglês", block=1)
    r = client.get("/cartoes")
    assert "Prova de Inglês" in r.text
    assert "BLOCO 1" in r.text.upper()


def test_setting_and_persisting_answer_key(client):
    register_and_login(client)
    card_id = _create_card(client, block=1)  # bloco 1 = 20 questões
    form_data = {f"q{i}": "A" for i in range(1, 21)}
    r = client.post(f"/cartoes/{card_id}/editar", data=form_data)
    assert r.status_code == 200

    from backend.db import SessionLocal
    from backend.models import AnswerCard
    import json

    db = SessionLocal()
    card = db.get(AnswerCard, card_id)
    answers = json.loads(card.key.answers_json)
    assert answers["1"] == "A"
    assert answers["20"] == "A"
    db.close()


def test_print_card_returns_valid_pdf(client):
    register_and_login(client)
    card_id = _create_card(client, block=3)
    r = client.get(f"/cartoes/{card_id}/imprimir")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 1000


def test_delete_unused_card_succeeds(client):
    register_and_login(client)
    card_id = _create_card(client)
    client.post(f"/cartoes/{card_id}/excluir")
    r = client.get("/cartoes")
    assert "Prova de Matemática" not in r.text


def test_delete_card_already_used_in_a_scan_is_blocked(client):
    """Seção 18: o cartão é reutilizável entre turmas — não pode
    desaparecer depois de já ter sido usado em uma correção."""
    register_and_login(client)
    card_id = _create_card(client, name="Prova Usada")
    client.post("/turmas", data={"name": "Turma X", "school": ""})

    from backend.db import SessionLocal
    from backend.models import ScanSession

    db = SessionLocal()
    db.add(ScanSession(classroom_id=1, card_id=card_id, correct_count=1, wrong_count=1, blank_count=1))
    db.commit()
    db.close()

    client.post(f"/cartoes/{card_id}/excluir")
    r = client.get("/cartoes")
    assert "Prova Usada" in r.text  # continua existindo


def test_teacher_cannot_see_another_teachers_card(client):
    register_and_login(client, email="ana@escola.com")
    _create_card(client, name="Prova da Ana")
    client.get("/logout")

    register_and_login(client, name="Prof Beto", email="beto@escola.com")
    r = client.get("/cartoes")
    assert "Prova da Ana" not in r.text


def test_teacher_cannot_print_another_teachers_card(client):
    register_and_login(client, email="ana@escola.com")
    card_id = _create_card(client, name="Prova da Ana")
    client.get("/logout")

    register_and_login(client, name="Prof Beto", email="beto@escola.com")
    r = client.get(f"/cartoes/{card_id}/imprimir")
    # não deve devolver o PDF de outro professor — redireciona
    assert r.headers.get("content-type") != "application/pdf"
