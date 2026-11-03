"""
vistas/licitaciones.py — Tablón de encargos / licitaciones públicas.

  · Clientes publican encargos (descripción técnica, presupuesto CLP/USD, referencias).
  · Productores activos postulan con una propuesta.
  · Regla de 1 semana: desde la primera propuesta el cliente tiene 7 días para
    elegir o cerrar. Si no, core.revisar_inactividad() emite el aviso formal.
"""
import streamlit as st

import core
import db
from components import (botones_contacto, cuenta_regresiva, encabezado, esc,
                        insignias, ir_a)
from config import DIAS_INACTIVIDAD, GENEROS

ETIQUETA_ESTADO = {
    "abierto": ("Abierto", "humano"),
    "asignado": ("Productor elegido", "comprador"),
    "cerrado": ("Cerrado por el cliente", "neutro"),
    "vencido_inactividad": ("Vencido por inactividad", "peligro"),
}


def _monto(moneda: str, valor: float) -> str:
    """Formato regional: CLP 60.000 / USD 50."""
    return f"{moneda} {valor:,.0f}".replace(",", ".")


def _presupuesto(e: dict) -> str:
    return _monto(e["presupuesto_moneda"], e["presupuesto_monto"])


def render(usuario: dict | None) -> None:
    encabezado("Encargos",
               "Cuenta lo que necesitas y recibe propuestas de productores verificados.",
               semilla=33)

    rol = usuario["rol"] if usuario else None
    nombres = ["Encargos abiertos"]
    if rol == "cliente":
        nombres += ["Publicar encargo", "Mis encargos"]
    if rol == "productor":
        nombres += ["Mis propuestas"]
    tabs = dict(zip(nombres, st.tabs(nombres)))

    with tabs["Encargos abiertos"]:
        _tablon(usuario)
    if rol == "cliente":
        with tabs["Publicar encargo"]:
            _publicar(usuario)
        with tabs["Mis encargos"]:
            _mis_encargos(usuario)
    if rol == "productor":
        with tabs["Mis propuestas"]:
            _mis_propuestas(usuario)


# ----------------------------------------------------------------------------
def _tablon(usuario: dict | None) -> None:
    encargos = db.todos("""
        SELECT e.*, u.username, u.verificado, u.tipo_verificacion,
               (SELECT COUNT(*) FROM propuestas p WHERE p.encargo_id = e.id) AS n_propuestas
        FROM encargos_licitacion e JOIN usuarios u ON u.id = e.cliente_id
        WHERE e.estado = 'abierto' ORDER BY u.verificado DESC, e.fecha_publicacion DESC""")
    if not encargos:
        st.info("No hay encargos abiertos ahora mismo.")
        return
    puede, motivo = core.puede_postular(usuario) if usuario else (False, "")

    for e in encargos:
        with st.container(border=True):
            chips = [c for c in (e["genero"], e["duracion_max"] and f"Duración: {e['duracion_max']}",
                                 f"{e['n_propuestas']} propuestas", core.hace(e["fecha_publicacion"])) if c]
            st.markdown(
                f'<div class="bs-titulo">{esc(e["titulo"])}</div>'
                f'<div class="bs-autor">Publicado por @{esc(e["username"])}</div>'
                f'<div>{insignias(e)}</div>'
                f'<div class="bs-texto">{esc(e["descripcion"])}</div>'
                + (f'<div class="bs-texto"><b>Referencias:</b> {esc(e["referencias"])}</div>'
                   if e["referencias"] else "")
                + f'<div class="bs-chips">{"".join(f"<span class=bs-chip>{esc(c)}</span>" for c in chips)}</div>'
                f'<div class="bs-precio">{_presupuesto(e)} <small>presupuesto</small></div>',
                unsafe_allow_html=True)

            if not usuario or usuario["rol"] != "productor":
                continue
            ya = db.uno("SELECT estado FROM propuestas WHERE encargo_id=? AND productor_id=?",
                        (e["id"], usuario["id"]))
            if ya:
                st.caption("Ya enviaste una propuesta a este encargo.")
            elif not puede:
                st.caption(motivo)
            else:
                with st.expander("Postular a este encargo"):
                    _form_propuesta(e, usuario)


def _form_propuesta(e: dict, productor: dict) -> None:
    with st.form(f"prop_{e['id']}", clear_on_submit=True):
        mensaje = st.text_area("Tu propuesta", max_chars=800,
                               placeholder="Cómo lo harías, referencias de tu catálogo, revisiones incluidas…")
        c1, c2, c3 = st.columns(3)
        moneda = c1.selectbox("Moneda", ["CLP", "USD"],
                              index=0 if e["presupuesto_moneda"] == "CLP" else 1)
        precio = c2.number_input("Precio", min_value=1.0, value=float(e["presupuesto_monto"]), step=1.0)
        plazo = c3.number_input("Entrega (días)", min_value=1, max_value=60, value=3)
        if st.form_submit_button("Enviar propuesta", type="primary"):
            if len(mensaje.strip()) < 20:
                st.error("Cuéntale al cliente un poco más (mínimo 20 caracteres).")
                return
            db.ejecutar("INSERT INTO propuestas (encargo_id, productor_id, mensaje, precio, moneda, "
                        "plazo_dias, fecha) VALUES (?,?,?,?,?,?,?)",
                        (e["id"], productor["id"], mensaje.strip(), precio, moneda, int(plazo), db.ahora()))
            # La primera propuesta inicia el reloj de 7 días
            if not e["fecha_primera_propuesta"]:
                db.ejecutar("UPDATE encargos_licitacion SET fecha_primera_propuesta=? WHERE id=?",
                            (db.ahora(), e["id"]))
                core.notificar(e["cliente_id"],
                               f"Recibiste la primera propuesta para «{e['titulo']}». Tienes "
                               f"{DIAS_INACTIVIDAD} días para elegir un productor o cerrar el encargo.",
                               "alerta")
            else:
                core.notificar(e["cliente_id"], f"Nueva propuesta para «{e['titulo']}».")
            st.success("Propuesta enviada.")
            st.rerun()


# ----------------------------------------------------------------------------
def _publicar(usuario: dict) -> None:
    if usuario["estado"] == "aviso_suspension":
        st.error("Tu cuenta tiene un aviso formal de suspensión por no responder propuestas "
                 "a tiempo. No puedes publicar encargos mientras está en revisión.")
        return
    with st.form("nuevo_encargo", clear_on_submit=False):
        titulo = st.text_input("Título", placeholder="Beat synthwave estilo 80s para single")
        descripcion = st.text_area("Descripción técnica", max_chars=1500,
                                   placeholder="Busco beat synthwave estilo 80s de máximo 2 minutos, "
                                               "con bajo arpegiado y batería tipo LinnDrum…")
        c1, c2 = st.columns(2)
        genero = c1.selectbox("Género", GENEROS, index=GENEROS.index("Synthwave"))
        duracion = c2.text_input("Duración máxima", placeholder="2 minutos")
        referencias = st.text_input("Referencias", placeholder="Artistas o enlaces de referencia")
        c3, c4 = st.columns([2, 1])
        monto = c3.number_input("Presupuesto", min_value=1.0, value=60000.0, step=1000.0)
        moneda = c4.selectbox("Moneda", ["CLP", "USD"])
        acepto = st.checkbox(f"Responderé las propuestas en {DIAS_INACTIVIDAD} días",
                             help="Si recibes propuestas y no eliges ni cierras el encargo en "
                                  f"{DIAS_INACTIVIDAD} días, tu cuenta recibe un aviso formal de "
                                  "suspensión permanente.")
        if st.form_submit_button("Publicar encargo", type="primary"):
            if len(titulo.strip()) < 5 or len(descripcion.strip()) < 20:
                st.error("Agrega un título (mín. 5 caracteres) y una descripción (mín. 20).")
            elif not acepto:
                st.error("Debes aceptar la regla de respuesta de 7 días.")
            else:
                db.ejecutar("INSERT INTO encargos_licitacion (cliente_id, titulo, descripcion, genero, "
                            "referencias, duracion_max, presupuesto_monto, presupuesto_moneda, "
                            "fecha_publicacion) VALUES (?,?,?,?,?,?,?,?,?)",
                            (usuario["id"], titulo.strip(), descripcion.strip(), genero,
                             referencias.strip(), duracion.strip(), monto, moneda, db.ahora()))
                st.success("Encargo publicado. Te avisaremos cuando lleguen propuestas.")


def _mis_encargos(usuario: dict) -> None:
    encargos = db.todos("SELECT * FROM encargos_licitacion WHERE cliente_id=? "
                        "ORDER BY fecha_publicacion DESC", (usuario["id"],))
    if not encargos:
        st.info("Aún no publicas encargos.")
        return
    for e in encargos:
        etiqueta, clase = ETIQUETA_ESTADO[e["estado"]]
        with st.container(border=True):
            st.markdown(f'<span class="bs-badge {clase}">{etiqueta}</span>'
                        f'<div class="bs-titulo">{esc(e["titulo"])}</div>'
                        f'<div class="bs-autor">{_presupuesto(e)}, publicado {core.hace(e["fecha_publicacion"])}</div>',
                        unsafe_allow_html=True)
            if e["estado"] == "vencido_inactividad":
                st.error("Este encargo venció sin respuesta. Tu cuenta recibió un aviso formal y "
                         "está en revisión para suspensión permanente.")
            propuestas = db.todos("""
                SELECT p.*, u.username, u.whatsapp, u.email, u.verificado, u.tipo_verificacion
                FROM propuestas p JOIN usuarios u ON u.id = p.productor_id
                WHERE p.encargo_id=? ORDER BY u.verificado DESC, p.fecha""", (e["id"],))

            if e["estado"] == "abierto":
                cuenta_regresiva(e["fecha_primera_propuesta"])
            for p in propuestas:
                _propuesta_cliente(e, p, usuario)
            if e["estado"] == "abierto" and propuestas:
                if st.button("Cerrar encargo sin elegir", key=f"cerrar_{e['id']}",
                             help="Cuenta como respuesta: no se aplica la regla de inactividad."):
                    db.transaccion([
                        ("UPDATE encargos_licitacion SET estado='cerrado' WHERE id=?", (e["id"],)),
                        ("UPDATE propuestas SET estado='rechazada' WHERE encargo_id=?", (e["id"],)),
                    ])
                    for p in propuestas:
                        core.notificar(p["productor_id"], f"«{e['titulo']}» fue cerrado sin seleccionar productor.")
                    st.rerun()


def _propuesta_cliente(e: dict, p: dict, usuario: dict) -> None:
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        c1.markdown(f'<b>@{esc(p["username"])}</b> {insignias(p)}'
                    f'<div class="bs-texto">{esc(p["mensaje"])}</div>'
                    f'<div class="bs-autor">{_monto(p["moneda"], p["precio"])}, entrega en '
                    f'{p["plazo_dias"]} días</div>', unsafe_allow_html=True)
        c2.button("Ver perfil", key=f"vp_{p['id']}", on_click=ir_a,
                  args=("productores",), kwargs={"perfil_id": p["productor_id"]})
        if e["estado"] == "abierto":
            if c2.button("Elegir", key=f"sel_{p['id']}", type="primary"):
                pedido = core.crear_pedido(usuario["id"], p["productor_id"], "encargo", e["id"],
                                           f"Encargo «{e['titulo']}»", p["precio"], p["moneda"])
                db.transaccion([
                    ("UPDATE encargos_licitacion SET estado='asignado', productor_seleccionado_id=? "
                     "WHERE id=?", (p["productor_id"], e["id"])),
                    ("UPDATE propuestas SET estado = CASE WHEN id=? THEN 'aceptada' ELSE 'rechazada' END "
                     "WHERE encargo_id=?", (p["id"], e["id"])),
                ])
                core.notificar(p["productor_id"], f"¡Te eligieron para «{e['titulo']}»! Pedido #{pedido}.",
                               "exito")
                st.rerun()
        elif p["estado"] == "aceptada":
            st.success("Elegiste esta propuesta. Coordina el pago directo con el productor:")
            msg = (f"Hola @{p['username']}, te elegí en BeatStorage LATAM para «{e['titulo']}» "
                   f"({_monto(p['moneda'], p['precio'])}). ¿Cómo coordinamos el pago?")
            botones_contacto({**p, "id": p["productor_id"]}, msg, f"enc_{p['id']}")


def _mis_propuestas(usuario: dict) -> None:
    tabla = db.df("""
        SELECT e.titulo AS Encargo, p.moneda || ' ' || CAST(p.precio AS INT) AS Precio,
               p.plazo_dias AS 'Días', p.estado AS Estado, e.estado AS 'Estado encargo',
               p.fecha AS Fecha
        FROM propuestas p JOIN encargos_licitacion e ON e.id = p.encargo_id
        WHERE p.productor_id=? ORDER BY p.fecha DESC""", (usuario["id"],))
    if tabla.empty:
        st.info("Aún no envías propuestas.")
    else:
        st.dataframe(tabla, hide_index=True, width="stretch")
