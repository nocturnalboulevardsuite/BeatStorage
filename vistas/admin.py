"""
vistas/admin.py — Panel de administración.

  · Revisión de productores (pruebas DAW + declaración de IA).
  · Activación de membresías pagadas por transferencia ($3.000 / $5.000 CLP…).
  · Cuentas con aviso de suspensión por inactividad (confirmar o levantar).
  · Explorador de tablas como DataFrames de pandas.
"""
from datetime import timedelta
from pathlib import Path

import streamlit as st

import core
import db
from components import esc, reproductor
from config import MIN_BEATS_PRODUCTOR, MOTIVOS_REPORTE, NOMBRE_MEMBRESIA, TARIFAS


def render(usuario: dict) -> None:
    st.markdown("## Administración")
    m = db.uno("""SELECT
        (SELECT COUNT(*) FROM onboarding_productor WHERE estado_revision='pendiente') rev,
        (SELECT COUNT(*) FROM membresias WHERE estado='pendiente_pago')              mem,
        (SELECT COUNT(*) FROM usuarios WHERE estado='aviso_suspension')             avisos,
        (SELECT COUNT(DISTINCT beat_id) FROM reportes WHERE estado='pendiente')       denuncias,
        (SELECT COALESCE(SUM(monto_clp),0) FROM membresias WHERE estado IN ('activa','vencida')) ingresos""")
    c = st.columns(5)
    c[0].metric("Productores por revisar", m["rev"])
    c[1].metric("Pagos por confirmar", m["mem"])
    c[2].metric("Beats denunciados", m["denuncias"])
    c[3].metric("Avisos de suspensión", m["avisos"])
    c[4].metric("Ingresos (CLP)", f"${m['ingresos']:,}".replace(",", "."))

    t = st.tabs(["Productores", "Membresías", "Denuncias", "Inactividad", "Base de datos"])
    with t[0]:
        _revision_productores()
    with t[1]:
        _membresias()
    with t[2]:
        _denuncias()
    with t[3]:
        _inactividad()
    with t[4]:
        _base_datos()


def _revision_productores() -> None:
    pendientes = db.todos("""
        SELECT o.*, u.username, u.email, u.pais FROM onboarding_productor o
        JOIN usuarios u ON u.id = o.productor_id
        WHERE o.estado_revision='pendiente' ORDER BY o.fecha_envio""")
    if not pendientes:
        st.info("No hay productores esperando revisión.")
    for o in pendientes:
        with st.container(border=True):
            n = core.beats_publicos(o["productor_id"])
            st.markdown(f"**@{esc(o['username'])}** ({esc(o['pais'] or '')}, {esc(o['email'])})  \n"
                        f"DAW: **{esc(o['daw_principal'])}**, beats subidos: **{n}/{MIN_BEATS_PRODUCTOR}**, "
                        f"enviado {core.hace(o['fecha_envio'])}")
            if o["usa_ia"]:
                st.warning(f"Declara uso de IA en: {o['areas_ia']}. {o['detalle_ia']}")
            else:
                st.caption("Declara no usar IA.")
            pruebas = db.todos("SELECT archivo_path FROM pruebas_autoria WHERE onboarding_id=?", (o["id"],))
            cols = st.columns(max(1, min(4, len(pruebas))))
            for i, p in enumerate(pruebas):
                if Path(p["archivo_path"]).exists():
                    cols[i % len(cols)].image(p["archivo_path"], width="stretch")
            nota = st.text_input("Nota para el productor", key=f"nota_ob_{o['id']}")
            a, r, _ = st.columns([1, 1, 3])
            if a.button("Aprobar", key=f"apr_{o['id']}", type="primary"):
                _resolver(o, "aprobado", nota)
            if r.button("Rechazar", key=f"rech_{o['id']}"):
                _resolver(o, "rechazado", nota)


def _resolver(o: dict, estado: str, nota: str) -> None:
    db.ejecutar("UPDATE onboarding_productor SET estado_revision=?, nota_admin=?, fecha_revision=? "
                "WHERE id=?", (estado, nota.strip(), db.ahora(), o["id"]))
    if estado == "aprobado":
        core.notificar(o["productor_id"], "Tus pruebas de autoría fueron aprobadas. "
                       f"Al llegar a {MIN_BEATS_PRODUCTOR} beats tu perfil será público.", "exito")
    else:
        core.notificar(o["productor_id"], f"Tu verificación fue rechazada: {nota or 'sin nota'}.", "alerta")
    core.actualizar_estado_productor(o["productor_id"])
    st.rerun()


def _membresias() -> None:
    st.caption("Tarifas: " + ", ".join(
        f"{NOMBRE_MEMBRESIA[t]} ${v['mensual']:,}/mes o ${v['anual']:,}/año".replace(",", ".")
        for t, v in TARIFAS.items()))
    pendientes = db.todos("""SELECT m.*, u.username, u.rol FROM membresias m
                             JOIN usuarios u ON u.id=m.usuario_id
                             WHERE m.estado='pendiente_pago' ORDER BY m.fecha_solicitud""")
    if not pendientes:
        st.info("No hay pagos por confirmar.")
    for mb in pendientes:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**@{esc(mb['username'])}** pide **{NOMBRE_MEMBRESIA[mb['tipo']]}** "
                        f"plan {mb['plan']}: **${mb['monto_clp']:,} CLP**".replace(",", ".") +
                        f"  \nReferencia: {esc(mb['referencia_pago'] or 'sin referencia')}, "
                        f"{core.hace(mb['fecha_solicitud'])}")
            if c2.button("Activar", key=f"act_{mb['id']}", type="primary"):
                core.activar_membresia(mb["id"])
                st.rerun()
            if c3.button("Rechazar", key=f"rmem_{mb['id']}"):
                db.ejecutar("UPDATE membresias SET estado='rechazada' WHERE id=?", (mb["id"],))
                core.notificar(mb["usuario_id"], "No pudimos confirmar tu transferencia. Escríbenos "
                                                 "con el comprobante.", "alerta")
                st.rerun()
    st.markdown("#### Historial")
    st.dataframe(db.df("SELECT m.id, u.username, m.tipo, m.plan, m.monto_clp, m.estado, m.fecha_inicio, "
                       "m.fecha_fin FROM membresias m JOIN usuarios u ON u.id=m.usuario_id "
                       "ORDER BY m.id DESC"), hide_index=True, width="stretch")


def _denuncias() -> None:
    """Denuncias agrupadas por beat: escuchar, ver la declaración de IA del productor y decidir."""
    beats = db.todos("""
        SELECT b.id AS beat_id, b.titulo, b.archivo_preview, b.uso_ia, u.username, u.id AS productor_id,
               COUNT(r.id) AS n, GROUP_CONCAT(r.motivo) AS motivos, MIN(r.id) AS reporte_id
        FROM reportes r JOIN beats b ON b.id = r.beat_id JOIN usuarios u ON u.id = b.productor_id
        WHERE r.estado = 'pendiente' GROUP BY b.id ORDER BY n DESC, MIN(r.fecha)""")
    if not beats:
        st.info("No hay denuncias pendientes.")
        return
    for d in beats:
        with st.container(border=True):
            motivos = sorted(set(d["motivos"].split(",")))
            st.markdown(f"**«{esc(d['titulo'])}»** de @{esc(d['username'])}: {d['n']} denuncia(s)  \n"
                        + ", ".join(MOTIVOS_REPORTE[mo] for mo in motivos))
            reproductor(d["archivo_preview"], d["titulo"])
            ob = core.onboarding_de(d["productor_id"])
            declaracion = ("declara uso de IA en " + ob["areas_ia"]) if ob and ob["usa_ia"] else "declara no usar IA"
            st.caption(f"El productor {declaracion}. Beat marcado con IA: {'sí' if d['uso_ia'] else 'no'}.")
            for r in db.todos("SELECT detalle FROM reportes WHERE beat_id=? AND estado='pendiente' "
                              "AND detalle != ''", (d["beat_id"],)):
                st.markdown(f"> {esc(r['detalle'])}")
            nota = st.text_input("Nota para el productor (opcional)", key=f"nota_rep_{d['beat_id']}")
            c1, c2, c3, _ = st.columns([1, 1.2, 1, 1.5])
            if c1.button("Desestimar", key=f"des_{d['beat_id']}"):
                core.resolver_reporte(d["reporte_id"], "desestimar", nota)
                st.rerun()
            if c2.button("Marcar con IA", key=f"mia_{d['beat_id']}", disabled=bool(d["uso_ia"])):
                core.resolver_reporte(d["reporte_id"], "marcar_ia", nota)
                st.rerun()
            if c3.button("Retirar beat", key=f"retb_{d['beat_id']}", type="primary"):
                core.resolver_reporte(d["reporte_id"], "retirar", nota)
                st.rerun()


def _inactividad() -> None:
    st.caption("Clientes que no respondieron propuestas en 7 días. La sanción final requiere "
               "confirmación humana para evitar suspensiones por error.")
    avisos = db.todos("SELECT * FROM usuarios WHERE estado='aviso_suspension'")
    if not avisos:
        st.info("No hay cuentas con aviso de suspensión.")
    for u in avisos:
        with st.container(border=True):
            encargos = db.todos("SELECT titulo, fecha_aviso FROM encargos_licitacion "
                                "WHERE cliente_id=? AND estado='vencido_inactividad'", (u["id"],))
            st.markdown(f"**@{esc(u['username'])}** ({esc(u['email'])})  \nEncargos vencidos: " +
                        ", ".join(f"«{esc(e['titulo'])}»" for e in encargos))
            c1, c2, _ = st.columns([1.4, 1, 2])
            if c1.button("Confirmar suspensión", key=f"susp_{u['id']}", type="primary"):
                db.ejecutar("UPDATE usuarios SET estado='suspendido' WHERE id=?", (u["id"],))
                st.rerun()
            if c2.button("Levantar aviso", key=f"lev_{u['id']}"):
                db.ejecutar("UPDATE usuarios SET estado='activo' WHERE id=?", (u["id"],))
                core.notificar(u["id"], "Levantamos el aviso de suspensión. Recuerda responder "
                                        "las propuestas a tiempo.", "exito")
                st.rerun()

    st.markdown("#### Simulador de plazo (demo)")
    abiertos = db.todos("SELECT e.id, e.titulo, u.username FROM encargos_licitacion e "
                        "JOIN usuarios u ON u.id=e.cliente_id WHERE e.estado='abierto' "
                        "AND e.fecha_primera_propuesta IS NOT NULL")
    if abiertos:
        sel = st.selectbox("Encargo con propuestas", abiertos,
                           format_func=lambda e: f"#{e['id']} {e['titulo']} (@{e['username']})")
        dias = st.slider("Retroceder el reloj (días)", 1, 10, 8)
        if st.button("Simular paso del tiempo y revisar"):
            nueva = db.a_fecha(db.ahora()) - timedelta(days=dias)
            db.ejecutar("UPDATE encargos_licitacion SET fecha_primera_propuesta=? WHERE id=?",
                        (nueva.strftime(db.FORMATO_FECHA), sel["id"]))
            core.revisar_inactividad()
            st.rerun()
    else:
        st.caption("No hay encargos abiertos con propuestas.")


def _base_datos() -> None:
    tabla = st.selectbox("Tabla", db.TABLAS)
    columnas = "*"
    if tabla == "usuarios":  # nunca exponer hashes
        columnas = ("id, username, email, rol, nombre_publico, pais, estado, verificado, "
                    "tipo_verificacion, plan_verificacion, moneda_verificacion, verificado_hasta, fecha_registro")
    datos = db.df(f"SELECT {columnas} FROM {tabla} ORDER BY 1 DESC")
    st.dataframe(datos, hide_index=True, width="stretch")
    st.download_button("Exportar CSV", datos.to_csv(index=False).encode(), f"{tabla}.csv")
