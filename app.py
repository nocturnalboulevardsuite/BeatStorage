"""
app.py — Punto de entrada de BeatStorage LATAM.

Ejecutar:  streamlit run app.py

Flujo de cada ejecución:
  1. Configura la página e inicializa la BD (y los datos demo la primera vez).
  2. Ejecuta tareas periódicas (vencimiento de membresías, regla de 7 días).
  3. Inyecta el CSS según el tema activo (oscuro: rosa oscuro / claro: blanco y rojo).
  4. Barra lateral: logo, navegación con íconos y bloque de sesión.
  5. Renderiza la vista elegida.
"""
import streamlit as st

st.set_page_config(page_title="BeatStorage LATAM", page_icon=":material/graphic_eq:",
                   layout="wide", initial_sidebar_state="auto")

# ----------------------------------------------------------------------------
# 0. Comprobaciones de instalación (mensajes claros en vez de errores crípticos)
# ----------------------------------------------------------------------------
VERSION_MINIMA = (1, 55)
if tuple(int(x) for x in st.__version__.split(".")[:2]) < VERSION_MINIMA:
    st.error(f"Esta app necesita Streamlit {VERSION_MINIMA[0]}.{VERSION_MINIMA[1]} o superior "
             f"(tienes {st.__version__}). Revisa que requirements.txt diga streamlit>=1.55 "
             "y reinicia la app.")
    st.stop()

try:
    import auth  # noqa: E402  (después de set_page_config)
    import core  # noqa: E402
    import db  # noqa: E402
    import styles  # noqa: E402
    from components import esc, icono, insignias  # noqa: E402
    from config import PAISES  # noqa: E402
    from vistas import (admin, catalogo, licitaciones, onboarding, panel,  # noqa: E402
                        productores, servicios)
    styles.paleta  # solo existe en la versión 3 de styles.py
except (ImportError, AttributeError) as error:
    st.error("Hay archivos de una versión anterior mezclados con este app.py. Sube **todos** los "
             "archivos de la versión 3 (components.py, styles.py, la carpeta vistas/ y "
             f".streamlit/config.toml), no solo app.py.\n\nDetalle: `{error}`")
    st.stop()


# ----------------------------------------------------------------------------
# 1. Base de datos (una sola vez por proceso)
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Preparando BeatStorage…")
def preparar_bd() -> bool:
    if db.inicializar():
        import seed
        seed.poblar()
    return True


preparar_bd()
core.tareas_periodicas()
styles.inyectar_css()

# ----------------------------------------------------------------------------
# 2. Páginas: id interno → (ícono Material, nombre visible, vista)
#    Los ids no cambian aunque cambie el texto, así los botones "ir_a" siguen funcionando.
# ----------------------------------------------------------------------------
PAGINAS = {
    "catalogo":     (":material/library_music:", "Catálogo", catalogo.render),
    "voz":          (":material/mic:", "Fix my Vocal", servicios.render),
    "tablon":       (":material/assignment:", "Encargos", licitaciones.render),
    "productores":  (":material/headphones:", "Productores", productores.render),
    "panel":        (":material/space_dashboard:", "Mi panel", panel.render),
    "verificacion": (":material/verified_user:", "Verificación", onboarding.render),
    "admin":        (":material/admin_panel_settings:", "Administración", admin.render),
}


def paginas_para(usuario: dict | None) -> list[str]:
    base = ["catalogo", "voz", "tablon", "productores"]
    if not usuario:
        return base
    if usuario["rol"] == "admin":
        return base + ["admin"]
    return base + ["panel"] + (["verificacion"] if usuario["rol"] == "productor" else [])


def etiqueta(pagina: str) -> str:
    ico, nombre, _ = PAGINAS[pagina]
    return f"{ico}  {nombre}"


# ----------------------------------------------------------------------------
# 3. Barra lateral
# ----------------------------------------------------------------------------
def bloque_sesion(usuario: dict | None) -> None:
    if usuario:
        nombre = esc(usuario["nombre_publico"] or usuario["username"])
        st.markdown(f'<div class="bs-usuario"><b>{nombre}</b><br><small>@{esc(usuario["username"])}'
                    f'</small></div>{insignias(usuario)}', unsafe_allow_html=True)
        n = core.no_leidas(usuario["id"])
        if n:
            st.markdown(f'<div class="bs-nota">{icono("campana")} {n} sin leer</div>',
                        unsafe_allow_html=True)
        if usuario["estado"] == "aviso_suspension":
            st.markdown(f'<div class="bs-nota" style="color:var(--bs-peligro)">{icono("alerta")} '
                        'Cuenta en revisión</div>', unsafe_allow_html=True)
        st.write("")
        if st.button("Cerrar sesión", icon=":material/logout:", type="tertiary"):
            auth.cerrar_sesion()
            st.rerun()
        return

    ingresar, registrarse = st.tabs(["Ingresar", "Crear cuenta"])
    with ingresar:
        with st.form("login", border=False):
            u = st.text_input("Usuario o correo")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", type="primary", width="stretch"):
                encontrado, error = auth.autenticar(u, p)
                if encontrado:
                    st.session_state["uid"] = encontrado["id"]
                    st.rerun()
                st.error(error)
        with st.popover("Cuentas demo", icon=":material/info:", type="tertiary"):
            st.caption("Contraseña: demo1234 (admin: admin1234)")
            st.code("sandyy88\nartista_lima\nlofi_valpo\nmezclas_bogota\ntrapsur\nadmin", language=None)

    with registrarse:
        with st.form("registro", border=False):
            rol = st.segmented_control("Quiero", ["cliente", "productor"], default="cliente",
                                       format_func={"cliente": "Comprar",
                                                    "productor": "Vender beats"}.get)
            username = st.text_input("Usuario")
            email = st.text_input("Correo")
            pais = st.selectbox("País", PAISES)
            wsp = st.text_input("WhatsApp (opcional)", placeholder="56912345678")
            pw = st.text_input("Contraseña", type="password", help="Mínimo 8 caracteres")
            if st.form_submit_button("Crear cuenta", type="primary", width="stretch"):
                ok, res = auth.crear_usuario(username, email, pw, rol or "cliente",
                                             pais=pais, whatsapp=wsp)
                if ok:
                    st.session_state["uid"] = res
                    st.session_state["nav"] = "verificacion" if rol == "productor" else "catalogo"
                    st.rerun()
                st.error(res)


usuario = auth.usuario_actual()
opciones = paginas_para(usuario)
if st.session_state.get("nav") not in opciones:
    st.session_state["nav"] = opciones[0]

with st.sidebar:
    st.markdown('<div class="bs-logo">BeatStorage <span>LATAM</span></div>', unsafe_allow_html=True)
    st.write("")
    pagina = st.radio("Navegación", opciones, key="nav", format_func=etiqueta,
                      label_visibility="collapsed")
    st.divider()
    bloque_sesion(usuario)

# ----------------------------------------------------------------------------
# 4. Vista seleccionada
# ----------------------------------------------------------------------------
PAGINAS[pagina][2](usuario)
