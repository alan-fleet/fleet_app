import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
# MODELO VEHÍCULO
# =========================

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    patente = Column(String, unique=True)
    modelo = Column(String)
    kilometros = Column(Integer)

    ultimo_service = Column(String, default="")
    proximo_service = Column(String, default="")

    empresa_asignada = Column(String, default="")
    fecha_asignacion = Column(String, default="")
    km_asignacion = Column(Integer, default=0)
    valor_mensual = Column(String, default="")

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

    <form method="post" action="/add">
        <p><input name="patente" placeholder="Patente" required></p>
        <p><input name="modelo" placeholder="Modelo" required></p>
        <p><input name="kilometros" type="number" placeholder="Kilómetros actuales" required></p>

        <h3>Asignación comercial</h3>

        <p><input name="empresa_asignada" placeholder="Empresa asignada"></p>
        <p><input name="fecha_asignacion" placeholder="Fecha asignación (dd/mm/aaaa)"></p>
        <p><input name="km_asignacion" type="number" placeholder="KM al asignar"></p>
        <p><input name="valor_mensual" placeholder="Valor mensual alquiler"></p>

        <button type="submit">Guardar</button>
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
    db.close()

    html_vehicles = ""

    for v in vehicles:
        html_vehicles += f"""
        <div style="border:1px solid #ccc; padding:15px; margin-bottom:15px; border-radius:10px;">
            <h3>{v.patente} - {v.modelo}</h3>

            <p><strong>Kilómetros actuales:</strong> {v.kilometros} km</p>

            <h4>🏢 Asignación comercial</h4>

            <p><strong>Empresa:</strong> {v.empresa_asignada or "-"}</p>
            <p><strong>Fecha asignación:</strong> {v.fecha_asignacion or "-"}</p>
            <p><strong>KM asignación:</strong> {v.km_asignacion or 0} km</p>
            <p><strong>Valor mensual:</strong> {v.valor_mensual or "-"}</p>
        </div>
        """

    return HTML.format(vehicles=html_vehicles)

# =========================
# AGREGAR VEHÍCULO
# =========================

@app.post("/add")
def add_vehicle(
    patente: str = Form(...),
    modelo: str = Form(...),
    kilometros: int = Form(...),

    empresa_asignada: str = Form(""),
    fecha_asignacion: str = Form(""),
    km_asignacion: int = Form(0),
    valor_mensual: str = Form("")
):
    db = SessionLocal()

    nuevo = Vehicle(
        patente=patente,
        modelo=modelo,
        kilometros=kilometros,

        empresa_asignada=empresa_asignada,
        fecha_asignacion=fecha_asignacion,
        km_asignacion=km_asignacion,
        valor_mensual=valor_mensual
    )

    db.add(nuevo)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)