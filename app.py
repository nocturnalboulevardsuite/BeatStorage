"""
app.py — Punto de entrada de BeatStorage LATAM.

Ejecutar:  streamlit run app.py

Flujo de cada ejecución:
  1. Configura la página e inicializa la BD (y los datos demo la primera vez).
  2. Ejecuta tareas periódicas (vencimiento de membresías, regla de 7 días).
  3. Inyecta el CSS.
  4. Barra lateral: logo, navegación según el rol y bloque de sesión.
  5. Renderiza la vista elegida.
"""
import streamlit as st

st.set_page_config(page_title="BeatStorage LATAM", page_icon="🎛️", layout="wide",
                   initial_sidebar_state="auto")

import auth  # noqa: E402  (después de set_page_config)
import core  # noqa: E402
import db  # noqa: E402
import styles  # noqa: E402
from components import insignias  # noqa: E402
from config import APP_LEMA, PAISES  # noqa: E402
from vistas import (admin, catalogo, licitaciones, onboarding, panel,  # noqa: E402
                    productores, servicios)


# ----------------------------------------------------------------------------
# 1. Base de datos (una sola vez por proceso)
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Preparando BeatStorage y generando beats de demostración…")
def preparar_bd() -> bool:
    if db.inicializar():
        import seed
        seed.poblar()
    return True


preparar_bd()
core.tareas_periodicas()
styles.inyectar_css()

# ----------------------------------------------------------------------------
# 2. Páginas disponibles por rol
# ----------------------------------------------------------------------------
PAGINAS = {
    "🏠 Catálogo": catalogo.render,
    "🎤 Fix my Vocal": servicios.render,
    "📋 Tablón de encargos": licitaciones.render,
    "🎧 Productores": productores.render,
    "🧭 Mi panel": panel.render,
    "🛡️ Verificación de productor": onboarding.render,
    "⚙️ Administración": admin.render,
}


def paginas_para(usuario: dict | None) -> list[str]:
    base = ["🏠 Catálogo", "🎤 Fix my Vocal", "📋 Tablón de encargos", "🎧 Productores"]
    if not usuario:
        return base
    if usuario["rol"] == "admin":
        return base + ["⚙️ Administración"]
    extra = ["🧭 Mi panel"]
    if usuario["rol"] == "productor":
        extra.append("🛡️ Verificación de productor")
    return base + extra


# ----------------------------------------------------------------------------
# 3. Barra lateral
# ----------------------------------------------------------------------------
def bloque_sesion(usuario: dict | None) -> None:
    if usuario:
        st.markdown(f"**@{usuario['username']}** ({usuario['rol']})")
        if usuario["rol"] != "admin":
            st.markdown(insignias(usuario) or '<span class="bs-badge neutro">Sin verificación</span>',
                        unsafe_allow_html=True)
        n = core.no_leidas(usuario["id"])
        if n:
            st.caption(f"🔔 {n} notificaciones sin leer en Mi panel")
        if usuario["estado"] == "aviso_suspension":
            st.error("Cuenta con aviso de suspensión.")
        if st.button("Cerrar sesión", width="stretch"):
            auth.cerrar_sesion()
            st.rerun()
        return

    ingresar, registrarse = st.tabs(["Ingresar", "Crear cuenta"])
    with ingresar:
        with st.form("login"):
            u = st.text_input("Usuario o correo")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", type="primary", width="stretch"):
                encontrado, error = auth.autenticar(u, p)
                if encontrado:
                    st.session_state["uid"] = encontrado["id"]
                    st.rerun()
                st.error(error)
        with st.expander("Cuentas de demostración"):
            st.caption("Contraseña: demo1234 (admin: admin1234)")
            st.code("sandyy88\nartista_lima\nlofi_valpo\nmezclas_bogota\ntrapsur\nadmin", language=None)

    with registrarse:
        with st.form("registro"):
            rol = st.radio("Quiero", ["cliente", "productor"], horizontal=True,
                           format_func={"cliente": "Comprar / encargar",
                                        "productor": "Vender mis beats"}.get)
            username = st.text_input("Usuario")
            email = st.text_input("Correo")
            pais = st.selectbox("País", PAISES)
            wsp = st.text_input("WhatsApp (opcional)", placeholder="56912345678")
            pw = st.text_input("Contraseña (mín. 8)", type="password")
            if st.form_submit_button("Crear cuenta", type="primary", width="stretch"):
                ok, res = auth.crear_usuario(username, email, pw, rol, pais=pais, whatsapp=wsp)
                if ok:
                    st.session_state["uid"] = res
                    st.session_state["nav"] = ("🛡️ Verificación de productor" if rol == "productor"
                                               else "🏠 Catálogo")
                    st.rerun()
                st.error(res)


usuario = auth.usuario_actual()
opciones = paginas_para(usuario)
if st.session_state.get("nav") not in opciones:
    st.session_state["nav"] = opciones[0]

with st.sidebar:
    st.markdown(f'<div class="bs-logo">BeatStorage <span>LATAM</span></div>'
                f'<div class="bs-lema">{APP_LEMA}</div>', unsafe_allow_html=True)
    pagina = st.radio("Navegación", opciones, key="nav", label_visibility="collapsed")
    st.divider()
    bloque_sesion(usuario)

# ----------------------------------------------------------------------------
# 4. Vista seleccionada
# ----------------------------------------------------------------------------
PAGINAS[pagina](usuario)
