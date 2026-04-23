from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

app = FastAPI()

DATABASE_URL = "sqlite:///./vehicles.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# USUARIOS (login simple)
USERS = {
    "alan": "1234",
    "socio": "1234"
}

SESSIONS = {}

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    patente = Column(String)
    modelo = Column(String)
    km_actual = Column(Integer)

    ultimo_service_km = Column(Integer)
    proximo_service_km = Column(Integer)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return RedirectResponse("/login")

# 🔐 LOGIN PAGE
@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <h2>Login FleetUp</h2>
    <input id="user" placeholder="Usuario"><br><br>
    <input id="pass" placeholder="Contraseña" type="password"><br><br>
    <button onclick="login()">Entrar</button>

    <script>
    function login(){
        fetch("/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                username: user.value,
                password: pass.value
            })
        }).then(res => {
            if(res.ok){
                window.location.href = "/app";
            } else {
                alert("Login incorrecto");
            }
        })
    }
    </script>
    """

# 🔐 LOGIN LOGIC
@app.post("/login")
async def do_login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if USERS.get(username) == password:
        response = RedirectResponse(url="/app", status_code=302)
        response.set_cookie("user", username)
        return response

    return {"error": "login incorrecto"}

# 🔐 APP (PROTEGIDA)
@app.get("/app", response_class=HTMLResponse)
def app_web(request: Request):

    user = request.cookies.get("user")
    if user not in USERS:
        return RedirectResponse("/login")

    return """
<!DOCTYPE html>
<html>
<head>
<title>FleetUp</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body { font-family: Arial; padding: 15px; background: #f0f0f0; }
.card { padding: 15px; margin: 10px 0; border-radius: 10px; }
input, button { width: 100%; padding: 10px; margin-top: 5px; }
button { background: black; color: white; border: none; border-radius: 5px; }
.edit-box { background: #fff3cd; padding: 10px; margin-top: 10px; border-radius: 8px; }
</style>
</head>

<body>

<h2>🚗 FleetUp</h2>
<button onclick="logout()">Cerrar sesión</button>

<h3>Agregar vehículo</h3>
<input id="patente" placeholder="Patente">
<input id="modelo" placeholder="Modelo">
<input id="km" placeholder="Kilómetros">
<button onclick="crearVehiculo()">Guardar</button>

<h3>Vehículos</h3>

<button onclick="filtro='todos'; cargarVehiculos()">Todos</button>
<button onclick="filtro='rojo'; cargarVehiculos()">🔴 Service</button>
<button onclick="filtro='amarillo'; cargarVehiculos()">🟡 Próximos</button>

<div id="lista"></div>

<script>
const API = window.location.origin;
const SERVICE_INTERVAL = 10000;
let filtro = "todos";

function logout(){
    document.cookie = "user=; Max-Age=0";
    window.location.href = "/login";
}

function crearVehiculo() {
    fetch(`${API}/vehicles/?patente=${patente.value}&modelo=${modelo.value}&km_actual=${km.value}`, {
        method: "POST"
    }).then(() => cargarVehiculos());
}

function sumarKM(v, cantidad) {
    let nuevoKm = parseInt(v.km_actual) + cantidad;

    fetch(`${API}/vehicles/${v.id}?patente=${v.patente}&modelo=${v.modelo}&km_actual=${nuevoKm}&ultimo_service_km=${v.ultimo_service_km || 0}&proximo_service_km=${v.proximo_service_km || 0}`, {
        method: "PUT"
    }).then(() => cargarVehiculos());
}

function mostrarEditor(v) {
    document.getElementById("edit-"+v.id).innerHTML = `
        <div class="edit-box">
            <input id="e_patente_${v.id}" value="${v.patente}">
            <input id="e_modelo_${v.id}" value="${v.modelo}">
            <input id="e_km_${v.id}" value="${v.km_actual}">
            <input id="e_us_${v.id}" value="${v.ultimo_service_km || 0}">
            <input id="e_ps_${v.id}" value="${v.proximo_service_km || 0}">
            <button onclick="guardarEdicion(${v.id})">Guardar cambios</button>
        </div>
    `;
}

function guardarEdicion(id) {
    let p = document.getElementById("e_patente_"+id).value;
    let m = document.getElementById("e_modelo_"+id).value;
    let km = document.getElementById("e_km_"+id).value;
    let us = document.getElementById("e_us_"+id).value;
    let ps = document.getElementById("e_ps_"+id).value;

    fetch(`${API}/vehicles/${id}?patente=${p}&modelo=${m}&km_actual=${km}&ultimo_service_km=${us}&proximo_service_km=${ps}`, {
        method: "PUT"
    }).then(() => cargarVehiculos());
}

function serviceRealizado(v) {
    let kmActual = v.km_actual;
    let proximo = parseInt(kmActual) + SERVICE_INTERVAL;

    fetch(`${API}/vehicles/${v.id}?patente=${v.patente}&modelo=${v.modelo}&km_actual=${kmActual}&ultimo_service_km=${kmActual}&proximo_service_km=${proximo}`, {
        method: "PUT"
    }).then(() => cargarVehiculos());
}

function getColor(v) {
    if (!v.proximo_service_km) return "white";
    if (v.km_actual >= v.proximo_service_km) return "#ffcccc";
    if (v.proximo_service_km - v.km_actual <= 2000) return "#fff3cd";
    return "white";
}

function cargarVehiculos() {
    fetch(`${API}/vehicles/`)
    .then(res => res.json())
    .then(data => {
        lista.innerHTML = "";
        data.forEach(v => {

            let color = getColor(v);

            if (filtro === "rojo" && color !== "#ffcccc") return;
            if (filtro === "amarillo" && color !== "#fff3cd") return;

            lista.innerHTML += `
                <div class="card" style="background:${color}">
                    <b>${v.modelo}</b><br>
                    Patente: ${v.patente}<br>
                    KM: ${v.km_actual}<br>
                    Último service: ${v.ultimo_service_km || "-"}<br>
                    Próximo service: ${v.proximo_service_km || "-"}<br><br>

                    <button onclick='sumarKM(${JSON.stringify(v)}, 100)'>+100</button>
                    <button onclick='sumarKM(${JSON.stringify(v)}, 500)'>+500</button>
                    <button onclick='sumarKM(${JSON.stringify(v)}, 1000)'>+1000</button>

                    <button onclick='mostrarEditor(${JSON.stringify(v)})'>Editar</button>
                    <button onclick='serviceRealizado(${JSON.stringify(v)})'>Service realizado</button>

                    <div id="edit-${v.id}"></div>
                </div>
            `;
        });
    });
}

cargarVehiculos();
</script>

</body>
</html>
"""

# CRUD
@app.post("/vehicles/")
def create_vehicle(patente: str, modelo: str, km_actual: int):
    db = SessionLocal()
    v = Vehicle(patente=patente, modelo=modelo, km_actual=km_actual)
    db.add(v)
    db.commit()
    db.refresh(v)
    db.close()
    return v

@app.get("/vehicles/")
def get_vehicles():
    db = SessionLocal()
    v = db.query(Vehicle).all()
    db.close()
    return v

@app.put("/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: int, patente: str, modelo: str, km_actual: int,
                   ultimo_service_km: int = 0, proximo_service_km: int = 0):
    db = SessionLocal()
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()

    v.patente = patente
    v.modelo = modelo
    v.km_actual = km_actual
    v.ultimo_service_km = ultimo_service_km
    v.proximo_service_km = proximo_service_km

    db.commit()
    db.refresh(v)
    db.close()
    return v