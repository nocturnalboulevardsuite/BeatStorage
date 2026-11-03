"""
core.py — Reglas de negocio de BeatStorage LATAM (independientes de la interfaz).
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import db
from config import (DIAS_INACTIVIDAD, DIAS_POR_PLAN, DIAS_RECORDATORIO,
                    MIN_BEATS_PRODUCTOR, NOMBRE_MEMBRESIA, TARIFAS)


# ----------------------------------------------------------------------------
# Utilidades de tiempo
# ----------------------------------------------------------------------------
def _ahora_dt() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def dias_desde(fecha: str | None) -> float:
    if not fecha:
        return 0.0
    return (_ahora_dt() - db.a_fecha(fecha)).total_seconds() / 86_400


def hace(fecha: str | None) -> str:
    d = dias_desde(fecha)
    if d < 1 / 24:
        return "hace un momento"
    if d < 1:
        return f"hace {int(d * 24)} h"
    if d < 2:
        return "ayer"
    return f"hace {int(d)} días"


def fecha_corta(fecha: str | None) -> str:
    return db.a_fecha(fecha).strftime("%d-%m-%Y") if fecha else "—"


# ----------------------------------------------------------------------------
# Notificaciones
# ----------------------------------------------------------------------------
def notificar(usuario_id: int, mensaje: str, tipo: str = "info") -> None:
    db.ejecutar("INSERT INTO notificaciones (usuario_id, mensaje, tipo, fecha) VALUES (?,?,?,?)",
                (usuario_id, mensaje, tipo, db.ahora()))


def no_leidas(usuario_id: int) -> int:
    return db.uno("SELECT COUNT(*) n FROM notificaciones WHERE usuario_id=? AND leida=0",
                  (usuario_id,))["n"]


# ----------------------------------------------------------------------------
# Tareas periódicas (se ejecutan en cada carga; son consultas baratas).
# En producción irían en un cron / scheduler.
# ----------------------------------------------------------------------------
def revisar_membresias() -> None:
    """Desactiva verificaciones vencidas."""
    vencidos = db.todos(
        "SELECT id, tipo_verificacion FROM usuarios "
        "WHERE verificado = 1 AND verificado_hasta IS NOT NULL AND verificado_hasta < ?",
        (db.ahora(),))
    for u in vencidos:
        db.ejecutar("UPDATE usuarios SET verificado = 0 WHERE id = ?", (u["id"],))
        notificar(u["id"], f"Tu membresía {NOMBRE_MEMBRESIA.get(u['tipo_verificacion'], '')} "
                           "venció. Renuévala para mantener tu insignia.", "alerta")
    db.ejecutar("UPDATE membresias SET estado='vencida' WHERE estado='activa' AND fecha_fin < ?",
                (db.ahora(),))


def revisar_inactividad() -> None:
    """
    Regla de 1 semana del tablón:
      · El reloj parte con la PRIMERA propuesta recibida.
      · Día 5 → recordatorio preventivo.
      · Día 7 sin seleccionar productor ni cerrar el encargo → el encargo vence y
        la cuenta recibe un AVISO FORMAL de suspensión permanente. Un admin
        confirma o levanta la suspensión (revisión humana antes de la sanción final).
    """
    pendientes = db.todos(
        "SELECT * FROM encargos_licitacion WHERE estado = 'abierto' "
        "AND fecha_primera_propuesta IS NOT NULL AND productor_seleccionado_id IS NULL")
    for e in pendientes:
        dias = dias_desde(e["fecha_primera_propuesta"])
        if dias >= DIAS_INACTIVIDAD:
            db.transaccion([
                ("UPDATE encargos_licitacion SET estado='vencido_inactividad', fecha_aviso=? "
                 "WHERE id=?", (db.ahora(), e["id"])),
                ("UPDATE usuarios SET estado='aviso_suspension' "
                 "WHERE id=? AND estado='activo'", (e["cliente_id"],)),
                ("UPDATE propuestas SET estado='rechazada' WHERE encargo_id=? AND estado='enviada'",
                 (e["id"],)),
            ])
            notificar(e["cliente_id"],
                      f"AVISO FORMAL: tu encargo «{e['titulo']}» recibió propuestas y no "
                      f"respondiste en {DIAS_INACTIVIDAD} días. Tu cuenta queda en revisión "
                      "para suspensión permanente por irresponsabilidad comercial.", "critica")
            for p in db.todos("SELECT productor_id FROM propuestas WHERE encargo_id=?", (e["id"],)):
                notificar(p["productor_id"],
                          f"El encargo «{e['titulo']}» venció sin respuesta del cliente.", "info")
        elif dias >= DIAS_RECORDATORIO and not e["recordatorio_enviado"]:
            db.ejecutar("UPDATE encargos_licitacion SET recordatorio_enviado=1 WHERE id=?", (e["id"],))
            restan = DIAS_INACTIVIDAD - int(dias)
            notificar(e["cliente_id"],
                      f"Recordatorio: te quedan {restan} días para elegir un productor o cerrar "
                      f"«{e['titulo']}». Si no respondes, tu cuenta podría ser suspendida.", "alerta")


def tareas_periodicas() -> None:
    revisar_membresias()
    revisar_inactividad()


# ----------------------------------------------------------------------------
# Productores
# ----------------------------------------------------------------------------
def beats_publicos(productor_id: int) -> int:
    return db.uno("SELECT COUNT(*) n FROM beats WHERE productor_id=? AND es_exclusivo=0 AND retirado=0",
                  (productor_id,))["n"]


def onboarding_de(productor_id: int) -> dict | None:
    return db.uno("SELECT * FROM onboarding_productor WHERE productor_id=?", (productor_id,))


def actualizar_estado_productor(productor_id: int) -> None:
    """Un productor queda 'activo' (visible) solo con onboarding aprobado + 10 beats."""
    u = db.uno("SELECT estado FROM usuarios WHERE id=?", (productor_id,))
    if not u or u["estado"] == "suspendido":
        return
    ob = onboarding_de(productor_id)
    listo = bool(ob and ob["estado_revision"] == "aprobado"
                 and beats_publicos(productor_id) >= MIN_BEATS_PRODUCTOR)
    nuevo = "activo" if listo else "pendiente_verificacion"
    if nuevo != u["estado"]:
        db.ejecutar("UPDATE usuarios SET estado=? WHERE id=?", (nuevo, productor_id))
        if listo:
            notificar(productor_id, "¡Tu perfil ya es público! Tus beats aparecen en el catálogo.",
                      "exito")


def puede_postular(u: dict) -> tuple[bool, str]:
    if not u or u["rol"] != "productor":
        return False, "Solo productores pueden postular."
    if u["estado"] != "activo":
        return False, ("Completa tu verificación de productor (pruebas de autoría + "
                       f"{MIN_BEATS_PRODUCTOR} beats) para postular.")
    from config import SOLO_PRODUCTOR_REAL_POSTULA
    if SOLO_PRODUCTOR_REAL_POSTULA and not u["verificado"]:
        return False, "Necesitas la membresía Productor Real para postular."
    return True, ""


def stats_productor(pid: int) -> dict:
    return db.uno("""
        SELECT
          (SELECT COUNT(*) FROM beats WHERE productor_id=:p AND retirado=0)           AS total_beats,
          (SELECT COUNT(*) FROM beats WHERE productor_id=:p AND es_exclusivo=0 AND retirado=0) AS beats_publicos,
          (SELECT COUNT(*) FROM beats WHERE productor_id=:p AND es_exclusivo=1 AND retirado=0) AS exclusivos,
          (SELECT COUNT(*) FROM pedidos WHERE productor_id=:p
                                         AND estado IN ('confirmado','entregado'))   AS ventas,
          (SELECT ROUND(AVG(calificacion),1) FROM resenas WHERE productor_id=:p)      AS rating,
          (SELECT COUNT(*) FROM resenas WHERE productor_id=:p)                        AS n_resenas,
          (SELECT COALESCE(SUM(reproducciones),0) FROM beats WHERE productor_id=:p)   AS plays
    """.replace(":p", "?"), (pid,) * 7)


def sumar_reproduccion(beat_id: int) -> None:
    db.ejecutar("UPDATE beats SET reproducciones = reproducciones + 1 WHERE id=?", (beat_id,))


# ----------------------------------------------------------------------------
# Pedidos (pago P2P) y reseñas verificadas
# ----------------------------------------------------------------------------
def crear_pedido(cliente_id: int, productor_id: int, tipo: str, item_id: int | None,
                 descripcion: str, monto: float, moneda: str = "USD") -> int:
    pid = db.ejecutar(
        "INSERT INTO pedidos (cliente_id, productor_id, tipo, item_id, descripcion, monto, "
        "moneda, fecha_creacion) VALUES (?,?,?,?,?,?,?,?)",
        (cliente_id, productor_id, tipo, item_id, descripcion, monto, moneda, db.ahora()))
    notificar(productor_id, f"Nuevo pedido #{pid}: {descripcion}. El cliente te contactará "
                            "para coordinar el pago.", "info")
    return pid


def cambiar_estado_pedido(pedido_id: int, productor_id: int, nuevo: str) -> None:
    p = db.uno("SELECT * FROM pedidos WHERE id=? AND productor_id=?", (pedido_id, productor_id))
    if not p:
        return
    fecha = db.ahora() if nuevo == "confirmado" else p["fecha_confirmacion"]
    db.ejecutar("UPDATE pedidos SET estado=?, fecha_confirmacion=? WHERE id=?",
                (nuevo, fecha, pedido_id))
    textos = {
        "confirmado": "El productor confirmó tu pago. Ya puedes dejar una reseña verificada.",
        "entregado": "Tu pedido fue marcado como entregado.",
        "cancelado": "Tu pedido fue cancelado por el productor.",
    }
    notificar(p["cliente_id"], f"Pedido #{pedido_id}: {textos[nuevo]}",
              "exito" if nuevo != "cancelado" else "alerta")


def pedidos_para_resenar(cliente_id: int) -> list[dict]:
    return db.todos("""
        SELECT p.*, u.username AS productor FROM pedidos p
        JOIN usuarios u ON u.id = p.productor_id
        LEFT JOIN resenas r ON r.pedido_id = p.id
        WHERE p.cliente_id=? AND p.estado IN ('confirmado','entregado') AND r.id IS NULL
        ORDER BY p.fecha_creacion DESC""", (cliente_id,))


def crear_resena(cliente_id: int, pedido_id: int, calificacion: int, comentario: str) -> tuple[bool, str]:
    """Solo se permite reseñar pedidos propios, confirmados y sin reseña previa."""
    p = db.uno("SELECT * FROM pedidos WHERE id=? AND cliente_id=? "
               "AND estado IN ('confirmado','entregado')", (pedido_id, cliente_id))
    if not p:
        return False, "Solo puedes reseñar compras o servicios confirmados por el productor."
    if db.uno("SELECT id FROM resenas WHERE pedido_id=?", (pedido_id,)):
        return False, "Ya dejaste una reseña para este pedido."
    db.ejecutar("INSERT INTO resenas (pedido_id, cliente_id, productor_id, calificacion, "
                "comentario, fecha) VALUES (?,?,?,?,?,?)",
                (pedido_id, cliente_id, p["productor_id"], int(calificacion),
                 comentario.strip(), db.ahora()))
    notificar(p["productor_id"], f"Recibiste una reseña de {calificacion}★ (pedido #{pedido_id}).",
              "exito")
    return True, "Reseña publicada."


def enlaces_contacto(productor: dict, mensaje: str) -> dict:
    """Arma enlaces directos de WhatsApp y correo con el mensaje prellenado."""
    enlaces = {}
    if productor.get("whatsapp"):
        enlaces["whatsapp"] = f"https://wa.me/{productor['whatsapp']}?text={quote(mensaje)}"
    if productor.get("email"):
        enlaces["email"] = (f"mailto:{productor['email']}?subject="
                            f"{quote('Pedido en BeatStorage LATAM')}&body={quote(mensaje)}")
    return enlaces


# ----------------------------------------------------------------------------
# Membresías de verificación
# ----------------------------------------------------------------------------
def tipo_membresia_para(rol: str) -> str | None:
    return {"cliente": "comprador_real", "productor": "productor_real"}.get(rol)


def solicitar_membresia(usuario: dict, plan: str, referencia: str) -> tuple[bool, str]:
    tipo = tipo_membresia_para(usuario["rol"])
    if not tipo:
        return False, "Este tipo de cuenta no tiene membresía."
    if tipo == "productor_real":
        ob = onboarding_de(usuario["id"])
        if not ob or ob["estado_revision"] != "aprobado":
            return False, ("Primero necesitas aprobar el filtro anti-IA (pruebas de autoría) "
                           "para optar a la insignia Productor Real / Humano.")
    if db.uno("SELECT id FROM membresias WHERE usuario_id=? AND estado='pendiente_pago'",
              (usuario["id"],)):
        return False, "Ya tienes una solicitud en revisión."
    db.ejecutar("INSERT INTO membresias (usuario_id, tipo, plan, monto_clp, referencia_pago, "
                "fecha_solicitud) VALUES (?,?,?,?,?,?)",
                (usuario["id"], tipo, plan, TARIFAS[tipo][plan], referencia.strip(), db.ahora()))
    return True, "Solicitud enviada. La activamos apenas confirmemos tu transferencia."


def activar_membresia(membresia_id: int) -> None:
    m = db.uno("SELECT * FROM membresias WHERE id=?", (membresia_id,))
    u = db.uno("SELECT * FROM usuarios WHERE id=?", (m["usuario_id"],))
    inicio = _ahora_dt()
    # Si renueva antes de vencer, se suma el tiempo restante
    if u["verificado"] and u["verificado_hasta"] and u["tipo_verificacion"] == m["tipo"]:
        inicio = max(inicio, db.a_fecha(u["verificado_hasta"]))
    fin = (inicio + timedelta(days=DIAS_POR_PLAN[m["plan"]])).strftime(db.FORMATO_FECHA)
    db.transaccion([
        ("UPDATE membresias SET estado='activa', fecha_inicio=?, fecha_fin=? WHERE id=?",
         (db.ahora(), fin, membresia_id)),
        ("UPDATE usuarios SET verificado=1, tipo_verificacion=?, plan_verificacion=?, "
         "moneda_verificacion='CLP', verificado_hasta=? WHERE id=?",
         (m["tipo"], m["plan"], fin, u["id"])),
    ])
    notificar(u["id"], f"Membresía {NOMBRE_MEMBRESIA[m['tipo']]} activa hasta "
                       f"{fecha_corta(fin)}. ¡Tu insignia ya es visible!", "exito")


# ----------------------------------------------------------------------------
# Consultas base reutilizadas por las vistas (incluyen datos del productor p_*)
# ----------------------------------------------------------------------------
SQL_BEATS = """
    SELECT b.*, u.username AS p_username, u.whatsapp AS p_whatsapp, u.email AS p_email,
           u.verificado AS p_verificado, u.tipo_verificacion AS p_tipo_verificacion,
           u.pais AS p_pais, c.username AS cliente_username
    FROM beats b
    JOIN usuarios u ON u.id = b.productor_id
    LEFT JOIN usuarios c ON c.id = b.cliente_exclusivo_id
"""
SQL_SERVICIOS = """
    SELECT s.*, u.username AS p_username, u.whatsapp AS p_whatsapp, u.email AS p_email,
           u.verificado AS p_verificado, u.tipo_verificacion AS p_tipo_verificacion,
           u.pais AS p_pais
    FROM servicios s
    JOIN usuarios u ON u.id = s.productor_id
"""


# ----------------------------------------------------------------------------
# Gestión del catálogo por el productor
# ----------------------------------------------------------------------------
def editar_beat(beat_id: int, productor_id: int, titulo: str, genero: str, bpm: int,
                tonalidad: str, precio_usd: float, uso_ia: bool) -> tuple[bool, str]:
    b = db.uno("SELECT * FROM beats WHERE id=? AND productor_id=? AND retirado=0",
               (beat_id, productor_id))
    if not b:
        return False, "No encontramos ese beat en tu catálogo."
    if len(titulo.strip()) < 2:
        return False, "El título es muy corto."
    if b["uso_ia"] and not uso_ia:
        # Una vez marcado como IA (por el productor o por moderación) no se puede desmarcar solo
        return False, "Un beat marcado con uso de IA solo puede desmarcarlo el equipo de moderación."
    db.ejecutar("UPDATE beats SET titulo=?, genero=?, bpm=?, tonalidad=?, precio_usd=?, uso_ia=? "
                "WHERE id=?", (titulo.strip(), genero, int(bpm), tonalidad,
                               0 if b["es_exclusivo"] else float(precio_usd), int(uso_ia), beat_id))
    return True, "Cambios guardados."


def retirar_beat(beat_id: int, productor_id: int | None = None, motivo: str = "") -> tuple[bool, str]:
    """
    Borrado lógico: el beat deja de verse, pero se conserva para pedidos y reseñas.
    productor_id=None → acción de moderación (admin).
    Los trabajos exclusivos no se pueden retirar: el cliente perdería su descarga.
    """
    b = db.uno("SELECT * FROM beats WHERE id=? AND retirado=0", (beat_id,))
    if not b or (productor_id is not None and b["productor_id"] != productor_id):
        return False, "No encontramos ese beat."
    if b["es_exclusivo"] and productor_id is not None:
        return False, "Los trabajos exclusivos no se pueden retirar: pertenecen a tu cliente."
    db.ejecutar("UPDATE beats SET retirado=1 WHERE id=?", (beat_id,))
    if productor_id is None:
        notificar(b["productor_id"], f"Moderación retiró tu beat «{b['titulo']}». {motivo}", "alerta")
    actualizar_estado_productor(b["productor_id"])
    return True, "Beat retirado del catálogo."


def cambiar_estado_servicio(servicio_id: int, productor_id: int, activo: bool) -> None:
    db.ejecutar("UPDATE servicios SET activo=? WHERE id=? AND productor_id=?",
                (int(activo), servicio_id, productor_id))


# ----------------------------------------------------------------------------
# Denuncias de la comunidad
# ----------------------------------------------------------------------------
def crear_reporte(beat_id: int, denunciante: dict, motivo: str, detalle: str) -> tuple[bool, str]:
    from config import MOTIVOS_REPORTE
    if motivo not in MOTIVOS_REPORTE:
        return False, "Motivo no válido."
    b = db.uno("SELECT productor_id FROM beats WHERE id=? AND retirado=0", (beat_id,))
    if not b:
        return False, "Ese beat ya no está disponible."
    if b["productor_id"] == denunciante["id"]:
        return False, "No puedes denunciar tus propios beats."
    if db.uno("SELECT id FROM reportes WHERE beat_id=? AND denunciante_id=?",
              (beat_id, denunciante["id"])):
        return False, "Ya denunciaste este beat. El equipo lo está revisando."
    db.ejecutar("INSERT INTO reportes (beat_id, denunciante_id, motivo, detalle, fecha) "
                "VALUES (?,?,?,?,?)", (beat_id, denunciante["id"], motivo, detalle.strip(), db.ahora()))
    return True, "Gracias. El equipo revisará la denuncia; no le diremos al productor quién la hizo."


def resolver_reporte(reporte_id: int, accion: str, nota: str = "") -> None:
    """accion: 'desestimar' | 'marcar_ia' | 'retirar'. Resuelve todas las denuncias del mismo beat."""
    r = db.uno("SELECT r.*, b.titulo, b.productor_id FROM reportes r JOIN beats b ON b.id=r.beat_id "
               "WHERE r.id=?", (reporte_id,))
    if not r:
        return
    if accion == "marcar_ia":
        db.ejecutar("UPDATE beats SET uso_ia=1 WHERE id=?", (r["beat_id"],))
        notificar(r["productor_id"], f"Moderación marcó «{r['titulo']}» como hecho con IA tras una "
                                     f"denuncia. {nota}".strip(), "alerta")
    elif accion == "retirar":
        retirar_beat(r["beat_id"], None, nota)
    estado = "desestimado" if accion == "desestimar" else "resuelto"
    db.ejecutar("UPDATE reportes SET estado=?, resolucion=? WHERE beat_id=? AND estado='pendiente'",
                (estado, f"{accion}: {nota}".strip(": "), r["beat_id"]))
