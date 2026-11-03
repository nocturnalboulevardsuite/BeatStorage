"""
seed.py — Datos de demostración. Se ejecuta solo si la base de datos está vacía.

Cuentas (contraseña de todas: demo1234, admin: admin1234):
    admin            → Administración
    lofi_valpo       → Productor con membresía Productor Real (12 beats + exclusivo)
    mezclas_bogota   → Productor activo con servicios Fix my Vocal
    trapsur          → Productor pendiente de revisión (declara uso de IA)
    (además: una denuncia pendiente sobre un beat de mezclas_bogota)
    sandyy88         → Cliente con membresía Comprador Real
    artista_lima     → Cliente sin membresía
"""
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image, ImageDraw

import audio
import auth
import core
import db
from config import CARPETAS


def _hace(dias: float) -> str:
    t = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=dias)
    return t.strftime(db.FORMATO_FECHA)


def _beat(productor_id: int, semilla: int, titulo: str, genero: str, bpm: int, tono: str,
          precio: float, dias: float, exclusivo_para: int | None = None,
          precio_excl: float | None = None, uso_ia: int = 0) -> int:
    sr = 22_050
    x = audio.generar_beat_demo(semilla, bpm=bpm, segundos=30, sr=sr)
    original = CARPETAS["originales"] / f"{uuid.uuid4().hex}.wav"
    audio.escribir_wav(original, x, sr)
    preview, dur = audio.crear_preescucha(x, sr)
    return db.ejecutar(
        "INSERT INTO beats (productor_id, titulo, genero, bpm, tonalidad, precio_usd, archivo_original, "
        "formato_original, archivo_preview, duracion_seg, uso_ia, es_exclusivo, cliente_exclusivo_id, "
        "precio_exclusivo_usd, reproducciones, fecha_subida) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (productor_id, titulo, genero, bpm, tono, 0 if exclusivo_para else precio, str(original), "wav",
         str(preview), dur, uso_ia, int(bool(exclusivo_para)), exclusivo_para, precio_excl,
         int(np.random.default_rng(semilla).integers(20, 900)), _hace(dias)))


def _captura_daw(semilla: int) -> str:
    """Dibuja una captura ficticia de 'playlist' de un DAW para la demo de revisión."""
    rng = np.random.default_rng(semilla)
    img = Image.new("RGB", (640, 360), (38, 42, 48))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 640, 28], fill=(24, 26, 30))
    d.text((10, 8), "Proyecto_trap_v3.flp  |  Playlist  |  140 BPM", fill=(200, 200, 210))
    colores = [(214, 58, 120), (47, 111, 228), (14, 159, 138), (201, 130, 0)]
    for pista in range(8):
        y = 40 + pista * 38
        d.text((8, y + 10), f"Pista {pista + 1}", fill=(170, 170, 180))
        for _ in range(int(rng.integers(2, 6))):
            x0 = int(rng.integers(80, 560))
            d.rectangle([x0, y + 4, x0 + int(rng.integers(30, 120)), y + 30],
                        fill=colores[pista % 4], outline=(20, 20, 20))
    ruta = CARPETAS["pruebas"] / f"{uuid.uuid4().hex}.png"
    img.save(ruta)
    return str(ruta)


def _voz(semilla: int, limpia: bool) -> str:
    x = audio.generar_voz_demo(semilla, limpia)
    return str(audio.crear_preescucha(x, 22_050)[0])


def poblar() -> None:
    crear = auth.crear_usuario
    _, admin = crear("admin", "admin@beatstorage.lat", "admin1234", "admin", "Equipo BeatStorage", "Chile")
    _, valpo = crear("lofi_valpo", "valpo@example.com", "demo1234", "productor", "Valpo Lo-Fi Lab",
                     "Chile", "56911111111",
                     bio="Beats con cinta, polvo de vinilo y vista al puerto. Produzco desde 2016 en "
                         "un home studio del cerro Alegre.",
                     creditos="200 beats creados. Ha producido para artistas independientes de "
                              "Valparaíso, Santiago y Lima.")
    _, bogota = crear("mezclas_bogota", "bogota@example.com", "demo1234", "productor", "Andrés M. Studio",
                      "Colombia", "573000000000",
                      bio="Ingeniero de mezcla. Arreglo voces grabadas en el celular para que suenen "
                          "a estudio.", creditos="Más de 300 voces editadas para maquetas y singles.")
    _, trapsur = crear("trapsur", "trapsur@example.com", "demo1234", "productor", "TrapSur", "Argentina",
                       "5491100000000")
    _, sandy = crear("sandyy88", "sandy@example.com", "demo1234", "cliente", "Sandy", "Chile", "56922222222")
    _, lima = crear("artista_lima", "lima@example.com", "demo1234", "cliente", "Lu Quispe", "Perú",
                    "51999999999")

    # ---- Onboarding (filtro anti-IA) ----
    for pid, daw, ia, areas, estado in (
            (valpo, "Ableton Live", 0, "", "aprobado"),
            (bogota, "Pro Tools", 0, "", "aprobado"),
            (trapsur, "FL Studio", 1, "Separación de stems, Masterización automática", "pendiente")):
        ob = db.ejecutar("INSERT INTO onboarding_productor (productor_id, daw_principal, usa_ia, areas_ia, "
                         "detalle_ia, declaracion_aceptada, estado_revision, fecha_envio) VALUES (?,?,?,?,?,1,?,?)",
                         (pid, daw, ia, areas, "Uso IA solo para separar samples de vinilos." if ia else "",
                          estado, _hace(20)))
        for k in range(2):
            db.ejecutar("INSERT INTO pruebas_autoria (onboarding_id, archivo_path) VALUES (?,?)",
                        (ob, _captura_daw(pid * 10 + k)))

    # ---- Beats ----
    titulos_valpo = [("Cerro Alegre", "Lo-Fi", 82, "Am", 15), ("Neón en Bellavista", "Synthwave", 108, "Dm", 25),
                     ("Ascensor 1883", "Boom Bap", 90, "Gm", 20), ("Niebla de Marzo", "Lo-Fi", 75, "Em", 12),
                     ("Perreo en la Costanera", "Reggaetón", 96, "C#m", 30), ("Cassette Azul", "Synthwave", 112, "F#m", 22),
                     ("Calle Condell", "Trap", 140, "Bm", 18), ("Pacífico Frío", "R&B", 68, "Fm", 25),
                     ("Micro Verde", "Drill", 142, "G#m", 20), ("Feria de Domingo", "Cumbia", 98, "Am", 15),
                     ("Último Trolebús", "Lo-Fi", 80, "Cm", 10), ("Marea Alta", "Afrobeat", 104, "Dm", 28)]
    for i, (t, g, bpm, tono, precio) in enumerate(titulos_valpo):
        _beat(valpo, 100 + i, t, g, bpm, tono, precio, dias=30 - i)
    _beat(valpo, 999, "Luces de Viña", "Synthwave", 110, "Am", 0, dias=10,
          exclusivo_para=sandy, precio_excl=50)

    titulos_bog = [("Chapinero de Noche", "Reggaetón", 92), ("Monserrate", "Dembow", 118),
                   ("La Candelaria", "Trap", 136), ("Usaquén", "R&B", 70), ("Transmilenio", "Drill", 144),
                   ("Llovizna", "Lo-Fi", 78), ("Bacatá", "Afrobeat", 102), ("Septimazo", "Boom Bap", 88),
                   ("Páramo", "Pop", 100), ("Ruana", "Cumbia", 96)]
    for i, (t, g, bpm) in enumerate(titulos_bog):
        _beat(bogota, 200 + i, t, g, bpm, "Am", 10 + (i % 3) * 5, dias=25 - i)

    for i, (t, g) in enumerate([("Sur Profundo", "Trap"), ("Conurbano", "Drill"), ("Fernet", "Trap")]):
        _beat(trapsur, 300 + i, t, g, 140, "Em", 10, dias=3 - i, uso_ia=1)

    # ---- Servicios ----
    for pid, cat, tipo, titulo, desc, precio, dias, demo in (
        (bogota, "fix_my_vocal", "afinacion", "Afinación natural en Melodyne",
         "Corrijo nota por nota sin el efecto robot. Incluye ajuste de timing.", 25, 2, True),
        (bogota, "fix_my_vocal", "limpieza", "Limpieza de voz grabada en celular",
         "Saco ruido de ventilador, eco de pieza y zumbido eléctrico.", 15, 1, True),
        (bogota, "fix_my_vocal", "deessing", "De-essing y control de sibilancias",
         "Suavizo las eses y los golpes de aire sin apagar la voz.", 10, 1, False),
        (bogota, "fix_my_vocal", "mezcla_master", "Mezcla + master para single",
         "Voz y beat balanceados y listos para plataformas (-14 LUFS).", 60, 4, False),
        (valpo, "beat_personalizado", "beat_personalizado", "Beat a medida desde cero",
         "Te mando 2 bocetos en 48 h, eliges uno y lo terminamos juntos. Incluye stems.", 50, 5, False),
    ):
        db.ejecutar("INSERT INTO servicios (productor_id, categoria, tipo, titulo, descripcion, precio_usd, "
                    "precio_personalizable, entrega_dias, demo_antes_path, demo_despues_path) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (pid, cat, tipo, titulo, desc, precio, int(cat == "beat_personalizado"), dias,
                     _voz(pid + dias, False) if demo else None, _voz(pid + dias, True) if demo else None))

    # ---- Membresías activas ----
    for uid, tipo, plan, monto, dias in ((valpo, "productor_real", "anual", 20_000, 365),
                                         (sandy, "comprador_real", "mensual", 3_000, 30)):
        fin = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=dias - 5)).strftime(db.FORMATO_FECHA)
        db.ejecutar("INSERT INTO membresias (usuario_id, tipo, plan, monto_clp, estado, fecha_solicitud, "
                    "fecha_inicio, fecha_fin, referencia_pago) VALUES (?,?,?,?, 'activa', ?,?,?, 'TRX-DEMO')",
                    (uid, tipo, plan, monto, _hace(5), _hace(5), fin))
        db.ejecutar("UPDATE usuarios SET verificado=1, tipo_verificacion=?, plan_verificacion=?, "
                    "verificado_hasta=? WHERE id=?", (tipo, plan, fin, uid))
    db.ejecutar("INSERT INTO membresias (usuario_id, tipo, plan, monto_clp, referencia_pago, fecha_solicitud) "
                "VALUES (?,?,?,?,?,?)", (bogota, "productor_real", "mensual", 5_000, "Op. 8841203", _hace(0.3)))

    # ---- Pedidos confirmados + reseñas verificadas ----
    p1 = db.ejecutar("INSERT INTO pedidos (cliente_id, productor_id, tipo, item_id, descripcion, monto, moneda, "
                     "estado, fecha_creacion, fecha_confirmacion) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (sandy, valpo, "exclusivo", None, "Beat exclusivo «Luces de Viña»", 50, "USD",
                      "entregado", _hace(12), _hace(11)))
    p2 = db.ejecutar("INSERT INTO pedidos (cliente_id, productor_id, tipo, item_id, descripcion, monto, moneda, "
                     "estado, fecha_creacion, fecha_confirmacion) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (lima, bogota, "servicio", 1, "Servicio «Afinación natural en Melodyne»", 25, "USD",
                      "confirmado", _hace(6), _hace(5)))
    db.ejecutar("INSERT INTO pedidos (cliente_id, productor_id, tipo, item_id, descripcion, monto, moneda, "
                "fecha_creacion) VALUES (?,?,?,?,?,?,?,?)",
                (lima, valpo, "beat", 1, "Beat «Cerro Alegre»", 15, "USD", _hace(0.5)))
    db.ejecutar("INSERT INTO resenas (pedido_id, cliente_id, productor_id, calificacion, comentario, fecha) "
                "VALUES (?,?,?,?,?,?)", (p1, sandy, valpo, 5,
                                         "Entendió la onda ochentera al tiro. Entregó antes de lo acordado.", _hace(10)))
    db.ejecutar("INSERT INTO resenas (pedido_id, cliente_id, productor_id, calificacion, comentario, fecha) "
                "VALUES (?,?,?,?,?,?)", (p2, lima, bogota, 4,
                                         "Mi voz de celular quedó irreconocible, para bien.", _hace(4)))

    # ---- Tablón de encargos ----
    e1 = db.ejecutar("INSERT INTO encargos_licitacion (cliente_id, titulo, descripcion, genero, referencias, "
                     "duracion_max, presupuesto_monto, presupuesto_moneda, fecha_publicacion, "
                     "fecha_primera_propuesta) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (sandy, "Beat synthwave estilo 80s",
                      "Busco beat synthwave estilo 80s de máximo 2 minutos, con bajo arpegiado, "
                      "batería tipo LinnDrum y pads brillantes.", "Synthwave",
                      "The Midnight, Los Prisioneros", "2 minutos", 60_000, "CLP", _hace(4), _hace(3)))
    db.ejecutar("INSERT INTO propuestas (encargo_id, productor_id, mensaje, precio, moneda, plazo_dias, fecha) "
                "VALUES (?,?,?,?,?,?,?)",
                (e1, valpo, "Tengo un set de sintes análogos ideal para esto. Escucha «Cassette Azul» en "
                            "mi catálogo: te entrego en 3 días con 2 revisiones.", 60_000, "CLP", 3, _hace(3)))
    e2 = db.ejecutar("INSERT INTO encargos_licitacion (cliente_id, titulo, descripcion, genero, duracion_max, "
                     "presupuesto_monto, presupuesto_moneda, fecha_publicacion, fecha_primera_propuesta) "
                     "VALUES (?,?,?,?,?,?,?,?,?)",
                     (lima, "Arreglar voces de maqueta acústica",
                      "Grabé guitarra y voz en mi pieza, se escucha el eco y desafino en el coro. "
                      "Necesito afinación suave y limpieza.", "Pop", "3:30", 40, "USD", _hace(6.5), _hace(6)))
    db.ejecutar("INSERT INTO propuestas (encargo_id, productor_id, mensaje, precio, moneda, plazo_dias, fecha) "
                "VALUES (?,?,?,?,?,?,?)",
                (e2, bogota, "Hago afinación natural en Melodyne y quito el eco de la pieza. Mira el "
                             "antes/después en mi servicio de limpieza.", 35, "USD", 2, _hace(6)))
    db.ejecutar("INSERT INTO encargos_licitacion (cliente_id, titulo, descripcion, genero, referencias, "
                "duracion_max, presupuesto_monto, presupuesto_moneda, fecha_publicacion) VALUES (?,?,?,?,?,?,?,?,?)",
                (sandy, "Cumbia con sintes para videoclip",
                 "Cumbia moderna con guacharaca, bajo sintético y espacio para dos voces.", "Cumbia",
                 "Ritmo de cumbia villera con toque electrónico", "3 minutos", 45, "USD", _hace(1)))

    # ---- Una denuncia pendiente para la demo de moderación ----
    beat_denunciado = db.uno("SELECT id FROM beats WHERE productor_id=? ORDER BY id LIMIT 1", (bogota,))["id"]
    db.ejecutar("INSERT INTO reportes (beat_id, denunciante_id, motivo, detalle, fecha) VALUES (?,?,?,?,?)",
                (beat_denunciado, sandy, "ia_no_declarada",
                 "La melodía suena igual a las que generan las apps de IA.", _hace(0.2)))

    for pid in (valpo, bogota, trapsur):
        core.actualizar_estado_productor(pid)
    core.notificar(lima, "Recibiste una propuesta para «Arreglar voces de maqueta acústica». "
                         "Tienes 7 días para responder.", "alerta")
