from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from backend.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    google_sub = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    classrooms = relationship("Classroom", back_populates="teacher", cascade="all, delete-orphan")
    cards = relationship("AnswerCard", back_populates="teacher", cascade="all, delete-orphan")

class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(120), nullable=False)
    school = Column(String(160), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    teacher = relationship("User", back_populates="classrooms")
    students = relationship("Student", back_populates="classroom", cascade="all, delete-orphan")
    scans = relationship("ScanSession", back_populates="classroom", cascade="all, delete-orphan")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    student_code = Column(String(80), nullable=False)
    name = Column(String(160), nullable=False)
    classroom = relationship("Classroom", back_populates="students")
    scans = relationship("ScanSession", back_populates="student")
    __table_args__ = (UniqueConstraint("classroom_id", "student_code", name="uq_student_code_class"),)

class AnswerCard(Base):
    __tablename__ = "answer_cards"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(160), nullable=False)
    block = Column(Integer, nullable=False)
    question_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    teacher = relationship("User", back_populates="cards")
    key = relationship("AnswerKey", back_populates="card", uselist=False, cascade="all, delete-orphan")
    scans = relationship("ScanSession", back_populates="card")

class AnswerKey(Base):
    __tablename__ = "answer_keys"
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("answer_cards.id"), unique=True, nullable=False)
    answers_json = Column(Text, nullable=False)
    card = relationship("AnswerCard", back_populates="key")

class ScanSession(Base):
    __tablename__ = "scan_sessions"
    id = Column(Integer, primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    card_id = Column(Integer, ForeignKey("answer_cards.id"), nullable=False)
    status = Column(String(30), default="processed")
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    blank_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    classroom = relationship("Classroom", back_populates="scans")
    student = relationship("Student", back_populates="scans")
    card = relationship("AnswerCard", back_populates="scans")
    answers = relationship("ScanAnswer", back_populates="scan", cascade="all, delete-orphan")

class ScanAnswer(Base):
    __tablename__ = "scan_answers"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scan_sessions.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    detected_option = Column(String(10), nullable=True)  # letra (A-E) ou "MULT"
    correct = Column(Boolean, nullable=True)
    scan = relationship("ScanSession", back_populates="answers")
