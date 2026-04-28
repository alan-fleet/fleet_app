# main.py
# FleetUp + Dashboard Financiero + Gastos Separados por Categoria + Vencimientos + Desplegables
# PASO 4 FINAL: Alertas por email

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, Form, Query
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

<h2>Buscar vehiculos</h2>
<form method="get" action="/" style="background:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:20px;">
    <div style="display:grid; grid-template-columns:2fr 1fr auto auto; gap:10px; align-items:end;">
        <div>
            <label style="font-size:12px; color:#666;">Buscar por patente o modelo</label>
            <input name="q" value="{search_query}" placeholder="Ej: ABC123 o Toyota" style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px;">
        </div>
        <div>
            <label style="font-size:12px; color:#666;">Filtrar por estado</label>
            <select name="filtro" style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px;">
                <option value="todos" {sel_todos}>Todos</option>
                <option value="ok" {sel_ok}>Todo OK</option>
                <option value="proximo" {sel_proximo}>Proximo service</option>
                <option value="vencido" {sel_vencido}>Service vencido</option>
            </select>
        </div>
        <button type="submit" style="padding:8px 16px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer;">Buscar</button>
        <a href="/" style="padding:8px 16px; background:#6c757d; color:white; text-decoration:none; border-radius:4px; display:inline-block; text-align:center;">Limpiar</a>
    </div>
</form>

<div style="text-align:right; margin-bottom:10px;">
    <a href="/send_alerts" style="padding:8px 16px; background:#28a745; color:white; text-decoration:none; border-radius:4px; display:inline-block;">Enviar alertas por email</a>
</div>

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
# HOME CON BUSQUEDA Y FILTROS
# =========================================================

@app.get("/", response_class=HTMLResponse)
def home(
    q: str = Query(default=""),
    filtro: str = Query(default="todos")
):
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

        # FILTROS
        if q and q.lower() not in v.patente.lower() and q.lower() not in v.modelo.lower():
            continue
        if filtro != "todos" and alerta_tipo != filtro:
            continue

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

            <p>
                <a href="/edit_vehicle/{v.id}" style="padding:8px 12px; background:#007bff; color:white; text-decoration:none; border-radius:4px; display:inline-block; margin-top:10px;">Editar vehiculo</a>
            </p>

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

    if not html_vehicles:
        html_vehicles = "<p style='color:#999;'>No se encontraron vehiculos con esos filtros.</p>"

    dashboard_general = f"""
    <div style="background:#f8f9fa; padding:20px; border-radius:10px;">
        <h2>Resumen General</h2>
        <p><strong>Facturacion mensual:</strong> ${total_ingresos}</p>
        <p><strong>Gastos totales:</strong> ${total_gastos}</p>
        <p><strong>Ganancia total:</strong> ${total_ingresos - total_gastos}</p>
    </div>
    """

    # Selected options
    sel_todos = "selected" if filtro == "todos" else ""
    sel_ok = "selected" if filtro == "ok" else ""
    sel_proximo = "selected" if filtro == "proximo" else ""
    sel_vencido = "selected" if filtro == "vencido" else ""

    db.close()

    return HTML.format(
        dashboard_general=dashboard_general,
        vehicles=html_vehicles,
        search_query=q,
        sel_todos=sel_todos,
        sel_ok=sel_ok,
        sel_proximo=sel_proximo,
        sel_vencido=sel_vencido
    )

# =========================================================
# ALERTAS POR EMAIL
# =========================================================

@app.get("/send_alerts", response_class=HTMLResponse)
def send_alerts_form():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enviar Alertas</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family:Arial; padding:20px; max-width:600px; margin:auto;">
        <h1>Enviar alertas por email</h1>
        <p style="color:#666;">Se enviara un resumen de vencimientos proximos y services vencidos al email indicado.</p>
        <p style="color:#666; font-size:14px;">Nota: Configura las variables GMAIL_USER y GMAIL_PASSWORD en Render para que funcione.</p>
        <form method="post" action="/send_alerts">
            <p>
                <label>Email destinatario</label><br>
                <input name="email_destino" type="email" placeholder="tu@email.com" required style="width:100%; padding:8px; border:1px solid #ccc; border-radius:4px;">
            </p>
            <p>
                <button type="submit" style="padding:10px 20px; background:#28a745; color:white; border:none; border-radius:4px; cursor:pointer;">Enviar alerta</button>
                <a href="/" style="padding:10px 20px; background:#6c757d; color:white; text-decoration:none; border-radius:4px; display:inline-block;">Volver</a>
            </p>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/send_alerts", response_class=HTMLResponse)
def send_alerts(email_destino: str = Form(...)):
    GMAIL_USER = os.getenv("GMAIL_USER", "")
    GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "")

    db = SessionLocal()
    vehicles = db.query(Vehicle).all()
    deadlines = db.query(VehicleDeadline).all()

    lineas = ["<h2>FleetUp - Resumen de alertas</h2>"]

    # Services
    lineas.append("<h3>Estado de services</h3><ul>")
    for v in vehicles:
        alerta_texto, _, alerta_tipo = calcular_alerta(v)
        if alerta_tipo in ("vencido", "proximo"):
            lineas.append(f"<li>{v.patente} - {v.modelo}: <strong>{alerta_texto}</strong></li>")
    lineas.append("</ul>")

    # Vencimientos
    lineas.append("<h3>Vencimientos proximos o vencidos</h3><ul>")
    for d in deadlines:
        estado = alerta_vencimiento(d.fecha_vencimiento)
        if "Vencido" in estado or "Proximo" in estado:
            v = d.vehicle
            lineas.append(f"<li>{v.patente if v else '?'} - {d.tipo}: {d.fecha_vencimiento} ({estado})</li>")
    lineas.append("</ul>")

    db.close()

    cuerpo_html = "\n".join(lineas)

    resultado = ""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        resultado = """
        <div style="background:#fff3cd; padding:15px; border-radius:8px; border:1px solid #ffc107;">
            <p style="margin:0;"><strong>No estan configuradas las variables de entorno</strong></p>
            <p style="margin:8px 0 0 0; font-size:14px;">Anda a tu servicio en Render, Environment, y agrega GMAIL_USER y GMAIL_PASSWORD.</p>
        </div>"""
    else:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "FleetUp - Alertas de vencimientos"
            msg["From"] = GMAIL_USER
            msg["To"] = email_destino
            msg.attach(MIMEText(cuerpo_html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(GMAIL_USER, GMAIL_PASSWORD)
                server.sendmail(GMAIL_USER, email_destino, msg.as_string())

            resultado = f'<div style="background:#d4edda; padding:15px; border-radius:8px; border:1px solid #28a745;"><p style="margin:0;">Email enviado correctamente a <strong>{email_destino}</strong></p></div>'
        except Exception as e:
            resultado = f'<div style="background:#f8d7da; padding:15px; border-radius:8px; border:1px solid #dc3545;"><p style="margin:0;">Error al enviar: {str(e)}</p></div>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resultado</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family:Arial; padding:20px; max-width:600px; margin:auto;">
        <h1>Resultado del envio</h1>
        {resultado}
        <p style="margin-top:20px;">
            <a href="/" style="padding:10px 20px; background:#007bff; color:white; text-decoration:none; border-radius:4px; display:inline-block;">Volver al inicio</a>
        </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# =========================================================
# EDITAR VEHICULO
# =========================================================

@app.get("/edit_vehicle/{vehicle_id}", response_class=HTMLResponse)
def edit_vehicle_form(vehicle_id: int):
    db = SessionLocal()
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    db.close()

    if not v:
        return RedirectResponse("/")

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Editar Vehiculo</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family:Arial; padding:20px; max-width:600px; margin:auto;">
        <h1>Editar Vehiculo</h1>
        <form method="post" action="/edit_vehicle/{v.id}">
            <p><label>Patente</label><br><input name="patente" value="{v.patente}" required style="width:100%; padding:8px;"></p>
            <p><label>Modelo</label><br><input name="modelo" value="{v.modelo}" required style="width:100%; padding:8px;"></p>
            <p><label>KM actuales</label><br><input name="kilometros" type="number" value="{v.kilometros}" required style="width:100%; padding:8px;"></p>
            <p><label>Valor mensual</label><br><input name="valor_mensual" value="{v.valor_mensual}" style="width:100%; padding:8px;"></p>
            
            <h3>Asignacion comercial</h3>
            <p><label>Empresa asignada</label><br><input name="empresa_asignada" value="{v.empresa_asignada or ''}" style="width:100%; padding:8px;"></p>
            <p><label>Fecha asignacion</label><br><input name="fecha_asignacion" type="date" value="{v.fecha_asignacion or ''}" style="width:100%; padding:8px;"></p>
            <p><label>KM en asignacion</label><br><input name="km_asignacion" type="number" value="{v.km_asignacion or 0}" style="width:100%; padding:8px;"></p>
            
            <p>
                <button type="submit" style="padding:10px 20px; background:#28a745; color:white; border:none; border-radius:4px; cursor:pointer;">Guardar cambios</button>
                <a href="/" style="padding:10px 20px; background:#6c757d; color:white; text-decoration:none; border-radius:4px; display:inline-block;">Cancelar</a>
            </p>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/edit_vehicle/{vehicle_id}")
def edit_vehicle(
    vehicle_id: int,
    patente: str = Form(...),
    modelo: str = Form(...),
    kilometros: int = Form(...),
    empresa_asignada: str = Form(""),
    fecha_asignacion: str = Form(""),
    km_asignacion: int = Form(0),
    valor_mensual: str = Form("0")
):
    db = SessionLocal()
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if v:
        v.patente = patente
        v.modelo = modelo
        v.kilometros = kilometros
        v.empresa_asignada = empresa_asignada
        v.fecha_asignacion = fecha_asignacion
        v.km_asignacion = km_asignacion
        v.valor_mensual = valor_mensual
        db.commit()
    db.close()
    return RedirectResponse("/", status_code=302)

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