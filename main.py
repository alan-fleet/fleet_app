# main.py
# FleetUp + Dashboard Financiero + Gastos Separados por Categoria + Vencimientos + Desplegables
# FASE 4 COMPLETA - segura sobre tu base real

import os
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

app = FastAPI()

# =========================================================
# DATABASE
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

    vehicle = relationship(
        "Vehicle",
        back_populates="services"
    )

class VehicleExpense(Base):
    __tablename__ = "vehicle_expenses"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    categoria = Column(String)
    fecha = Column(String, default="")
    monto = Column(String, default="0")
    observaciones = Column(String, default="")

    vehicle = relationship(
        "Vehicle",
        back_populates="expenses"
    )

class VehicleDeadline(Base):
    __tablename__ = "vehicle_deadlines"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    tipo = Column(String)
    fecha_vencimiento = Column(String, default="")
    observaciones = Column(String, default="")

    vehicle = relationship(
        "Vehicle",
        back_populates="deadlines"
    )

Base.metadata.create_all(bind=engine)

# =========================================================
# AUXILIARES
# =========================================================

def to_number(valor):
    try:
        limpio = (
            str(valor)
            .replace("$", "")
            .replace(".", "")
            .replace(",", "")
            .strip()
        )
        return int(limpio) if limpio else 0
    except:
        return 0

def calcular_alerta(vehicle):
    if not vehicle.services:
        if vehicle.kilometros >= 13000:
            return "Proximo service", "#fff3cd", "proximo"
        return "Sin services cargados", "#d4edda", "ok"

    ultimo_service = max(
        vehicle.services,
        key=lambda s: s.kilometraje
    )

    km_desde_service = vehicle.kilometros - ultimo_service.kilometraje

    if km_desde_service >= 14000:
        return "Service vencido", "#f8d7da", "vencido"
    elif km_desde_service >= 13000:
        return "Proximo service", "#fff3cd", "proximo"
    else:
        return "Todo OK", "#d4edda", "ok"

def alerta_vencimiento(fecha):
    try:
        hoy = datetime.today()
        venc = datetime.strptime(fecha, "%Y-%m-%d")
        dias = (venc - hoy).days

        if dias < 0:
            return "Vencido"
        elif dias <= 30:
            return "Proximo a vencer"
        else:
            return "Vigente"
    except:
        return "Sin fecha valida"

def filtrar_categoria(items, nombre):
    return [x for x in items if x.categoria == nombre]

def filtrar_deadline(items, nombre):
    return [x for x in items if x.tipo == nombre]

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

<body style="font-family:Arial; padding:20px; max-width:1100px; margin:auto;">

<h1>FleetUp</h1>

{dashboard_general}

<hr>

<h2>Agregar vehiculo</h2>

<form method="post" action="/add_vehicle">
    <p><input name="patente" placeholder="Patente" required></p>
    <p><input name="modelo" placeholder="Modelo" required></p>
    <p><input name="kilometros" type="number" placeholder="KM actuales" required></p>

    <h3>Asignacion comercial</h3>
    <p><input name="empresa_asignada" placeholder="Empresa asignada"></p>
    <p><input name="fecha_asignacion" placeholder="Fecha asignacion"></p>
    <p><input name="km_asignacion" type="number" placeholder="KM asignacion"></p>
    <p><input name="valor_mensual" placeholder="Valor mensual"></p>

    <button type="submit">Guardar vehiculo</button>
</form>

<hr>

<h2>Vehiculos</h2>

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
    total_gastos = 0
    html_vehicles = ""

    categorias = [
        "Patente",
        "Seguro",
        "VTV/BTV",
        "Cubiertas",
        "Otros"
    ]

    for v in vehicles:
        alerta_texto, alerta_color, alerta_tipo = calcular_alerta(v)

        ingreso_mensual = to_number(v.valor_mensual)
        gasto_services = sum(to_number(s.costo) for s in v.services)
        gasto_extra = sum(to_number(e.monto) for e in v.expenses)

        gasto_total = gasto_services + gasto_extra
        ganancia = ingreso_mensual - gasto_total

        total_ingresos += ingreso_mensual
        total_gastos += gasto_total

        services_html = ""
        for s in v.services:
            services_html += f"""
            <li>
                {s.fecha} | {s.kilometraje} km |
                {s.tipo_service} | ${s.costo}
            </li>
            """

        categorias_html = ""

        for cat in categorias:
            gastos_cat = filtrar_categoria(v.expenses, cat)
            venc_cat = filtrar_deadline(v.deadlines, cat)

            gastos_html = ""
            for g in gastos_cat:
                gastos_html += f"""
                <li>{g.fecha} | ${g.monto} | {g.observaciones}</li>
                """

            venc_html = ""
            for d in venc_cat:
                estado = alerta_vencimiento(d.fecha_vencimiento)
                venc_html += f"""
                <li>{d.fecha_vencimiento} | {estado} | {d.observaciones}</li>
                """

            categorias_html += f"""
            <details style="
                margin-bottom:15px;
                border:1px solid #ddd;
                border-radius:8px;
                padding:10px;
                background:#fafafa;
            ">
                <summary style="
                    cursor:pointer;
                    font-size:18px;
                    font-weight:bold;
                ">
                    {cat}
                </summary>

                <h4>Historial de gastos</h4>
                <ul>
                    {gastos_html if gastos_html else "<li>Sin registros</li>"}
                </ul>

                <h4>Vencimientos</h4>
                <ul>
                    {venc_html if venc_html else "<li>Sin vencimientos</li>"}
                </ul>
            </details>
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

            <h3>Dashboard financiero</h3>
            <p><strong>Ingreso mensual:</strong> ${ingreso_mensual}</p>
            <p><strong>Gasto total:</strong> ${gasto_total}</p>
            <p><strong>Ganancia:</strong> ${ganancia}</p>

            <hr>

            <h3>Registrar service</h3>

            <form method="post" action="/add_service">
                <input type="hidden" name="vehicle_id" value="{v.id}">
                <p><input name="fecha" placeholder="Fecha" required></p>
                <p><input name="kilometraje" type="number" placeholder="Kilometraje" required></p>
                <p><input name="tipo_service" placeholder="Tipo service" required></p>
                <p><input name="costo" placeholder="Costo" required></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>
                <button type="submit">Guardar service</button>
            </form>

            <h4>Historial services</h4>
            <ul>{services_html}</ul>

            <hr>

            <h3>Agregar gasto</h3>

            <form method="post" action="/add_expense">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p>
                    <select name="categoria" required>
                        <option value="">Seleccionar categoria</option>
                        <option value="Patente">Patente</option>
                        <option value="Seguro">Seguro</option>
                        <option value="VTV/BTV">VTV/BTV</option>
                        <option value="Cubiertas">Cubiertas</option>
                        <option value="Otros">Otros</option>
                    </select>
                </p>

                <p><input name="fecha" placeholder="Fecha"></p>
                <p><input name="monto" placeholder="Monto" required></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>

                <button type="submit">Guardar gasto</button>
            </form>

            <hr>

            <h3>Agregar vencimiento</h3>

            <form method="post" action="/add_deadline">
                <input type="hidden" name="vehicle_id" value="{v.id}">

                <p>
                    <select name="tipo" required>
                        <option value="">Seleccionar tipo</option>
                        <option value="Patente">Patente</option>
                        <option value="Seguro">Seguro</option>
                        <option value="VTV/BTV">VTV/BTV</option>
                        <option value="Cubiertas">Cubiertas</option>
                        <option value="Otros">Otros</option>
                    </select>
                </p>

                <p><input name="fecha_vencimiento" type="date" required></p>
                <p><input name="observaciones" placeholder="Observaciones"></p>

                <button type="submit">Guardar vencimiento</button>
            </form>

            <hr>

            {categorias_html}

        </details>
        """

    dashboard_general = f"""
    <div style="background:#f8f9fa; padding:20px; border-radius:10px;">
        <h2>Resumen General</h2>
        <p><strong>Facturacion mensual:</strong> ${total_ingresos}</p>
        <p><strong>Gastos totales:</strong> ${total_gastos}</p>
        <p><strong>Ganancia total:</strong> ${total_ingresos - total_gastos}</p>
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

    nuevo = Service(
        vehicle_id=vehicle_id,
        fecha=fecha,
        kilometraje=kilometraje,
        tipo_service=tipo_service,
        costo=costo,
        observaciones=observaciones
    )

    db.add(nuevo)

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
    categoria: str = Form(...),
    fecha: str = Form(""),
    monto: str = Form(...),
    observaciones: str = Form("")
):
    db = SessionLocal()

    nuevo = VehicleExpense(
        vehicle_id=vehicle_id,
        categoria=categoria,
        fecha=fecha,
        monto=monto,
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
    observaciones: str = Form("")
):
    db = SessionLocal()

    nuevo = VehicleDeadline(
        vehicle_id=vehicle_id,
        tipo=tipo,
        fecha_vencimiento=fecha_vencimiento,
        observaciones=observaciones
    )

    db.add(nuevo)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=302)

@app.post("/delete_vehicle")
def delete_vehicle(
    vehicle_id: int = Form(...)
):
    db = SessionLocal()

    item = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id
    ).first()

    if item:
        db.delete(item)
        db.commit()

    db.close()

    return RedirectResponse("/", status_code=302)

@app.post("/delete_service")
def delete_service(
    service_id: int = Form(...)
):
    db = SessionLocal()

    item = db.query(Service).filter(
        Service.id == service_id
    ).first()

    if item:
        db.delete(item)
        db.commit()

    db.close()

    return RedirectResponse("/", status_code=302)

@app.post("/delete_expense")
def delete_expense(
    expense_id: int = Form(...)
):
    db = SessionLocal()

    item = db.query(VehicleExpense).filter(
        VehicleExpense.id == expense_id
    ).first()

    if item:
        db.delete(item)
        db.commit()

    db.close()

    return RedirectResponse("/", status_code=302)

@app.post("/delete_deadline")
def delete_deadline(
    deadline_id: int = Form(...)
):
    db = SessionLocal()

    item = db.query(VehicleDeadline).filter(
        VehicleDeadline.id == deadline_id
    ).first()

    if item:
        db.delete(item)
        db.commit()

    db.close()

    return RedirectResponse("/", status_code=302)