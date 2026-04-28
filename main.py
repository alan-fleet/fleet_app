# main.py

# FleetUp - FASE 5: Edición + Filtros + Alertas email + Navegación mejorada

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, Form, Request, Query
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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =========================================================

# MODELOS

# =========================================================

class Vehicle(Base):
**tablename** = "vehicles"

```
id = Column(Integer, primary_key=True, index=True)
patente = Column(String, unique=True)
modelo = Column(String)
kilometros = Column(Integer)
empresa_asignada = Column(String, default="")
fecha_asignacion = Column(String, default="")
km_asignacion = Column(Integer, default=0)
valor_mensual = Column(String, default="0")

services = relationship("Service", back_populates="vehicle", cascade="all, delete-orphan")
expenses = relationship("VehicleExpense", back_populates="vehicle", cascade="all, delete-orphan")
deadlines = relationship("VehicleDeadline", back_populates="vehicle", cascade="all, delete-orphan")
```

class Service(Base):
**tablename** = "services"

```
id = Column(Integer, primary_key=True, index=True)
vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
fecha = Column(String)
kilometraje = Column(Integer)
tipo_service = Column(String)
costo = Column(String, default="0")
observaciones = Column(String, default="")

vehicle = relationship("Vehicle", back_populates="services")
```

class VehicleExpense(Base):
**tablename** = "vehicle_expenses"

```
id = Column(Integer, primary_key=True, index=True)
vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
categoria = Column(String)
fecha = Column(String, default="")
monto = Column(String, default="0")
observaciones = Column(String, default="")

vehicle = relationship("Vehicle", back_populates="expenses")
```

class VehicleDeadline(Base):
**tablename** = "vehicle_deadlines"

```
id = Column(Integer, primary_key=True, index=True)
vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
tipo = Column(String)
fecha_vencimiento = Column(String, default="")
observaciones = Column(String, default="")

vehicle = relationship("Vehicle", back_populates="deadlines")
```

Base.metadata.create_all(bind=engine)

# =========================================================

# AUXILIARES

# =========================================================

def to_number(valor):
try:
limpio = str(valor).replace("$", "").replace(".", "").replace(",", "").strip()
return int(limpio) if limpio else 0
except:
return 0

def calcular_alerta(vehicle):
if not vehicle.services:
if vehicle.kilometros >= 13000:
return "🟡 Próximo service", "#fff3cd", "proximo"
return "🟢 Sin services cargados", "#d4edda", "ok"

```
ultimo_service = max(vehicle.services, key=lambda s: s.kilometraje)
km_desde_service = vehicle.kilometros - ultimo_service.kilometraje

if km_desde_service >= 14000:
    return "🔴 Service vencido", "#f8d7da", "vencido"
elif km_desde_service >= 13000:
    return "🟡 Próximo service", "#fff3cd", "proximo"
else:
    return "🟢 Todo OK", "#d4edda", "ok"
```

def alerta_vencimiento(fecha):
try:
hoy = datetime.today()
venc = datetime.strptime(fecha, "%Y-%m-%d")
dias = (venc - hoy).days
if dias < 0:
return "🔴 Vencido"
elif dias <= 30:
return "🟡 Próximo a vencer"
else:
return "🟢 Vigente"
except:
return "⚪ Sin fecha válida"

def filtrar_categoria(items, nombre):
return [x for x in items if x.categoria == nombre]

def filtrar_deadline(items, nombre):
return [x for x in items if x.tipo == nombre]

# =========================================================

# ESTILOS GLOBALES

# =========================================================

ESTILOS = """

<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');

  :root {
    --bg: #0f0f13;
    --surface: #1a1a24;
    --surface2: #22222f;
    --accent: #5b6af0;
    --accent2: #e05b8a;
    --text: #e8e8f0;
    --muted: #7a7a9a;
    --ok: #2d6a4f;
    --ok-bg: #1a3d2e;
    --warn: #7c5c00;
    --warn-bg: #3d2e00;
    --danger: #7c2020;
    --danger-bg: #3d0f0f;
    --radius: 12px;
    --radius-sm: 8px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }

  /* NAV */
  nav {
    background: var(--surface);
    border-bottom: 1px solid #2a2a3a;
    padding: 0 32px;
    display: flex;
    align-items: center;
    gap: 32px;
    height: 60px;
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .nav-brand {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 20px;
    color: var(--accent);
    text-decoration: none;
    letter-spacing: -0.5px;
  }

  .nav-links { display: flex; gap: 4px; }

  .nav-link {
    color: var(--muted);
    text-decoration: none;
    padding: 6px 14px;
    border-radius: var(--radius-sm);
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
  }

  .nav-link:hover, .nav-link.active {
    background: var(--surface2);
    color: var(--text);
  }

  /* LAYOUT */
  .container { max-width: 1100px; margin: 0 auto; padding: 32px 20px; }

  h1 {
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 24px;
    letter-spacing: -0.5px;
  }

  h2 {
    font-family: 'Syne', sans-serif;
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 16px;
  }

  h3 {
    font-family: 'Syne', sans-serif;
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* CARDS */
  .card {
    background: var(--surface);
    border: 1px solid #2a2a3a;
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 16px;
  }

  .card-ok { border-left: 4px solid #4ade80; }
  .card-warn { border-left: 4px solid #fbbf24; }
  .card-danger { border-left: 4px solid #f87171; }

  /* DASHBOARD STATS */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .stat {
    background: var(--surface);
    border: 1px solid #2a2a3a;
    border-radius: var(--radius);
    padding: 20px;
  }

  .stat-label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .stat-value { font-family: 'Syne', sans-serif; font-size: 28px; font-weight: 800; }
  .stat-value.positive { color: #4ade80; }
  .stat-value.negative { color: #f87171; }
  .stat-value.neutral { color: var(--accent); }

  /* FORMULARIOS */
  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
  .form-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px; }

  label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }

  input, select, textarea {
    width: 100%;
    background: var(--surface2);
    border: 1px solid #2a2a3a;
    border-radius: var(--radius-sm);
    color: var(--text);
    padding: 10px 12px;
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    outline: none;
    transition: border-color 0.2s;
  }

  input:focus, select:focus, textarea:focus {
    border-color: var(--accent);
  }

  select option { background: var(--surface2); }

  /* BOTONES */
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 18px;
    border-radius: var(--radius-sm);
    border: none;
    font-size: 14px;
    font-weight: 500;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
  }

  .btn-primary { background: var(--accent); color: white; }
  .btn-primary:hover { background: #4a59e0; }

  .btn-danger { background: #7c2020; color: #ffaaaa; }
  .btn-danger:hover { background: #9c2020; }

  .btn-ghost {
    background: transparent;
    color: var(--muted);
    border: 1px solid #2a2a3a;
  }
  .btn-ghost:hover { background: var(--surface2); color: var(--text); }

  .btn-sm { padding: 6px 12px; font-size: 12px; }

  .btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }

  /* TABLA */
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { text-align: left; padding: 10px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); border-bottom: 1px solid #2a2a3a; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e1e2a; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--surface2); }

  /* BADGE */
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }
  .badge-ok { background: #1a3d2e; color: #4ade80; }
  .badge-warn { background: #3d2e00; color: #fbbf24; }
  .badge-danger { background: #3d0f0f; color: #f87171; }

  /* DETAILS / ACCORDION */
  details { margin-bottom: 16px; }

  details > summary {
    list-style: none;
    cursor: pointer;
    padding: 16px 20px;
    background: var(--surface);
    border: 1px solid #2a2a3a;
    border-radius: var(--radius);
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 16px;
    transition: background 0.2s;
    user-select: none;
  }

  details > summary:hover { background: var(--surface2); }
  details[open] > summary { border-radius: var(--radius) var(--radius) 0 0; border-bottom: none; }

  .details-body {
    background: var(--surface);
    border: 1px solid #2a2a3a;
    border-top: none;
    border-radius: 0 0 var(--radius) var(--radius);
    padding: 20px;
  }

  /* BÚSQUEDA */
  .search-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    align-items: flex-end;
  }

  .search-bar input, .search-bar select {
    flex: 1;
  }

  /* ALERTA VENC */
  .alert-box {
    background: var(--surface);
    border: 1px solid #3d2e00;
    border-radius: var(--radius);
    padding: 16px;
    margin-bottom: 16px;
  }

  .alert-box.danger { border-color: #7c2020; }

  hr { border: none; border-top: 1px solid #2a2a3a; margin: 24px 0; }

  .section-title {
    font-family: 'Syne', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #2a2a3a;
  }

  .empty { color: var(--muted); font-size: 14px; padding: 12px 0; }
</style>

"""

# =========================================================

# COMPONENTES HTML

# =========================================================

def nav(active="vehiculos"):
links = [
("vehiculos", "/", "🚗 Vehículos"),
("dashboard", "/dashboard", "📊 Dashboard"),
("vencimientos", "/vencimientos", "📅 Vencimientos"),
("alertas", "/send_alerts", "🔔 Enviar alertas"),
]
html = '<nav><a class="nav-brand" href="/">⚡ FleetUp</a><div class="nav-links">'
for key, href, label in links:
cls = "nav-link active" if active == key else "nav-link"
html += f'<a class="{cls}" href="{href}">{label}</a>'
html += "</div></nav>"
return html

def page(content, active="vehiculos"):
return f"""<!DOCTYPE html>

<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FleetUp</title>
  {ESTILOS}
</head>
<body>
  {nav(active)}
  <div class="container">
    {content}
  </div>
</body>
</html>"""

def badge_alerta(estado):
if "🔴" in estado:
return f'<span class="badge badge-danger">{estado}</span>'
elif "🟡" in estado:
return f'<span class="badge badge-warn">{estado}</span>'
return f'<span class="badge badge-ok">{estado}</span>'

def card_class(tipo):
if tipo == "vencido":
return "card card-danger"
elif tipo == "proximo":
return "card card-warn"
return "card card-ok"

# =========================================================

# HOME - LISTADO DE VEHÍCULOS

# =========================================================

@app.get("/", response_class=HTMLResponse)
def home(
q: str = Query(default=""),
filtro: str = Query(default="todos")
):
db = SessionLocal()
vehicles = db.query(Vehicle).all()

```
categorias = ["Patente", "Seguro", "VTV/BTV", "Cubiertas", "Otros"]
html_vehicles = ""

for v in vehicles:
    alerta_texto, _, alerta_tipo = calcular_alerta(v)

    # Filtros
    if q and q.lower() not in v.patente.lower() and q.lower() not in v.modelo.lower():
        continue
    if filtro != "todos" and alerta_tipo != filtro:
        continue

    ingreso_mensual = to_number(v.valor_mensual)
    gasto_services = sum(to_number(s.costo) for s in v.services)
    gasto_extra = sum(to_number(e.monto) for e in v.expenses)
    gasto_total = gasto_services + gasto_extra
    ganancia = ingreso_mensual - gasto_total

    # Services
    services_rows = ""
    for s in sorted(v.services, key=lambda x: x.kilometraje, reverse=True):
        services_rows += f"""
        <tr>
          <td>{s.fecha}</td>
          <td>{s.kilometraje:,} km</td>
          <td>{s.tipo_service}</td>
          <td>${to_number(s.costo):,}</td>
          <td>{s.observaciones}</td>
          <td>
            <form method="post" action="/delete_service" style="display:inline">
              <input type="hidden" name="service_id" value="{s.id}">
              <button class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar service?')">✕</button>
            </form>
            <a class="btn btn-ghost btn-sm" href="/edit_service/{s.id}">✏️</a>
          </td>
        </tr>"""

    # Gastos por categoría
    categorias_html = ""
    for cat in categorias:
        gastos_cat = filtrar_categoria(v.expenses, cat)
        venc_cat = filtrar_deadline(v.deadlines, cat)

        gastos_rows = ""
        for g in gastos_cat:
            gastos_rows += f"""
            <tr>
              <td>{g.fecha}</td>
              <td>${to_number(g.monto):,}</td>
              <td>{g.observaciones}</td>
              <td>
                <form method="post" action="/delete_expense" style="display:inline">
                  <input type="hidden" name="expense_id" value="{g.id}">
                  <button class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar gasto?')">✕</button>
                </form>
                <a class="btn btn-ghost btn-sm" href="/edit_expense/{g.id}">✏️</a>
              </td>
            </tr>"""

        venc_rows = ""
        for d in venc_cat:
            estado = alerta_vencimiento(d.fecha_vencimiento)
            venc_rows += f"""
            <tr>
              <td>{d.fecha_vencimiento}</td>
              <td>{badge_alerta(estado)}</td>
              <td>{d.observaciones}</td>
              <td>
                <form method="post" action="/delete_deadline" style="display:inline">
                  <input type="hidden" name="deadline_id" value="{d.id}">
                  <button class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar vencimiento?')">✕</button>
                </form>
                <a class="btn btn-ghost btn-sm" href="/edit_deadline/{d.id}">✏️</a>
              </td>
            </tr>"""

        categorias_html += f"""
        <details style="margin-bottom:12px;">
          <summary>📂 {cat}</summary>
          <div class="details-body">
            <div class="section-title">Gastos</div>
            {'<table><thead><tr><th>Fecha</th><th>Monto</th><th>Obs.</th><th></th></tr></thead><tbody>' + gastos_rows + '</tbody></table>' if gastos_rows else '<p class="empty">Sin gastos registrados</p>'}

            <div class="section-title" style="margin-top:20px;">Vencimientos</div>
            {'<table><thead><tr><th>Fecha</th><th>Estado</th><th>Obs.</th><th></th></tr></thead><tbody>' + venc_rows + '</tbody></table>' if venc_rows else '<p class="empty">Sin vencimientos</p>'}

            <hr>
            <h3>Agregar gasto — {cat}</h3>
            <form method="post" action="/add_expense">
              <input type="hidden" name="vehicle_id" value="{v.id}">
              <input type="hidden" name="categoria" value="{cat}">
              <div class="form-grid">
                <div><label>Fecha</label><input name="fecha" type="date"></div>
                <div><label>Monto</label><input name="monto" placeholder="0" required></div>
              </div>
              <div><label>Observaciones</label><input name="observaciones" placeholder="Opcional"></div>
              <div class="btn-row"><button class="btn btn-primary" type="submit">Guardar gasto</button></div>
            </form>

            <h3 style="margin-top:20px;">Agregar vencimiento — {cat}</h3>
            <form method="post" action="/add_deadline">
              <input type="hidden" name="vehicle_id" value="{v.id}">
              <input type="hidden" name="tipo" value="{cat}">
              <div class="form-grid">
                <div><label>Fecha vencimiento</label><input name="fecha_vencimiento" type="date" required></div>
                <div><label>Observaciones</label><input name="observaciones" placeholder="Opcional"></div>
              </div>
              <div class="btn-row"><button class="btn btn-primary" type="submit">Guardar vencimiento</button></div>
            </form>
          </div>
        </details>"""

    ganancia_color = "positive" if ganancia >= 0 else "negative"

    html_vehicles += f"""
    <details>
      <summary>
        {badge_alerta(alerta_texto)}
        <span style="margin-left:8px;">{v.patente} — {v.modelo}</span>
        <span style="margin-left:auto; font-size:13px; color:var(--muted);">{v.kilometros:,} km</span>
      </summary>
      <div class="details-body">

        <div class="stats-grid">
          <div class="stat">
            <div class="stat-label">Ingreso mensual</div>
            <div class="stat-value neutral">${ingreso_mensual:,}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Gastos totales</div>
            <div class="stat-value negative">${gasto_total:,}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Ganancia</div>
            <div class="stat-value {ganancia_color}">${ganancia:,}</div>
          </div>
        </div>

        <div class="btn-row" style="margin-bottom:20px;">
          <a class="btn btn-ghost" href="/edit_vehicle/{v.id}">✏️ Editar vehículo</a>
          <form method="post" action="/delete_vehicle" style="display:inline">
            <input type="hidden" name="vehicle_id" value="{v.id}">
            <button class="btn btn-danger" onclick="return confirm('¿Eliminar este vehículo?')">🗑 Eliminar</button>
          </form>
        </div>

        <div class="section-title">Registrar service</div>
        <form method="post" action="/add_service">
          <input type="hidden" name="vehicle_id" value="{v.id}">
          <div class="form-grid">
            <div><label>Fecha</label><input name="fecha" type="date" required></div>
            <div><label>Kilometraje</label><input name="kilometraje" type="number" placeholder="0" required></div>
          </div>
          <div class="form-grid">
            <div><label>Tipo de service</label><input name="tipo_service" placeholder="Ej: Aceite y filtros" required></div>
            <div><label>Costo</label><input name="costo" placeholder="0" required></div>
          </div>
          <div><label>Observaciones</label><input name="observaciones" placeholder="Opcional"></div>
          <div class="btn-row"><button class="btn btn-primary" type="submit">Guardar service</button></div>
        </form>

        <div class="section-title" style="margin-top:24px;">Historial de services</div>
        {'<table><thead><tr><th>Fecha</th><th>KM</th><th>Tipo</th><th>Costo</th><th>Obs.</th><th></th></tr></thead><tbody>' + services_rows + '</tbody></table>' if services_rows else '<p class="empty">Sin services registrados</p>'}

        <div class="section-title" style="margin-top:24px;">Gastos y vencimientos por categoría</div>
        {categorias_html}

      </div>
    </details>"""

db.close()

# Barra de búsqueda
search_html = f"""
<form method="get" action="/">
  <div class="search-bar">
    <div style="flex:2">
      <label>Buscar vehículo</label>
      <input name="q" value="{q}" placeholder="Patente o modelo...">
    </div>
    <div style="flex:1">
      <label>Filtrar por estado</label>
      <select name="filtro">
        <option value="todos" {'selected' if filtro == 'todos' else ''}>Todos</option>
        <option value="ok" {'selected' if filtro == 'ok' else ''}>🟢 Todo OK</option>
        <option value="proximo" {'selected' if filtro == 'proximo' else ''}>🟡 Próximo service</option>
        <option value="vencido" {'selected' if filtro == 'vencido' else ''}>🔴 Vencido</option>
      </select>
    </div>
    <button class="btn btn-primary" type="submit">Buscar</button>
    <a class="btn btn-ghost" href="/">Limpiar</a>
  </div>
</form>"""

content = f"""
<h1>🚗 Vehículos</h1>

{search_html}

<details style="margin-bottom:24px;">
  <summary>➕ Agregar vehículo</summary>
  <div class="details-body">
    <form method="post" action="/add_vehicle">
      <div class="form-grid">
        <div><label>Patente</label><input name="patente" placeholder="ABC123" required></div>
        <div><label>Modelo</label><input name="modelo" placeholder="Toyota Corolla" required></div>
      </div>
      <div class="form-grid">
        <div><label>KM actuales</label><input name="kilometros" type="number" placeholder="0" required></div>
        <div><label>Valor mensual</label><input name="valor_mensual" placeholder="0"></div>
      </div>
      <div class="section-title" style="margin-top:8px;">Asignación comercial</div>
      <div class="form-grid">
        <div><label>Empresa asignada</label><input name="empresa_asignada" placeholder="Nombre empresa"></div>
        <div><label>Fecha asignación</label><input name="fecha_asignacion" type="date"></div>
      </div>
      <div><label>KM en asignación</label><input name="km_asignacion" type="number" placeholder="0" style="max-width:200px"></div>
      <div class="btn-row"><button class="btn btn-primary" type="submit">Guardar vehículo</button></div>
    </form>
  </div>
</details>

{html_vehicles if html_vehicles else '<div class="card"><p class="empty">No hay vehículos cargados aún.</p></div>'}
"""

return page(content, active="vehiculos")
```

# =========================================================

# DASHBOARD GENERAL

# =========================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
db = SessionLocal()
vehicles = db.query(Vehicle).all()

```
total_ingresos = 0
total_gastos = 0
total_ganancia = 0
rows = ""

for v in vehicles:
    alerta_texto, _, alerta_tipo = calcular_alerta(v)
    ingreso = to_number(v.valor_mensual)
    gastos = sum(to_number(s.costo) for s in v.services) + sum(to_number(e.monto) for e in v.expenses)
    ganancia = ingreso - gastos

    total_ingresos += ingreso
    total_gastos += gastos
    total_ganancia += ganancia

    color_ganancia = "#4ade80" if ganancia >= 0 else "#f87171"

    rows += f"""
    <tr>
      <td><a href="/" style="color:var(--accent);text-decoration:none;">{v.patente}</a></td>
      <td>{v.modelo}</td>
      <td>{v.empresa_asignada or '—'}</td>
      <td>${ingreso:,}</td>
      <td>${gastos:,}</td>
      <td style="color:{color_ganancia};font-weight:bold;">${ganancia:,}</td>
      <td>{badge_alerta(alerta_texto)}</td>
    </tr>"""

db.close()

ganancia_color = "positive" if total_ganancia >= 0 else "negative"

content = f"""
<h1>📊 Dashboard General</h1>

<div class="stats-grid">
  <div class="stat">
    <div class="stat-label">Facturación mensual total</div>
    <div class="stat-value neutral">${total_ingresos:,}</div>
  </div>
  <div class="stat">
    <div class="stat-label">Gastos totales</div>
    <div class="stat-value negative">${total_gastos:,}</div>
  </div>
  <div class="stat">
    <div class="stat-label">Ganancia total</div>
    <div class="stat-value {ganancia_color}">${total_ganancia:,}</div>
  </div>
  <div class="stat">
    <div class="stat-label">Vehículos activos</div>
    <div class="stat-value neutral">{len(vehicles)}</div>
  </div>
</div>

<div class="card">
  <table>
    <thead>
      <tr>
        <th>Patente</th>
        <th>Modelo</th>
        <th>Empresa</th>
        <th>Ingreso</th>
        <th>Gastos</th>
        <th>Ganancia</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>
"""
return page(content, active="dashboard")
```

# =========================================================

# VENCIMIENTOS

# =========================================================

@app.get("/vencimientos", response_class=HTMLResponse)
def vencimientos():
db = SessionLocal()
deadlines = db.query(VehicleDeadline).all()

```
proximos = []
vencidos = []
vigentes = []

for d in deadlines:
    estado = alerta_vencimiento(d.fecha_vencimiento)
    entrada = (d, estado)
    if "🔴" in estado:
        vencidos.append(entrada)
    elif "🟡" in estado:
        proximos.append(entrada)
    else:
        vigentes.append(entrada)

def tabla(items):
    if not items:
        return '<p class="empty">Sin registros</p>'
    rows = ""
    for d, estado in items:
        v = d.vehicle
        rows += f"""
        <tr>
          <td>{v.patente if v else '?'} — {v.modelo if v else '?'}</td>
          <td>{d.tipo}</td>
          <td>{d.fecha_vencimiento}</td>
          <td>{badge_alerta(estado)}</td>
          <td>{d.observaciones}</td>
        </tr>"""
    return f"""
    <table>
      <thead><tr><th>Vehículo</th><th>Tipo</th><th>Fecha</th><th>Estado</th><th>Obs.</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""

db.close()

content = f"""
<h1>📅 Vencimientos</h1>

<div class="section-title">🔴 Vencidos ({len(vencidos)})</div>
<div class="card card-danger">{tabla(vencidos)}</div>

<div class="section-title">🟡 Próximos a vencer ({len(proximos)})</div>
<div class="card card-warn">{tabla(proximos)}</div>

<div class="section-title">🟢 Vigentes ({len(vigentes)})</div>
<div class="card card-ok">{tabla(vigentes)}</div>
"""
return page(content, active="vencimientos")
```

# =========================================================

# ALERTAS POR EMAIL

# =========================================================

@app.get("/send_alerts", response_class=HTMLResponse)
def send_alerts_form():
content = """
<h1>🔔 Enviar alertas por email</h1>
<div class="card">
<p style="color:var(--muted); margin-bottom:20px;">
Se enviará un resumen de vencimientos próximos y services vencidos al email indicado.
<br>Configurá las credenciales de Gmail en las variables de entorno de Render.
</p>
<form method="post" action="/send_alerts">
<div><label>Email destinatario</label><input name="email_destino" type="email" placeholder="tu@email.com" required style="max-width:400px;"></div>
<div class="btn-row"><button class="btn btn-primary" type="submit">📨 Enviar alerta</button></div>
</form>
</div>
"""
return page(content, active="alertas")

@app.post("/send_alerts", response_class=HTMLResponse)
def send_alerts(email_destino: str = Form(…)):
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "")

```
db = SessionLocal()
vehicles = db.query(Vehicle).all()
deadlines = db.query(VehicleDeadline).all()

lineas = ["<h2>🚗 FleetUp — Resumen de alertas</h2>"]

# Services
lineas.append("<h3>🛠 Estado de services</h3><ul>")
for v in vehicles:
    alerta_texto, _, alerta_tipo = calcular_alerta(v)
    if alerta_tipo in ("vencido", "proximo"):
        lineas.append(f"<li>{v.patente} — {v.modelo}: <strong>{alerta_texto}</strong></li>")
lineas.append("</ul>")

# Vencimientos
lineas.append("<h3>📅 Vencimientos próximos o vencidos</h3><ul>")
for d in deadlines:
    estado = alerta_vencimiento(d.fecha_vencimiento)
    if "🔴" in estado or "🟡" in estado:
        v = d.vehicle
        lineas.append(f"<li>{v.patente if v else '?'} — {d.tipo}: {d.fecha_vencimiento} ({estado})</li>")
lineas.append("</ul>")

db.close()

cuerpo_html = "\n".join(lineas)

resultado = ""
if not GMAIL_USER or not GMAIL_PASSWORD:
    resultado = """
    <div class="card card-warn">
      <p>⚠️ No están configuradas las variables de entorno <strong>GMAIL_USER</strong> y <strong>GMAIL_PASSWORD</strong> en Render.</p>
      <p style="margin-top:8px;color:var(--muted);">Andá a tu servicio en Render → Environment → agregá esas dos variables.</p>
    </div>"""
else:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🚗 FleetUp — Alertas de vencimientos"
        msg["From"] = GMAIL_USER
        msg["To"] = email_destino
        msg.attach(MIMEText(cuerpo_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, email_destino, msg.as_string())

        resultado = f'<div class="card card-ok"><p>✅ Email enviado correctamente a <strong>{email_destino}</strong></p></div>'
    except Exception as e:
        resultado = f'<div class="card card-danger"><p>❌ Error al enviar: {str(e)}</p></div>'

content = f"""
<h1>🔔 Enviar alertas por email</h1>
{resultado}
<div class="btn-row"><a class="btn btn-ghost" href="/send_alerts">← Volver</a></div>
"""
return page(content, active="alertas")
```

# =========================================================

# EDITAR VEHÍCULO

# =========================================================

@app.get("/edit_vehicle/{vehicle_id}", response_class=HTMLResponse)
def edit_vehicle_form(vehicle_id: int):
db = SessionLocal()
v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
db.close()

```
if not v:
    return RedirectResponse("/")

content = f"""
<h1>✏️ Editar vehículo</h1>
<div class="card">
  <form method="post" action="/edit_vehicle/{v.id}">
    <div class="form-grid">
      <div><label>Patente</label><input name="patente" value="{v.patente}" required></div>
      <div><label>Modelo</label><input name="modelo" value="{v.modelo}" required></div>
    </div>
    <div class="form-grid">
      <div><label>KM actuales</label><input name="kilometros" type="number" value="{v.kilometros}" required></div>
      <div><label>Valor mensual</label><input name="valor_mensual" value="{v.valor_mensual}"></div>
    </div>
    <div class="section-title">Asignación comercial</div>
    <div class="form-grid">
      <div><label>Empresa asignada</label><input name="empresa_asignada" value="{v.empresa_asignada or ''}"></div>
      <div><label>Fecha asignación</label><input name="fecha_asignacion" type="date" value="{v.fecha_asignacion or ''}"></div>
    </div>
    <div><label>KM en asignación</label><input name="km_asignacion" type="number" value="{v.km_asignacion or 0}" style="max-width:200px"></div>
    <div class="btn-row">
      <button class="btn btn-primary" type="submit">Guardar cambios</button>
      <a class="btn btn-ghost" href="/">Cancelar</a>
    </div>
  </form>
</div>"""
return page(content)
```

@app.post("/edit_vehicle/{vehicle_id}")
def edit_vehicle(
vehicle_id: int,
patente: str = Form(…),
modelo: str = Form(…),
kilometros: int = Form(…),
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

# EDITAR SERVICE

# =========================================================

@app.get("/edit_service/{service_id}", response_class=HTMLResponse)
def edit_service_form(service_id: int):
db = SessionLocal()
s = db.query(Service).filter(Service.id == service_id).first()
db.close()

```
if not s:
    return RedirectResponse("/")

content = f"""
<h1>✏️ Editar service</h1>
<div class="card">
  <form method="post" action="/edit_service/{s.id}">
    <div class="form-grid">
      <div><label>Fecha</label><input name="fecha" type="date" value="{s.fecha}" required></div>
      <div><label>Kilometraje</label><input name="kilometraje" type="number" value="{s.kilometraje}" required></div>
    </div>
    <div class="form-grid">
      <div><label>Tipo de service</label><input name="tipo_service" value="{s.tipo_service}" required></div>
      <div><label>Costo</label><input name="costo" value="{s.costo}" required></div>
    </div>
    <div><label>Observaciones</label><input name="observaciones" value="{s.observaciones or ''}"></div>
    <div class="btn-row">
      <button class="btn btn-primary" type="submit">Guardar cambios</button>
      <a class="btn btn-ghost" href="/">Cancelar</a>
    </div>
  </form>
</div>"""
return page(content)
```

@app.post("/edit_service/{service_id}")
def edit_service(
service_id: int,
fecha: str = Form(…),
kilometraje: int = Form(…),
tipo_service: str = Form(…),
costo: str = Form(…),
observaciones: str = Form("")
):
db = SessionLocal()
s = db.query(Service).filter(Service.id == service_id).first()
if s:
s.fecha = fecha
s.kilometraje = kilometraje
s.tipo_service = tipo_service
s.costo = costo
s.observaciones = observaciones
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

# =========================================================

# EDITAR GASTO

# =========================================================

@app.get("/edit_expense/{expense_id}", response_class=HTMLResponse)
def edit_expense_form(expense_id: int):
db = SessionLocal()
g = db.query(VehicleExpense).filter(VehicleExpense.id == expense_id).first()
db.close()

```
if not g:
    return RedirectResponse("/")

categorias_options = ""
for cat in ["Patente", "Seguro", "VTV/BTV", "Cubiertas", "Otros"]:
    sel = "selected" if g.categoria == cat else ""
    categorias_options += f'<option value="{cat}" {sel}>{cat}</option>'

content = f"""
<h1>✏️ Editar gasto</h1>
<div class="card">
  <form method="post" action="/edit_expense/{g.id}">
    <div class="form-grid">
      <div><label>Categoría</label>
        <select name="categoria" required>
          {categorias_options}
        </select>
      </div>
      <div><label>Fecha</label><input name="fecha" type="date" value="{g.fecha or ''}"></div>
    </div>
    <div class="form-grid">
      <div><label>Monto</label><input name="monto" value="{g.monto}" required></div>
      <div><label>Observaciones</label><input name="observaciones" value="{g.observaciones or ''}"></div>
    </div>
    <div class="btn-row">
      <button class="btn btn-primary" type="submit">Guardar cambios</button>
      <a class="btn btn-ghost" href="/">Cancelar</a>
    </div>
  </form>
</div>"""
return page(content)
```

@app.post("/edit_expense/{expense_id}")
def edit_expense(
expense_id: int,
categoria: str = Form(…),
fecha: str = Form(""),
monto: str = Form(…),
observaciones: str = Form("")
):
db = SessionLocal()
g = db.query(VehicleExpense).filter(VehicleExpense.id == expense_id).first()
if g:
g.categoria = categoria
g.fecha = fecha
g.monto = monto
g.observaciones = observaciones
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

# =========================================================

# EDITAR VENCIMIENTO

# =========================================================

@app.get("/edit_deadline/{deadline_id}", response_class=HTMLResponse)
def edit_deadline_form(deadline_id: int):
db = SessionLocal()
d = db.query(VehicleDeadline).filter(VehicleDeadline.id == deadline_id).first()
db.close()

```
if not d:
    return RedirectResponse("/")

tipos_options = ""
for tipo in ["Patente", "Seguro", "VTV/BTV", "Cubiertas", "Otros"]:
    sel = "selected" if d.tipo == tipo else ""
    tipos_options += f'<option value="{tipo}" {sel}>{tipo}</option>'

content = f"""
<h1>✏️ Editar vencimiento</h1>
<div class="card">
  <form method="post" action="/edit_deadline/{d.id}">
    <div class="form-grid">
      <div><label>Tipo</label>
        <select name="tipo" required>
          {tipos_options}
        </select>
      </div>
      <div><label>Fecha vencimiento</label><input name="fecha_vencimiento" type="date" value="{d.fecha_vencimiento or ''}" required></div>
    </div>
    <div><label>Observaciones</label><input name="observaciones" value="{d.observaciones or ''}"></div>
    <div class="btn-row">
      <button class="btn btn-primary" type="submit">Guardar cambios</button>
      <a class="btn btn-ghost" href="/">Cancelar</a>
    </div>
  </form>
</div>"""
return page(content)
```

@app.post("/edit_deadline/{deadline_id}")
def edit_deadline(
deadline_id: int,
tipo: str = Form(…),
fecha_vencimiento: str = Form(…),
observaciones: str = Form("")
):
db = SessionLocal()
d = db.query(VehicleDeadline).filter(VehicleDeadline.id == deadline_id).first()
if d:
d.tipo = tipo
d.fecha_vencimiento = fecha_vencimiento
d.observaciones = observaciones
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

# =========================================================

# RUTAS EXISTENTES (delete)

# =========================================================

@app.post("/add_vehicle")
def add_vehicle(
patente: str = Form(…),
modelo: str = Form(…),
kilometros: int = Form(…),
empresa_asignada: str = Form(""),
fecha_asignacion: str = Form(""),
km_asignacion: int = Form(0),
valor_mensual: str = Form("0")
):
db = SessionLocal()
db.add(Vehicle(
patente=patente, modelo=modelo, kilometros=kilometros,
empresa_asignada=empresa_asignada, fecha_asignacion=fecha_asignacion,
km_asignacion=km_asignacion, valor_mensual=valor_mensual
))
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

@app.post("/add_service")
def add_service(
vehicle_id: int = Form(…),
fecha: str = Form(…),
kilometraje: int = Form(…),
tipo_service: str = Form(…),
costo: str = Form(…),
observaciones: str = Form("")
):
db = SessionLocal()
db.add(Service(vehicle_id=vehicle_id, fecha=fecha, kilometraje=kilometraje,
tipo_service=tipo_service, costo=costo, observaciones=observaciones))
v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
if v:
v.kilometros = kilometraje
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

@app.post("/add_expense")
def add_expense(
vehicle_id: int = Form(…),
categoria: str = Form(…),
fecha: str = Form(""),
monto: str = Form(…),
observaciones: str = Form("")
):
db = SessionLocal()
db.add(VehicleExpense(vehicle_id=vehicle_id, categoria=categoria,
fecha=fecha, monto=monto, observaciones=observaciones))
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

@app.post("/add_deadline")
def add_deadline(
vehicle_id: int = Form(…),
tipo: str = Form(…),
fecha_vencimiento: str = Form(…),
observaciones: str = Form("")
):
db = SessionLocal()
db.add(VehicleDeadline(vehicle_id=vehicle_id, tipo=tipo,
fecha_vencimiento=fecha_vencimiento, observaciones=observaciones))
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

@app.post("/delete_vehicle")
def delete_vehicle(vehicle_id: int = Form(…)):
db = SessionLocal()
item = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
if item:
db.delete(item)
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

@app.post("/delete_service")
def delete_service(service_id: int = Form(…)):
db = SessionLocal()
item = db.query(Service).filter(Service.id == service_id).first()
if item:
db.delete(item)
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

@app.post("/delete_expense")
def delete_expense(expense_id: int = Form(…)):
db = SessionLocal()
item = db.query(VehicleExpense).filter(VehicleExpense.id == expense_id).first()
if item:
db.delete(item)
db.commit()
db.close()
return RedirectResponse("/", status_code=302)

@app.post("/delete_deadline")
def delete_deadline(deadline_id: int = Form(…)):
db = SessionLocal()
item = db.query(VehicleDeadline).filter(VehicleDeadline.id == deadline_id).first()
if item:
db.delete(item)
db.commit()
db.close()
return RedirectResponse("/", status_code=302)