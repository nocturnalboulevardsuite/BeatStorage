"""
components.py — Componentes de interfaz reutilizables.
"""
import base64
import hashlib
import html
import random
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import core
from config import DIAS_INACTIVIDAD, MOTIVOS_REPORTE, TIPOS_SERVICIO_VOZ

esc = html.escape


# ----------------------------------------------------------------------------
# Navegación
# ----------------------------------------------------------------------------
def ir_a(pagina: str, **extra) -> None:
    """Callback para botones: cambia de página antes del siguiente renderizado."""
    st.session_state["nav"] = pagina
    for clave, valor in extra.items():
        st.session_state[clave] = valor


# ----------------------------------------------------------------------------
# Encabezado con forma de onda
# ----------------------------------------------------------------------------
def encabezado(titulo: str, subtitulo: str = "", cifras: list[tuple[str, str]] | None = None,
               semilla: int = 7) -> None:
    rng = random.Random(semilla)
    barras = "".join(
        f'<span style="height:{rng.randint(12, 100)}%;animation-delay:{i * 12}ms"></span>'
        for i in range(64))
    cifras_html = ""
    if cifras:
        cifras_html = '<div class="bs-cifras">' + "".join(
            f'<div class="bs-cifra"><b>{esc(str(v))}</b><small>{esc(k)}</small></div>'
            for k, v in cifras) + "</div>"
    st.markdown(
        f'<div class="bs-hero"><h1>{esc(titulo)}</h1><p>{esc(subtitulo)}</p>'
        f'{cifras_html}<div class="bs-onda" aria-hidden="true">{barras}</div></div>',
        unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Insignias
# ----------------------------------------------------------------------------
def insignias(u: dict, con_ia: bool | None = None) -> str:
    """Devuelve HTML con las insignias de verificación de un usuario."""
    partes = []
    if u.get("verificado") and u.get("tipo_verificacion") == "productor_real":
        partes.append('<span class="bs-badge humano" title="Autoría humana verificada">'
                      '✔ Productor Real</span>')
    if u.get("verificado") and u.get("tipo_verificacion") == "comprador_real":
        partes.append('<span class="bs-badge comprador" title="Cliente verificado, no es bot">'
                      '✔ Comprador Real</span>')
    if con_ia:
        partes.append('<span class="bs-badge ia" title="El productor declaró uso de IA">'
                      'Usa IA (declarado)</span>')
    return "".join(partes)


def estrellas(valor: float | None) -> str:
    if not valor:
        return "Sin reseñas"
    llenas = int(round(valor))
    return "★" * llenas + "☆" * (5 - llenas) + f" {valor:.1f}"


# ----------------------------------------------------------------------------
# Reproductor HTML5 protegido
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=48)
def _audio_b64(ruta: str, mtime: float) -> str:
    return base64.b64encode(Path(ruta).read_bytes()).decode()


_PLANTILLA_REPRODUCTOR = """
<style>
*{box-sizing:border-box;font-family:'Instrument Sans',system-ui,sans-serif}
body{margin:0;background:transparent;user-select:none;-webkit-user-select:none}
.pl{display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid rgba(128,128,128,.28);
    border-radius:14px;background:rgba(128,128,128,.07)}
.bt{width:42px;height:42px;flex:none;border:none;border-radius:50%;cursor:pointer;color:#fff;font-size:15px;
    background:linear-gradient(135deg,#D63A78,#2F6FE4)}
.bt:focus-visible{outline:2px solid #2F6FE4;outline-offset:2px}
.mt{flex:1;min-width:0}
.ti{font-weight:600;font-size:13px;color:#D63A78;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.br{position:relative;height:6px;margin:7px 0 4px;border-radius:3px;background:rgba(128,128,128,.28);cursor:pointer}
.fi{height:100%;width:0;border-radius:3px;background:linear-gradient(90deg,#D63A78,#2F6FE4)}
.rw{display:flex;justify-content:space-between;gap:8px;font-size:11px;color:#8a8f99;white-space:nowrap}
.rw span:last-child{overflow:hidden;text-overflow:ellipsis}
</style>
<div class="pl" oncontextmenu="return false" ondragstart="return false">
  <button class="bt" id="__ID__b" aria-label="Reproducir">▶</button>
  <div class="mt">
    <div class="ti">__TITULO__</div>
    <div class="br" id="__ID__r"><div class="fi" id="__ID__f"></div></div>
    <div class="rw"><span id="__ID__t">0:00</span><span>__NOTA__</span></div>
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
  const mmss = s => isFinite(s) ? Math.floor(s/60) + ":" + String(Math.floor(s%60)).padStart(2,"0") : "0:00";
  b.onclick = () => a.paused ? a.play() : a.pause();
  a.onplay = () => { b.textContent = "❚❚"; b.setAttribute("aria-label","Pausar"); };
  a.onpause = () => { b.textContent = "▶"; b.setAttribute("aria-label","Reproducir"); };
  a.ontimeupdate = () => { f.style.width = (a.currentTime / a.duration * 100 || 0) + "%";
                           t.textContent = mmss(a.currentTime) + " / " + mmss(a.duration); };
  r.onclick = e => { const p = e.offsetX / r.clientWidth; if (isFinite(a.duration)) a.currentTime = p * a.duration; };
  __AUTOPLAY__
})();
</script>
"""


def reproductor(ruta: str | None, titulo: str,
                nota: str = "🔒 Con marca de agua", autoplay: bool = False) -> None:
    """Reproductor HTML5 embebido sin opción de descarga (solo recibe la preescucha)."""
    if not ruta or not Path(ruta).exists():
        st.caption("Audio no disponible.")
        return
    p = Path(ruta)
    uid = "p" + hashlib.md5(str(p).encode()).hexdigest()[:8]
    codigo = (_PLANTILLA_REPRODUCTOR
              .replace("__ID__", uid)
              .replace("__TITULO__", esc(titulo))
              .replace("__NOTA__", esc(nota))
              .replace("__AUTOPLAY__", "a.play().catch(()=>{});" if autoplay else "")
              .replace("__B64__", _audio_b64(str(p), p.stat().st_mtime)))
    # st.iframe reemplaza a components.html desde Streamlit 1.5x (los textos ya van escapados)
    if hasattr(st, "iframe"):
        st.iframe(codigo, height=78)
    else:
        components.html(codigo, height=78)


# ----------------------------------------------------------------------------
# Contacto P2P
# ----------------------------------------------------------------------------
def botones_contacto(productor: dict, mensaje: str, clave: str) -> None:
    enlaces = core.enlaces_contacto(productor, mensaje)
    if not enlaces:
        st.warning("Este productor aún no registra WhatsApp ni correo.")
        return
    cols = st.columns(len(enlaces))
    if "whatsapp" in enlaces:
        cols[0].link_button("Escribir por WhatsApp", enlaces["whatsapp"], width="stretch",
                            type="primary")
    if "email" in enlaces:
        cols[-1].link_button("Escribir por correo", enlaces["email"], width="stretch")
    st.caption("El pago se coordina directo con el productor (transferencia u otro medio "
               "acordado). Cuando confirme tu pago, podrás dejar una reseña verificada.")


def flujo_pedido(clave: str, usuario: dict | None, productor: dict, tipo: str,
                 item_id: int | None, descripcion: str, monto: float, moneda: str = "USD",
                 texto_boton: str = "Confirmar pedido") -> None:
    """Paso 1: registrar el pedido. Paso 2: abrir WhatsApp/correo con mensaje prellenado."""
    if not usuario:
        st.info("Inicia sesión como cliente para hacer pedidos.")
        return
    if usuario["rol"] != "cliente":
        st.caption("Los pedidos se hacen desde una cuenta de cliente.")
        return
    if usuario["estado"] == "aviso_suspension":
        st.error("Tu cuenta está en revisión por inactividad. No puedes hacer pedidos nuevos.")
        return
    clave_pedido = f"pedido_{clave}"
    if not st.session_state.get(clave_pedido):
        if st.button(texto_boton, key=f"btn_{clave}", type="primary", width="stretch"):
            st.session_state[clave_pedido] = core.crear_pedido(
                usuario["id"], productor["id"], tipo, item_id, descripcion, monto, moneda)
            st.rerun()
        return
    pid = st.session_state[clave_pedido]
    st.success(f"Pedido #{pid} registrado. Ahora coordina el pago con @{productor['username']}.")
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


def tarjeta_beat(b: dict, usuario: dict | None, prefijo: str = "cat") -> None:
    """Tarjeta de beat del catálogo con escucha protegida y compra P2P."""
    k = f"{prefijo}_b{b['id']}"
    prod = _productor_desde(b)
    with st.container(border=True):
        chips = [b["genero"]]
        if b.get("bpm"):
            chips.append(f"{b['bpm']} BPM")
        if b.get("tonalidad"):
            chips.append(b["tonalidad"])
        chips.append("WAV" if b["formato_original"] == "wav" else "MP3")
        st.markdown(
            f'<div class="bs-titulo">{esc(b["titulo"])}</div>'
            f'<div class="bs-autor">@{esc(prod["username"])}'
            f'{" en " + esc(b["p_pais"]) if b.get("p_pais") else ""}</div>'
            f'<div>{insignias(prod, con_ia=bool(b["uso_ia"]))}</div>'
            f'<div class="bs-chips">{"".join(f"<span class=bs-chip>{esc(c)}</span>" for c in chips)}</div>'
            f'<div class="bs-precio">US$ {b["precio_usd"]:,.0f} <small>licencia estándar</small></div>',
            unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        sonando = st.session_state.get("sonando") == k
        if c1.button("Pausar" if sonando else "Escuchar", key=f"play_{k}", width="stretch"):
            st.session_state["sonando"] = None if sonando else k
            if not sonando:
                core.sumar_reproduccion(b["id"])
            st.rerun()
        comprando = st.session_state.get("comprando") == k
        if c2.button("Cerrar" if comprando else "Comprar", key=f"buy_{k}", width="stretch"):
            st.session_state["comprando"] = None if comprando else k
            st.rerun()
        c3.button("Perfil", key=f"prof_{k}", width="stretch",
                  on_click=ir_a, args=("🎧 Productores",), kwargs={"perfil_id": b["productor_id"]})

        if st.session_state.get("sonando") == k:
            reproductor(b["archivo_preview"], b["titulo"], autoplay=True)
            if usuario and usuario["id"] != b["productor_id"]:
                formulario_denuncia(b, usuario, k)
        if st.session_state.get("comprando") == k:
            st.markdown('<div class="bs-texto">Licencia no exclusiva: uso en una canción, '
                        'distribución digital y créditos al productor. El productor te envía '
                        'el archivo original tras confirmar el pago.</div>', unsafe_allow_html=True)
            flujo_pedido(k, usuario, prod, "beat", b["id"],
                         f"Beat «{b['titulo']}»", b["precio_usd"], "USD",
                         texto_boton="Solicitar compra")


def formulario_denuncia(b: dict, usuario: dict, k: str) -> None:
    """La comunidad ayuda al filtro anti-IA: denuncia discreta tras escuchar el beat."""
    clave = f"denuncia_{k}"
    if not st.session_state.get(clave):
        if st.button("Denunciar este beat", key=f"rep_{k}", type="tertiary"):
            st.session_state[clave] = True
            st.rerun()
        return
    with st.form(f"form_rep_{k}"):
        motivo = st.radio("¿Qué pasa con este beat?", list(MOTIVOS_REPORTE),
                          format_func=MOTIVOS_REPORTE.get)
        detalle = st.text_area("Detalle (opcional)", max_chars=400,
                               placeholder="Ej.: es idéntico a un beat de otro productor.")
        enviar, cancelar = st.columns(2)
        if enviar.form_submit_button("Enviar denuncia", type="primary"):
            ok, msg = core.crear_reporte(b["id"], usuario, motivo, detalle)
            if ok:
                st.session_state[clave] = False
            (st.success if ok else st.warning)(msg)
        if cancelar.form_submit_button("Cancelar"):
            st.session_state[clave] = False
            st.rerun()


def tarjeta_exclusivo(b: dict, usuario: dict | None) -> None:
    """Trabajo privado exclusivo: escuchable como portafolio, bloqueado para compra/descarga."""
    with st.container(border=True):
        st.markdown(
            f'<span class="bs-badge exclusivo">Exclusivo</span>'
            f'<div class="bs-sello-excl">Beat creado exclusivamente para '
            f'<b>{esc(b["cliente_username"])}</b> (US$ {b["precio_exclusivo_usd"]:,.0f})</div>'
            f'<div class="bs-titulo">{esc(b["titulo"])}</div>',
            unsafe_allow_html=True)
        reproductor(b["archivo_preview"], b["titulo"], nota="🔒 Solo escucha")
        if usuario and usuario["id"] == b["cliente_exclusivo_id"]:
            ruta = Path(b["archivo_original"])
            if ruta.exists():
                st.download_button("Descargar mi archivo original", ruta.read_bytes(),
                                   file_name=f"{b['titulo']}.{b['formato_original']}",
                                   key=f"dl_excl_{b['id']}", width="stretch", type="primary")
        else:
            st.caption("Bloqueado para compra y descarga: pertenece a su cliente original.")


def tarjeta_servicio(s: dict, usuario: dict | None, prefijo: str = "srv") -> None:
    k = f"{prefijo}_s{s['id']}"
    prod = _productor_desde(s)
    with st.container(border=True):
        tipo = TIPOS_SERVICIO_VOZ.get(s["tipo"], "Beat personalizado por encargo")
        desde = "desde " if s["precio_personalizable"] else ""
        st.markdown(
            f'<div class="bs-titulo">{esc(s["titulo"])}</div>'
            f'<div class="bs-autor">@{esc(prod["username"])}</div>'
            f'<div>{insignias(prod)}</div>'
            f'<div class="bs-chips"><span class="bs-chip">{esc(tipo)}</span>'
            f'<span class="bs-chip">Entrega en {s["entrega_dias"]} días</span></div>'
            f'<div class="bs-texto">{esc(s["descripcion"] or "")}</div>'
            f'<div class="bs-precio">{desde}US$ {s["precio_usd"]:,.0f}</div>',
            unsafe_allow_html=True)
        if s.get("demo_antes_path") and s.get("demo_despues_path"):
            with st.expander("Escuchar antes y después"):
                reproductor(s["demo_antes_path"], "Antes", nota="Toma original")
                reproductor(s["demo_despues_path"], "Después", nota="Con el servicio aplicado")
        c1, c2 = st.columns(2)
        abierto = st.session_state.get("pidiendo") == k
        if c1.button("Cerrar" if abierto else "Pedir servicio", key=f"ask_{k}", width="stretch",
                     type="secondary" if abierto else "primary"):
            st.session_state["pidiendo"] = None if abierto else k
            st.rerun()
        c2.button("Perfil", key=f"prof_{k}", width="stretch",
                  on_click=ir_a, args=("🎧 Productores",), kwargs={"perfil_id": s["productor_id"]})
        if abierto:
            flujo_pedido(k, usuario, prod, "servicio", s["id"], f"Servicio «{s['titulo']}»",
                         s["precio_usd"], "USD")


# ----------------------------------------------------------------------------
# Cuenta regresiva de la regla de 7 días
# ----------------------------------------------------------------------------
def cuenta_regresiva(fecha_primera_propuesta: str | None) -> None:
    if not fecha_primera_propuesta:
        st.caption("Aún sin propuestas: el plazo de 7 días parte con la primera.")
        return
    transcurrido = core.dias_desde(fecha_primera_propuesta)
    restante = max(0.0, DIAS_INACTIVIDAD - transcurrido)
    pct = min(100, transcurrido / DIAS_INACTIVIDAD * 100)
    color = ("var(--bs-humano)" if restante > 2 else
             "var(--bs-ia)" if restante > 0 else "var(--bs-peligro)")
    dias, horas = int(restante), int((restante % 1) * 24)
    texto = (f"Quedan {dias} días y {horas} h para elegir un productor o cerrar el encargo."
             if restante > 0 else "Plazo vencido.")
    st.markdown(f'<div class="bs-reloj"><div class="riel"><div style="width:{pct:.0f}%;'
                f'background:{color}"></div></div><small style="color:{color}">{texto}</small></div>',
                unsafe_allow_html=True)


def avatar(u: dict, tam: int = 96) -> None:
    if u.get("foto_path") and Path(u["foto_path"]).exists():
        st.image(u["foto_path"], width=tam)
    else:
        inicial = (u.get("nombre_publico") or u["username"])[:1].upper()
        st.markdown(f'<div class="bs-avatar" style="width:{tam}px;height:{tam}px">{esc(inicial)}</div>',
                    unsafe_allow_html=True)
