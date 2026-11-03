"""
styles.py — Identidad visual de BeatStorage LATAM.

Dos paletas que siguen el tema activo de Streamlit (st.context.theme.type):
  · Oscuro: fondo ciruela casi negro y rosa oscuro (#C2185B).
  · Claro: todo blanco y rojo (#C8102E).
Minimalismo: una sola tinta de acento, bordes finos, nada de emojis; los íconos son SVG.
"""
import streamlit as st

PALETAS = {
    "dark": {
        "fondo": "#110E13", "superficie": "#1A161D", "superficie2": "#221D26",
        "borde": "#2E2833", "texto": "#EEE8F0", "tenue": "#9B92A1",
        "acento": "#C2185B", "acento_texto": "#E0558F", "acento_suave": "rgba(194,24,91,.14)",
        "ia": "#D9A23A", "ia_suave": "rgba(217,162,58,.12)", "peligro": "#F0506E",
    },
    "light": {
        "fondo": "#FFFFFF", "superficie": "#FFFFFF", "superficie2": "#FAF6F6",
        "borde": "#EEE6E7", "texto": "#1B1416", "tenue": "#6E6366",
        "acento": "#C8102E", "acento_texto": "#B00D27", "acento_suave": "rgba(200,16,46,.07)",
        "ia": "#9A6200", "ia_suave": "rgba(154,98,0,.08)", "peligro": "#C8102E",
    },
}


def tema_actual() -> str:
    """'dark' o 'light'. Si Streamlit aún no lo informa (p. ej. en pruebas), se asume oscuro."""
    try:
        return st.context.theme.type or "dark"
    except Exception:
        return "dark"


def paleta() -> dict:
    return PALETAS[tema_actual()]


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Instrument+Sans:wght@400;500;600&display=swap');

:root {
  --bs-fondo: __fondo__; --bs-sup: __superficie__; --bs-sup2: __superficie2__;
  --bs-borde: __borde__; --bs-texto: __texto__; --bs-tenue: __tenue__;
  --bs-acento: __acento__; --bs-acento-t: __acento_texto__; --bs-acento-s: __acento_suave__;
  --bs-ia: __ia__; --bs-ia-s: __ia_suave__; --bs-peligro: __peligro__;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
.stMarkdown, button, input, textarea, select {
  font-family: 'Instrument Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
h1, h2, h3, .bs-display {
  font-family: 'Bricolage Grotesque', 'Instrument Sans', system-ui, sans-serif !important;
  letter-spacing: -0.025em;
}
footer, [data-testid="stDecoration"] { display: none; }
.block-container { padding-top: 2.4rem; max-width: 1140px; }

/* ---------- Encabezado ---------- */
.bs-hero { margin: 0 0 1.6rem; }
.bs-hero h1 { font-size: clamp(1.9rem, 4.2vw, 2.8rem); font-weight: 800; line-height: 1.02; margin: 0; padding: 0; }
.bs-hero p { margin: .45rem 0 0; color: var(--bs-tenue); font-size: 1rem; max-width: 56ch; }
.bs-onda { display: flex; align-items: flex-end; gap: 3px; height: 28px; margin-top: 18px; }
.bs-onda span {
  flex: 1; min-width: 2px; border-radius: 2px; background: var(--bs-acento); opacity: .9;
  transform-origin: bottom; animation: bs-subir .8s cubic-bezier(.2,.8,.2,1) both;
}
@keyframes bs-subir { from { transform: scaleY(.08); } to { transform: scaleY(1); } }
@media (prefers-reduced-motion: reduce) { .bs-onda span { animation: none; } }

/* ---------- Íconos e insignias ---------- */
.bs-ico { width: 1em; height: 1em; vertical-align: -0.14em; flex: none; }
.bs-badge {
  display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; margin: 0 4px 2px 0;
  border-radius: 999px; font-size: .72rem; font-weight: 600; white-space: nowrap;
  color: var(--bs-acento-t); background: var(--bs-acento-s);
}
.bs-badge.ia { color: var(--bs-ia); background: var(--bs-ia-s); }
.bs-badge.neutro { color: var(--bs-tenue); background: var(--bs-sup2); }
.bs-badge.peligro { color: var(--bs-peligro); background: var(--bs-acento-s); }

/* ---------- Tarjetas ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--bs-borde) !important; border-radius: 14px; background: var(--bs-sup);
  transition: border-color .15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color: var(--bs-acento) !important; }
.bs-titulo { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 600; font-size: 1.08rem; line-height: 1.2; margin: 0; }
.bs-autor  { font-size: .84rem; color: var(--bs-tenue); margin: 2px 0 6px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.bs-meta   { display: flex; flex-wrap: wrap; gap: 12px; font-size: .8rem; color: var(--bs-tenue); margin: 2px 0 4px; }
.bs-precio { font-family: 'Bricolage Grotesque', sans-serif; font-size: clamp(1.05rem, 2.2vw, 1.25rem); font-weight: 600; margin: 0; white-space: nowrap; }
.bs-texto  { font-size: .92rem; color: var(--bs-texto); opacity: .85; line-height: 1.55; max-width: 70ch; margin: 4px 0; }
.bs-nota   { font-size: .8rem; color: var(--bs-tenue); display: flex; align-items: center; gap: 6px; }

/* ---------- Cuenta regresiva ---------- */
.bs-reloj { margin: 8px 0 12px; }
.bs-reloj .riel { height: 4px; border-radius: 2px; background: var(--bs-borde); overflow: hidden; }
.bs-reloj .riel > div { height: 100%; border-radius: 2px; }
.bs-reloj small { display: block; margin-top: 6px; font-size: .8rem; color: var(--bs-tenue); }

/* ---------- Listas con ícono (pasos, notificaciones) ---------- */
.bs-item { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-bottom: 1px solid var(--bs-borde); font-size: .92rem; }
.bs-item:last-child { border-bottom: none; }
.bs-item .bs-ico { margin-top: 3px; }
.bs-item small { display: block; color: var(--bs-tenue); font-size: .78rem; margin-top: 2px; }
.bs-item.leido { opacity: .6; }

/* ---------- Perfil y planes ---------- */
.bs-avatar {
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; color: #fff; background: var(--bs-acento);
}
.bs-plan { border: 1px solid var(--bs-borde); border-radius: 14px; padding: 18px; background: var(--bs-sup); }
.bs-plan b.monto { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.6rem; display: block; margin: 4px 0; }
.bs-plan small { color: var(--bs-tenue); }

/* ---------- Barra lateral: logo, cuenta y acceso ---------- */
[data-testid="stSidebarContent"] { padding-top: .2rem; }
[data-testid="stSidebarUserContent"] { padding-top: 1.2rem; }
.bs-marca { display: flex; align-items: center; gap: 12px; margin: 0 0 1.4rem; min-width: 0; }
.bs-isotipo { width: 42px; height: 42px; flex: none; }
.bs-marca-texto { display: flex; flex-direction: column; min-width: 0; line-height: 1; }
.bs-marca-nombre {
  font-family: 'Bricolage Grotesque', 'Instrument Sans', sans-serif; font-weight: 800;
  font-size: 1.32rem; letter-spacing: -0.03em; color: var(--bs-texto);
  white-space: nowrap; overflow: hidden; text-overflow: clip;
}
.bs-marca-region {
  font-family: 'Instrument Sans', sans-serif; font-weight: 600; font-size: .78rem;
  color: var(--bs-acento-t); margin-top: 4px;
}
.bs-acceso-texto { font-size: .86rem; line-height: 1.45; color: var(--bs-tenue); margin: 0 0 .4rem; }
.bs-cuenta { display: flex; align-items: center; gap: 10px; min-width: 0; }
.bs-cuenta-avatar {
  width: 36px; height: 36px; flex: none; border-radius: 50%; background: var(--bs-acento-s);
  color: var(--bs-acento-t); display: flex; align-items: center; justify-content: center;
  font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800;
}
.bs-cuenta-datos { display: flex; flex-direction: column; min-width: 0; line-height: 1.25; }
.bs-cuenta-datos b, .bs-cuenta-datos small { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bs-cuenta-datos small { color: var(--bs-tenue); font-size: .78rem; }
.bs-cuenta-extra { margin-top: 8px; display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
[data-testid="stSidebar"] [data-testid="stTabs"] button p { font-size: .9rem; }
[data-testid="stSidebar"] hr { margin: 1rem 0; }

/* ---------- Ajuste del texto: que nada se corte ni desborde ---------- */
h1, h2, h3 { text-wrap: balance; overflow-wrap: break-word; }
.bs-titulo { overflow-wrap: anywhere; }
.bs-texto, .bs-item { overflow-wrap: break-word; }
.bs-autor .bs-badge { margin: 0; }

/* ---------- Botones ---------- */
.stButton > button, .stDownloadButton > button, .stLinkButton > a, [data-testid="stPopover"] button {
  border-radius: 10px; font-weight: 600; padding-left: .7rem; padding-right: .7rem;
}
.stButton > button[kind="secondary"], [data-testid="stPopover"] button {
  background: transparent; border-color: var(--bs-borde);
}
.stButton > button[kind="secondary"]:hover, [data-testid="stPopover"] button:hover {
  border-color: var(--bs-acento); color: var(--bs-acento-t);
}
/* Botones solo-ícono de las tarjetas: cuadrados y discretos */
div[class*="st-key-ico_"] { display: flex; justify-content: center; }
div[class*="st-key-ico_"] button {
  width: 40px; min-width: 40px; height: 40px; min-height: 40px; padding: 0 !important;
  border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
}
div[class*="st-key-ico_"] button[kind="primary"] { color: #fff; }
div[class*="st-key-ico_"] button [data-testid="stIconMaterial"] { font-size: 1.2rem; }
/* La fila precio + íconos (la más interna) no se apila en móvil */
[data-testid="stHorizontalBlock"]:has([class*="st-key-ico_"]):not(:has([data-testid="stHorizontalBlock"])) { flex-wrap: nowrap !important; gap: .4rem; }
[data-testid="stHorizontalBlock"]:has([class*="st-key-ico_"]):not(:has([data-testid="stHorizontalBlock"])) > [data-testid="stColumn"] {
  min-width: 0 !important; width: auto !important;
}
button:focus-visible, a:focus-visible { outline: 2px solid var(--bs-acento) !important; outline-offset: 2px; }

@media (max-width: 640px) {
  .block-container { padding-top: 3.4rem; }
  .bs-onda { height: 20px; }
}
</style>
"""


def inyectar_css() -> None:
    css = _CSS
    for clave, valor in paleta().items():
        css = css.replace(f"__{clave}__", valor)
    st.markdown(css, unsafe_allow_html=True)
