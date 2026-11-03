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
    # Ojo: una expresión suelta (p. ej. "styles.paleta") la dibuja Streamlit en pantalla
    # por su función "magic"; por eso se comprueba con hasattr y no con una línea suelta.
    if not hasattr(styles, "paleta"):
        raise AttributeError("styles.py es de una versión anterior")
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
# 3. Barra lateral: logo arriba, debajo la sesión (iniciar sesión / registrarse)
#    y al final la navegación.
# ----------------------------------------------------------------------------
# Isotipo: una "caja" redondeada que guarda una forma de onda (beats almacenados).
LOGO_SVG = """
<svg class="bs-isotipo" viewBox="0 0 40 40" role="img" aria-label="BeatStorage LATAM">
  <rect width="40" height="40" rx="11" fill="var(--bs-acento)"/>
  <g fill="#fff">
    <rect x="8.5"  y="17" width="3" height="6"  rx="1.5"/>
    <rect x="14"   y="12" width="3" height="16" rx="1.5"/>
    <rect x="19.5" y="8"  width="3" height="24" rx="1.5"/>
    <rect x="25"   y="13" width="3" height="14" rx="1.5"/>
    <rect x="30.5" y="16.5" width="3" height="7" rx="1.5"/>
  </g>
</svg>
"""


def logo() -> None:
    st.markdown(f'<div class="bs-marca">{LOGO_SVG}<div class="bs-marca-texto">'
                '<span class="bs-marca-nombre">BeatStorage</span>'
                '<span class="bs-marca-region">LATAM</span></div></div>',
                unsafe_allow_html=True)


def bloque_usuario(usuario: dict) -> None:
    """Tarjeta compacta del usuario conectado."""
    nombre = esc(usuario["nombre_publico"] or usuario["username"])
    inicial = esc((usuario["nombre_publico"] or usuario["username"])[:1].upper())
    avisos = ""
    n = core.no_leidas(usuario["id"])
    if n:
        avisos = f'<div class="bs-nota">{icono("campana")} {n} sin leer</div>'
    if usuario["estado"] == "aviso_suspension":
        avisos += (f'<div class="bs-nota" style="color:var(--bs-peligro)">{icono("alerta")} '
                   'Cuenta en revisión</div>')
    st.markdown(
        f'<div class="bs-cuenta"><div class="bs-cuenta-avatar">{inicial}</div>'
        f'<div class="bs-cuenta-datos"><b>{nombre}</b><small>@{esc(usuario["username"])}</small></div></div>'
        f'<div class="bs-cuenta-extra">{insignias(usuario)}{avisos}</div>',
        unsafe_allow_html=True)


def bloque_acceso() -> None:
    """Iniciar sesión / Registrarse para visitantes."""
    st.markdown('<p class="bs-acceso-texto">Entra para comprar beats, publicar encargos '
                'o vender tu música.</p>', unsafe_allow_html=True)
    ingresar, registrarse = st.tabs(["Iniciar sesión", "Registrarse"])
    with ingresar:
        with st.form("login", border=False):
            u = st.text_input("Usuario o correo")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Iniciar sesión", type="primary", width="stretch"):
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
                                                    "productor": "Vender beats"}.get,
                                       width="stretch")
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
    logo()
    if usuario:
        bloque_usuario(usuario)
    else:
        bloque_acceso()
    st.divider()
    pagina = st.radio("Navegación", opciones, key="nav", format_func=etiqueta,
                      label_visibility="collapsed")
    if usuario:
        st.divider()
        if st.button("Cerrar sesión", icon=":material/logout:", type="tertiary"):
            auth.cerrar_sesion()
            st.rerun()

# ----------------------------------------------------------------------------
# 4. Vista seleccionada
# ----------------------------------------------------------------------------
PAGINAS[pagina][2](usuario)
