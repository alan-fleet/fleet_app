# main.py
# FleetUp completo + Dashboard Financiero + Editar + Eliminar + Alertas + Desplegables

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

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
    valor_mensual = Column(String, default="0")

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
    costo = Column(String, default="0")
    observaciones = Column(String, default="")

    vehicle = relationship("Vehicle", back_populates="services")


Base.metadata.create_all(bind=engine)


# =========================
# FUNCIONES AUXILIARES
# =========================

def to_number(valor):
    try:
        limpio = str(valor).replace("$", "").replace(".", "").replace(",", "").strip()
        return int(limpio) if limpio else 0
    except:
        return 0


def calcular_alerta(vehicle):
    if not vehicle.services:
        if vehicle.kilometros >= 13000:
            return "🟡 Próximo service", "#fff3cd"
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
<body style="font-family: Arial; padding: 20px; max-width: 900px; margin: auto;">

<h1>🚗 FleetUp</h1>

{dashboard_general}

<hr>

<h2>Agregar vehículo</h2>

<form method="post" action="/add_vehicle">
    <p><input name="patente" placeholder="Patente" required></p>
    <p><input name="modelo" placeholder="Modelo" required></p>
    <p><input name="kilometros" type="number" placeholder="Kilómetros actuales" required></p>

    <h3>🏢 Asignación comercial</h3>

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

    total_ingresos = 0
    total_gastos = 0
    html_vehicles = ""

    for v in vehicles:
        alerta_texto, alerta_color = calcular_alerta(v)

        ingreso_mensual = to_number(v.valor_mensual)
        gasto_services = sum(to_number(s.costo) for s in v.services)
        ganancia = ingreso_mensual - gasto_services

        total_ingresos += ingreso_mensual
        total_gastos += gasto_services

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
        <details style="
            background:{alerta_color};
            border:1px solid #ccc;
            border-radius:10px;
            padding:15px;
            margin-bottom:20px;
        ">
            <summary style="cursor:pointer; font-size:18px;">
                <strong>{v.patente} - {v.modelo}</strong>
            </summary>

            <h2>{alerta_texto}</h2>

            <p><strong>KM actuales:</strong> {v.kilometros}</p>

            <h3>💰 Dashboard financiero</h3>
            <p><strong>Ingreso mensual:</strong> ${ingreso_mensual}</p>
            <p><strong>Gasto total services:</strong> ${gasto_services}</p>
            <p><strong>Ganancia estimada:</strong> ${ganancia}</p>

            <h3>🏢 Asignación comercial</h3>
            <p><strong>Empresa:</strong> {v.empresa_asignada or "-"}</p>
            <p><strong>Fecha asignación:</strong> {v.fecha_asignacion or "-"}</p>
            <p><strong>KM asignación:</strong> {v.km_asignacion}</p>
            <p><strong>Valor mensual:</strong> {v.valor_mensual}</p>

            <form method="post" action="/update_km">
                <input type="hidden" name="vehicle_id" value="{v.id}">
                <input name="nuevo_km" type="number" placeholder="Nuevo KM" required>
                <button type="submit">Actualizar KM</button>
            </form>

            <hr>

            <h4>✏ Editar vehículo</h4>

            <form method="post" action="/edit_vehicle">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p><input name="patente" value="{v.patente}" required></p>
                <p><input name="modelo" value="{v.modelo}" required></p>
                <p><input name="empresa_asignada" value="{v.empresa_asignada}"></p>
                <p><input name="fecha_asignacion" value="{v.fecha_asignacion}"></p>
                <p><input name="km_asignacion" type="number" value="{v.km_asignacion}"></p>
                <p><input name="valor_mensual" value="{v.valor_mensual}"></p>

                <button type="submit">Guardar cambios</button>
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

            <form method="post" action="/delete_vehicle">
                <input type="hidden" name="vehicle_id" value="{v.id}">
                <button type="submit">🗑 Eliminar vehículo</button>
            </form>

        </details>
        """

    dashboard_general = f"""
    <div style="background:#f8f9fa; padding:20px; border-radius:10px;">
        <h2>📊 Resumen General</h2>
        <p><strong>Facturación mensual total:</strong> ${total_ingresos}</p>
        <p><strong>Gasto total services:</strong> ${total_gastos}</p>
        <p><strong>Ganancia total estimada:</strong> ${total_ingresos - total_gastos}</p>
    </div>
    """

    db.close()

    return HTML.format(
        dashboard_general=dashboard_general,
        vehicles=html_vehicles
    )


# =========================
# RUTAS
# =========================

@app.post("/add_vehicle")
def add_vehicle(
    patente: str = Form(...),
    modelo: str = Form(...),
    kilometros: int = Form(...),
    empresa_asignada: str = Form(""),
    fecha_asignacion: str = Form(""),
    km_asignacion: int = Form(0),
    valor_mensual: str = Form("0")
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


@app.post("/edit_vehicle")
def edit_vehicle(
    vehicle_id: int = Form(...),
    patente: str = Form(...),
    modelo: str = Form(...),
    empresa_asignada: str = Form(""),
    fecha_asignacion: str = Form(""),
    km_asignacion: int = Form(0),
    valor_mensual: str = Form("0")
):
    db = SessionLocal()

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    if vehicle:
        vehicle.patente = patente
        vehicle.modelo = modelo
        vehicle.empresa_asignada = empresa_asignada
        vehicle.fecha_asignacion = fecha_asignacion
        vehicle.km_asignacion = km_asignacion
        vehicle.valor_mensual = valor_mensual
        db.commit()

    db.close()
    return RedirectResponse("/", status_code=302)


@app.post("/update_km")
def update_km(
    vehicle_id: int = Form(...),
    nuevo_km: int = Form(...)
):
    db = SessionLocal()

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    if vehicle:
        vehicle.kilometros = nuevo_km
        db.commit()

    db.close()
    return RedirectResponse("/", status_code=302)


@app.post("/add_service")
def add_service(
    vehicle_id: int = Form(...),
    fecha: str = Form(...),
    kilometraje: int = Form(...),
    tipo_service: str = Form(...),
    costo: str = Form(...),
    observaciones: str = Form("")
):
    db = SessionLocal()

    nuevo_service = Service(
        vehicle_id=vehicle_id,
        fecha=fecha,
        kilometraje=kilometraje,
        tipo_service=tipo_service,
        costo=costo,
        observaciones=observaciones
    )

    db.add(nuevo_service)

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if vehicle:
        vehicle.kilometros = kilometraje

    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)


@app.post("/delete_vehicle")
def delete_vehicle(
    vehicle_id: int = Form(...)
):
    db = SessionLocal()

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    if vehicle:
        db.delete(vehicle)
        db.commit()

    db.close()
    return RedirectResponse("/", status_code=302)


@app.post("/delete_service")
def delete_service(
    service_id: int = Form(...)
):
    db = SessionLocal()

    service = db.query(Service).filter(Service.id == service_id).first()

    if service:
        db.delete(service)
        db.commit()

    db.close()
    return RedirectResponse("/", status_code=302)