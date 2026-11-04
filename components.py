"""
components.py — Componentes de interfaz reutilizables.

Sin emojis: los íconos son SVG en línea (HTML) y, en botones nativos de Streamlit,
íconos Material (":material/..."). Los botones de las tarjetas son solo-ícono con
tooltip, para que nunca aparezcan textos cortados como "Escu…".
"""
import base64
import hashlib
import html
import random
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import core
import styles
from config import DIAS_INACTIVIDAD, MOTIVOS_REPORTE, TIPOS_SERVICIO_VOZ

esc = html.escape

# ----------------------------------------------------------------------------
# Íconos SVG (trazo de 1.8px, heredan el color del texto)
# ----------------------------------------------------------------------------
_TRAZOS = {
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "verificado": '<path d="M12 2.5l2.4 1.8 3 .1.9 2.8 2.4 1.8-.9 2.9.9 2.8-2.4 1.8-.9 2.8-3 .1L12 21.5l-2.4-1.8-3-.1-.9-2.8L3.3 15l.9-2.8-.9-2.9 2.4-1.8.9-2.8 3-.1z"/><path d="m8.5 12 2.4 2.4 4.6-4.8"/>',
    "chispa": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    "candado": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "campana": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "alerta": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    "bloqueo": '<circle cx="12" cy="12" r="9"/><path d="m5.7 5.7 12.6 12.6"/>',
    "circulo": '<circle cx="12" cy="12" r="9"/>',
    "circulo_ok": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.4 2.4 4.6-4.8"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "estrella": '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
    "reloj": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
}


def icono(nombre: str, tam: str = "1em", color: str = "currentColor") -> str:
    return (f'<svg class="bs-ico" style="width:{tam};height:{tam}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{_TRAZOS[nombre]}</svg>')


# ----------------------------------------------------------------------------
# Navegación
# ----------------------------------------------------------------------------
def ir_a(pagina: str, **extra) -> None:
    """Callback para botones: cambia de página (id interno) antes del siguiente renderizado."""
    st.session_state["nav"] = pagina
    for clave, valor in extra.items():
        st.session_state[clave] = valor


# ----------------------------------------------------------------------------
# Encabezado: título, una línea y la forma de onda (elemento de marca)
# ----------------------------------------------------------------------------
def encabezado(titulo: str, subtitulo: str = "", semilla: int = 7) -> None:
    """Título, una línea y un ecualizador que se mueve lento, como sintonizando música."""
    from ecualizador import ecualizador_html
    sub = f"<p>{esc(subtitulo)}</p>" if subtitulo else ""
    st.markdown(f'<div class="bs-hero"><h1>{esc(titulo)}</h1>{sub}'
                f'{ecualizador_html(72, 40, semilla)}</div>',
                unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Insignias
# ----------------------------------------------------------------------------
def insignias(u: dict, con_ia: bool | None = None) -> str:
    partes = []
    if u.get("verificado") and u.get("tipo_verificacion") == "productor_real":
        partes.append(f'<span class="bs-badge" title="Autoría humana verificada">'
                      f'{icono("verificado")} Productor Real</span>')
    if u.get("verificado") and u.get("tipo_verificacion") == "comprador_real":
        partes.append(f'<span class="bs-badge" title="Cliente verificado">'
                      f'{icono("verificado")} Comprador Real</span>')
    if con_ia:
        partes.append(f'<span class="bs-badge ia" title="El productor declaró uso de IA">'
                      f'{icono("chispa")} IA declarada</span>')
    return "".join(partes)


def estrellas(valor: float | None) -> str:
    if not valor:
        return "Sin reseñas"
    llenas = int(round(valor))
    return "★" * llenas + "☆" * (5 - llenas) + f" {valor:.1f}"


# ----------------------------------------------------------------------------
# Reproductor HTML5 protegido (colores según el tema activo)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=48)
def _audio_b64(ruta: str, mtime: float) -> str:
    return base64.b64encode(Path(ruta).read_bytes()).decode()


_SVG_PLAY = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M8 5.5v13l10.5-6.5z"/></svg>'
_SVG_PAUSA = ('<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">'
              '<rect x="6.5" y="5" width="4" height="14" rx="1"/><rect x="13.5" y="5" width="4" height="14" rx="1"/></svg>')
_SVG_CANDADO = ('<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round"><rect x="4" y="11" width="16" height="10" rx="2"/>'
                '<path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>')

_PLANTILLA_REPRODUCTOR = """
<style>
*{box-sizing:border-box;font-family:'Instrument Sans',system-ui,-apple-system,sans-serif}
body{margin:0;background:transparent;user-select:none;-webkit-user-select:none}
.pl{display:flex;align-items:center;gap:12px;padding:8px 12px 8px 8px;border-radius:12px;background:__SUP2__}
.bt{width:38px;height:38px;flex:none;border:none;border-radius:50%;cursor:pointer;color:#fff;
    background:__ACENTO__;display:flex;align-items:center;justify-content:center}
.bt:focus-visible{outline:2px solid __ACENTO__;outline-offset:2px}
.mt{flex:1;min-width:0}
.br{height:4px;border-radius:2px;background:__BORDE__;cursor:pointer;position:relative}
.br::before{content:"";position:absolute;inset:-8px 0}
.fi{height:100%;width:0;border-radius:2px;background:__ACENTO__}
.rw{display:flex;justify-content:space-between;gap:8px;margin-top:6px;font-size:11px;color:__TENUE__;white-space:nowrap}
.rw span:last-child{display:flex;align-items:center;gap:4px}
</style>
<div class="pl" oncontextmenu="return false" ondragstart="return false">
  <button class="bt" id="__ID__b" aria-label="Reproducir __TITULO__">__PLAY__</button>
  <div class="mt">
    <div class="br" id="__ID__r"><div class="fi" id="__ID__f"></div></div>
    <div class="rw"><span id="__ID__t">0:00</span><span>__CANDADO__ __NOTA__</span></div>
  </div>
</div>
<script>
(function(){
  // El audio llega en base64 y se convierte en un Blob en memoria:
  // no hay URL pública que copiar ni controles nativos con "Descargar".
  const raw = atob("__B64__"); const buf = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);
  const a = new Audio(URL.createObjectURL(new Blob([buf], {type: "audio/wav"})));
  const b = document.getElementById("__ID__b"), f = document.getElementById("__ID__f"),
        r = document.getElementById("__ID__r"), t = document.getElementById("__ID__t");
  const PLAY = `__PLAY__`, PAUSA = `__PAUSA__`;
  const mmss = s => isFinite(s) ? Math.floor(s/60) + ":" + String(Math.floor(s%60)).padStart(2,"0") : "0:00";
  b.onclick = () => a.paused ? a.play() : a.pause();
  a.onplay = () => { b.innerHTML = PAUSA; b.setAttribute("aria-label","Pausar"); };
  a.onpause = () => { b.innerHTML = PLAY; b.setAttribute("aria-label","Reproducir"); };
  a.ontimeupdate = () => { f.style.width = (a.currentTime / a.duration * 100 || 0) + "%";
                           t.textContent = mmss(a.currentTime) + " / " + mmss(a.duration); };
  r.onclick = e => { const p = e.offsetX / r.clientWidth; if (isFinite(a.duration)) a.currentTime = p * a.duration; };
  __AUTOPLAY__
})();
</script>
"""


def reproductor(ruta: str | None, titulo: str, nota: str = "Con marca de agua",
                autoplay: bool = False) -> None:
    """Reproductor embebido sin opción de descarga (solo recibe la preescucha)."""
    if not ruta or not Path(ruta).exists():
        st.caption("Audio no disponible.")
        return
    p = Path(ruta)
    pal = styles.paleta()
    uid = "p" + hashlib.md5(str(p).encode()).hexdigest()[:8]
    codigo = (_PLANTILLA_REPRODUCTOR
              .replace("__ID__", uid)
              .replace("__TITULO__", esc(titulo))
              .replace("__NOTA__", esc(nota))
              .replace("__PLAY__", _SVG_PLAY).replace("__PAUSA__", _SVG_PAUSA)
              .replace("__CANDADO__", _SVG_CANDADO)
              .replace("__ACENTO__", pal["acento"]).replace("__SUP2__", pal["superficie2"])
              .replace("__BORDE__", pal["borde"]).replace("__TENUE__", pal["tenue"])
              .replace("__AUTOPLAY__", "a.play().catch(()=>{});" if autoplay else "")
              .replace("__B64__", _audio_b64(str(p), p.stat().st_mtime)))
    if hasattr(st, "iframe"):  # st.iframe reemplaza a components.html (textos ya escapados)
        st.iframe(codigo, height=64)
    else:
        components.html(codigo, height=64)


# ----------------------------------------------------------------------------
# Contacto P2P
# ----------------------------------------------------------------------------
def botones_contacto(productor: dict, mensaje: str, clave: str) -> None:
    enlaces = core.enlaces_contacto(productor, mensaje)
    if not enlaces:
        st.caption("Este productor aún no registra WhatsApp ni correo.")
        return
    cols = st.columns(len(enlaces))
    if "whatsapp" in enlaces:
        cols[0].link_button("WhatsApp", enlaces["whatsapp"], icon=":material/chat:",
                            width="stretch", type="primary")
    if "email" in enlaces:
        cols[-1].link_button("Correo", enlaces["email"], icon=":material/mail:", width="stretch")
    st.caption("El pago se acuerda directo con el productor.")


def flujo_pedido(clave: str, usuario: dict | None, productor: dict, tipo: str,
                 item_id: int | None, descripcion: str, monto: float, moneda: str = "USD",
                 texto_boton: str = "Confirmar pedido") -> None:
    """Paso 1: registrar el pedido. Paso 2: abrir WhatsApp/correo con mensaje prellenado."""
    if not usuario:
        st.info("Inicia sesión como cliente para comprar.")
        return
    if usuario["rol"] != "cliente":
        st.caption("Las compras se hacen desde una cuenta de cliente.")
        return
    if usuario["estado"] == "aviso_suspension":
        st.error("Tu cuenta está en revisión. No puedes hacer pedidos nuevos.")
        return
    clave_pedido = f"pedido_{clave}"
    if not st.session_state.get(clave_pedido):
        if st.button(texto_boton, key=f"btn_{clave}", type="primary", width="stretch"):
            st.session_state[clave_pedido] = core.crear_pedido(
                usuario["id"], productor["id"], tipo, item_id, descripcion, monto, moneda)
            st.rerun()
        return
    pid = st.session_state[clave_pedido]
    st.success(f"Pedido #{pid} registrado.")
    mensaje = (f"Hola @{productor['username']}, soy @{usuario['username']} de BeatStorage LATAM. "
               f"Te escribo por el pedido #{pid}: {descripcion} ({moneda} {monto:,.0f}). "
               "¿Cómo coordinamos el pago?")
    botones_contacto(productor, mensaje, clave)


# ----------------------------------------------------------------------------
# Tarjetas
# ----------------------------------------------------------------------------
def _productor_desde(fila: dict) -> dict:
    """Extrae los datos del productor de una fila con JOIN (columnas prefijadas p_)."""
    return {"id": fila["productor_id"], "username": fila["p_username"],
            "whatsapp": fila.get("p_whatsapp"), "email": fila.get("p_email"),
            "verificado": fila.get("p_verificado"),
            "tipo_verificacion": fila.get("p_tipo_verificacion")}


def _meta(*valores) -> str:
    return '<div class="bs-meta">' + "".join(f"<span>{esc(str(v))}</span>" for v in valores if v) + "</div>"


def tarjeta_beat(b: dict, usuario: dict | None, prefijo: str = "cat") -> None:
    """Tarjeta de beat: datos esenciales, precio y tres botones solo-ícono."""
    k = f"{prefijo}_b{b['id']}"
    prod = _productor_desde(b)
    sonando = st.session_state.get("sonando") == k
    comprando = st.session_state.get("comprando") == k

    with st.container(border=True):
        st.markdown(
            f'<div class="bs-titulo">{esc(b["titulo"])}</div>'
            f'<div class="bs-autor">@{esc(prod["username"])} {insignias(prod, con_ia=bool(b["uso_ia"]))}</div>'
            + _meta(b["genero"], b.get("bpm") and f"{b['bpm']} BPM", b.get("tonalidad")),
            unsafe_allow_html=True)

        c_precio, c1, c2, c3 = st.columns([2.4, 1, 1, 1], vertical_alignment="center")
        c_precio.markdown(f'<div class="bs-precio">US$ {b["precio_usd"]:,.0f}</div>',
                          unsafe_allow_html=True)
        if c1.button("", key=f"ico_play_{k}", help="Cerrar reproductor" if sonando else "Escuchar",
                     icon=":material/stop:" if sonando else ":material/play_arrow:",
                     type="primary" if sonando else "secondary"):
            st.session_state["sonando"] = None if sonando else k
            if not sonando:
                core.sumar_reproduccion(b["id"])
            st.rerun()
        if c2.button("", key=f"ico_buy_{k}", help="Cerrar" if comprando else "Comprar",
                     icon=":material/close:" if comprando else ":material/shopping_bag:"):
            st.session_state["comprando"] = None if comprando else k
            st.rerun()
        c3.button("", key=f"ico_prof_{k}", help="Ver productor", icon=":material/person:",
                  on_click=ir_a, args=("productores",), kwargs={"perfil_id": b["productor_id"]})

        if sonando:
            reproductor(b["archivo_preview"], b["titulo"], autoplay=True)
            if usuario and usuario["id"] != b["productor_id"]:
                formulario_denuncia(b, usuario, k)
        if comprando:
            st.markdown('<div class="bs-nota">Licencia no exclusiva. Recibes el archivo original '
                        'tras confirmar el pago.</div>', unsafe_allow_html=True)
            flujo_pedido(k, usuario, prod, "beat", b["id"], f"Beat «{b['titulo']}»",
                         b["precio_usd"], "USD", texto_boton="Solicitar compra")


def formulario_denuncia(b: dict, usuario: dict, k: str) -> None:
    """Denuncia discreta tras escuchar el beat (ayuda al filtro anti-IA)."""
    clave = f"denuncia_{k}"
    if not st.session_state.get(clave):
        if st.button("Denunciar", key=f"rep_{k}", type="tertiary", icon=":material/flag:"):
            st.session_state[clave] = True
            st.rerun()
        return
    with st.form(f"form_rep_{k}"):
        motivo = st.radio("Motivo", list(MOTIVOS_REPORTE), format_func=MOTIVOS_REPORTE.get)
        detalle = st.text_area("Detalle (opcional)", max_chars=400)
        enviar, cancelar = st.columns(2)
        if enviar.form_submit_button("Enviar", type="primary", width="stretch"):
            ok, msg = core.crear_reporte(b["id"], usuario, motivo, detalle)
            if ok:
                st.session_state[clave] = False
            (st.success if ok else st.warning)(msg)
        if cancelar.form_submit_button("Cancelar", width="stretch"):
            st.session_state[clave] = False
            st.rerun()


def tarjeta_exclusivo(b: dict, usuario: dict | None) -> None:
    """Trabajo privado exclusivo: se escucha como portafolio; sin compra ni descarga."""
    with st.container(border=True):
        st.markdown(
            f'<div class="bs-titulo">{esc(b["titulo"])}</div>'
            f'<div class="bs-autor">Beat creado exclusivamente para {esc(b["cliente_username"])} '
            f'(US$ {b["precio_exclusivo_usd"]:,.0f})</div>', unsafe_allow_html=True)
        reproductor(b["archivo_preview"], b["titulo"], nota="Solo escucha")
        if usuario and usuario["id"] == b["cliente_exclusivo_id"]:
            ruta = Path(b["archivo_original"])
            if ruta.exists():
                st.download_button("Descargar original", ruta.read_bytes(), icon=":material/download:",
                                   file_name=f"{b['titulo']}.{b['formato_original']}",
                                   key=f"dl_excl_{b['id']}", width="stretch", type="primary")


def tarjeta_servicio(s: dict, usuario: dict | None, prefijo: str = "srv") -> None:
    k = f"{prefijo}_s{s['id']}"
    prod = _productor_desde(s)
    abierto = st.session_state.get("pidiendo") == k
    with st.container(border=True):
        tipo = TIPOS_SERVICIO_VOZ.get(s["tipo"], "Beat a medida")
        desde = "desde " if s["precio_personalizable"] else ""
        st.markdown(
            f'<div class="bs-titulo">{esc(s["titulo"])}</div>'
            f'<div class="bs-autor">@{esc(prod["username"])} {insignias(prod)}</div>'
            + _meta(tipo, f"{s['entrega_dias']} días")
            + (f'<div class="bs-texto">{esc(s["descripcion"])}</div>' if s["descripcion"] else ""),
            unsafe_allow_html=True)
        if s.get("demo_antes_path") and s.get("demo_despues_path"):
            reproductor(s["demo_antes_path"], "Antes", nota="Antes")
            reproductor(s["demo_despues_path"], "Después", nota="Después")

        c_precio, c1, c2 = st.columns([3.4, 1, 1], vertical_alignment="center")
        c_precio.markdown(f'<div class="bs-precio">{desde}US$ {s["precio_usd"]:,.0f}</div>',
                          unsafe_allow_html=True)
        if c1.button("", key=f"ico_ask_{k}", help="Cerrar" if abierto else "Pedir servicio",
                     icon=":material/close:" if abierto else ":material/shopping_bag:"):
            st.session_state["pidiendo"] = None if abierto else k
            st.rerun()
        c2.button("", key=f"ico_prof_{k}", help="Ver productor", icon=":material/person:",
                  on_click=ir_a, args=("productores",), kwargs={"perfil_id": s["productor_id"]})
        if abierto:
            flujo_pedido(k, usuario, prod, "servicio", s["id"], f"Servicio «{s['titulo']}»",
                         s["precio_usd"], "USD", texto_boton="Pedir servicio")


# ----------------------------------------------------------------------------
# Cuenta regresiva de la regla de 7 días
# ----------------------------------------------------------------------------
def cuenta_regresiva(fecha_primera_propuesta: str | None) -> None:
    if not fecha_primera_propuesta:
        return
    transcurrido = core.dias_desde(fecha_primera_propuesta)
    restante = max(0.0, DIAS_INACTIVIDAD - transcurrido)
    pct = min(100, transcurrido / DIAS_INACTIVIDAD * 100)
    color = "var(--bs-acento)" if restante > 2 else "var(--bs-peligro)"
    dias, horas = int(restante), int((restante % 1) * 24)
    texto = f"{dias} d {horas} h para responder" if restante > 0 else "Plazo vencido"
    st.markdown(f'<div class="bs-reloj"><div class="riel"><div style="width:{pct:.0f}%;'
                f'background:{color}"></div></div><small>{icono("reloj")} {texto}</small></div>',
                unsafe_allow_html=True)


def avatar(u: dict, tam: int = 96) -> None:
    if u.get("foto_path") and Path(u["foto_path"]).exists():
        st.image(u["foto_path"], width=tam)
    else:
        inicial = (u.get("nombre_publico") or u["username"])[:1].upper()
        st.markdown(f'<div class="bs-avatar" style="width:{tam}px;height:{tam}px;'
                    f'font-size:{tam * 0.42:.0f}px">{esc(inicial)}</div>', unsafe_allow_html=True)


def lista_iconos(items: list[tuple[str, str, str]]) -> None:
    """Lista con íconos SVG: [(icono, texto_html, detalle)]."""
    st.markdown("".join(
        f'<div class="bs-item">{icono(ic)}<div>{texto}'
        + (f"<small>{esc(det)}</small>" if det else "") + "</div></div>"
        for ic, texto, det in items), unsafe_allow_html=True)
