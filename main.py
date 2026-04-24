import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

app = FastAPI()

# =========================
# BASE DE DATOS
# =========================

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vehicles.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =========================
# MODELOS
# =========================

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    patente = Column(String, unique=True)
    modelo = Column(String)
    kilometros = Column(Integer)

    empresa_asignada = Column(String, default="")
    fecha_asignacion = Column(String, default="")
    km_asignacion = Column(Integer, default=0)
    valor_mensual = Column(String, default="")

    services = relationship("Service", back_populates="vehicle")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    fecha = Column(String)
    kilometraje = Column(Integer)
    tipo_service = Column(String)
    costo = Column(String)
    observaciones = Column(String)

    vehicle = relationship("Vehicle", back_populates="services")


Base.metadata.create_all(bind=engine)

# =========================
# HTML
# =========================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FleetUp</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: Arial; padding: 20px;">

<h1>🚗 FleetUp</h1>

<h2>Agregar vehículo</h2>

<form method="post" action="/add_vehicle">
    <p><input name="patente" placeholder="Patente" required></p>
    <p><input name="modelo" placeholder="Modelo" required></p>
    <p><input name="kilometros" type="number" placeholder="Kilómetros actuales" required></p>

    <h3>Asignación comercial</h3>

    <p><input name="empresa_asignada" placeholder="Empresa asignada"></p>
    <p><input name="fecha_asignacion" placeholder="Fecha asignación"></p>
    <p><input name="km_asignacion" type="number" placeholder="KM asignación"></p>
    <p><input name="valor_mensual" placeholder="Valor mensual"></p>

    <button type="submit">Guardar vehículo</button>
</form>

<hr>

<h2>Vehículos</h2>

{vehicles}

</body>
</html>
"""

# =========================
# HOME
# =========================

@app.get("/", response_class=HTMLResponse)
def home():
    db = SessionLocal()
    vehicles = db.query(Vehicle).all()

    html_vehicles = ""

    for v in vehicles:
        services_html = ""

        for s in v.services:
            services_html += f"""
            <li>
                {s.fecha} | {s