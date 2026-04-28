# main.py
# FleetUp - Version completa con todas las funcionalidades
# PASO 6 FINAL: Eliminar vehiculo + Edicion completa + Dashboard

import os
from datetime import datetime
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

    services = relationship("Service", back_populates="vehicle", cascade="all, delete-orphan")
    expenses = relationship("VehicleExpense", back_populates="vehicle", cascade="all, delete-orphan")
    deadlines = relationship("VehicleDeadline", back_populates="vehicle", cascade="all, delete-orphan")


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
    categoria = Column(String)
    fecha = Column(String, default="")
    monto = Column(String, default="0")
    observaciones = Column(String, default="")

    vehicle = relationship("Vehicle", back_populates="expenses")


class VehicleDeadline(Base):
    __tablename__ = "vehicle_deadlines"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    tipo = Column(String)
    fecha_vencimiento = Column(String, default="")
    observaciones = Column(String, default="")

    vehicle = relationship("Vehicle", back_populates="deadlines")


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
            return "Proximo service", "#1a1d29", "proximo"
        return "Sin services", "#1a1d29", "ok"

    ultimo_service = max(vehicle.services, key=lambda s: s.kilometraje)
    km_desde_service = vehicle.kilometros - ultimo_service.kilometraje

    if km_desde_service >= 14000:
        return "Service vencido", "#1a1d29", "vencido"
    elif km_desde_service >= 13000:
        return "Proximo service", "#1a1d29", "proximo"
    else:
        return "Todo OK", "#1a1d29", "ok"


def alerta_vencimiento(fecha):
    try:
        hoy = datetime.today()
        venc = datetime.strptime(fecha, "%Y-%m-%d")
        dias = (venc - hoy).days
        if dias < 0:
            return "Vencido", "danger"
        elif dias <= 30:
            return "Proximo", "warning"
        else:
            return "Vigente", "ok"
    except:
        return "Sin fecha", "muted"


def filtrar_categoria(items, nombre):
    return [x for x in items if x.categoria == nombre]


def filtrar_deadline(items, nombre):
    return [x for x in items if x.tipo == nombre]


def get_badge_class(tipo):
    if tipo == "vencido":
        return "badge-danger"
    elif tipo == "proximo":
        return "badge-warning"
    return "badge-ok"


def get_deadline_badge(estado_tuple):
    _, tipo = estado_tuple
    if tipo == "danger":
        return "badge-danger"
    elif tipo == "warning":
        return "badge-warning"
    elif tipo == "ok":
        return "badge-ok"
    return "badge-muted"

# =========================================================
# ESTILOS MODERNOS
# =========================================================

MODERN_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #12172b;
    --bg-card: #1a1d29;
    --text-primary: #e4e7f0;
    --text-secondary: #8b92b3;
    --accent: #00d9ff;
    --accent-glow: rgba(0, 217, 255, 0.3);
    --danger: #ff4757;
    --danger-glow: rgba(255, 71, 87, 0.2);
    --warning: #ffa502;
    --warning-glow: rgba(255, 165, 2, 0.2);
    --success: #26de81;
    --success-glow: rgba(38, 222, 129, 0.2);
    --radius: 16px;
    --shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

body {
    font-family: 'Outfit', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
}

body::before {
    content: '';
    position: fixed;
    top: -50%;
    right: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(0, 217, 255, 0.05) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 24px;
    position: relative;
    z-index: 1;
}

/* NAV */
.nav {
    background: var(--bg-card);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    padding: 0 24px;
    display: flex;
    align-items: center;
    gap: 32px;
    height: 64px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(20px);
    background: rgba(26, 29, 41, 0.8);
}

.nav-brand {
    font-size: 24px;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), #00a8cc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-decoration: none;
}

.nav-links {
    display: flex;
    gap: 8px;
}

.nav-link {
    color: var(--text-secondary);
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.3s;
}

.nav-link:hover, .nav-link.active {
    background: rgba(0, 217, 255, 0.1);
    color: var(--accent);
}

h1 {
    font-size: 48px;
    font-weight: 800;
    margin-bottom: 8px;
    background: linear-gradient(135deg, var(--accent), #00a8cc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1px;
}

.subtitle {
    color: var(--text-secondary);
    font-size: 16px;
    margin-bottom: 40px;
    font-weight: 300;
}

/* CARDS */
.card {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
    border: 1px solid rgba(255, 255, 255, 0.05);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), transparent);
    opacity: 0;
    transition: opacity 0.3s;
}

.card:hover::before {
    opacity: 1;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 48px rgba(0, 217, 255, 0.15);
}

/* STATS GRID */
.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
}

.stat-card {
    background: var(--bg-secondary);
    border-radius: var(--radius);
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    position: relative;
    overflow: hidden;
}

.stat-card::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--success));
}

.stat-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    font-weight: 600;
    margin-bottom: 8px;
}

.stat-value {
    font-size: 36px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
}

.stat-value.positive { color: var(--success); }
.stat-value.negative { color: var(--danger); }

/* BADGES */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-ok {
    background: var(--success-glow);
    color: var(--success);
    border: 1px solid var(--success);
}

.badge-warning {
    background: var(--warning-glow);
    color: var(--warning);
    border: 1px solid var(--warning);
}

.badge-danger {
    background: var(--danger-glow);
    color: var(--danger);
    border: 1px solid var(--danger);
}

.badge-muted {
    background: rgba(139, 146, 179, 0.1);
    color: var(--text-secondary);
    border: 1px solid var(--text-secondary);
}

/* BUTTONS */
.btn {
    display: inline-block;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    border: none;
    cursor: pointer;
    transition: all 0.3s;
    font-family: 'Outfit', sans-serif;
}

.btn-primary {
    background: linear-gradient(135deg, var(--accent), #00a8cc);
    color: #000;
    box-shadow: 0 4px 16px var(--accent-glow);
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px var(--accent-glow);
}

.btn-secondary {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-secondary:hover {
    background: var(--bg-card);
    border-color: var(--accent);
}

.btn-danger {
    background: linear-gradient(135deg, var(--danger), #d63031);
    color: white;
}

.btn-danger:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px var(--danger-glow);
}

.btn-sm {
    padding: 6px 12px;
    font-size: 12px;
}

.btn-group {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

/* FORMS */
.search-bar {
    background: var(--bg-secondary);
    padding: 20px;
    border-radius: var(--radius);
    margin-bottom: 32px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.form-grid {
    display: grid;
    grid-template-columns: 2fr 1fr auto auto;
    gap: 12px;
    align-items: end;
}

.form-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

label {
    display: block;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    margin-bottom: 6px;
    font-weight: 600;
}

input, select {
    width: 100%;
    padding: 12px 16px;
    background: var(--bg-primary);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 14px;
    font-family: 'Outfit', sans-serif;
    transition: all 0.3s;
}

input:focus, select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
}

/* VEHICLE CARDS */
.vehicle-card {
    background: var(--bg-card);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 20px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.vehicle-header {
    padding: 20px 24px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: background 0.3s;
    position: relative;
}

.vehicle-header:hover {
    background: rgba(0, 217, 255, 0.02);
}

.vehicle-header::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    transition: background 0.3s;
}

.vehicle-header.status-ok::before { background: var(--success); }
.vehicle-header.status-proximo::before { background: var(--warning); }
.vehicle-header.status-vencido::before { background: var(--danger); }

.vehicle-title {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
}

.vehicle-meta {
    display: flex;
    gap: 16px;
    align-items: center;
    color: var(--text-secondary);
    font-size: 14px;
    font-family: 'JetBrains Mono', monospace;
}

.vehicle-body {
    padding: 0 24px 24px 24px;
    display: none;
}

details[open] .vehicle-body {
    display: block;
    animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.mini-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin: 20px 0;
    padding: 20px;
    background: var(--bg-secondary);
    border-radius: 12px;
}

.mini-stat {
    text-align: center;
}

.mini-stat-label {
    font-size: 11px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.mini-stat-value {
    font-size: 20px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}

/* SECTIONS */
.section {
    margin-top: 32px;
}

.section-title {
    font-size: 14px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.section-title::before {
    content: '';
    width: 3px;
    height: 14px;
    background: var(--accent);
    border-radius: 2px;
}

.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    margin: 32px 0;
}

/* TABLES */
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

th {
    text-align: left;
    padding: 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-secondary);
    font-weight: 600;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

td {
    padding: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
}

tr:hover td {
    background: rgba(0, 217, 255, 0.02);
}

.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-secondary);
}

.empty-state-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.3;
}

/* ADD VEHICLE MODAL */
.modal-trigger {
    position: fixed;
    bottom: 32px;
    right: 32px;
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, var(--accent), #00a8cc);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    color: #000;
    cursor: pointer;
    box-shadow: 0 8px 24px var(--accent-glow);
    transition: all 0.3s;
    z-index: 50;
    border: none;
    font-weight: 800;
}

.modal-trigger:hover {
    transform: scale(1.1) rotate(90deg);
    box-shadow: 0 12px 32px var(--accent-glow);
}

.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(10px);
    z-index: 100;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

.modal.active {
    display: flex;
}

.modal-content {
    background: var(--bg-card);
    border-radius: var(--radius);
    max-width: 600px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    padding: 32px;
    position: relative;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-close {
    position: absolute;
    top: 16px;
    right: 16px;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    font-size: 24px;
    cursor: pointer;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    transition: all 0.3s;
}

.modal-close:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
}
</style>
"""

# =========================================================
# NAV COMPONENT
# =========================================================

def nav_component(active="vehiculos"):
    return f"""
    <div class="nav">
        <a class="nav-brand" href="/">FleetUp</a>
        <div class="nav-links">
            <a class="nav-link {'active' if active == 'vehiculos' else ''}" href="/">Vehiculos</a>
            <a class="nav-link {'active' if active == 'dashboard' else ''}" href="/dashboard">Dashboard</a>
        </div>
    </div>
    """

# =========================================================
# HOME
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

    categorias = ["Patente", "Seguro", "VTV/BTV", "Cubiertas", "Otros"]

    for v in vehicles:
        alerta_texto, alerta_color, alerta_tipo = calcular_alerta(v)

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

        services_rows = ""
        for s in sorted(v.services, key=lambda x: x.kilometraje, reverse=True):
            services_rows += f"""
            <tr>
                <td>{s.fecha}</td>
                <td>{s.kilometraje:,} km</td>
                <td>{s.tipo_service}</td>
                <td>${to_number(s.costo):,}</td>
                <td style="font-family: 'Outfit', sans-serif;">{s.observaciones}</td>
                <td>
                    <div class="btn-group">
                        <a href="/edit_service/{s.id}" class="btn btn-secondary btn-sm">✏️</a>
                        <form method="post" action="/delete_service" style="display:inline;">
                            <input type="hidden" name="service_id" value="{s.id}">
                            <button class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar service?')">🗑️</button>
                        </form>
                    </div>
                </td>
            </tr>"""

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
                    <td style="font-family: 'Outfit', sans-serif;">{g.observaciones}</td>
                    <td>
                        <div class="btn-group">
                            <a href="/edit_expense/{g.id}" class="btn btn-secondary btn-sm">✏️</a>
                            <form method="post" action="/delete_expense" style="display:inline;">
                                <input type="hidden" name="expense_id" value="{g.id}">
                                <button class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar gasto?')">🗑️</button>
                            </form>
                        </div>
                    </td>
                </tr>"""

            venc_rows = ""
            for d in venc_cat:
                estado_text, estado_tipo = alerta_vencimiento(d.fecha_vencimiento)
                badge_class = get_deadline_badge((estado_text, estado_tipo))
                venc_rows += f"""
                <tr>
                    <td>{d.fecha_vencimiento}</td>
                    <td><span class="badge {badge_class}">{estado_text}</span></td>
                    <td style="font-family: 'Outfit', sans-serif;">{d.observaciones}</td>
                    <td>
                        <div class="btn-group">
                            <a href="/edit_deadline/{d.id}" class="btn btn-secondary btn-sm">✏️</a>
                            <form method="post" action="/delete_deadline" style="display:inline;">
                                <input type="hidden" name="deadline_id" value="{d.id}">
                                <button class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar vencimiento?')">🗑️</button>
                            </form>
                        </div>
                    </td>
                </tr>"""

            categorias_html += f"""
            <div class="section">
                <div class="section-title">{cat}</div>
                <div class="card">
                    <h4 style="margin-bottom:12px; font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:1px;">Gastos</h4>
                    {'<table><thead><tr><th>Fecha</th><th>Monto</th><th>Obs.</th><th></th></tr></thead><tbody>' + gastos_rows + '</tbody></table>' if gastos_rows else '<div class="empty-state"><div class="empty-state-icon">💸</div><p>Sin gastos</p></div>'}
                    
                    <div class="divider"></div>
                    
                    <h4 style="margin-bottom:12px; font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:1px;">Vencimientos</h4>
                    {'<table><thead><tr><th>Fecha</th><th>Estado</th><th>Obs.</th><th></th></tr></thead><tbody>' + venc_rows + '</tbody></table>' if venc_rows else '<div class="empty-state"><div class="empty-state-icon">📅</div><p>Sin vencimientos</p></div>'}
                </div>
            </div>"""

        ganancia_class = "positive" if ganancia >= 0 else "negative"
        badge_class = get_badge_class(alerta_tipo)

        html_vehicles += f"""
        <details class="vehicle-card">
            <summary class="vehicle-header status-{alerta_tipo}">
                <div>
                    <div class="vehicle-title">{v.patente} — {v.modelo}</div>
                    <div class="vehicle-meta">
                        <span class="badge {badge_class}">{alerta_texto}</span>
                        <span>{v.kilometros:,} km</span>
                    </div>
                </div>
            </summary>
            <div class="vehicle-body">
                <div class="mini-stats">
                    <div class="mini-stat">
                        <div class="mini-stat-label">Ingreso</div>
                        <div class="mini-stat-value" style="color:var(--accent);">${ingreso_mensual:,}</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-label">Gastos</div>
                        <div class="mini-stat-value" style="color:var(--danger);">${gasto_total:,}</div>
                    </div>
                    <div class="mini-stat">
                        <div class="mini-stat-label">Ganancia</div>
                        <div class="mini-stat-value stat-value {ganancia_class}">${ganancia:,}</div>
                    </div>
                </div>

                <div class="btn-group">
                    <a href="/edit_vehicle/{v.id}" class="btn btn-secondary btn-sm">✏️ Editar vehiculo</a>
                    <form method="post" action="/delete_vehicle" style="display:inline;">
                        <input type="hidden" name="vehicle_id" value="{v.id}">
                        <button class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar {v.patente}? Esta accion no se puede deshacer.')">🗑️ Eliminar</button>
                    </form>
                </div>

                <div class="section">
                    <div class="section-title">Registrar service</div>
                    <form method="post" action="/add_service" style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                        <input type="hidden" name="vehicle_id" value="{v.id}">
                        <div><label>Fecha</label><input name="fecha" type="date" required></div>
                        <div><label>Kilometraje</label><input name="kilometraje" type="number" placeholder="0" required></div>
                        <div><label>Tipo</label><input name="tipo_service" placeholder="Aceite y filtros" required></div>
                        <div><label>Costo</label><input name="costo" placeholder="0" required></div>
                        <div style="grid-column:1/-1;"><label>Observaciones</label><input name="observaciones" placeholder="Opcional"></div>
                        <div style="grid-column:1/-1;"><button class="btn btn-primary" type="submit">Guardar service</button></div>
                    </form>
                </div>

                <div class="section">
                    <div class="section-title">Historial de services</div>
                    <div class="card">
                        {'<table><thead><tr><th>Fecha</th><th>KM</th><th>Tipo</th><th>Costo</th><th>Obs.</th><th></th></tr></thead><tbody>' + services_rows + '</tbody></table>' if services_rows else '<div class="empty-state"><div class="empty-state-icon">🔧</div><p>Sin services</p></div>'}
                    </div>
                </div>

                {categorias_html}
            </div>
        </details>"""

    if not html_vehicles:
        html_vehicles = '<div class="empty-state"><div class="empty-state-icon">🚗</div><p>No se encontraron vehiculos</p></div>'

    ganancia_total = total_ingresos - total_gastos
    ganancia_class = "positive" if ganancia_total >= 0 else "negative"

    sel_todos = "selected" if filtro == "todos" else ""
    sel_ok = "selected" if filtro == "ok" else ""
    sel_proximo = "selected" if filtro == "proximo" else ""
    sel_vencido = "selected" if filtro == "vencido" else ""

    db.close()

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>FleetUp</title>
        {MODERN_STYLES}
    </head>
    <body>
        {nav_component("vehiculos")}
        
        <div class="container">
            <h1>Vehiculos</h1>
            <div class="subtitle">Gestion de flota vehicular</div>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">Facturacion</div>
                    <div class="stat-value">${total_ingresos:,}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Gastos</div>
                    <div class="stat-value negative">${total_gastos:,}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Ganancia</div>
                    <div class="stat-value {ganancia_class}">${ganancia_total:,}</div>
                </div>
            </div>

            <div class="search-bar">
                <form method="get" action="/">
                    <div class="form-grid">
                        <div>
                            <label>Buscar vehiculo</label>
                            <input name="q" value="{q}" placeholder="Patente o modelo...">
                        </div>
                        <div>
                            <label>Estado</label>
                            <select name="filtro">
                                <option value="todos" {sel_todos}>Todos</option>
                                <option value="ok" {sel_ok}>Todo OK</option>
                                <option value="proximo" {sel_proximo}>Proximo</option>
                                <option value="vencido" {sel_vencido}>Vencido</option>
                            </select>
                        </div>
                        <button class="btn btn-primary" type="submit">Buscar</button>
                        <a class="btn btn-secondary" href="/">Limpiar</a>
                    </div>
                </form>
            </div>

            <div class="section-title">Vehiculos</div>
            {html_vehicles}
        </div>

        <button class="modal-trigger" onclick="document.getElementById('addVehicleModal').classList.add('active')">+</button>

        <div class="modal" id="addVehicleModal">
            <div class="modal-content">
                <button class="modal-close" onclick="document.getElementById('addVehicleModal').classList.remove('active')">×</button>
                <h2 style="margin-bottom:24px;">Agregar vehiculo</h2>
                <form method="post" action="/add_vehicle">
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Patente</label><input name="patente" placeholder="ABC123" required></div>
                        <div><label>Modelo</label><input name="modelo" placeholder="Toyota Corolla" required></div>
                    </div>
                    <div class="form-grid-2" style="margin-bottom:24px;">
                        <div><label>KM actuales</label><input name="kilometros" type="number" placeholder="0" required></div>
                        <div><label>Valor mensual</label><input name="valor_mensual" placeholder="0"></div>
                    </div>
                    
                    <div class="section-title">Asignacion comercial</div>
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Empresa</label><input name="empresa_asignada" placeholder="Nombre empresa"></div>
                        <div><label>Fecha</label><input name="fecha_asignacion" type="date"></div>
                    </div>
                    <div style="margin-bottom:24px;">
                        <label>KM asignacion</label>
                        <input name="km_asignacion" type="number" placeholder="0">
                    </div>
                    
                    <button class="btn btn-primary" type="submit" style="width:100%;">Guardar vehiculo</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    db = SessionLocal()
    vehicles = db.query(Vehicle).all()

    total_ingresos = 0
    total_gastos = 0
    rows = ""

    for v in vehicles:
        alerta_texto, _, alerta_tipo = calcular_alerta(v)
        ingreso = to_number(v.valor_mensual)
        gastos = sum(to_number(s.costo) for s in v.services) + sum(to_number(e.monto) for e in v.expenses)
        ganancia = ingreso - gastos

        total_ingresos += ingreso
        total_gastos += gastos

        badge_class = get_badge_class(alerta_tipo)
        ganancia_class = "positive" if ganancia >= 0 else "negative"

        rows += f"""
        <tr>
            <td><a href="/" style="color:var(--accent);text-decoration:none;font-weight:600;">{v.patente}</a></td>
            <td>{v.modelo}</td>
            <td>{v.empresa_asignada or '—'}</td>
            <td>${ingreso:,}</td>
            <td>${gastos:,}</td>
            <td><span class="stat-value {ganancia_class}" style="font-size:16px;">${ganancia:,}</span></td>
            <td><span class="badge {badge_class}">{alerta_texto}</span></td>
        </tr>"""

    db.close()

    ganancia_total = total_ingresos - total_gastos
    ganancia_class = "positive" if ganancia_total >= 0 else "negative"

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Dashboard - FleetUp</title>
        {MODERN_STYLES}
    </head>
    <body>
        {nav_component("dashboard")}
        
        <div class="container">
            <h1>Dashboard General</h1>
            <div class="subtitle">Resumen financiero de toda la flota</div>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">Facturacion mensual</div>
                    <div class="stat-value">${total_ingresos:,}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Gastos totales</div>
                    <div class="stat-value negative">${total_gastos:,}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Ganancia total</div>
                    <div class="stat-value {ganancia_class}">${ganancia_total:,}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Vehiculos activos</div>
                    <div class="stat-value">{len(vehicles)}</div>
                </div>
            </div>

            <div class="section-title">Detalle por vehiculo</div>
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
        </div>
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
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Editar Vehiculo</title>
        {MODERN_STYLES}
    </head>
    <body>
        <div class="container" style="max-width:700px;">
            <h1>Editar Vehiculo</h1>
            <div class="subtitle">Actualizar datos del vehiculo</div>
            
            <div class="card">
                <form method="post" action="/edit_vehicle/{v.id}">
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Patente</label><input name="patente" value="{v.patente}" required></div>
                        <div><label>Modelo</label><input name="modelo" value="{v.modelo}" required></div>
                    </div>
                    <div class="form-grid-2" style="margin-bottom:24px;">
                        <div><label>KM actuales</label><input name="kilometros" type="number" value="{v.kilometros}" required></div>
                        <div><label>Valor mensual</label><input name="valor_mensual" value="{v.valor_mensual}"></div>
                    </div>
                    
                    <div class="section-title">Asignacion comercial</div>
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Empresa</label><input name="empresa_asignada" value="{v.empresa_asignada or ''}"></div>
                        <div><label>Fecha</label><input name="fecha_asignacion" type="date" value="{v.fecha_asignacion or ''}"></div>
                    </div>
                    <div style="margin-bottom:24px;">
                        <label>KM asignacion</label>
                        <input name="km_asignacion" type="number" value="{v.km_asignacion or 0}">
                    </div>
                    
                    <div class="btn-group">
                        <button class="btn btn-primary" type="submit">Guardar cambios</button>
                        <a class="btn btn-secondary" href="/">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
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
# EDITAR SERVICE
# =========================================================

@app.get("/edit_service/{service_id}", response_class=HTMLResponse)
def edit_service_form(service_id: int):
    db = SessionLocal()
    s = db.query(Service).filter(Service.id == service_id).first()
    db.close()

    if not s:
        return RedirectResponse("/")

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Editar Service</title>
        {MODERN_STYLES}
    </head>
    <body>
        <div class="container" style="max-width:700px;">
            <h1>Editar Service</h1>
            <div class="subtitle">Actualizar datos del service</div>
            
            <div class="card">
                <form method="post" action="/edit_service/{s.id}">
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Fecha</label><input name="fecha" type="date" value="{s.fecha}" required></div>
                        <div><label>Kilometraje</label><input name="kilometraje" type="number" value="{s.kilometraje}" required></div>
                    </div>
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Tipo</label><input name="tipo_service" value="{s.tipo_service}" required></div>
                        <div><label>Costo</label><input name="costo" value="{s.costo}" required></div>
                    </div>
                    <div style="margin-bottom:24px;">
                        <label>Observaciones</label>
                        <input name="observaciones" value="{s.observaciones or ''}">
                    </div>
                    
                    <div class="btn-group">
                        <button class="btn btn-primary" type="submit">Guardar cambios</button>
                        <a class="btn btn-secondary" href="/">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/edit_service/{service_id}")
def edit_service(
    service_id: int,
    fecha: str = Form(...),
    kilometraje: int = Form(...),
    tipo_service: str = Form(...),
    costo: str = Form(...),
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

    if not g:
        return RedirectResponse("/")

    categorias = ["Patente", "Seguro", "VTV/BTV", "Cubiertas", "Otros"]
    options = "".join([f'<option value="{cat}" {"selected" if g.categoria == cat else ""}>{cat}</option>' for cat in categorias])

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Editar Gasto</title>
        {MODERN_STYLES}
    </head>
    <body>
        <div class="container" style="max-width:700px;">
            <h1>Editar Gasto</h1>
            <div class="subtitle">Actualizar datos del gasto</div>
            
            <div class="card">
                <form method="post" action="/edit_expense/{g.id}">
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Categoria</label><select name="categoria" required>{options}</select></div>
                        <div><label>Fecha</label><input name="fecha" type="date" value="{g.fecha or ''}"></div>
                    </div>
                    <div class="form-grid-2" style="margin-bottom:24px;">
                        <div><label>Monto</label><input name="monto" value="{g.monto}" required></div>
                        <div><label>Observaciones</label><input name="observaciones" value="{g.observaciones or ''}"></div>
                    </div>
                    
                    <div class="btn-group">
                        <button class="btn btn-primary" type="submit">Guardar cambios</button>
                        <a class="btn btn-secondary" href="/">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/edit_expense/{expense_id}")
def edit_expense(
    expense_id: int,
    categoria: str = Form(...),
    fecha: str = Form(""),
    monto: str = Form(...),
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

    if not d:
        return RedirectResponse("/")

    tipos = ["Patente", "Seguro", "VTV/BTV", "Cubiertas", "Otros"]
    options = "".join([f'<option value="{t}" {"selected" if d.tipo == t else ""}>{t}</option>' for t in tipos])

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Editar Vencimiento</title>
        {MODERN_STYLES}
    </head>
    <body>
        <div class="container" style="max-width:700px;">
            <h1>Editar Vencimiento</h1>
            <div class="subtitle">Actualizar datos del vencimiento</div>
            
            <div class="card">
                <form method="post" action="/edit_deadline/{d.id}">
                    <div class="form-grid-2" style="margin-bottom:16px;">
                        <div><label>Tipo</label><select name="tipo" required>{options}</select></div>
                        <div><label>Fecha vencimiento</label><input name="fecha_vencimiento" type="date" value="{d.fecha_vencimiento or ''}" required></div>
                    </div>
                    <div style="margin-bottom:24px;">
                        <label>Observaciones</label>
                        <input name="observaciones" value="{d.observaciones or ''}">
                    </div>
                    
                    <div class="btn-group">
                        <button class="btn btn-primary" type="submit">Guardar cambios</button>
                        <a class="btn btn-secondary" href="/">Cancelar</a>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/edit_deadline/{deadline_id}")
def edit_deadline(
    deadline_id: int,
    tipo: str = Form(...),
    fecha_vencimiento: str = Form(...),
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
# RUTAS BASICAS
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
    vehicle_id: int = Form(...),
    fecha: str = Form(...),
    kilometraje: int = Form(...),
    tipo_service: str = Form(...),
    costo: str = Form(...),
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
    vehicle_id: int = Form(...),
    categoria: str = Form(...),
    fecha: str = Form(""),
    monto: str = Form(...),
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
    vehicle_id: int = Form(...),
    tipo: str = Form(...),
    fecha_vencimiento: str = Form(...),
    observaciones: str = Form("")
):
    db = SessionLocal()
    db.add(VehicleDeadline(vehicle_id=vehicle_id, tipo=tipo,
                           fecha_vencimiento=fecha_vencimiento, observaciones=observaciones))
    db.commit()
    db.close()
    return RedirectResponse("/", status_code=302)


@app.post("/delete_vehicle")
def delete_vehicle(vehicle_id: int = Form(...)):
    db = SessionLocal()
    item = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if item:
        db.delete(item)
        db.commit()
    db.close()
    return RedirectResponse("/", status_code=302)


@app.post("/delete_service")
def delete_service(service_id: int = Form(...)):
    db = SessionLocal()
    item = db.query(Service).filter(Service.id == service_id).first()
    if item:
        db.delete(item)
        db.commit()
    db.close()
    return RedirectResponse("/", status_code=302)


@app.post("/delete_expense")
def delete_expense(expense_id: int = Form(...)):
    db = SessionLocal()
    item = db.query(VehicleExpense).filter(VehicleExpense.id == expense_id).first()
    if item:
        db.delete(item)
        db.commit()
    db.close()
    return RedirectResponse("/", status_code=302)


@app.post("/delete_deadline")
def delete_deadline(deadline_id: int = Form(...)):
    db = SessionLocal()
    item = db.query(VehicleDeadline).filter(VehicleDeadline.id == deadline_id).first()
    if item:
        db.delete(item)
        db.commit()
    db.close()
    return RedirectResponse("/", status_code=302)