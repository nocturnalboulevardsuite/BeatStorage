"""
vistas/onboarding.py — Verificación de productor (filtro anti-IA).

Requisitos para que un productor sea público:
  1. Pruebas de autoría: capturas del proyecto abierto en su DAW (mín. 2).
  2. Declaración obligatoria de uso de IA (sí/no, en qué áreas).
  3. Revisión humana del equipo (admin).
  4. Al menos 10 beats completos subidos.
"""
import uuid
from pathlib import Path

import streamlit as st

import core
import db
from components import encabezado, ir_a, lista_iconos
from config import AREAS_IA, CARPETAS, DAWS, MIN_BEATS_PRODUCTOR


def render(usuario: dict) -> None:
    encabezado("Verificación de productor",
               "Confirmamos que detrás de cada catálogo hay una persona.", semilla=55)

    ob = core.onboarding_de(usuario["id"])
    n_beats = core.beats_publicos(usuario["id"])

    # ---- Estado de los requisitos ------------------------------------------
    estado_ob = ob["estado_revision"] if ob else None
    pasos = [
        ("Pruebas de autoría y declaración de IA enviadas", ob is not None),
        ("Revisión del equipo aprobada", estado_ob == "aprobado"),
        (f"{MIN_BEATS_PRODUCTOR} beats completos subidos ({n_beats}/{MIN_BEATS_PRODUCTOR})",
         n_beats >= MIN_BEATS_PRODUCTOR),
    ]
    lista_iconos([("circulo_ok" if ok else "circulo", texto, "") for texto, ok in pasos])
    if n_beats < MIN_BEATS_PRODUCTOR:
        st.button("Subir beats", icon=":material/upload:", on_click=ir_a, args=("panel",))

    if usuario["estado"] == "activo":
        st.success("Tu perfil es público y puedes postular al tablón de encargos.")
    if estado_ob == "pendiente":
        st.info("Tus pruebas están en revisión. Mientras tanto puedes seguir subiendo beats.")
        return
    if estado_ob == "aprobado":
        return
    if estado_ob == "rechazado":
        st.error(f"Tu verificación fue rechazada. Nota del equipo: {ob['nota_admin'] or 'sin nota'}. "
                 "Puedes enviar nuevas pruebas.")

    # ---- Formulario -------------------------------------------------------
    st.subheader("Envía tus pruebas de autoría")
    with st.form("onboarding"):
        daw = st.selectbox("DAW principal", DAWS)
        capturas = st.file_uploader(
            "Capturas de pantalla de tus proyectos (mínimo 2)",
            type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
            help="Que se vea el proyecto abierto: playlist, mixer o piano roll, con tu usuario si es posible.")
        st.markdown("**Declaración de uso de IA**")
        usa_ia = st.radio("¿Usas herramientas de IA en la creación sonora?",
                          ["No, todo mi trabajo es hecho por mí", "Sí, en algunas etapas"],
                          index=0)
        areas = st.multiselect("Si usas IA, ¿en qué etapas?", AREAS_IA)
        detalle = st.text_area("Detalle (opcional)", max_chars=500,
                               placeholder="Ej.: uso separación de stems para samplear vinilos.")
        juro = st.checkbox("Declaro que la información es verdadera y que los beats que publique "
                           "son de mi autoría. Entiendo que una declaración falsa implica la "
                           "baja de mi cuenta.")
        enviado = st.form_submit_button("Enviar a revisión", type="primary")

    if not enviado:
        return
    ia = usa_ia.startswith("Sí")
    if not capturas or len(capturas) < 2:
        st.error("Sube al menos 2 capturas de tu DAW.")
    elif ia and not areas:
        st.error("Indica en qué etapas usas IA.")
    elif not juro:
        st.error("Debes aceptar la declaración de autoría.")
    else:
        if ob:  # reenvío tras rechazo: se reemplaza la solicitud anterior
            db.ejecutar("DELETE FROM onboarding_productor WHERE id=?", (ob["id"],))
        ob_id = db.ejecutar(
            "INSERT INTO onboarding_productor (productor_id, daw_principal, usa_ia, areas_ia, "
            "detalle_ia, declaracion_aceptada, fecha_envio) VALUES (?,?,?,?,?,1,?)",
            (usuario["id"], daw, int(ia), ", ".join(areas), detalle.strip(), db.ahora()))
        for archivo in capturas:
            destino = CARPETAS["pruebas"] / f"{uuid.uuid4().hex}{Path(archivo.name).suffix.lower()}"
            destino.write_bytes(archivo.getvalue())
            db.ejecutar("INSERT INTO pruebas_autoria (onboarding_id, archivo_path) VALUES (?,?)",
                        (ob_id, str(destino)))
        st.success("¡Listo! Revisaremos tus pruebas en un plazo de 48 horas.")
        st.rerun()
