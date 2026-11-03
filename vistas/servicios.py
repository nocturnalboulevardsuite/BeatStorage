"""
vistas/servicios.py — "Fix my Vocal" (edición vocal, mezcla, master) y beats por encargo.
"""
import streamlit as st

import core
import db
from components import encabezado, tarjeta_servicio
from config import TIPOS_SERVICIO_VOZ


def render(usuario: dict | None) -> None:
    encabezado(
        "Fix my Vocal",
        "Para voces que suenan ahí nomás: afinación, limpieza, mezcla y master.",
        semilla=21)

    tab_voz, tab_beat = st.tabs(["Voces y mezcla", "Beat a medida"])

    with tab_voz:
        opciones = {"todos": "Todos los servicios", **TIPOS_SERVICIO_VOZ}
        tipo = st.selectbox("Tipo de servicio", list(opciones), format_func=opciones.get,
                            label_visibility="collapsed")
        sql = core.SQL_SERVICIOS + " WHERE s.categoria='fix_my_vocal' AND s.activo=1 AND u.estado='activo'"
        params: tuple = ()
        if tipo != "todos":
            sql += " AND s.tipo = ?"
            params = (tipo,)
        _grilla(db.todos(sql + " ORDER BY u.verificado DESC, s.precio_usd", params), usuario, "voz")

    with tab_beat:
        servicios = db.todos(core.SQL_SERVICIOS + " WHERE s.categoria='beat_personalizado' "
                             "AND s.activo=1 AND u.estado='activo' "
                             "ORDER BY u.verificado DESC, s.precio_usd")
        _grilla(servicios, usuario, "enc")


def _grilla(servicios: list[dict], usuario: dict | None, prefijo: str) -> None:
    if not servicios:
        st.caption("Aún no hay servicios en esta categoría.")
        return
    cols = st.columns(2)
    for i, s in enumerate(servicios):
        with cols[i % 2]:
            tarjeta_servicio(s, usuario, prefijo=prefijo)
