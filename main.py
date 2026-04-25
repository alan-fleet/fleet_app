# main.py
# FleetUp PRO — Financiero mensual + BTV + Services + Alertas + Dashboard

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

app = FastAPI()

# =====================================================
# BASE DE DATOS
# =====================================================

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


# =====================================================
# MODELOS
# =====================================================

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    patente = Column(String, unique=True)
    modelo = Column(String)
    kilometros = Column(Integer)

    empresa_asignada = Column(String, default="")
    fecha_asignacion = Column(String, default="")
    km_asignacion = Column(Integer, default=0)

    # BTV / VTV
    fecha_btv = Column(String, default="")
    vencimiento_btv = Column(String, default="")

    services = relationship(
        "Service",
        back_populates="vehicle",
        cascade="all, delete-orphan"
    )

    finances = relationship(
        "FinancialRecord",
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


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    mes = Column(String)
    anio = Column(String)

    ingreso = Column(String, default="0")
    seguro = Column(String, default="0")
    patente_gasto = Column(String, default="0")
    cubiertas = Column(String, default="0")
    otros_gastos = Column(String, default="0")
    observaciones = Column(String, default="")

    vehicle = relationship("Vehicle", back_populates="finances")


Base.metadata.create_all(bind=engine)


# =====================================================
# FUNCIONES
# =====================================================

def to_number(valor):
    try:
        limpio = str(valor).replace("$", "").replace(".", "").replace(",", "").strip()
        return int(limpio) if limpio else 0
    except:
        return 0


def calcular_alerta_service(vehicle):
    if not vehicle.services:
        if vehicle.kilometros >= 13000:
            return "🟡 Próximo service", "#fff3cd"
        return "🟢 Sin services cargados", "#d4edda"

    ultimo = max(vehicle.services, key=lambda s: s.kilometraje)
    km_desde = vehicle.kilometros - ultimo.kilometraje

    if km_desde >= 14000:
        return "🔴 Service vencido", "#f8d7da"
    elif km_desde >= 13000:
        return "🟡 Próximo service", "#fff3cd"
    return "🟢 Todo OK", "#d4edda"


# =====================================================
# HTML BASE
# =====================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FleetUp PRO</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: Arial; padding: 20px; max-width: 1000px; margin: auto;">

<h1>🚗 FleetUp PRO</h1>

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

    <h3>📄 BTV / VTV</h3>
    <p><input name="fecha_btv" placeholder="Fecha última BTV"></p>
    <p><input name="vencimiento_btv" placeholder="Vencimiento BTV"></p>

    <button type="submit">Guardar vehículo</button>
</form>

<hr>

<h2>Vehículos</h2>

{vehicles}

</body>
</html>
"""


# =====================================================
# HOME
# =====================================================

@app.get("/", response_class=HTMLResponse)
def home():
    db = SessionLocal()
    vehicles = db.query(Vehicle).all()

    total_ingresos = 0
    total_gastos = 0
    html_vehicles = ""

    for v in vehicles:
        alerta_texto, alerta_color = calcular_alerta_service(v)

        costo_services = sum(to_number(s.costo) for s in v.services)

        ingreso_total = sum(to_number(f.ingreso) for f in v.finances)
        seguro_total = sum(to_number(f.seguro) for f in v.finances)
        patente_total = sum(to_number(f.patente_gasto) for f in v.finances)
        cubiertas_total = sum(to_number(f.cubiertas) for f in v.finances)
        otros_total = sum(to_number(f.otros_gastos) for f in v.finances)

        gastos_totales = (
            costo_services
            + seguro_total
            + patente_total
            + cubiertas_total
            + otros_total
        )

        ganancia = ingreso_total - gastos_totales

        total_ingresos += ingreso_total
        total_gastos += gastos_totales

        services_html = ""
        for s in v.services:
            services_html += f"""
            <li>
                {s.fecha} | {s.kilometraje} km |
                {s.tipo_service} |
                ${s.costo} |
                {s.observaciones}
            </li>
            """

        finance_html = ""
        for f in v.finances:
            finance_html += f"""
            <li>
                {f.mes}/{f.anio} |
                Ingreso: ${f.ingreso} |
                Seguro: ${f.seguro} |
                Patente: ${f.patente_gasto} |
                Cubiertas: ${f.cubiertas} |
                Otros: ${f.otros_gastos}
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

            <h3>📄 BTV / VTV</h3>
            <p><strong>Última BTV:</strong> {v.fecha_btv or "-"}</p>
            <p><strong>Vencimiento:</strong> {v.vencimiento_btv or "-"}</p>

            <h3>💰 Dashboard financiero</h3>
            <p><strong>Ingreso total:</strong> ${ingreso_total}</p>
            <p><strong>Gastos totales:</strong> ${gastos_totales}</p>
            <p><strong>Ganancia neta:</strong> ${ganancia}</p>

            <h4>➕ Agregar registro financiero mensual</h4>

            <form method="post" action="/add_financial_record">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p><input name="mes" placeholder="Mes" required></p>
                <p><input name="anio" placeholder="Año" required></p>
                <p><input name="ingreso" placeholder="Ingreso mensual"></p>
                <p><input name="seguro" placeholder="Seguro"></p>
                <p><input name="patente_gasto" placeholder="Patente"></p>
                <p><input name="cubiertas" placeholder="Cubiertas"></p>
                <p><input name="otros_gastos" placeholder="Otros gastos"></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>

                <button type="submit">Guardar financiero</button>
            </form>

            <h4>📋 Historial financiero</h4>
            <ul>
                {finance_html}
            </ul>

            <h4>🛠 Services</h4>

            <form method="post" action="/add_service">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p><input name="fecha" placeholder="Fecha" required></p>
                <p><input name="kilometraje" type="number" placeholder="Kilometraje" required></p>
                <p><input name="tipo_service" placeholder="Tipo de service" required></p>
                <p><input name="costo" placeholder="Costo" required></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>

                <button type="submit">Guardar service</button>
            </form>

            <ul>
                {services_html}
            </ul>
        </details>
        """

    dashboard_general = f"""
    <div style="background:#f8f9fa; padding:20px; border-radius:10px;">
        <h2>📊 Resumen General</h2>
        <p><strong>Ingresos totales:</strong> ${total_ingresos}</p>
        <p><strong>Gastos totales:</strong> ${total_gastos}</p>
        <p><strong>Ganancia neta total:</strong> ${total_ingresos - total_gastos}</p>
    </div>
    """

    db.close()

    return HTML.format(
        dashboard_general=dashboard_general,
        vehicles=html_vehicles
    )


# =====================================================
# RUTAS
# =====================================================

@app.post("/add_vehicle")
def add_vehicle(
    patente: str = Form(...),
    modelo: str = Form(...),
    kilometros: int = Form(...),
    empresa_asignada: str = Form(""),
    fecha_asignacion: str = Form(""),
    km_asignacion: int = Form(0),
    fecha_btv: str = Form(""),
    vencimiento_btv: str = Form("")
):
    db = SessionLocal()

    nuevo = Vehicle(
        patente=patente,
        modelo=modelo,
        kilometros=kilometros,
        empresa_asignada=empresa_asignada,
        fecha_asignacion=fecha_asignacion,
        km_asignacion=km_asignacion,
        fecha_btv=fecha_btv,
        vencimiento_btv=vencimiento_btv
    )

    db.add(nuevo)
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

    nuevo = Service(
        vehicle_id=vehicle_id,
        fecha=fecha,
        kilometraje=kilometraje,
        tipo_service=tipo_service,
        costo=costo,
        observaciones=observaciones
    )

    db.add(nuevo)

    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if vehicle:
        vehicle.kilometros = kilometraje

    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)


@app.post("/add_financial_record")
def add_financial_record(
    vehicle_id: int = Form(...),
    mes: str = Form(...),
    anio: str = Form(...),
    ingreso: str = Form("0"),
    seguro: str = Form("0"),
    patente_gasto: str = Form("0"),
    cubiertas: str = Form("0"),
    otros_gastos: str = Form("0"),
    observaciones: str = Form("")
):
    db = SessionLocal()

    nuevo = FinancialRecord(
        vehicle_id=vehicle_id,
        mes=mes,
        anio=anio,
        ingreso=ingreso,
        seguro=seguro,
        patente_gasto=patente_gasto,
        cubiertas=cubiertas,
        otros_gastos=otros_gastos,
        observaciones=observaciones
    )

    db.add(nuevo)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)