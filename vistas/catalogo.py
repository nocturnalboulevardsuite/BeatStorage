"""
vistas/catalogo.py — Home y catálogo global de beats.

Orden del catálogo: primero productores con membresía "Productor Real"
(posicionamiento prioritario), luego por fecha de subida.
Solo aparecen beats de productores 'activos' (filtro anti-IA aprobado + 10 beats)
y nunca los trabajos exclusivos.
"""
import streamlit as st

import core
import db
from components import encabezado, tarjeta_beat
from config import CATALOGO_POR_PAGINA, GENEROS


def render(usuario: dict | None) -> None:
    encabezado("BeatStorage LATAM", "Beats y voces hechas por personas de Latinoamérica.")

    # ---- Filtros: búsqueda y género a la vista; el resto, dentro de "Filtros" ----
    paises = [p["pais"] for p in db.todos(
        "SELECT DISTINCT pais FROM usuarios WHERE rol='productor' AND estado='activo' "
        "AND pais IS NOT NULL ORDER BY pais")]
    c1, c2, c3 = st.columns([3, 1.6, 1], vertical_alignment="bottom")
    texto = c1.text_input("Buscar", placeholder="Buscar beat o productor",
                          label_visibility="collapsed", icon=":material/search:")
    genero = c2.selectbox("Género", ["Todos los géneros"] + GENEROS, label_visibility="collapsed")
    with c3.popover("Filtros", icon=":material/tune:", width="stretch"):
        pais = st.selectbox("País", ["Toda Latinoamérica"] + paises)
        precio = st.slider("Precio (US$)", 0, 200, (0, 200))
        orden = st.selectbox("Ordenar por", ["Recientes", "Más escuchados", "Menor precio"])
        solo_humanos = st.toggle("Solo Productor Real")

    # Si cambia cualquier filtro, la lista vuelve a la primera página
    firma = (texto, genero, pais, precio, orden, solo_humanos)
    if st.session_state.get("cat_firma") != firma:
        st.session_state["cat_firma"] = firma
        st.session_state["cat_limite"] = CATALOGO_POR_PAGINA

    sql = (core.SQL_BEATS + " WHERE b.es_exclusivo = 0 AND b.retirado = 0 AND u.estado = 'activo' "
           "AND b.precio_usd BETWEEN ? AND ?")
    params: list = [precio[0], precio[1]]
    if pais != "Toda Latinoamérica":
        sql += " AND u.pais = ?"
        params.append(pais)
    if texto.strip():
        sql += " AND (b.titulo LIKE ? OR u.username LIKE ? OR u.nombre_publico LIKE ?)"
        params += [f"%{texto.strip()}%"] * 3
    if genero != "Todos los géneros":
        sql += " AND b.genero = ?"
        params.append(genero)
    if solo_humanos:
        sql += " AND u.verificado = 1 AND u.tipo_verificacion = 'productor_real'"
    total = db.uno(f"SELECT COUNT(*) n FROM ({sql})", tuple(params))["n"]
    # Productor Real siempre primero (posicionamiento prioritario); luego el orden elegido
    sql += " ORDER BY u.verificado DESC, " + {
        "Recientes": "b.fecha_subida DESC, b.id DESC",
        "Más escuchados": "b.reproducciones DESC",
        "Menor precio": "b.precio_usd ASC",
    }[orden] + " LIMIT ?"
    limite = st.session_state["cat_limite"]
    beats = db.todos(sql, tuple(params + [limite]))

    if not beats:
        st.caption("Sin resultados. Prueba con otros filtros.")
        return

    st.caption(f"{total} beats")
    columnas = st.columns(3)
    for i, b in enumerate(beats):
        with columnas[i % 3]:
            tarjeta_beat(b, usuario, prefijo="cat")

    if total > len(beats):
        if st.button("Ver más", icon=":material/expand_more:", width="stretch"):
            st.session_state["cat_limite"] = limite + CATALOGO_POR_PAGINA
            st.rerun()
