# main.py COMPLETO con alertas automáticas de service
# Regla:
# 🟡 Amarillo desde +13.000 km desde último service
# 🔴 Rojo desde +14.000 km desde último service
# 🟢 Verde antes de eso

# (Pegar reemplazando TODO el archivo main.py actual)

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vehicles.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

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

    services = relationship(
        "Service",
        back_populates="vehicle",
        cascade="all, delete-orphan"
    )


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
# ALERTAS SERVICE
# =========================

def calcular_alerta(vehicle):
    if not vehicle.services:
        return "🟢 Sin services cargados", "#d4edda"

    ultimo_service = max(vehicle.services, key=lambda s: s.kilometraje)
    km_desde_service = vehicle.kilometros - ultimo_service.kilometraje

    if km_desde_service >= 14000:
        return "🔴 Service vencido", "#f8d7da"

    elif km_desde_service >= 13000:
        return "🟡 Próximo service", "#fff3cd"

    else:
        return "🟢 Todo OK", "#d4edda"


# =========================
# HTML BASE
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
        alerta_texto, alerta_color = calcular_alerta(v)

        services_html = ""

        for s in v.services:
            services_html += f"""
            <li>
                {s.fecha} | {s.kilometraje} km |
                {s.tipo_service} |
                ${s.costo} |
                {s.observaciones}

                <form method="post" action="/delete_service" style="display:inline;">
                    <input type="hidden" name="service_id" value="{s.id}">
                    <button type="submit">🗑 Eliminar service</button>
                </form>
            </li>
            """

        html_vehicles += f"""
        <div style="
            border:1px solid #ccc;
            padding:15px;
            margin-bottom:20px;
            border-radius:10px;
            background:{alerta_color};
        ">

            <h3>{v.patente} - {v.modelo}</h3>

            <h2>{alerta_texto}</h2>

            <p><strong>KM actuales:</strong> {v.kilometros}</p>

            <h4>🏢 Asignación comercial</h4>
            <p><strong>Empresa:</strong> {v.empresa_asignada or "-"}</p>
            <p><strong>Fecha asignación:</strong> {v.fecha_asignacion or "-"}</p>
            <p><strong>KM asignación:</strong> {v.km_asignacion}</p>
            <p><strong>Valor mensual:</strong> {v.valor_mensual or "-"}</p>

            <form method="post" action="/update_km">
                <input type="hidden" name="vehicle_id" value="{v.id}">
                <input name="nuevo_km" type="number" placeholder="Nuevo KM" required>
                <button type="submit">Actualizar KM</button>
            </form>

            <form method="post" action="/edit_vehicle">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p><input name="patente" value="{v.patente}" required></p>
                <p><input name="modelo" value="{v.modelo}" required></p>
                <p><input name="empresa_asignada" value="{v.empresa_asignada}"></p>
                <p><input name="fecha_asignacion" value="{v.fecha_asignacion}"></p>
                <p><input name="km_asignacion" type="number" value="{v.km_asignacion}"></p>
                <p><input name="valor_mensual" value="{v.valor_mensual}"></p>

                <button type="submit">✏️ Editar vehículo</button>
            </form>

            <form method="post" action="/delete_vehicle">
                <input type="hidden" name="vehicle_id" value="{v.id}">
                <button type="submit">🗑 Eliminar vehículo</button>
            </form>

            <hr>

            <h4>🛠 Registrar service</h4>

            <form method="post" action="/add_service">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p><input name="fecha" placeholder="Fecha" required></p>
                <p><input name="kilometraje" type="number" placeholder="Kilometraje" required></p>
                <p><input name="tipo_service" placeholder="Tipo de service" required></p>
                <p><input name="costo" placeholder="Costo" required></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>

                <button type="submit">Guardar service</button>
            </form>

            <h4>📋 Historial de services</h4>
            <ul>
                {services_html}
            </ul>

        </div>
        """

    db.close()
    return HTML.format(vehicles=html_vehicles)