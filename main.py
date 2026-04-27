# main.py
# FleetUp completo + Dashboard Financiero + Gastos + Vencimientos + Alertas Automáticas

import os
from datetime import datetime

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

app = FastAPI()

# =========================================================
# BASE DE DATOS
# =========================================================

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


# =========================================================
# MODELOS
# =========================================================

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

    expenses = relationship(
        "VehicleExpense",
        back_populates="vehicle",
        cascade="all, delete-orphan"
    )

    deadlines = relationship(
        "VehicleDeadline",
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


class VehicleExpense(Base):
    __tablename__ = "vehicle_expenses"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    tipo_gasto = Column(String)
    monto = Column(String, default="0")
    fecha = Column(String, default="")
    observaciones = Column(String, default="")

    vehicle = relationship("Vehicle", back_populates="expenses")


class VehicleDeadline(Base):
    __tablename__ = "vehicle_deadlines"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    tipo = Column(String)  # patente / seguro / VTV / cubiertas / service
    fecha_vencimiento = Column(String)
    monto = Column(String, default="0")
    observaciones = Column(String, default="")

    vehicle = relationship("Vehicle", back_populates="deadlines")


Base.metadata.create_all(bind=engine)


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def to_number(valor):
    try:
        limpio = str(valor)\
            .replace("$", "")\
            .replace(".", "")\
            .replace(",", "")\
            .strip()

        return int(limpio) if limpio else 0
    except:
        return 0


def dias_para_vencer(fecha_texto):
    try:
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d")
        hoy = datetime.now()
        diferencia = (fecha - hoy).days
        return diferencia
    except:
        return None


def calcular_alerta_service(vehicle):
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


def calcular_alerta_vencimiento(deadline):
    dias = dias_para_vencer(deadline.fecha_vencimiento)

    if dias is None:
        return "⚪ Sin fecha válida"

    if dias < 0:
        return "🔴 Vencido"
    elif dias <= 30:
        return f"🟡 Vence en {dias} días"
    else:
        return f"🟢 OK ({dias} días)"


# =========================================================
# HTML BASE
# =========================================================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>FleetUp</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>

<body style="font-family: Arial; padding:20px; max-width:1000px; margin:auto;">

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


# =========================================================
# HOME
# =========================================================

@app.get("/", response_class=HTMLResponse)
def home():
    db = SessionLocal()
    vehicles = db.query(Vehicle).all()

    total_ingresos = 0
    total_services = 0
    total_gastos_extra = 0

    html_vehicles = ""

    for v in vehicles:
        alerta_texto, alerta_color = calcular_alerta_service(v)

        ingreso_mensual = to_number(v.valor_mensual)
        gasto_services = sum(to_number(s.costo) for s in v.services)
        gasto_extra = sum(to_number(e.monto) for e in v.expenses)

        ganancia = ingreso_mensual - gasto_services - gasto_extra

        total_ingresos += ingreso_mensual
        total_services += gasto_services
        total_gastos_extra += gasto_extra

        services_html = ""
        expenses_html = ""
        deadlines_html = ""

        for s in v.services:
            services_html += f"""
            <li>
                {s.fecha} | {s.kilometraje} km |
                {s.tipo_service} |
                ${s.costo} |
                {s.observaciones}
            </li>
            """

        for e in v.expenses:
            expenses_html += f"""
            <li>
                {e.tipo_gasto} |
                ${e.monto} |
                {e.fecha} |
                {e.observaciones}
            </li>
            """

        for d in v.deadlines:
            estado = calcular_alerta_vencimiento(d)

            deadlines_html += f"""
            <li>
                <strong>{d.tipo}</strong> |
                vence: {d.fecha_vencimiento} |
                monto: ${d.monto} |
                {estado} |
                {d.observaciones}
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
            <p><strong>Gasto services:</strong> ${gasto_services}</p>
            <p><strong>Gastos extra:</strong> ${gasto_extra}</p>
            <p><strong>Ganancia estimada:</strong> ${ganancia}</p>

            <hr>

            <h3>💸 Agregar gasto financiero</h3>

            <form method="post" action="/add_expense">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p>
                    <select name="tipo_gasto" required>
                        <option value="">Seleccionar</option>
                        <option>Patente</option>
                        <option>Seguro</option>
                        <option>VTV/BTV</option>
                        <option>Cubiertas</option>
                        <option>Otros</option>
                    </select>
                </p>

                <p><input name="monto" placeholder="Monto" required></p>
                <p><input name="fecha" type="date"></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>

                <button type="submit">Guardar gasto</button>
            </form>

            <h4>📋 Historial gastos</h4>
            <ul>
                {expenses_html}
            </ul>

            <hr>

            <h3>📅 Agregar vencimiento</h3>

            <form method="post" action="/add_deadline">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p>
                    <select name="tipo" required>
                        <option value="">Seleccionar</option>
                        <option>Patente</option>
                        <option>Seguro</option>
                        <option>VTV/BTV</option>
                        <option>Cubiertas</option>
                        <option>Service</option>
                    </select>
                </p>

                <p><input name="fecha_vencimiento" type="date" required></p>
                <p><input name="monto" placeholder="Monto"></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>

                <button type="submit">Guardar vencimiento</button>
            </form>

            <h4>📋 Próximos vencimientos</h4>
            <ul>
                {deadlines_html}
            </ul>

            <hr>

            <h3>🛠 Registrar service</h3>

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

        </details>
        """

    dashboard_general = f"""
    <div style="background:#f8f9fa; padding:20px; border-radius:10px;">
        <h2>📊 Resumen General</h2>

        <p><strong>Facturación mensual total:</strong> ${total_ingresos}</p>
        <p><strong>Gasto total services:</strong> ${total_services}</p>
        <p><strong>Gastos financieros:</strong> ${total_gastos_extra}</p>
        <p><strong>Ganancia total estimada:</strong>
        ${total_ingresos - total_services - total_gastos_extra}</p>
    </div>
    """

    db.close()

    return HTML.format(
        dashboard_general=dashboard_general,
        vehicles=html_vehicles
    )


# =========================================================
# RUTAS
# =========================================================

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

    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id
    ).first()

    if vehicle:
        vehicle.kilometros = kilometraje

    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)


@app.post("/add_expense")
def add_expense(
    vehicle_id: int = Form(...),
    tipo_gasto: str = Form(...),
    monto: str = Form(...),
    fecha: str = Form(""),
    observaciones: str = Form("")
):
    db = SessionLocal()

    nuevo = VehicleExpense(
        vehicle_id=vehicle_id,
        tipo_gasto=tipo_gasto,
        monto=monto,
        fecha=fecha,
        observaciones=observaciones
    )

    db.add(nuevo)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)


@app.post("/add_deadline")
def add_deadline(
    vehicle_id: int = Form(...),
    tipo: str = Form(...),
    fecha_vencimiento: str = Form(...),
    monto: str = Form("0"),
    observaciones: str = Form("")
):
    db = SessionLocal()

    nuevo = VehicleDeadline(
        vehicle_id=vehicle_id,
        tipo=tipo,
        fecha_vencimiento=fecha_vencimiento,
        monto=monto,
        observaciones=observaciones
    )

    db.add(nuevo)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)