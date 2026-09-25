from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship
from .database import Base

usuario_turmas = Table(
    'usuario_turmas', Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuarios.id', ondelete='CASCADE'), primary_key=True),
    Column('turma_id', Integer, ForeignKey('turmas.id', ondelete='CASCADE'), primary_key=True),
)

class Turma(Base):
    __tablename__ = 'turmas'
    id = Column(Integer, primary_key=True)
    nome = Column(String(120), unique=True, nullable=False, index=True)
    alunos = relationship('Aluno', back_populates='turma', cascade='all, delete-orphan')
    usuarios = relationship('Usuario', secondary=usuario_turmas, back_populates='turmas')

class Aluno(Base):
    __tablename__ = 'alunos'
    id = Column(Integer, primary_key=True)
    nome = Column(String(180), nullable=False, index=True)
    matricula = Column(String(80), unique=True, nullable=False, index=True)
    turma_id = Column(Integer, ForeignKey('turmas.id'), nullable=False, index=True)
    turma = relationship('Turma', back_populates='alunos')
    resultados = relationship('Resultado', back_populates='aluno', cascade='all, delete-orphan')

class Resultado(Base):
    __tablename__ = 'resultados'
    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey('alunos.id'), nullable=False, index=True)
    prova_nome = Column(String(160), nullable=False, default='Prova')
    quantidade_questoes = Column(Integer, nullable=False)
    gabarito = Column(Text, nullable=False)
    respostas = Column(Text, nullable=False)
    acertos = Column(Integer, nullable=False)
    erros = Column(Integer, nullable=False)
    anuladas = Column(Integer, nullable=False, default=0)
    em_branco = Column(Integer, nullable=False, default=0)
    nota = Column(Float, nullable=False)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    aluno = relationship('Aluno', back_populates='resultados')

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    nome = Column(String(180), nullable=False)
    login = Column(String(180), unique=True, nullable=False, index=True)
    senha_hash = Column(String(400), nullable=False)
    tipo = Column(String(20), nullable=False, default='professor')  # admin | professor
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    turmas = relationship('Turma', secondary=usuario_turmas, back_populates='usuarios')
