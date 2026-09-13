"""
Schemas de validação de entrada (Seção 24 e 25).

As rotas recebem dados de formulário HTML (não JSON), então não usamos
o body-parsing automático do FastAPI/Pydantic — em vez disso, cada rota
recebe os campos via Form(...) normalmente e então constrói um destes
modelos, capturando ValidationError para devolver uma mensagem clara
ao professor em vez de deixar dado inválido chegar ao banco.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.services.blocks import BLOCK_QUESTION_COUNTS


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe seu nome.")
        return v


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ClassroomInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    school: Optional[str] = Field(default=None, max_length=160)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o nome da turma.")
        return v

    @field_validator("school")
    @classmethod
    def clean_school(cls, v):
        if v is None:
            return None
        v = v.strip()
        return v or None


class StudentInput(BaseModel):
    student_code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)

    @field_validator("student_code", "name")
    @classmethod
    def strip_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Preencha todos os campos do aluno.")
        return v


class CardInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    block: int

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Informe o nome do cartão.")
        return v

    @field_validator("block")
    @classmethod
    def valid_block(cls, v: int) -> int:
        if v not in BLOCK_QUESTION_COUNTS:
            raise ValueError("Bloco inválido.")
        return v
