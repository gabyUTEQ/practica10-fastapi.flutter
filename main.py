import os
import shutil
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 1. CONFIGURACIÓN DE LA BASE DE DATOS (Ajusta usuario, contraseña y nombre de BD)
DATABASE_URL = "mysql+pymysql://root:@localhost:3306/practica10_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. MODELO DE SQLALCHEMY (Coincide con tabla P10_foto)
class FotoDB(Base):
    __tablename__ = "P10_foto"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    descripcion = Column(String(255), nullable=False)
    ruta_foto = Column(String(255), nullable=False)
    fecha = Column(TIMESTAMP, server_default=func.now())

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# 3. ESQUEMAS DE VALIDACIÓN PYDANTIC
class FotoResponse(BaseModel):
    id: int
    descripcion: str
    ruta_foto: str
    fecha: Optional[datetime] = None

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    msg: str
    foto: FotoResponse

# 4. INICIALIZACIÓN DE FASTAPI Y CORS
app = FastAPI(title="API Gestión de Imágenes")

# Habilitar CORS para permitir peticiones desde Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear carpeta uploads si no existe y montarla como archivos estáticos
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Dependencia para obtener la sesión de BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 5. ENDPOINTS REST
@app.post("/fotos", response_model=UploadResponse)
async def subir_foto(
    descripcion: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Validar que el archivo sea una imagen (MIME type)
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen válida.")

    # Definir ruta de guardado
    ruta_archivo = f"uploads/{file.filename}"

    # Guardar archivo físicamente en el servidor usando shutil
    with open(ruta_archivo, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Guardar registro en MySQL
    nueva_foto = FotoDB(
        descripcion=descripcion,
        ruta_foto=ruta_archivo
    )
    db.add(nueva_foto)
    db.commit()
    db.refresh(nueva_foto)

    return {
        "msg": "Foto subida correctamente",
        "foto": nueva_foto
    }

@app.get("/fotos", response_model=List[FotoResponse])
def listar_fotos(db: Session = Depends(get_db)):
    fotos = db.query(FotoDB).order_by(FotoDB.id.desc()).all()
    return fotos
