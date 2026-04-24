import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI()

# =========================
# BASE DE DATOS (POSTGRES / SQLITE fallback)
# =========================

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vehicles.db")

# Render usa postgres://, SQLAlchemy necesita postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =========================
# MODELO
# =========================

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    patente = Column(String, unique=True)
    modelo = Column(String)
    kilometros = Column(Integer)
    ultimo_service = Column(String)
    proximo_service = Column(String)

Base.metadata.create_all(bind=engine)

# =========================
# FRONT SIMPLE
# =========================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FleetUp</title>
</head>
<body>
    <h1>🚗 FleetUp</h1>

    <h2>Agregar vehículo</h2>
    <form method="post" action="/add">
        <input name="patente" placeholder="Patente" required>
        <input name="modelo" placeholder="Modelo" required>
        <input name="kilometros" type="number" placeholder="Kilómetros" required>
        <button type="submit">Guardar</button>
    </form>

    <h2>Vehículos</h2>
    <ul>
    {vehicles}
    </ul>
</body>
</html>
"""

# =========================
# ENDPOINTS
# =========================

@app.get("/", response_class=HTMLResponse)
def home():
    db = SessionLocal()
    vehicles = db.query(Vehicle).all()
    db.close()

    html_list = ""
    for v in vehicles:
        html_list += f"<li>{v.patente} - {v.modelo} - {v.kilometros} km</li>"

    return HTML.format(vehicles=html_list)


@app.post("/add")
def add_vehicle(
    patente: str = Form(...),
    modelo: str = Form(...),
    kilometros: int = Form(...)
):
    db = SessionLocal()
    vehicle = Vehicle(
        patente=patente,
        modelo=modelo,
        kilometros=kilometros,
        ultimo_service="",
        proximo_service=""
    )
    db.add(vehicle)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)