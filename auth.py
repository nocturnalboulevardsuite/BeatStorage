"""
auth.py — Registro, inicio de sesión y sesión del usuario.

Las contraseñas se guardan con PBKDF2-HMAC-SHA256 + sal aleatoria (nunca en texto plano).
La sesión vive en st.session_state["uid"]; el usuario se relee de la BD en cada
ejecución para reflejar al instante cambios de estado (verificación, suspensión).
"""
import hashlib
import hmac
import re
import secrets
from datetime import timedelta

import streamlit as st

import db
from config import MAX_INTENTOS_LOGIN, MINUTOS_BLOQUEO

ITERACIONES = 200_000
RE_USERNAME = re.compile(r"^[A-Za-z0-9_.]{3,24}$")
RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), ITERACIONES
    ).hex()


def crear_usuario(username: str, email: str, password: str, rol: str,
                  nombre_publico: str = "", pais: str = "", whatsapp: str = "",
                  **extra) -> tuple[bool, str | int]:
    """Valida y crea un usuario. Devuelve (ok, id | mensaje de error)."""
    username, email = username.strip(), email.strip().lower()
    if not RE_USERNAME.match(username):
        return False, "El usuario debe tener 3–24 caracteres: letras, números, _ o ."
    if not RE_EMAIL.match(email):
        return False, "Escribe un correo válido."
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if rol not in ("cliente", "productor", "admin"):
        return False, "Rol no válido."
    if db.uno("SELECT id FROM usuarios WHERE username = ? OR email = ?", (username, email)):
        return False, "Ese usuario o correo ya está registrado."

    salt = secrets.token_hex(16)
    # Los productores parten pendientes: deben pasar el filtro anti-IA + 10 beats.
    estado = "pendiente_verificacion" if rol == "productor" else "activo"
    columnas = {
        "username": username, "email": email, "password_hash": _hash(password, salt),
        "salt": salt, "rol": rol, "nombre_publico": nombre_publico.strip() or username,
        "pais": pais, "whatsapp": re.sub(r"\D", "", whatsapp or ""), "estado": estado,
        **extra,
    }
    sql = (f"INSERT INTO usuarios ({', '.join(columnas)}) "
           f"VALUES ({', '.join('?' * len(columnas))})")
    return True, db.ejecutar(sql, tuple(columnas.values()))


def autenticar(username: str, password: str) -> tuple[dict | None, str]:
    u = db.uno("SELECT * FROM usuarios WHERE username = ? OR email = ?",
               (username.strip(), username.strip().lower()))
    if not u:
        _hash(password, secrets.token_hex(16))  # mismo costo: no revela si el usuario existe
        return None, "Usuario o contraseña incorrectos."

    # Bloqueo temporal tras varios intentos fallidos (protección contra fuerza bruta)
    if u["bloqueado_hasta"] and u["bloqueado_hasta"] > db.ahora():
        minutos = max(1, round((db.a_fecha(u["bloqueado_hasta"]) - db.a_fecha(db.ahora()))
                               .total_seconds() / 60))
        return None, f"Demasiados intentos fallidos. Vuelve a intentarlo en {minutos} minutos."

    if not hmac.compare_digest(u["password_hash"], _hash(password, u["salt"])):
        intentos = u["intentos_fallidos"] + 1
        if intentos >= MAX_INTENTOS_LOGIN:
            hasta = (db.a_fecha(db.ahora()) + timedelta(minutes=MINUTOS_BLOQUEO)).strftime(db.FORMATO_FECHA)
            db.ejecutar("UPDATE usuarios SET intentos_fallidos=0, bloqueado_hasta=? WHERE id=?",
                        (hasta, u["id"]))
            return None, (f"Demasiados intentos fallidos. Bloqueamos el acceso por "
                          f"{MINUTOS_BLOQUEO} minutos.")
        db.ejecutar("UPDATE usuarios SET intentos_fallidos=? WHERE id=?", (intentos, u["id"]))
        restantes = MAX_INTENTOS_LOGIN - intentos
        aviso = f" Te quedan {restantes} intentos." if restantes <= 2 else ""
        return None, "Usuario o contraseña incorrectos." + aviso

    if u["intentos_fallidos"] or u["bloqueado_hasta"]:
        db.ejecutar("UPDATE usuarios SET intentos_fallidos=0, bloqueado_hasta=NULL WHERE id=?",
                    (u["id"],))
    if u["estado"] == "suspendido":
        return None, ("Esta cuenta fue suspendida de forma permanente por "
                      "irresponsabilidad comercial. Escribe a soporte si crees que es un error.")
    return u, ""


def usuario_actual() -> dict | None:
    uid = st.session_state.get("uid")
    if not uid:
        return None
    u = db.uno("SELECT * FROM usuarios WHERE id = ?", (uid,))
    if not u or u["estado"] == "suspendido":
        st.session_state.pop("uid", None)
        return None
    return u


def cerrar_sesion() -> None:
    for clave in list(st.session_state.keys()):
        del st.session_state[clave]
