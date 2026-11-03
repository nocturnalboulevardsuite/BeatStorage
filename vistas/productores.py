"""
vistas/productores.py — Directorio y perfil público de productores.

El perfil muestra: biografía, créditos, estadísticas públicas, declaración de IA,
catálogo, servicios, trabajos privados exclusivos y reseñas verificadas.
"""
import streamlit as st

import core
import db
from components import (avatar, esc, estrellas, insignias, tarjeta_beat,
                        tarjeta_exclusivo, tarjeta_servicio)


def render(usuario: dict | None) -> None:
    productores = db.todos(
        "SELECT id, username, nombre_publico, pais, verificado, tipo_verificacion "
        "FROM usuarios WHERE rol='productor' AND estado='activo' "
        "ORDER BY verificado DESC, username")
    if not productores:
        st.info("Aún no hay productores públicos.")
        return
    ids = [p["id"] for p in productores]
    nombres = {p["id"]: f"@{p['username']}  ({p['nombre_publico']}, {p['pais'] or 'LATAM'})"
               for p in productores}
    if st.session_state.get("perfil_id") not in ids:
        st.session_state["perfil_id"] = ids[0]
    pid = st.selectbox("Productor", ids, format_func=nombres.get, key="perfil_id")
    perfil_publico(pid, usuario)


def perfil_publico(pid: int, usuario: dict | None) -> None:
    p = db.uno("SELECT * FROM usuarios WHERE id=? AND rol='productor'", (pid,))
    if not p:
        st.warning("Perfil no encontrado.")
        return
    s = core.stats_productor(pid)
    ob = core.onboarding_de(pid)

    # ---- Cabecera del perfil ---------------------------------------------
    c_foto, c_info = st.columns([1, 5])
    with c_foto:
        avatar(p)
    with c_info:
        st.markdown(f"## {esc(p['nombre_publico'] or p['username'])}")
        st.markdown(f'<div class="bs-autor">@{esc(p["username"])} desde {esc(p["pais"] or "LATAM")}</div>'
                    f'{insignias(p, con_ia=bool(ob and ob["usa_ia"]))}', unsafe_allow_html=True)
        if p["bio"]:
            st.markdown(f'<div class="bs-texto">{esc(p["bio"])}</div>', unsafe_allow_html=True)
        if p["creditos"]:
            st.markdown(f'<div class="bs-texto"><b>Créditos:</b> {esc(p["creditos"])}</div>',
                        unsafe_allow_html=True)

    m = st.columns(4)
    m[0].metric("Beats creados", s["total_beats"])
    m[1].metric("Ventas confirmadas", s["ventas"])
    m[2].metric("Calificación", f"{s['rating']:.1f} ★" if s["rating"] else "Sin reseñas",
                help=f"{s['n_resenas']} reseñas verificadas: {estrellas(s['rating'])}")
    m[3].metric("Reproducciones", s["plays"])

    # Transparencia sobre IA (declaración obligatoria del onboarding)
    if ob:
        if ob["usa_ia"]:
            st.warning(f"Declaración de IA: usa herramientas de IA en {ob['areas_ia'] or 'algunas etapas'}. "
                       f"{ob['detalle_ia'] or ''}")
        else:
            st.caption(f"Declara no usar IA generativa. DAW principal: {ob['daw_principal']}. "
                       "Autoría revisada por el equipo de BeatStorage.")

    t_cat, t_srv, t_excl, t_res = st.tabs(
        [f"Catálogo ({s['beats_publicos']})", "Servicios",
         f"Trabajos exclusivos ({s['exclusivos']})", f"Reseñas ({s['n_resenas']})"])

    with t_cat:
        beats = db.todos(core.SQL_BEATS + " WHERE b.productor_id=? AND b.es_exclusivo=0 AND b.retirado=0 "
                         "ORDER BY b.fecha_subida DESC, b.id DESC", (pid,))
        cols = st.columns(3)
        for i, b in enumerate(beats):
            with cols[i % 3]:
                tarjeta_beat(b, usuario, prefijo=f"perf{pid}")

    with t_srv:
        servicios = db.todos(core.SQL_SERVICIOS + " WHERE s.productor_id=? AND s.activo=1", (pid,))
        if not servicios:
            st.caption("Este productor aún no publica servicios.")
        cols = st.columns(2)
        for i, sv in enumerate(servicios):
            with cols[i % 2]:
                tarjeta_servicio(sv, usuario, prefijo=f"perf{pid}")

    with t_excl:
        st.caption("Portafolio de trabajos hechos a medida. Se pueden escuchar, pero no se "
                   "venden ni se descargan: pertenecen a su cliente.")
        exclusivos = db.todos(core.SQL_BEATS + " WHERE b.productor_id=? AND b.es_exclusivo=1 AND b.retirado=0 "
                              "ORDER BY b.fecha_subida DESC", (pid,))
        cols = st.columns(2)
        for i, b in enumerate(exclusivos):
            with cols[i % 2]:
                tarjeta_exclusivo(b, usuario)

    with t_res:
        resenas = db.todos("""
            SELECT r.*, u.username, u.verificado, u.tipo_verificacion, p.descripcion
            FROM resenas r JOIN usuarios u ON u.id = r.cliente_id
            JOIN pedidos p ON p.id = r.pedido_id
            WHERE r.productor_id=? ORDER BY r.fecha DESC""", (pid,))
        if not resenas:
            st.caption("Sin reseñas todavía. Solo clientes con compras confirmadas pueden opinar.")
        for r in resenas:
            with st.container(border=True):
                st.markdown(
                    f'<b style="color:var(--bs-acento-t)">{"★" * r["calificacion"]}{"☆" * (5 - r["calificacion"])}</b> '
                    f'<span class="bs-badge neutro">Compra verificada</span>{insignias(r)}'
                    f'<div class="bs-texto">{esc(r["comentario"] or "")}</div>'
                    f'<div class="bs-autor">@{esc(r["username"])}, {esc(r["descripcion"])}, '
                    f'{core.hace(r["fecha"])}</div>', unsafe_allow_html=True)
