"""
styles.py — Identidad visual de BeatStorage LATAM.

Decisiones de diseño:
  · Tipografía: Bricolage Grotesque (titulares, con carácter de afiche de tocata)
    + Instrument Sans (texto, muy legible en pantallas pequeñas).
  · Color: magenta "cumbia" (#D63A78) como acento principal y azul "cassette"
    (#2F6FE4) como secundario; verde-azulado para la insignia humana y ámbar para IA.
  · Superficies semitransparentes (rgba gris): el mismo CSS funciona sobre el
    tema claro y el oscuro de Streamlit (Menú ⋮ → Settings → Theme).
  · Elemento memorable: la franja de forma de onda del encabezado. Todo lo demás
    se mantiene sobrio.
"""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600;700&display=swap');

:root {
  --bs-acento: #D63A78;
  --bs-azul: #2F6FE4;
  --bs-humano: #0E9F8A;
  --bs-ia: #C98200;
  --bs-peligro: #D7263D;
  --bs-borde: rgba(128,128,128,.24);
  --bs-superficie: rgba(128,128,128,.07);
  --bs-tenue: rgba(128,128,128,.95);
  --bs-radio: 14px;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
.stMarkdown, button, input, textarea, select {
  font-family: 'Instrument Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
h1, h2, h3, .bs-display {
  font-family: 'Bricolage Grotesque', 'Instrument Sans', system-ui, sans-serif !important;
  letter-spacing: -0.02em;
}
footer { visibility: hidden; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }

/* ---------- Encabezado con forma de onda (elemento memorable) ---------- */
.bs-hero {
  position: relative; overflow: hidden;
  padding: 30px 32px 24px; margin-bottom: 1.4rem;
  border: 1px solid var(--bs-borde); border-radius: 22px;
  background: var(--bs-superficie);
}
.bs-hero h1 { font-size: clamp(1.8rem, 4vw, 2.7rem); line-height: 1.05; margin: 0 0 .4rem; padding: 0; font-weight: 800; }
.bs-hero p  { max-width: 60ch; margin: 0; opacity: .8; font-size: 1.02rem; }
.bs-onda { display: flex; align-items: flex-end; gap: 3px; height: 46px; margin-top: 22px; }
.bs-onda span {
  flex: 1; min-width: 2px; border-radius: 2px 2px 0 0;
  background: linear-gradient(180deg, var(--bs-acento), var(--bs-azul));
  opacity: .85; transform-origin: bottom;
  animation: bs-subir .9s cubic-bezier(.2,.8,.2,1) both;
}
@keyframes bs-subir { from { transform: scaleY(.05); } to { transform: scaleY(1); } }
@media (prefers-reduced-motion: reduce) { .bs-onda span { animation: none; } }

.bs-cifras { display: flex; flex-wrap: wrap; gap: 26px; margin-top: 18px; }
.bs-cifra b { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.45rem; display: block; line-height: 1.1; }
.bs-cifra small { opacity: .7; font-size: .82rem; }

/* ---------- Insignias ---------- */
.bs-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 9px; margin: 0 4px 4px 0; border-radius: 999px;
  font-size: .74rem; font-weight: 600; border: 1px solid; white-space: nowrap;
}
.bs-badge.humano    { color: var(--bs-humano);  border-color: rgba(14,159,138,.45); background: rgba(14,159,138,.10); }
.bs-badge.comprador { color: var(--bs-azul);    border-color: rgba(47,111,228,.45); background: rgba(47,111,228,.10); }
.bs-badge.ia        { color: var(--bs-ia);      border-color: rgba(201,130,0,.45);  background: rgba(201,130,0,.10); }
.bs-badge.exclusivo { color: var(--bs-acento);  border-color: rgba(214,58,120,.45); background: rgba(214,58,120,.10); }
.bs-badge.neutro    { color: var(--bs-tenue);   border-color: var(--bs-borde);      background: transparent; }
.bs-badge.peligro   { color: var(--bs-peligro); border-color: rgba(215,38,61,.45);  background: rgba(215,38,61,.10); }

/* ---------- Tarjetas de beat / servicio ---------- */
.bs-titulo { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.12rem; line-height: 1.2; margin: 0 0 2px; }
.bs-autor  { font-size: .86rem; opacity: .75; margin-bottom: 6px; }
.bs-chips  { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 8px; }
.bs-chip   { font-size: .76rem; padding: 2px 8px; border-radius: 6px; background: var(--bs-superficie); border: 1px solid var(--bs-borde); }
.bs-precio { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.35rem; font-weight: 700; margin: 2px 0 4px; }
.bs-precio small { font-size: .8rem; font-weight: 500; opacity: .65; }
.bs-texto  { font-size: .92rem; opacity: .88; line-height: 1.5; max-width: 72ch; }
.bs-sello-excl { font-size: .95rem; line-height: 1.4; margin: 4px 0 8px; }

/* ---------- Cuenta regresiva de 7 días ---------- */
.bs-reloj { margin: 6px 0 10px; }
.bs-reloj .riel { height: 8px; border-radius: 4px; background: var(--bs-borde); overflow: hidden; }
.bs-reloj .riel > div { height: 100%; border-radius: 4px; }
.bs-reloj small { display: block; margin-top: 4px; font-size: .82rem; }

/* ---------- Perfil ---------- */
.bs-avatar {
  width: 96px; height: 96px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Bricolage Grotesque', sans-serif; font-size: 2.2rem; font-weight: 800; color: #fff;
  background: linear-gradient(135deg, var(--bs-acento), var(--bs-azul));
}
.bs-plan { border: 1px solid var(--bs-borde); border-radius: var(--bs-radio); padding: 18px; background: var(--bs-superficie); }
.bs-plan b.monto { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.7rem; }

/* ---------- Barra lateral ---------- */
.bs-logo { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.35rem; line-height: 1; margin-bottom: 2px; }
.bs-logo span { color: var(--bs-acento); }
.bs-lema { font-size: .8rem; opacity: .7; margin-bottom: .6rem; }

/* ---------- Ajustes de widgets nativos ---------- */
.stButton > button, .stDownloadButton > button, .stLinkButton > a { border-radius: 10px; font-weight: 600; padding-left: .55rem; padding-right: .55rem; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: var(--bs-radio); }
button:focus-visible, a:focus-visible { outline: 2px solid var(--bs-azul) !important; outline-offset: 2px; }

@media (max-width: 640px) {
  .bs-hero { padding: 22px 18px 18px; }
  .bs-cifras { gap: 16px; }
}
</style>
"""


def inyectar_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
