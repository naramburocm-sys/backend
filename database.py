from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autodidacta.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pass_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db(app_models):
    app_models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        admin_user = db.query(app_models.User).filter_by(role="admin").first()
        if not admin_user:
            hashed_password = pass_context.hash("AdminPassword123*")
            new_admin = app_models.User(
                username="nelson_admin",
                email="naramburo.cm@gmail.com",
                password_hash=hashed_password,
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            print(">>> Usuario administrador inicial creado con éxito: nelson_admin / naramburo.cm@gmail.com")
    except Exception as e:
        print(f"Error al inicializar el usuario administrador: {e}")
    finally:
        db.close()