"""
vistas/panel.py — Panel personal (cliente o productor).

Cliente:   notificaciones, pedidos/historial, trabajos exclusivos, reseñas,
           membresía Comprador Real ($3.000 / $15.000 CLP), perfil.
Productor: notificaciones, Mi estudio (beats, exclusivos, servicios), pedidos recibidos,
           membresía Productor Real ($5.000 / $20.000 CLP), perfil.
"""
import uuid
from pathlib import Path

import streamlit as st

import audio
import core
import db
from components import avatar, esc, insignias, ir_a
from config import (ADMIN_EMAIL, ADMIN_WHATSAPP, CARPETAS, DATOS_TRANSFERENCIA,
                    FORMATOS_ESTANDAR, FORMATOS_VERIFICADO, GENEROS, MIN_BEATS_PRODUCTOR,
                    NOMBRE_MEMBRESIA, PAISES, PRECIO_BEAT_PERSONALIZADO,
                    PRECIO_BEAT_SUGERIDO, TARIFAS, TIPOS_SERVICIO_VOZ, TONALIDADES)

ICONO_NOTIF = {"info": "🔔", "exito": "✅", "alerta": "⚠️", "critica": "⛔"}


def render(usuario: dict) -> None:
    c1, c2 = st.columns([1, 6])
    with c1:
        avatar(usuario, 72)
    with c2:
        st.markdown(f"## Hola, {esc(usuario['nombre_publico'] or usuario['username'])}")
        st.markdown(f'<span class="bs-badge neutro">{usuario["rol"].capitalize()}</span>'
                    f'{insignias(usuario)}', unsafe_allow_html=True)

    if usuario["estado"] == "aviso_suspension":
        st.error("⛔ AVISO FORMAL DE SUSPENSIÓN: recibiste propuestas en el tablón y no respondiste "
                 "dentro de 7 días. Tu cuenta está en revisión para suspensión permanente por "
                 "irresponsabilidad comercial. Mientras dure la revisión no puedes publicar encargos "
                 f"ni hacer pedidos. Si hubo un error, escribe a {ADMIN_EMAIL}.")
    if usuario["rol"] == "productor" and usuario["estado"] == "pendiente_verificacion":
        st.warning("Tu perfil aún no es público. Completa la verificación de productor.")
        st.button("Ir a verificación", on_click=ir_a, args=("🛡️ Verificación de productor",))

    n = core.no_leidas(usuario["id"])
    if usuario["rol"] == "productor":
        nombres = [f"Notificaciones ({n})", "Mi estudio", "Pedidos recibidos",
                   "Productor Real", "Perfil"]
    else:
        nombres = [f"Notificaciones ({n})", "Mis pedidos", "Reseñas", "Comprador Real", "Perfil"]
    t = st.tabs(nombres)

    with t[0]:
        _notificaciones(usuario)
    if usuario["rol"] == "productor":
        with t[1]:
            _estudio(usuario)
        with t[2]:
            _pedidos_recibidos(usuario)
    else:
        with t[1]:
            _mis_pedidos(usuario)
        with t[2]:
            _resenas(usuario)
    with t[3]:
        _membresia(usuario)
    with t[4]:
        _perfil(usuario)


# ----------------------------------------------------------------------------
# Notificaciones
# ----------------------------------------------------------------------------
def _notificaciones(usuario: dict) -> None:
    notifs = db.todos("SELECT * FROM notificaciones WHERE usuario_id=? ORDER BY fecha DESC, id DESC "
                      "LIMIT 40", (usuario["id"],))
    if not notifs:
        st.caption("Sin notificaciones.")
        return
    if st.button("Marcar todas como leídas"):
        db.ejecutar("UPDATE notificaciones SET leida=1 WHERE usuario_id=?", (usuario["id"],))
        st.rerun()
    for nt in notifs:
        peso = "" if nt["leida"] else "**"
        st.markdown(f"{ICONO_NOTIF[nt['tipo']]} {peso}{nt['mensaje']}{peso}  \n"
                    f"<small style='opacity:.6'>{core.hace(nt['fecha'])}</small>",
                    unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Cliente
# ----------------------------------------------------------------------------
def _mis_pedidos(usuario: dict) -> None:
    tabla = db.df("""
        SELECT p.id AS '#', p.descripcion AS Detalle, u.username AS Productor,
               p.moneda || ' ' || CAST(p.monto AS INT) AS Monto, p.estado AS Estado,
               p.fecha_creacion AS Fecha
        FROM pedidos p JOIN usuarios u ON u.id = p.productor_id
        WHERE p.cliente_id=? ORDER BY p.fecha_creacion DESC""", (usuario["id"],))
    st.markdown("#### Historial de compras y servicios")
    if tabla.empty:
        st.info("Aún no haces pedidos. Explora el catálogo o Fix my Vocal.")
    else:
        st.dataframe(tabla, hide_index=True, width="stretch")

    exclusivos = db.todos("SELECT b.*, u.username FROM beats b JOIN usuarios u ON u.id=b.productor_id "
                          "WHERE b.es_exclusivo=1 AND b.cliente_exclusivo_id=?", (usuario["id"],))
    if exclusivos:
        st.markdown("#### Mis beats exclusivos")
        for b in exclusivos:
            ruta = Path(b["archivo_original"])
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{esc(b['titulo'])}** por @{esc(b['username'])} "
                        f"(US$ {b['precio_exclusivo_usd']:,.0f})")
            if ruta.exists():
                c2.download_button("Descargar original", ruta.read_bytes(),
                                   file_name=f"{b['titulo']}.{b['formato_original']}",
                                   key=f"mydl_{b['id']}")


def _resenas(usuario: dict) -> None:
    pendientes = core.pedidos_para_resenar(usuario["id"])
    if not pendientes:
        st.info("No tienes pedidos confirmados por reseñar. Las reseñas se habilitan cuando el "
                "productor confirma tu pago.")
        return
    for p in pendientes:
        with st.form(f"res_{p['id']}"):
            st.markdown(f"**Pedido #{p['id']}**: {esc(p['descripcion'])} con @{esc(p['productor'])}")
            nota = st.slider("Calificación", 1, 5, 5, key=f"nota_{p['id']}")
            comentario = st.text_area("Comentario", max_chars=600, key=f"com_{p['id']}")
            if st.form_submit_button("Publicar reseña", type="primary"):
                ok, msg = core.crear_resena(usuario["id"], p["id"], nota, comentario)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()


# ----------------------------------------------------------------------------
# Productor: Mi estudio
# ----------------------------------------------------------------------------
def _estudio(usuario: dict) -> None:
    n = core.beats_publicos(usuario["id"])
    if n < MIN_BEATS_PRODUCTOR:
        st.progress(n / MIN_BEATS_PRODUCTOR,
                    text=f"{n} de {MIN_BEATS_PRODUCTOR} beats mínimos para aparecer en el catálogo")
    sub = st.tabs(["Subir beat", "Mis beats", "Trabajo exclusivo", "Servicios"])
    with sub[0]:
        _form_beat(usuario, exclusivo=False)
    with sub[1]:
        tabla = db.df("""
            SELECT id AS '#', titulo AS Título, genero AS Género, bpm AS BPM,
                   precio_usd AS 'US$', formato_original AS Formato,
                   CASE es_exclusivo WHEN 1 THEN 'Exclusivo' ELSE 'Público' END AS Tipo,
                   reproducciones AS Reproducciones, fecha_subida AS Subido
            FROM beats WHERE productor_id=? AND retirado=0 ORDER BY fecha_subida DESC""", (usuario["id"],))
        if tabla.empty:
            st.info("Aún no subes beats.")
        else:
            st.dataframe(tabla, hide_index=True, width="stretch")
            _editar_beats(usuario)
    with sub[2]:
        st.caption("Publica un beat hecho a medida como prueba de portafolio. Se escucha en tu "
                   "perfil con la leyenda «Beat creado exclusivamente para…», pero nadie más "
                   "puede comprarlo ni descargarlo. Solo el cliente podrá bajar el original.")
        _form_beat(usuario, exclusivo=True)
    with sub[3]:
        _form_servicio(usuario)
        _gestionar_servicios(usuario)


def _editar_beats(usuario: dict) -> None:
    """Editar datos o retirar un beat (borrado lógico: pedidos y reseñas se conservan)."""
    beats = db.todos("SELECT * FROM beats WHERE productor_id=? AND retirado=0 "
                     "ORDER BY fecha_subida DESC", (usuario["id"],))
    st.markdown("#### Editar o retirar")
    b = st.selectbox("Beat", beats, key="editar_beat_sel",
                     format_func=lambda x: f"#{x['id']} {x['titulo']}"
                                           + (" (exclusivo)" if x["es_exclusivo"] else ""))
    with st.form(f"editar_beat_{b['id']}"):
        titulo = st.text_input("Título", b["titulo"])
        c1, c2, c3, c4 = st.columns(4)
        genero = c1.selectbox("Género", GENEROS,
                              index=GENEROS.index(b["genero"]) if b["genero"] in GENEROS else 0)
        bpm = c2.number_input("BPM", 40, 220, int(b["bpm"] or 90))
        tono = c3.selectbox("Tonalidad", TONALIDADES,
                            index=TONALIDADES.index(b["tonalidad"]) if b["tonalidad"] in TONALIDADES else 0)
        precio = c4.number_input("Precio (US$)", 1.0, 500.0, float(b["precio_usd"] or 20),
                                 disabled=bool(b["es_exclusivo"]))
        uso_ia = st.checkbox("Este beat usa herramientas de IA", value=bool(b["uso_ia"]))
        if st.form_submit_button("Guardar cambios", type="primary"):
            ok, msg = core.editar_beat(b["id"], usuario["id"], titulo, genero, bpm, tono, precio, uso_ia)
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()

    if b["es_exclusivo"]:
        st.caption("Los trabajos exclusivos no se pueden retirar: tu cliente conserva su descarga.")
        return
    restantes = core.beats_publicos(usuario["id"]) - 1
    if usuario["estado"] == "activo" and restantes < MIN_BEATS_PRODUCTOR:
        st.warning(f"Si retiras este beat quedarás con {restantes} beats públicos y tu perfil dejará "
                   f"de aparecer en el catálogo hasta volver a {MIN_BEATS_PRODUCTOR}.")
    confirmar = st.checkbox("Confirmo que quiero retirar este beat del catálogo", key=f"conf_ret_{b['id']}")
    if st.button("Retirar beat", key=f"ret_{b['id']}", disabled=not confirmar):
        ok, msg = core.retirar_beat(b["id"], usuario["id"])
        (st.success if ok else st.error)(msg)
        if ok:
            st.rerun()


def _gestionar_servicios(usuario: dict) -> None:
    servicios = db.todos("SELECT * FROM servicios WHERE productor_id=? ORDER BY activo DESC, id DESC",
                         (usuario["id"],))
    if not servicios:
        return
    st.markdown("#### Mis servicios")
    for s in servicios:
        c1, c2 = st.columns([4, 1])
        estado = "Publicado" if s["activo"] else "Pausado"
        c1.markdown(f"**{esc(s['titulo'])}**  \nUS$ {s['precio_usd']:,.0f}, entrega en "
                    f"{s['entrega_dias']} días, {estado.lower()}")
        if c2.button("Pausar" if s["activo"] else "Publicar", key=f"srv_tog_{s['id']}", width="stretch"):
            core.cambiar_estado_servicio(s["id"], usuario["id"], not s["activo"])
            st.rerun()


def _form_beat(usuario: dict, exclusivo: bool) -> None:
    verificado = usuario["verificado"] and usuario["tipo_verificacion"] == "productor_real"
    formatos = FORMATOS_VERIFICADO if verificado else FORMATOS_ESTANDAR
    ob = core.onboarding_de(usuario["id"])
    clave = "excl" if exclusivo else "pub"

    with st.form(f"beat_{clave}", clear_on_submit=True):
        titulo = st.text_input("Título")
        c1, c2, c3 = st.columns(3)
        genero = c1.selectbox("Género", GENEROS)
        bpm = c2.number_input("BPM", 40, 220, 90)
        tono = c3.selectbox("Tonalidad", TONALIDADES, index=TONALIDADES.index("Am"))
        cliente = None
        if exclusivo:
            c4, c5 = st.columns(2)
            cliente = c4.text_input("Usuario del cliente", placeholder="sandyy88")
            precio = c5.number_input("Precio pagado (US$)", 1.0, 5000.0, 50.0)
        else:
            precio = st.number_input(
                f"Precio licencia estándar (US$, sugerido {PRECIO_BEAT_SUGERIDO[0]}–{PRECIO_BEAT_SUGERIDO[1]})",
                1.0, 500.0, 20.0)
        archivo = st.file_uploader(f"Audio ({', '.join(f.upper() for f in formatos)})", type=formatos)
        if not verificado:
            st.caption("Con la membresía Productor Real puedes subir WAV en calidad original.")
        uso_ia = st.checkbox("Este beat usa herramientas de IA en alguna etapa",
                             value=bool(ob and ob["usa_ia"]))
        enviado = st.form_submit_button("Publicar beat" if not exclusivo else "Publicar trabajo exclusivo",
                                        type="primary")
    if not enviado:
        return
    if len(titulo.strip()) < 2 or not archivo:
        st.error("Agrega un título y un archivo de audio.")
        return
    cliente_id = None
    if exclusivo:
        c = db.uno("SELECT id FROM usuarios WHERE username=? AND rol='cliente'", (cliente.strip(),))
        if not c:
            st.error("No existe un cliente con ese usuario.")
            return
        cliente_id = c["id"]
    try:
        with st.spinner("Creando preescucha protegida con marca de agua…"):
            info = audio.procesar_subida(archivo.getvalue(), archivo.name)
    except audio.ErrorAudio as e:
        st.error(str(e))
        return
    db.ejecutar(
        "INSERT INTO beats (productor_id, titulo, genero, bpm, tonalidad, precio_usd, archivo_original, "
        "formato_original, archivo_preview, duracion_seg, uso_ia, es_exclusivo, cliente_exclusivo_id, "
        "precio_exclusivo_usd, fecha_subida) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (usuario["id"], titulo.strip(), genero, int(bpm), tono, 0 if exclusivo else precio,
         info["original"], info["formato"], info["preview"], info["duracion"], int(uso_ia),
         int(exclusivo), cliente_id, precio if exclusivo else None, db.ahora()))
    if exclusivo:
        core.notificar(cliente_id, f"@{usuario['username']} publicó tu beat exclusivo «{titulo.strip()}». "
                                   "Puedes descargar el original desde Mi panel.", "exito")
    core.actualizar_estado_productor(usuario["id"])
    st.success("Beat publicado. La preescucha pública lleva marca de agua.")
    st.rerun()


def _form_servicio(usuario: dict) -> None:
    with st.expander("Publicar un servicio"):
        with st.form("servicio", clear_on_submit=True):
            categoria = st.radio("Categoría", ["fix_my_vocal", "beat_personalizado"], horizontal=True,
                                 format_func={"fix_my_vocal": "Fix my Vocal",
                                              "beat_personalizado": "Beat por encargo"}.get)
            tipo = st.selectbox("Tipo (solo Fix my Vocal)", list(TIPOS_SERVICIO_VOZ),
                                format_func=TIPOS_SERVICIO_VOZ.get)
            titulo = st.text_input("Título")
            descripcion = st.text_area("Descripción", max_chars=600)
            c1, c2, c3 = st.columns(3)
            precio = c1.number_input("Precio base (US$)", 1.0, 2000.0, float(PRECIO_BEAT_PERSONALIZADO))
            dias = c2.number_input("Entrega (días)", 1, 60, 3)
            personalizable = c3.checkbox("Precio personalizable", value=True)
            antes = st.file_uploader("Demo «antes» (opcional)", type=FORMATOS_VERIFICADO, key="srv_a")
            despues = st.file_uploader("Demo «después» (opcional)", type=FORMATOS_VERIFICADO, key="srv_d")
            if st.form_submit_button("Publicar servicio", type="primary"):
                if len(titulo.strip()) < 3:
                    st.error("Agrega un título.")
                    return
                rutas = []
                try:
                    for f in (antes, despues):
                        rutas.append(audio.procesar_subida(f.getvalue(), f.name)["preview"] if f else None)
                except audio.ErrorAudio as e:
                    st.error(str(e))
                    return
                db.ejecutar(
                    "INSERT INTO servicios (productor_id, categoria, tipo, titulo, descripcion, precio_usd, "
                    "precio_personalizable, entrega_dias, demo_antes_path, demo_despues_path, fecha_creacion) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (usuario["id"], categoria, tipo if categoria == "fix_my_vocal" else "beat_personalizado",
                     titulo.strip(), descripcion.strip(), precio, int(personalizable), int(dias),
                     rutas[0], rutas[1], db.ahora()))
                st.success("Servicio publicado.")


def _pedidos_recibidos(usuario: dict) -> None:
    pedidos = db.todos("""
        SELECT p.*, u.username AS cliente, u.verificado, u.tipo_verificacion
        FROM pedidos p JOIN usuarios u ON u.id = p.cliente_id
        WHERE p.productor_id=? ORDER BY
          CASE p.estado WHEN 'solicitado' THEN 0 WHEN 'confirmado' THEN 1 ELSE 2 END,
          p.fecha_creacion DESC""", (usuario["id"],))
    if not pedidos:
        st.info("Aún no recibes pedidos.")
        return
    st.caption("Cuando recibas el pago por transferencia, marca el pedido como confirmado: "
               "eso habilita la reseña verificada del cliente.")
    for p in pedidos:
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            c1.markdown(f"**#{p['id']}** {esc(p['descripcion'])}  \n"
                        f"@{esc(p['cliente'])} {insignias(p)}  \n{p['moneda']} {p['monto']:,.0f}, "
                        f"estado **{p['estado']}**, {core.hace(p['fecha_creacion'])}", unsafe_allow_html=True)
            acciones = {"solicitado": [("Confirmar pago", "confirmado"), ("Cancelar", "cancelado")],
                        "confirmado": [("Marcar entregado", "entregado")]}.get(p["estado"], [])
            for i, (texto, nuevo) in enumerate(acciones):
                if c2.button(texto, key=f"ped_{p['id']}_{nuevo}", type="primary" if i == 0 else "secondary"):
                    core.cambiar_estado_pedido(p["id"], usuario["id"], nuevo)
                    st.rerun()


# ----------------------------------------------------------------------------
# Membresías de verificación (pago P2P, activación manual por admin)
# ----------------------------------------------------------------------------
def _membresia(usuario: dict) -> None:
    tipo = core.tipo_membresia_para(usuario["rol"])
    nombre = NOMBRE_MEMBRESIA[tipo]
    tarifas = TARIFAS[tipo]
    beneficios = {
        "comprador_real": "Insignia de cliente verificado en tus encargos: los productores saben que "
                          "no eres un bot ni una cuenta falsa, y tus solicitudes aparecen primero.",
        "productor_real": "Insignia de autoría humana, posicionamiento prioritario en el catálogo "
                          "global y subida de beats en WAV calidad original.",
    }[tipo]
    st.markdown(f"### {nombre}")
    st.markdown(f'<div class="bs-texto">{beneficios}</div>', unsafe_allow_html=True)

    if usuario["verificado"] and usuario["tipo_verificacion"] == tipo:
        st.success(f"Membresía activa ({usuario['plan_verificacion']}) hasta "
                   f"{core.fecha_corta(usuario['verificado_hasta'])}. Puedes renovarla abajo.")

    ahorro = round(100 - tarifas["anual"] / (tarifas["mensual"] * 12) * 100)
    c1, c2 = st.columns(2)
    for col, plan, extra in ((c1, "mensual", "Se renueva cada 30 días"),
                             (c2, "anual", f"Ahorras {ahorro}% frente al plan mensual")):
        col.markdown(f'<div class="bs-plan">Plan {plan}<br><b class="monto">${tarifas[plan]:,} CLP</b>'
                     f'<br><small>{extra}</small></div>'.replace(",", "."), unsafe_allow_html=True)

    pendiente = db.uno("SELECT * FROM membresias WHERE usuario_id=? AND estado='pendiente_pago'",
                       (usuario["id"],))
    st.write("")
    if pendiente:
        st.info(f"Tu solicitud de plan {pendiente['plan']} (${pendiente['monto_clp']:,} CLP) está "
                "en revisión. La activamos apenas confirmemos la transferencia.".replace(",", "."))
        return

    with st.form("membresia"):
        plan = st.radio("Plan", ["mensual", "anual"], horizontal=True,
                        format_func=lambda p: f"{p.capitalize()}: ${tarifas[p]:,} CLP".replace(",", "."))
        st.markdown(f"**Datos para transferir:** {DATOS_TRANSFERENCIA}")
        ref = st.text_input("Número de operación o comentario de la transferencia")
        if st.form_submit_button("Ya transferí, solicitar activación", type="primary"):
            ok, msg = core.solicitar_membresia(usuario, plan, ref)
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()
    st.link_button("Enviar comprobante por WhatsApp",
                   f"https://wa.me/{ADMIN_WHATSAPP}?text=Comprobante%20{nombre.replace(' ', '%20')}"
                   f"%20usuario%20{usuario['username']}")


# ----------------------------------------------------------------------------
# Perfil
# ----------------------------------------------------------------------------
def _perfil(usuario: dict) -> None:
    with st.form("perfil"):
        nombre = st.text_input("Nombre público", usuario["nombre_publico"] or "")
        c1, c2 = st.columns(2)
        pais = c1.selectbox("País", PAISES,
                            index=PAISES.index(usuario["pais"]) if usuario["pais"] in PAISES else 0)
        wsp = c2.text_input("WhatsApp con código de país", usuario["whatsapp"] or "",
                            placeholder="56912345678")
        bio = st.text_area("Biografía", usuario["bio"] or "", max_chars=600)
        creditos = usuario["creditos"] or ""
        if usuario["rol"] == "productor":
            creditos = st.text_input("Créditos públicos", creditos,
                                     placeholder="Ha producido tracks para…")
        foto = st.file_uploader("Foto de perfil", type=["png", "jpg", "jpeg", "webp"])
        if st.form_submit_button("Guardar cambios", type="primary"):
            ruta_foto = usuario["foto_path"]
            if foto:
                ruta_foto = str(CARPETAS["fotos"] / f"{uuid.uuid4().hex}{Path(foto.name).suffix.lower()}")
                Path(ruta_foto).write_bytes(foto.getvalue())
            db.ejecutar("UPDATE usuarios SET nombre_publico=?, pais=?, whatsapp=?, bio=?, creditos=?, "
                        "foto_path=? WHERE id=?",
                        (nombre.strip(), pais, "".join(ch for ch in wsp if ch.isdigit()), bio.strip(),
                         creditos.strip(), ruta_foto, usuario["id"]))
            st.success("Cambios guardados.")
            st.rerun()
