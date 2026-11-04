"""
app.py — Punto de entrada de BeatStorage LATAM.

Ejecutar:  streamlit run app.py

Este archivo concentra la capa visual principal de la versión 6:
  · Estética minimalista con luz RGBIC: la interfaz es neutra y el color solo
    aparece como luz de tira LED (tira superior, menú activo, pista que suena,
    portada del perfil y progreso del registro).
Novedades de la versión 5 que se mantienen:
  · Logo nuevo (una "b" formada por un mástil y un disco de vinilo).
  · Navegación lateral con botones (más cómoda que los radio buttons).
  · Productores estilo SoundCloud: directorio de artistas, portada de perfil y
    lista de pistas con forma de onda real que se ilumina al reproducir.
  · Registro paso a paso estilo Spotify (correo → contraseña → perfil) e inicio
    de sesión en una pantalla limpia y centrada.
Depende de los módulos de la versión 4 (components, styles, core, db, auth, audio, vistas/).
"""
import hashlib
from pathlib import Path

import numpy as np
import streamlit as st

st.set_page_config(page_title="BeatStorage LATAM", page_icon=":material/album:",
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
    import audio  # noqa: E402
    import auth  # noqa: E402
    import core  # noqa: E402
    import db  # noqa: E402
    import styles  # noqa: E402
    from components import (esc, flujo_pedido, formulario_denuncia, icono,  # noqa: E402
                            insignias, ir_a, tarjeta_servicio)
    from config import PAISES  # noqa: E402
    from vistas import admin, catalogo, licitaciones, onboarding, panel, servicios  # noqa: E402

    # Ojo: una expresión suelta (p. ej. "styles.paleta") la dibuja Streamlit en pantalla
    # por su función "magic"; por eso se comprueba con hasattr y no con una línea suelta.
    if not hasattr(styles, "paleta"):
        raise AttributeError("styles.py es de una versión anterior")
except (ImportError, AttributeError) as error:
    st.error("Hay archivos de una versión anterior mezclados con este app.py. Sube **todos** los "
             "archivos del proyecto (components.py, styles.py, la carpeta vistas/ y "
             f".streamlit/config.toml), no solo app.py.\n\nDetalle: `{error}`")
    st.stop()


# ----------------------------------------------------------------------------
# 1. Base de datos (una sola vez por proceso) y tareas periódicas
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
# 2. Capa visual: minimalista, con luz RGBIC.
#    La interfaz es neutra (usa las variables de styles.py, así funciona igual en
#    el tema oscuro y en el claro) y el color solo aparece como luz, igual que una
#    tira LED RGBIC: varios colores a la vez que avanzan. Hay luz en pocos lugares:
#    la tira superior, la página activa del menú, la pista que suena, la portada
#    del perfil y la barra de progreso del registro. Al pasar el cursor por un
#    productor se enciende un aro alrededor de su foto.
#    Si el sistema pide "reducir movimiento", la luz se queda quieta.
# ----------------------------------------------------------------------------
LED = ["#FF3D7F", "#FF8A3D", "#FFC83D", "#2EE6A6", "#3DB8FF", "#8C5CFF"]
CICLO_LED = 2.4  # segundos que tarda un color en recorrer todo el espectro


def _keyframes(nombre: str, con_texto: bool = False) -> str:
    """Animación que pasa por los seis colores LED (base del efecto RGBIC)."""
    pasos = list(enumerate(LED)) + [(len(LED), LED[0])]
    cuerpo = "".join(
        f"{i * 100 / len(LED):.2f}%{{background-color:{c}{';color:' + c if con_texto else ''}}}"
        for i, c in pasos)
    return f"@keyframes {nombre}{{{cuerpo}}}"


def retraso(i: int, total: int, ciclo: float, vueltas: float = 1.0) -> str:
    """Desfase de cada barra para que los colores avancen hacia la derecha."""
    return f"animation-delay:-{(total - i) / total * ciclo * vueltas:.3f}s"


_CSS = """
<style>
:root {
  __VARS__
  --espectro:   linear-gradient(90deg,  __DOBLE__);
  --espectro-v: linear-gradient(180deg, __DOBLE__);
  --espectro-c: conic-gradient(from 0deg, __UNO__);
}
__KF__
@keyframes bs-fluir   { from { background-position: 100% 0; } to { background-position: 0% 0; } }
@keyframes bs-fluir-v { from { background-position: 0 0%; }   to { background-position: 0 100%; } }
@keyframes bs-girar   { to { transform: rotate(1turn); } }

.block-container { max-width: 1040px; }

/* ---------- Tira LED superior ---------- */
[data-testid="stDecoration"] { display: none !important; }
.bs-tira { position: fixed; top: 0; left: 0; right: 0; height: 2px; z-index: 1000002; pointer-events: none;
  background: var(--espectro); background-size: 200% 100%; animation: bs-fluir 16s linear infinite; }
.bs-tira::after { content: ""; position: absolute; inset: 0 0 -6px; background: inherit;
  animation: inherit; filter: blur(8px); opacity: .55; }

/* ---------- Botones tipo píldora y tarjetas silenciosas ---------- */
.stButton > button, .stFormSubmitButton > button, .stLinkButton > a,
.stDownloadButton > button, [data-testid="stPopover"] > div > button { border-radius: 999px; }
div[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color: var(--bs-borde) !important; }

/* ---------- Logo (monocromo: la luz queda para la música) ---------- */
.bs-logo2 { display: flex; align-items: center; gap: 10px; margin: .2rem 0 1.8rem; }
.bs-logo2 svg { width: 30px; height: 30px; flex: none; }
.bs-logo2 .nombre { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
  font-size: 1.22rem; letter-spacing: -0.04em; color: var(--bs-texto); line-height: 1; }
.bs-logo2 .region { font-family: 'Instrument Sans', sans-serif; font-weight: 500; font-size: .8rem;
  color: var(--bs-tenue); margin-left: 5px; letter-spacing: 0; }

/* ---------- Navegación lateral: la página activa lleva una luz LED ---------- */
[class*="st-key-nav_"] button {
  position: relative; width: 100%; justify-content: flex-start; border: none !important;
  border-radius: 12px !important; padding: .5rem .8rem .5rem 1.05rem; min-height: 0;
  color: var(--bs-tenue); font-weight: 500; background: transparent; transition: color .15s, background .15s;
}
[class*="st-key-nav_"] button * { justify-content: flex-start; }
[class*="st-key-nav_"] button:hover { background: var(--bs-sup2); color: var(--bs-texto); }
[class*="st-key-nav_"] button[kind="primary"],
[class*="st-key-nav_"] button[kind="primary"]:hover { background: var(--bs-sup2); color: var(--bs-texto); font-weight: 600; }
[class*="st-key-nav_"] button[kind="primary"]::before {
  content: ""; position: absolute; left: 5px; top: 26%; bottom: 26%; width: 3px; border-radius: 3px;
  background: var(--espectro-v); background-size: 100% 200%; animation: bs-fluir-v 5s linear infinite;
}
[class*="st-key-nav_"] button:focus-visible { outline: 2px solid var(--bs-texto); outline-offset: 2px; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .25rem; }
[data-testid="stSidebar"] hr { margin: 1.1rem 0; opacity: .6; }
.bs-lateral-texto { font-size: .84rem; color: var(--bs-tenue); line-height: 1.5; margin: .3rem 0 .8rem; }

/* ---------- Directorio de productores (sin bordes; aro LED al pasar el cursor) ---------- */
[class*="st-key-artista_"] { padding: 18px 8px 6px; border-radius: 22px; transition: background .2s; }
[class*="st-key-artista_"]:hover { background: var(--bs-sup2); }
.bs-artista { text-align: center; }
.bs-artista .aro { position: relative; width: 108px; height: 108px; margin: 0 auto 14px; }
.bs-artista .aro::before { content: ""; position: absolute; inset: -4px; border-radius: 50%;
  background: var(--espectro-c); opacity: 0; transition: opacity .25s;
  animation: bs-girar 4s linear infinite paused; }
[class*="st-key-artista_"]:hover .bs-artista .aro::before { opacity: 1; animation-play-state: running; }
.bs-artista .foto { position: relative; width: 100%; height: 100%; border-radius: 50%; overflow: hidden;
  border: 3px solid var(--bs-sup2); display: flex; align-items: center; justify-content: center;
  font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 2.4rem; color: var(--bs-texto); }
.bs-artista .foto img { width: 100%; height: 100%; object-fit: cover; }
.bs-artista b { display: block; font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bs-artista small { display: block; color: var(--bs-tenue); font-size: .8rem; margin-top: 2px; }
[class*="st-key-artista_"] .stButton button { color: var(--bs-tenue); }
[class*="st-key-artista_"]:hover .stButton button { color: var(--bs-texto); }

/* ---------- Perfil: portada neutra con la onda iluminada ---------- */
.bs-portada { position: relative; height: 150px; border-radius: 22px; overflow: hidden; background: var(--bs-sup2); }
.bs-portada .barras { position: absolute; inset: auto 0 0 0; height: 62%; display: flex; align-items: flex-end;
  gap: 3px; padding: 0 22px; }
.bs-portada .barras span { flex: 1; border-radius: 3px 3px 0 0; opacity: .9;
  animation: bs-rgbic 9s linear infinite; }
.bs-cabecera { display: flex; align-items: flex-start; gap: 20px; margin: -56px 0 0 24px; position: relative; }
.bs-cabecera > div:last-child { padding-top: 66px; min-width: 0; }
.bs-cabecera .foto { width: 120px; height: 120px; flex: none; border-radius: 50%; overflow: hidden;
  border: 5px solid var(--bs-fondo); display: flex; align-items: center; justify-content: center;
  font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 2.8rem; color: var(--bs-texto); }
.bs-cabecera .foto img { width: 100%; height: 100%; object-fit: cover; }
.bs-cabecera h1 { margin: 0; padding: 0; font-size: clamp(1.6rem, 3.6vw, 2.3rem); letter-spacing: -0.035em; }
.bs-cabecera .lugar { color: var(--bs-tenue); font-size: .9rem; margin: 4px 0 6px;
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.bs-cifras2 { display: flex; gap: 32px; flex-wrap: wrap; margin: 20px 0 8px; }
.bs-cifras2 div { display: flex; flex-direction: column; }
.bs-cifras2 b { font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.3rem; line-height: 1.1;
  font-variant-numeric: tabular-nums; }
.bs-cifras2 small { color: var(--bs-tenue); font-size: .78rem; }
.bs-bio { color: var(--bs-tenue); font-size: .92rem; line-height: 1.6; max-width: 62ch; margin: 6px 0 4px; }

/* ---------- Filas de pistas ---------- */
[class*="st-key-fila_"] { padding: 12px 0; border-bottom: 1px solid color-mix(in srgb, var(--bs-borde) 70%, transparent); }
.bs-cover { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center;
  justify-content: center; color: var(--bs-texto); font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700; font-size: 1.1rem; }
.bs-cover.on { color: rgba(0, 0, 0, .72); animation: bs-rgbic 2.4s linear infinite; }
.bs-pista-tit { font-weight: 600; font-size: .95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bs-pista-sub { font-size: .78rem; color: var(--bs-tenue); white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; display: flex; gap: 10px; align-items: center; }
.bs-onda-fija svg { display: block; width: 100%; height: 34px; margin-top: 4px; }
@media (max-width: 640px) {
  .bs-cover { display: none; }
  .bs-cabecera { margin-left: 8px; gap: 14px; margin-top: -44px; }
  .bs-cabecera > div:last-child { padding-top: 50px; }
  .bs-cabecera .foto { width: 92px; height: 92px; font-size: 2.1rem; }
  .bs-portada { height: 120px; }
}

/* ---------- Registro e inicio de sesión ---------- */
.bs-acceso { text-align: center; margin: 1.8rem 0 1.5rem; }
.bs-acceso svg { width: 38px; height: 38px; }
.bs-acceso .titulo { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; letter-spacing: -0.04em;
  font-size: clamp(1.7rem, 4vw, 2.4rem); line-height: 1.08; margin: .9rem 0 0; text-wrap: balance; }
.bs-acceso p { color: var(--bs-tenue); margin: .5rem 0 0; }
.bs-progreso { height: 3px; border-radius: 3px; background: var(--bs-borde); overflow: hidden; margin: 4px 0 4px; }
.bs-progreso div { height: 100%; border-radius: 3px; transition: width .4s ease;
  background: var(--espectro); background-size: 200% 100%; animation: bs-fluir 6s linear infinite; }
.bs-paso { font-size: .8rem; color: var(--bs-tenue); }
.bs-reglas { margin: 4px 0 12px; }
.bs-reglas div { display: flex; align-items: center; gap: 8px; font-size: .86rem; color: var(--bs-tenue); padding: 3px 0; }
.bs-reglas div.ok { color: var(--bs-texto); }
.bs-separador { display: flex; align-items: center; gap: 12px; color: var(--bs-tenue); font-size: .8rem; margin: 14px 0; }
.bs-separador::before, .bs-separador::after { content: ""; flex: 1; height: 1px; background: var(--bs-borde); }
[class*="st-key-rol_"] button { min-height: 76px; border-radius: 16px !important; }

/* ---------- Reducir movimiento: la luz se queda quieta ---------- */
@media (prefers-reduced-motion: reduce) {
  .bs-tira, .bs-tira::after, .bs-progreso div, .bs-portada .barras span, .bs-cover.on,
  .bs-artista .aro::before, [class*="st-key-nav_"] button[kind="primary"]::before {
    animation-play-state: paused !important; }
}
</style>
<div class="bs-tira" aria-hidden="true"></div>
"""

st.markdown(_CSS
            .replace("__VARS__", " ".join(f"--led-{i + 1}: {c};" for i, c in enumerate(LED)))
            .replace("__DOBLE__", ", ".join(LED + LED + LED[:1]))
            .replace("__UNO__", ", ".join(LED + LED[:1]))
            .replace("__KF__", _keyframes("bs-rgbic")),
            unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 3. Logo: una "b" minúscula hecha con un mástil y un disco de vinilo
#    (beat + almacenamiento de música). El hueco del disco es transparente.
# ----------------------------------------------------------------------------
def logo_svg(uid: str = "l") -> str:
    return f"""<svg viewBox="0 0 40 40" role="img" aria-label="BeatStorage LATAM">
  <mask id="bsm-{uid}">
    <rect width="40" height="40" fill="#fff"/>
    <circle cx="21" cy="25" r="8" fill="none" stroke="#000" stroke-opacity=".4" stroke-width="1.1"/>
    <circle cx="21" cy="25" r="2.8" fill="#000"/>
  </mask>
  <g mask="url(#bsm-{uid})" fill="var(--bs-texto)">
    <rect x="6" y="3" width="7" height="34" rx="3.5"/>
    <circle cx="21" cy="25" r="12"/>
  </g>
</svg>"""


def logo() -> None:
    st.markdown(f'<div class="bs-logo2">{logo_svg("side")}<span class="nombre">beatstorage'
                f'<span class="region">latam</span></span></div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 4. Utilidades visuales: tono por nombre, foto/inicial, cifras compactas
# ----------------------------------------------------------------------------
def tinte(texto: str) -> str:
    """Fondo suave y estable por nombre, teñido con uno de los colores LED."""
    n = int(hashlib.md5(texto.encode()).hexdigest()[:2], 16) % len(LED) + 1
    return f"background:color-mix(in srgb, var(--led-{n}) 28%, var(--bs-sup2))"


def foto_html(u: dict) -> str:
    ruta = u.get("foto_path")
    if ruta and Path(ruta).exists():
        import base64
        tipo = "png" if ruta.lower().endswith("png") else "jpeg"
        datos = base64.b64encode(Path(ruta).read_bytes()).decode()
        return f'<img src="data:image/{tipo};base64,{datos}" alt="">'
    return esc((u.get("nombre_publico") or u["username"])[:1].upper())


def compacto(n: int | float | None) -> str:
    n = int(n or 0)
    if n < 1000:
        return str(n)
    return f"{n / 1000:.1f}".replace(".", ",").replace(",0", "") + " mil"


def _tema_oscuro(pal: dict) -> bool:
    """True si el tema activo es oscuro (se deduce de los colores de styles.paleta())."""
    def luz(color: str) -> float | None:
        h = str(color or "").strip().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) < 6:
            return None
        try:
            r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        except ValueError:
            return None
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    fondo, texto = luz(pal.get("fondo")), luz(pal.get("texto"))
    if fondo is not None:
        return fondo < 0.5
    if texto is not None:
        return texto > 0.5
    return True


# ----------------------------------------------------------------------------
# 5. Forma de onda real de cada pista (SoundCloud): se calcula una vez y se cachea
# ----------------------------------------------------------------------------
BARRAS_ONDA = 80


@st.cache_data(show_spinner=False, max_entries=512)
def picos(ruta: str, mtime: float) -> list[float]:
    try:
        x, _ = audio.leer_audio(Path(ruta).read_bytes(), "wav")
    except Exception:
        return [0.35] * BARRAS_ONDA
    bloques = np.array_split(np.abs(x), BARRAS_ONDA)
    v = np.array([np.sqrt(np.mean(b ** 2)) if len(b) else 0.0 for b in bloques])
    v = v / (v.max() or 1.0)
    return [round(float(max(0.1, a)), 3) for a in v]


def picos_de(ruta: str | None) -> list[float]:
    if not ruta or not Path(ruta).exists():
        return [0.35] * BARRAS_ONDA
    return picos(ruta, Path(ruta).stat().st_mtime)


def onda_fija(valores: list[float]) -> str:
    ancho = len(valores) * 4
    barras = "".join(f'<rect x="{i * 4}" y="{(36 - v * 34) / 2:.1f}" width="2.4" height="{v * 34:.1f}" rx="1.2"/>'
                     for i, v in enumerate(valores))
    return (f'<div class="bs-onda-fija"><svg viewBox="0 0 {ancho} 36" preserveAspectRatio="none" '
            f'fill="var(--bs-tenue)" fill-opacity=".35" aria-hidden="true">{barras}</svg></div>')


# Reproductor: mientras suena, la parte ya escuchada de la onda se ilumina como una
# tira RGBIC (cada barra con su color, y los colores avanzan). En pausa, la luz se
# congela; el botón lleva un aro de luz que gira.
_PLANTILLA_ONDA = """
<style>
*{box-sizing:border-box;font-family:'Instrument Sans',system-ui,-apple-system,sans-serif}
body{margin:0;background:transparent;user-select:none;-webkit-user-select:none}
__KF__
@keyframes girar{to{transform:rotate(1turn)}}
.w{display:flex;align-items:center;gap:12px;height:44px;padding:0 3px}
.bt{position:relative;flex:none;width:30px;height:30px;border-radius:50%;border:0;background:transparent;
    color:__TEXTO__;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0}
.bt::before{content:"";position:absolute;inset:0;border-radius:50%;background:conic-gradient(__UNO__);
    -webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 2px),#000 calc(100% - 1.5px));
    mask:radial-gradient(farthest-side,transparent calc(100% - 2px),#000 calc(100% - 1.5px));
    animation:girar __CICLO__s linear infinite;transition:opacity .2s}
.bt:focus-visible{outline:2px solid __TEXTO__;outline-offset:3px}
.o{flex:1;display:flex;align-items:center;gap:2px;height:36px;cursor:pointer}
.o i{flex:1;display:block;border-radius:2px;background:__TENUE__;opacity:.32;transition:opacity .15s}
.o i.on{opacity:1;animation:bs-rgbic __CICLO__s linear infinite;__BRILLO__}
.w.pausa .o i.on,.w.pausa .bt::before{animation-play-state:paused}
.w.pausa .bt::before{opacity:.45}
.t{flex:none;font-size:11px;color:__TENUE__;min-width:66px;text-align:right;font-variant-numeric:tabular-nums}
@media (prefers-reduced-motion:reduce){.o i.on,.bt::before{animation-play-state:paused}}
</style>
<div class="w pausa" id="w" oncontextmenu="return false" ondragstart="return false">
  <button class="bt" id="b" aria-label="Reproducir">__PLAY__</button>
  <div class="o" id="o">__BARRAS__</div>
  <span class="t" id="t">0:00</span>
</div>
<script>
(function(){
  // Preescucha con marca de agua en memoria (Blob): sin URL pública ni botón de descarga.
  const raw = atob("__B64__"); const buf = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);
  const a = new Audio(URL.createObjectURL(new Blob([buf], {type: "audio/wav"})));
  const w = document.getElementById("w"), b = document.getElementById("b"),
        o = document.getElementById("o"), t = document.getElementById("t");
  const barras = Array.from(o.children), PLAY = `__PLAY__`, PAUSA = `__PAUSA__`;
  const mmss = s => isFinite(s) ? Math.floor(s/60) + ":" + String(Math.floor(s%60)).padStart(2,"0") : "0:00";
  b.onclick = () => a.paused ? a.play() : a.pause();
  a.onplay = () => { b.innerHTML = PAUSA; b.setAttribute("aria-label","Pausar"); w.classList.remove("pausa"); };
  a.onpause = () => { b.innerHTML = PLAY; b.setAttribute("aria-label","Reproducir"); w.classList.add("pausa"); };
  a.ontimeupdate = () => {
    const k = Math.floor(a.currentTime / a.duration * barras.length) || 0;
    barras.forEach((el, i) => el.classList.toggle("on", i < k));
    t.textContent = mmss(a.currentTime) + " / " + mmss(a.duration);
  };
  o.onclick = e => { const r = o.getBoundingClientRect();
    if (isFinite(a.duration)) a.currentTime = (e.clientX - r.left) / r.width * a.duration;
    if (a.paused) a.play(); };
  a.play().catch(() => { b.innerHTML = PLAY; });
})();
</script>
"""
_SVG_PLAY = '<svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><path d="M8 5.5v13l10.5-6.5z"/></svg>'
_SVG_PAUSA = ('<svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor"><rect x="6.5" y="5" '
              'width="4" height="14" rx="1"/><rect x="13.5" y="5" width="4" height="14" rx="1"/></svg>')


def reproductor_onda(ruta: str | None) -> None:
    """Reproductor estilo SoundCloud con la onda iluminada en RGBIC; clic para saltar."""
    if not ruta or not Path(ruta).exists():
        st.caption("Audio no disponible.")
        return
    from components import _audio_b64  # caché compartida con el reproductor clásico
    pal = styles.paleta()
    valores = picos_de(ruta)
    barras = "".join(f'<i style="height:{v * 100:.0f}%;{retraso(i, len(valores), CICLO_LED, 2)}"></i>'
                     for i, v in enumerate(valores))
    # En el tema oscuro las barras encendidas brillan; en el claro el brillo ensucia, se omite.
    brillo = "box-shadow:0 0 6px currentColor" if _tema_oscuro(pal) else ""
    codigo = (_PLANTILLA_ONDA
              .replace("__KF__", _keyframes("bs-rgbic", con_texto=True))
              .replace("__UNO__", ", ".join(LED + LED[:1])).replace("__CICLO__", str(CICLO_LED))
              .replace("__BRILLO__", brillo)
              .replace("__BARRAS__", barras).replace("__PLAY__", _SVG_PLAY).replace("__PAUSA__", _SVG_PAUSA)
              .replace("__TENUE__", pal["tenue"]).replace("__TEXTO__", pal["texto"])
              .replace("__B64__", _audio_b64(ruta, Path(ruta).stat().st_mtime)))
    if hasattr(st, "iframe"):          # Streamlit ≥ 1.56
        st.iframe(codigo, height=46)
    else:
        import streamlit.components.v1 as components
        components.html(codigo, height=46)


# ----------------------------------------------------------------------------
# 6. Fila de pista (SoundCloud): play, portada, título, onda, precio y menú "más"
# ----------------------------------------------------------------------------
def _alternar(clave_estado: str, valor: str, beat_id: int | None = None) -> None:
    actual = st.session_state.get(clave_estado)
    st.session_state[clave_estado] = None if actual == valor else valor
    if beat_id and clave_estado == "sonando" and actual != valor:
        core.sumar_reproduccion(beat_id)


def fila_pista(b: dict, usuario: dict | None, prefijo: str) -> None:
    k = f"{prefijo}_b{b['id']}"
    sonando = st.session_state.get("sonando") == k
    comprando = st.session_state.get("comprando") == k
    exclusivo = bool(b["es_exclusivo"])

    with st.container(key=f"fila_{k}"):
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.button("", key=f"ico_play_{k}", help="Cerrar" if sonando else "Escuchar",
                      icon=":material/stop:" if sonando else ":material/play_arrow:",
                      type="primary" if sonando else "secondary",
                      on_click=_alternar, args=("sonando", k, b["id"]))
            estilo = "" if sonando else f' style="{tinte(b["titulo"])}"'
            st.markdown(f'<div class="bs-cover{" on" if sonando else ""}"{estilo}>'
                        f'{esc(b["titulo"][:1].upper())}</div>', unsafe_allow_html=True, width=48)

            with st.container(gap="small"):
                detalles = [b["genero"], b.get("bpm") and f"{b['bpm']} BPM", b.get("tonalidad"),
                            f"{compacto(b['reproducciones'])} reproducciones"]
                ia = (f'<span class="bs-badge ia">{icono("chispa")} IA</span>' if b["uso_ia"] else "")
                sub = ("Exclusivo para " + esc(b["cliente_username"] or "un cliente")) if exclusivo else \
                    "".join(f"<span>{esc(str(d))}</span>" for d in detalles if d)
                st.markdown(f'<div class="bs-pista-tit">{esc(b["titulo"])}</div>'
                            f'<div class="bs-pista-sub">{sub}{ia}</div>', unsafe_allow_html=True)
                if sonando:
                    reproductor_onda(b["archivo_preview"])
                else:
                    st.markdown(onda_fija(picos_de(b["archivo_preview"])), unsafe_allow_html=True)

            if not exclusivo:
                st.button(f"US$ {b['precio_usd']:,.0f}", key=f"buyrow_{k}",
                          icon=":material/close:" if comprando else ":material/shopping_bag:",
                          type="primary" if comprando else "secondary",
                          on_click=_alternar, args=("comprando", k))
            with st.popover("", icon=":material/more_horiz:", key=f"mas_{k}", type="tertiary",
                            help="Más opciones"):
                if exclusivo and usuario and usuario["id"] == b["cliente_exclusivo_id"]:
                    ruta = Path(b["archivo_original"])
                    if ruta.exists():
                        st.download_button("Descargar original", ruta.read_bytes(),
                                           file_name=f"{b['titulo']}.{b['formato_original']}",
                                           icon=":material/download:", key=f"dl_{k}")
                elif exclusivo:
                    st.caption("Trabajo exclusivo: solo escucha, sin compra ni descarga.")
                if usuario and usuario["id"] != b["productor_id"]:
                    formulario_denuncia(b, usuario, k)
                elif not usuario:
                    st.caption("Inicia sesión para denunciar contenido.")

        if comprando and not exclusivo:
            st.caption("Licencia no exclusiva. Recibes el original tras confirmar el pago.")
            prod = {"id": b["productor_id"], "username": b["p_username"],
                    "whatsapp": b.get("p_whatsapp"), "email": b.get("p_email")}
            flujo_pedido(k, usuario, prod, "beat", b["id"], f"Beat «{b['titulo']}»",
                         b["precio_usd"], "USD", texto_boton="Solicitar compra")


# ----------------------------------------------------------------------------
# 7. Productores: directorio de artistas y perfil
# ----------------------------------------------------------------------------
def ver_perfil(pid: int | None) -> None:
    st.session_state["perfil_id"] = pid


def vista_productores(usuario: dict | None) -> None:
    pid = st.session_state.get("perfil_id")
    if pid and db.uno("SELECT id FROM usuarios WHERE id=? AND rol='productor' AND estado='activo'", (pid,)):
        perfil_productor(pid, usuario)
        return

    st.markdown('<div class="bs-hero"><h1>Productores</h1>'
                '<p>Escucha a quienes hacen la música.</p></div>', unsafe_allow_html=True)
    busqueda = st.text_input("Buscar productor", placeholder="Buscar por nombre o país",
                             label_visibility="collapsed", icon=":material/search:")
    sql = """SELECT u.*, (SELECT COUNT(*) FROM beats b WHERE b.productor_id=u.id AND b.es_exclusivo=0
                          AND b.retirado=0) AS pistas,
                     (SELECT COALESCE(SUM(reproducciones),0) FROM beats b WHERE b.productor_id=u.id) AS plays
             FROM usuarios u WHERE u.rol='productor' AND u.estado='activo'"""
    params: tuple = ()
    if busqueda.strip():
        sql += " AND (u.username LIKE ? OR u.nombre_publico LIKE ? OR u.pais LIKE ?)"
        params = (f"%{busqueda.strip()}%",) * 3
    artistas = db.todos(sql + " ORDER BY u.verificado DESC, plays DESC", params)
    if not artistas:
        st.caption("No encontramos productores con esa búsqueda.")
        return

    st.write("")
    columnas = st.columns(4)
    for i, a in enumerate(artistas):
        with columnas[i % 4]:
            with st.container(key=f"artista_{a['id']}"):
                st.markdown(
                    f'<div class="bs-artista"><div class="aro"><div class="foto" style="{tinte(a["username"])}">'
                    f'{foto_html(a)}</div></div><b>{esc(a["nombre_publico"] or a["username"])}</b>'
                    f'<small>{esc(a["pais"] or "LATAM")}</small>'
                    f'<small>{a["pistas"]} pistas, {compacto(a["plays"])} reproducciones</small></div>',
                    unsafe_allow_html=True)
                st.button("Ver perfil", key=f"art_{a['id']}", width="stretch", type="tertiary",
                          on_click=ver_perfil, args=(a["id"],))


def _reproducir_primera(pid: int, primera: int) -> None:
    st.session_state["sonando"] = f"perf{pid}_b{primera}"
    st.session_state[f"seccion_{pid}"] = "Pistas"
    core.sumar_reproduccion(primera)


def _pedir_a_medida(pid: int, servicio_id: int) -> None:
    st.session_state["pidiendo"] = f"perf{pid}_s{servicio_id}"
    st.session_state[f"seccion_{pid}"] = "Servicios"


def perfil_productor(pid: int, usuario: dict | None) -> None:
    p = db.uno("SELECT * FROM usuarios WHERE id=?", (pid,))
    s = core.stats_productor(pid)
    ob = core.onboarding_de(pid)
    pistas = db.todos(core.SQL_BEATS + " WHERE b.productor_id=? AND b.es_exclusivo=0 AND b.retirado=0 "
                      "ORDER BY b.fecha_subida DESC, b.id DESC", (pid,))
    a_medida = db.uno("SELECT id FROM servicios WHERE productor_id=? AND categoria='beat_personalizado' "
                      "AND activo=1 LIMIT 1", (pid,))

    st.button("Productores", icon=":material/arrow_back:", type="tertiary", on_click=ver_perfil, args=(None,))

    # ---- Portada con forma de onda y cabecera ----
    alturas = picos_de(pistas[0]["archivo_preview"]) if pistas else [0.4] * BARRAS_ONDA
    barras = "".join(f'<span style="height:{v * 100:.0f}%;{retraso(i, len(alturas), 9)}"></span>'
                     for i, v in enumerate(alturas))
    st.markdown(
        f'<div class="bs-portada" aria-hidden="true"><div class="barras">{barras}</div></div>'
        f'<div class="bs-cabecera"><div class="foto" style="{tinte(p["username"])}">'
        f'{foto_html(p)}</div><div><h1>{esc(p["nombre_publico"] or p["username"])}</h1>'
        f'<div class="lugar">@{esc(p["username"])} {icono("pin")} {esc(p["pais"] or "LATAM")} '
        f'{insignias(p, con_ia=bool(ob and ob["usa_ia"]))}</div></div></div>',
        unsafe_allow_html=True)

    # ---- Acciones principales ----
    st.write("")
    with st.container(horizontal=True, gap="small"):
        if pistas:
            st.button("Reproducir", icon=":material/play_arrow:", type="primary", key=f"repr_{pid}",
                      on_click=_reproducir_primera, args=(pid, pistas[0]["id"]))
        enlaces = core.enlaces_contacto(p, f"Hola @{p['username']}, te escribo desde BeatStorage LATAM.")
        if enlaces.get("whatsapp"):
            st.link_button("Contactar", enlaces["whatsapp"], icon=":material/chat:")
        elif enlaces.get("email"):
            st.link_button("Contactar", enlaces["email"], icon=":material/mail:")
        if a_medida:
            st.button("Beat a medida", icon=":material/tune:", key=f"medida_{pid}",
                      on_click=_pedir_a_medida, args=(pid, a_medida["id"]))

    st.markdown(
        '<div class="bs-cifras2">'
        f'<div><b>{s["beats_publicos"]}</b><small>pistas</small></div>'
        f'<div><b>{compacto(s["plays"])}</b><small>reproducciones</small></div>'
        f'<div><b>{s["ventas"]}</b><small>ventas</small></div>'
        f'<div><b>{(str(s["rating"]) + " ★") if s["rating"] else "—"}</b><small>calificación</small></div>'
        '</div>'
        + (f'<div class="bs-bio">{esc(p["bio"])}</div>' if p["bio"] else "")
        + (f'<div class="bs-bio">{esc(p["creditos"])}</div>' if p["creditos"] else ""),
        unsafe_allow_html=True)

    # ---- Secciones como píldoras clicables ----
    st.write("")
    secciones = ["Pistas", "Servicios", "Exclusivos", "Reseñas"]
    if not st.session_state.get(f"seccion_{pid}"):   # si se deselecciona, vuelve a "Pistas"
        st.session_state[f"seccion_{pid}"] = "Pistas"
    seccion = st.segmented_control("Sección", secciones, key=f"seccion_{pid}",
                                   label_visibility="collapsed") or "Pistas"
    st.write("")

    if seccion == "Pistas":
        if not pistas:
            st.caption("Aún no hay pistas públicas.")
        for b in pistas:
            fila_pista(b, usuario, f"perf{pid}")

    elif seccion == "Servicios":
        servicios_p = db.todos(core.SQL_SERVICIOS + " WHERE s.productor_id=? AND s.activo=1", (pid,))
        if not servicios_p:
            st.caption("Este productor aún no ofrece servicios.")
        cols = st.columns(2)
        for i, sv in enumerate(servicios_p):
            with cols[i % 2]:
                tarjeta_servicio(sv, usuario, prefijo=f"perf{pid}")

    elif seccion == "Exclusivos":
        st.caption("Trabajos hechos a medida. Se escuchan, pero pertenecen a su cliente.")
        exclusivos = db.todos(core.SQL_BEATS + " WHERE b.productor_id=? AND b.es_exclusivo=1 "
                              "AND b.retirado=0 ORDER BY b.fecha_subida DESC", (pid,))
        if not exclusivos:
            st.caption("Sin trabajos exclusivos publicados.")
        for b in exclusivos:
            fila_pista(b, usuario, f"perfx{pid}")

    else:
        resenas = db.todos("""SELECT r.*, u.username FROM resenas r JOIN usuarios u ON u.id=r.cliente_id
                              WHERE r.productor_id=? ORDER BY r.fecha DESC""", (pid,))
        if not resenas:
            st.caption("Sin reseñas todavía. Solo opinan clientes con compras confirmadas.")
        for r in resenas:
            st.markdown(
                f'<div class="bs-item">{icono("estrella")}<div>'
                f'<b style="color:var(--bs-acento-t)">{"★" * r["calificacion"]}{"☆" * (5 - r["calificacion"])}</b> '
                f'{esc(r["comentario"] or "")}<small>@{esc(r["username"])}, compra verificada, '
                f'{core.hace(r["fecha"])}</small></div></div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 8. Registro paso a paso (estilo Spotify) e inicio de sesión
# ----------------------------------------------------------------------------
def abrir_acceso(modo: str | None) -> None:
    st.session_state["acceso"] = modo
    if modo == "registro":
        st.session_state["reg_paso"] = 1


def _cabecera_acceso(titulo: str, subtitulo: str = "") -> None:
    sub = f"<p>{esc(subtitulo)}</p>" if subtitulo else ""
    st.markdown(f'<div class="bs-acceso">{logo_svg("acc")}<div class="titulo">{esc(titulo)}</div>{sub}</div>',
                unsafe_allow_html=True)


def _ir_paso(paso: int) -> None:
    st.session_state["reg_paso"] = paso


def _reglas_clave(clave: str) -> list[tuple[str, bool]]:
    return [("1 letra", any(c.isalpha() for c in clave)),
            ("1 número", any(c.isdigit() for c in clave)),
            ("8 caracteres como mínimo", len(clave) >= 8)]


def pagina_registro() -> None:
    _, centro, _ = st.columns([1, 1.3, 1])
    with centro:
        paso = st.session_state.setdefault("reg_paso", 1)
        datos = st.session_state.setdefault("reg_datos", {})

        if paso > 1:
            st.button("", icon=":material/arrow_back:", key="reg_atras", type="tertiary",
                      help="Volver", on_click=_ir_paso, args=(paso - 1,))
            st.markdown(f'<div class="bs-progreso"><div style="width:{(paso - 1) / 3 * 100:.0f}%"></div></div>'
                        f'<div class="bs-paso">Paso {paso - 1} de 3</div>', unsafe_allow_html=True)

        # ---- Paso 1: correo ----
        if paso == 1:
            _cabecera_acceso("Regístrate para empezar a escuchar")
            with st.form("reg_1", border=False):
                email = st.text_input("Correo electrónico", value=datos.get("email", ""),
                                      placeholder="nombre@dominio.com")
                if st.form_submit_button("Siguiente", type="primary", width="stretch"):
                    email = email.strip().lower()
                    if not auth.RE_EMAIL.match(email):
                        st.error("Escribe un correo válido.")
                    elif db.uno("SELECT id FROM usuarios WHERE email=?", (email,)):
                        st.error("Ese correo ya tiene una cuenta. Inicia sesión.")
                    else:
                        datos["email"] = email
                        _ir_paso(2)
                        st.rerun()
            st.markdown('<div class="bs-separador">o</div>', unsafe_allow_html=True)
            st.button("¿Ya tienes una cuenta? Inicia sesión", type="tertiary", width="stretch",
                      key="reg_a_login", on_click=abrir_acceso, args=("login",))

        # ---- Paso 2: contraseña con reglas visibles ----
        elif paso == 2:
            _cabecera_acceso("Crea una contraseña", datos.get("email", ""))
            clave = st.text_input("Contraseña", type="password", key="reg_clave")
            reglas = _reglas_clave(clave)
            st.markdown('<div class="bs-reglas">' + "".join(
                f'<div class="{"ok" if ok else ""}">{icono("circulo_ok" if ok else "circulo")} {texto}</div>'
                for texto, ok in reglas) + "</div>", unsafe_allow_html=True)
            if st.button("Siguiente", type="primary", width="stretch", key="reg_sig_2",
                         disabled=not all(ok for _, ok in reglas)):
                datos["clave"] = clave
                _ir_paso(3)
                st.rerun()

        # ---- Paso 3: perfil y cómo usará la plataforma ----
        else:
            _cabecera_acceso("Cuéntanos sobre ti")
            sugerido = "".join(c for c in datos.get("email", "").split("@")[0] if c.isalnum() or c in "_.")[:24]
            nombre = st.text_input("Nombre", value=datos.get("nombre", ""),
                                   help="Este nombre aparecerá en tu perfil")
            usuario_n = st.text_input("Nombre de usuario", value=datos.get("usuario", sugerido))
            c1, c2 = st.columns(2)
            pais = c1.selectbox("País", PAISES)
            wsp = c2.text_input("WhatsApp (opcional)", placeholder="56912345678")

            st.markdown('<div class="bs-paso" style="margin-top:8px">¿Cómo vas a usar BeatStorage?</div>',
                        unsafe_allow_html=True)
            rol = datos.get("rol", "cliente")
            r1, r2 = st.columns(2)
            if r1.button("Escuchar y comprar", key="rol_cliente", icon=":material/headphones:",
                         type="primary" if rol == "cliente" else "secondary", width="stretch"):
                datos["rol"] = "cliente"
                st.rerun()
            if r2.button("Vender mis beats", key="rol_productor", icon=":material/piano:",
                         type="primary" if rol == "productor" else "secondary", width="stretch"):
                datos["rol"] = "productor"
                st.rerun()
            if rol == "productor":
                st.caption("Después te pediremos pruebas de autoría y 10 beats para aparecer en el catálogo.")

            if st.button("Crear cuenta", type="primary", width="stretch", key="reg_crear"):
                datos.update(nombre=nombre, usuario=usuario_n)
                ok, res = auth.crear_usuario(usuario_n, datos.get("email", ""), datos.get("clave", ""), rol,
                                             nombre_publico=nombre, pais=pais, whatsapp=wsp)
                if ok:
                    for clave in ("reg_paso", "reg_datos", "reg_clave", "acceso"):
                        st.session_state.pop(clave, None)
                    st.session_state["uid"] = res
                    st.session_state["nav"] = "verificacion" if rol == "productor" else "catalogo"
                    st.rerun()
                st.error(res)


def pagina_login() -> None:
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        _cabecera_acceso("Inicia sesión en BeatStorage")
        with st.form("login", border=False):
            u = st.text_input("Correo o nombre de usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Iniciar sesión", type="primary", width="stretch"):
                encontrado, error = auth.autenticar(u, p)
                if encontrado:
                    st.session_state["uid"] = encontrado["id"]
                    st.session_state["acceso"] = None
                    st.rerun()
                st.error(error)
        st.markdown('<div class="bs-separador">o</div>', unsafe_allow_html=True)
        st.button("¿No tienes cuenta? Regístrate", type="tertiary", width="stretch",
                  key="login_a_reg", on_click=abrir_acceso, args=("registro",))
        with st.popover("Cuentas demo", icon=":material/info:", type="tertiary", width="stretch"):
            st.caption("Contraseña: demo1234 (admin: admin1234)")
            st.code("sandyy88\nartista_lima\nlofi_valpo\nmezclas_bogota\ntrapsur\nadmin", language=None)


# ----------------------------------------------------------------------------
# 9. Páginas y navegación lateral con botones
# ----------------------------------------------------------------------------
PAGINAS = {
    "catalogo":     (":material/library_music:", "Catálogo", catalogo.render),
    "voz":          (":material/mic:", "Fix my Vocal", servicios.render),
    "tablon":       (":material/assignment:", "Encargos", licitaciones.render),
    "productores":  (":material/headphones:", "Productores", vista_productores),
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


def navegar(pagina: str) -> None:
    st.session_state["nav"] = pagina
    st.session_state["acceso"] = None
    if pagina == "productores":
        st.session_state["perfil_id"] = None  # el menú siempre lleva al directorio


def bloque_usuario(usuario: dict) -> None:
    nombre = esc(usuario["nombre_publico"] or usuario["username"])
    avisos = ""
    n = core.no_leidas(usuario["id"])
    if n:
        avisos += f'<div class="bs-nota">{icono("campana")} {n} sin leer</div>'
    if usuario["estado"] == "aviso_suspension":
        avisos += (f'<div class="bs-nota" style="color:var(--bs-peligro)">{icono("alerta")} '
                   'Cuenta en revisión</div>')
    st.markdown(
        f'<div class="bs-cuenta"><div class="bs-cuenta-avatar">{esc(nombre[:1].upper())}</div>'
        f'<div class="bs-cuenta-datos"><b>{nombre}</b><small>@{esc(usuario["username"])}</small></div></div>'
        f'<div class="bs-cuenta-extra">{insignias(usuario)}{avisos}</div>', unsafe_allow_html=True)


usuario = auth.usuario_actual()
opciones = paginas_para(usuario)
if st.session_state.get("nav") not in opciones:
    st.session_state["nav"] = opciones[0]
acceso = None if usuario else st.session_state.get("acceso")

with st.sidebar:
    logo()
    for pid in opciones:
        ico, nombre, _ = PAGINAS[pid]
        activa = pid == st.session_state["nav"] and not acceso
        st.button(nombre, key=f"nav_{pid}", icon=ico, width="stretch",
                  type="primary" if activa else "tertiary", on_click=navegar, args=(pid,))
    st.divider()
    if usuario:
        bloque_usuario(usuario)
        st.button("Cerrar sesión", icon=":material/logout:", type="tertiary", key="salir",
                  on_click=auth.cerrar_sesion)
    else:
        st.markdown('<p class="bs-lateral-texto">Compra beats, encarga producciones '
                    'o vende tu música.</p>', unsafe_allow_html=True)
        st.button("Registrarte", type="primary", width="stretch", key="cta_registro",
                  on_click=abrir_acceso, args=("registro",))
        st.button("Iniciar sesión", width="stretch", key="cta_login",
                  on_click=abrir_acceso, args=("login",))

# ----------------------------------------------------------------------------
# 10. Vista seleccionada
# ----------------------------------------------------------------------------
if acceso == "registro":
    pagina_registro()
elif acceso == "login":
    pagina_login()
else:
    PAGINAS[st.session_state["nav"]][2](usuario)
