from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import List
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import models
from database import get_db, init_db
import cloudinary.uploader
import os

app = FastAPI(title="Plataforma Web de Autoestudio", version="1.0.0")

# CORS para conectar con el Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "tu_clave_secreta_super_segura_cambiar_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pass_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.on_event("startup")
def startup_event():
    init_db(models)

# --- 1. AUTENTICACIÓN FLEXIBLE ---
auth_router = APIRouter(prefix="/auth", tags=["Autenticación"])

class LoginRequest(BaseModel):
    login_identifier: str
    password: str

@auth_router.post("/login")
def login_for_access_token(form_data: LoginRequest, db = Depends(get_db)):
    user = db.query(models.User).filter(
        (models.User.username == form_data.login_identifier) | 
        (models.User.email == form_data.login_identifier)
    ).first()

    if not user or not pass_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    to_encode = {"sub": user.username, "role": user.role}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": encoded_jwt, 
        "token_type": "bearer",
        "user": {"username": user.username, "email": user.email, "role": user.role}
    }

app.include_router(auth_router)

# --- 2. CARGA DE CURSOS Y PANEL ADMIN ---
admin_router = APIRouter(prefix="/admin", tags=["Administración"])

class LessonSchema(BaseModel):
    title: str
    duration_minutes: int
    order_index: int
    video_url: str
    audio_url: str
    visual_resource_url: str

class OptionSchema(BaseModel):
    option_text: str
    is_correct: bool

class QuestionSchema(BaseModel):
    question_text: str
    order_index: int
    options: List[OptionSchema]

class QuizSchema(BaseModel):
    title: str
    passing_score: float = 70.0
    questions: List[QuestionSchema]

class ModuleSchema(BaseModel):
    title: str
    order_index: int
    lessons: List[LessonSchema]
    quiz: QuizSchema = None

class CourseUploadSchema(BaseModel):
    title: str
    description: str
    duration_hours: int = Field(..., le=12, description="Límite máximo de 12 horas")
    cover_image: str
    modules: List[ModuleSchema]

@admin_router.post("/courses/upload")
def upload_course_package(course_data: CourseUploadSchema, db = Depends(get_db)):
    try:
        new_course = models.Course(
            title=course_data.title, description=course_data.description,
            duration_hours=course_data.duration_hours, cover_image=course_data.cover_image
        )
        db.add(new_course)
        db.commit()
        db.refresh(new_course)

        for mod_data in course_data.modules:
            new_module = models.Module(
                course_id=new_course.id, title=mod_data.title, order_index=mod_data.order_index
            )
            db.add(new_module)
            db.commit()
            db.refresh(new_module)

            for les_data in mod_data.lessons:
                new_lesson = models.Lesson(
                    module_id=new_module.id, title=les_data.title, duration_minutes=les_data.duration_minutes,
                    order_index=les_data.order_index, video_url=les_data.video_url,
                    audio_url=les_data.audio_url, visual_resource_url=les_data.visual_resource_url
                )
                db.add(new_lesson)
            
            if mod_data.quiz:
                new_quiz = models.Quiz(
                    module_id=new_module.id, title=mod_data.quiz.title, passing_score=mod_data.quiz.passing_score
                )
                db.add(new_quiz)
                db.commit()
                db.refresh(new_quiz)

                for q_data in mod_data.quiz.questions:
                    new_q = models.Question(
                        quiz_id=new_quiz.id, question_text=q_data.question_text, order_index=q_data.order_index
                    )
                    db.add(new_q)
                    db.commit()
                    db.refresh(new_q)

                    for opt_data in q_data.options:
                        new_opt = models.Option(
                            question_id=new_q.id, option_text=opt_data.option_text, is_correct=opt_data.is_correct
                        )
                        db.add(new_opt)

            db.commit()

        return {"status": "success", "message": f"Curso '{new_course.title}' cargado correctamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@admin_router.get("/metrics")
def get_metrics(db = Depends(get_db)):
    return {
        "total_courses": db.query(models.Course).count(),
        "total_users": db.query(models.User).count(),
        "total_completed_lessons": db.query(models.UserProgress).filter_by(is_completed=True).count()
    }

app.include_router(admin_router)