"""
db.py — Capa de datos de BeatStorage LATAM (SQLite + pandas).

Tablas principales pedidas en el brief:
    usuarios, beats, servicios (+ vista servicios_voz), encargos_licitacion, resenas
Tablas de soporte necesarias para que las reglas funcionen:
    onboarding_productor, pruebas_autoria, propuestas, pedidos, membresias, notificaciones

Todas las fechas se guardan como texto ISO en UTC ('YYYY-MM-DD HH:MM:SS').
Para producción basta con migrar este esquema a PostgreSQL (los tipos son compatibles).
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import pandas as pd

from config import DB_PATH

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"


def ahora() -> str:
    """Fecha/hora actual en UTC como texto ISO."""
    return datetime.now(timezone.utc).strftime(FORMATO_FECHA)


def a_fecha(texto: str) -> datetime:
    """Convierte el texto ISO guardado en la BD a datetime (naive, UTC)."""
    return datetime.strptime(texto[:19], FORMATO_FECHA)


# ----------------------------------------------------------------------------
# ESQUEMA RELACIONAL
# ----------------------------------------------------------------------------
ESQUEMA = """
-- 1) USUARIOS ---------------------------------------------------------------
-- Un solo registro por persona. 'rol' define el modo (cliente/productor/admin).
-- Los campos *_verificacion guardan la membresía pagada (CLP).
CREATE TABLE IF NOT EXISTS usuarios (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    username             TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email                TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash        TEXT NOT NULL,
    salt                 TEXT NOT NULL,
    rol                  TEXT NOT NULL CHECK (rol IN ('cliente','productor','admin')),
    nombre_publico       TEXT,
    pais                 TEXT,
    whatsapp             TEXT,
    bio                  TEXT DEFAULT '',
    creditos             TEXT DEFAULT '',        -- "Ha producido tracks para..."
    foto_path            TEXT,
    estado               TEXT NOT NULL DEFAULT 'activo'
                         CHECK (estado IN ('activo','pendiente_verificacion',
                                           'aviso_suspension','suspendido')),
    verificado           INTEGER NOT NULL DEFAULT 0,
    tipo_verificacion    TEXT CHECK (tipo_verificacion IN ('comprador_real','productor_real')
                                     OR tipo_verificacion IS NULL),
    plan_verificacion    TEXT CHECK (plan_verificacion IN ('mensual','anual')
                                     OR plan_verificacion IS NULL),
    moneda_verificacion  TEXT NOT NULL DEFAULT 'CLP',
    verificado_hasta     TEXT,
    intentos_fallidos    INTEGER NOT NULL DEFAULT 0,  -- protección contra fuerza bruta
    bloqueado_hasta      TEXT,
    fecha_registro       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2) ONBOARDING DE PRODUCTOR (filtro anti-IA) --------------------------------
CREATE TABLE IF NOT EXISTS onboarding_productor (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    productor_id         INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    daw_principal        TEXT NOT NULL,
    usa_ia               INTEGER NOT NULL DEFAULT 0,
    areas_ia             TEXT DEFAULT '',
    detalle_ia           TEXT DEFAULT '',
    declaracion_aceptada INTEGER NOT NULL DEFAULT 0,
    estado_revision      TEXT NOT NULL DEFAULT 'pendiente'
                         CHECK (estado_revision IN ('pendiente','aprobado','rechazado')),
    nota_admin           TEXT DEFAULT '',
    fecha_envio          TEXT NOT NULL DEFAULT (datetime('now')),
    fecha_revision       TEXT
);

CREATE TABLE IF NOT EXISTS pruebas_autoria (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    onboarding_id  INTEGER NOT NULL REFERENCES onboarding_productor(id) ON DELETE CASCADE,
    archivo_path   TEXT NOT NULL,
    fecha          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 3) BEATS --------------------------------------------------------------------
-- es_exclusivo = 1 → "Trabajo privado exclusivo": se escucha en el portafolio
-- pero no se puede comprar ni descargar (solo el cliente_exclusivo_id).
CREATE TABLE IF NOT EXISTS beats (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    productor_id          INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo                TEXT NOT NULL,
    genero                TEXT NOT NULL,
    bpm                   INTEGER,
    tonalidad             TEXT,
    precio_usd            REAL NOT NULL DEFAULT 0 CHECK (precio_usd >= 0),
    archivo_original      TEXT NOT NULL,
    formato_original      TEXT NOT NULL CHECK (formato_original IN ('wav','mp3')),
    archivo_preview       TEXT NOT NULL,
    duracion_seg          REAL,
    uso_ia                INTEGER NOT NULL DEFAULT 0,
    es_exclusivo          INTEGER NOT NULL DEFAULT 0,
    cliente_exclusivo_id  INTEGER REFERENCES usuarios(id),
    precio_exclusivo_usd  REAL,
    reproducciones        INTEGER NOT NULL DEFAULT 0,
    retirado              INTEGER NOT NULL DEFAULT 0,  -- borrado lógico (conserva historial)
    fecha_subida          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 4) SERVICIOS (beat por encargo + Fix my Vocal) --------------------------------
CREATE TABLE IF NOT EXISTS servicios (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    productor_id           INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria              TEXT NOT NULL CHECK (categoria IN ('beat_personalizado','fix_my_vocal')),
    tipo                   TEXT NOT NULL,
    titulo                 TEXT NOT NULL,
    descripcion            TEXT DEFAULT '',
    precio_usd             REAL NOT NULL CHECK (precio_usd >= 0),
    precio_personalizable  INTEGER NOT NULL DEFAULT 0,
    entrega_dias           INTEGER NOT NULL DEFAULT 3,
    demo_antes_path        TEXT,
    demo_despues_path      TEXT,
    activo                 INTEGER NOT NULL DEFAULT 1,
    fecha_creacion         TEXT NOT NULL DEFAULT (datetime('now'))
);
-- Vista "Servicios_Voz" pedida en el brief
CREATE VIEW IF NOT EXISTS servicios_voz AS
    SELECT * FROM servicios WHERE categoria = 'fix_my_vocal';

-- 5) TABLÓN DE ENCARGOS / LICITACIONES ------------------------------------------
CREATE TABLE IF NOT EXISTS encargos_licitacion (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id                INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo                    TEXT NOT NULL,
    descripcion               TEXT NOT NULL,
    genero                    TEXT,
    referencias               TEXT DEFAULT '',
    duracion_max              TEXT DEFAULT '',
    presupuesto_monto         REAL NOT NULL CHECK (presupuesto_monto > 0),
    presupuesto_moneda        TEXT NOT NULL CHECK (presupuesto_moneda IN ('CLP','USD')),
    estado                    TEXT NOT NULL DEFAULT 'abierto'
                              CHECK (estado IN ('abierto','asignado','cerrado','vencido_inactividad')),
    productor_seleccionado_id INTEGER REFERENCES usuarios(id),
    fecha_publicacion         TEXT NOT NULL DEFAULT (datetime('now')),
    fecha_primera_propuesta   TEXT,            -- inicia el reloj de 7 días
    recordatorio_enviado      INTEGER NOT NULL DEFAULT 0,
    fecha_aviso               TEXT
);

CREATE TABLE IF NOT EXISTS propuestas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    encargo_id    INTEGER NOT NULL REFERENCES encargos_licitacion(id) ON DELETE CASCADE,
    productor_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    mensaje       TEXT NOT NULL,
    precio        REAL NOT NULL CHECK (precio > 0),
    moneda        TEXT NOT NULL CHECK (moneda IN ('CLP','USD')),
    plazo_dias    INTEGER NOT NULL DEFAULT 3,
    estado        TEXT NOT NULL DEFAULT 'enviada'
                  CHECK (estado IN ('enviada','aceptada','rechazada')),
    fecha         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (encargo_id, productor_id)
);

-- 6) PEDIDOS (compras y servicios coordinados P2P) --------------------------------
-- El pago es directo entre personas; el productor marca 'confirmado' cuando
-- recibe el pago. Solo pedidos confirmados/entregados habilitan reseñas.
CREATE TABLE IF NOT EXISTS pedidos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id          INTEGER NOT NULL REFERENCES usuarios(id),
    productor_id        INTEGER NOT NULL REFERENCES usuarios(id),
    tipo                TEXT NOT NULL CHECK (tipo IN ('beat','servicio','encargo','exclusivo')),
    item_id             INTEGER,
    descripcion         TEXT NOT NULL,
    monto               REAL NOT NULL,
    moneda              TEXT NOT NULL CHECK (moneda IN ('CLP','USD')),
    estado              TEXT NOT NULL DEFAULT 'solicitado'
                        CHECK (estado IN ('solicitado','confirmado','entregado','cancelado')),
    fecha_creacion      TEXT NOT NULL DEFAULT (datetime('now')),
    fecha_confirmacion  TEXT
);

-- 7) RESEÑAS VERIFICADAS ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS resenas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id     INTEGER NOT NULL UNIQUE REFERENCES pedidos(id),
    cliente_id    INTEGER NOT NULL REFERENCES usuarios(id),
    productor_id  INTEGER NOT NULL REFERENCES usuarios(id),
    calificacion  INTEGER NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
    comentario    TEXT DEFAULT '',
    fecha         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 8) MEMBRESÍAS (historial de pagos de verificación) --------------------------------
CREATE TABLE IF NOT EXISTS membresias (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo             TEXT NOT NULL CHECK (tipo IN ('comprador_real','productor_real')),
    plan             TEXT NOT NULL CHECK (plan IN ('mensual','anual')),
    monto_clp        INTEGER NOT NULL,
    referencia_pago  TEXT DEFAULT '',
    estado           TEXT NOT NULL DEFAULT 'pendiente_pago'
                     CHECK (estado IN ('pendiente_pago','activa','vencida','rechazada')),
    fecha_solicitud  TEXT NOT NULL DEFAULT (datetime('now')),
    fecha_inicio     TEXT,
    fecha_fin        TEXT
);

-- 9) NOTIFICACIONES ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notificaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    mensaje     TEXT NOT NULL,
    tipo        TEXT NOT NULL DEFAULT 'info' CHECK (tipo IN ('info','exito','alerta','critica')),
    leida       INTEGER NOT NULL DEFAULT 0,
    fecha       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 10) DENUNCIAS DE LA COMUNIDAD (IA no declarada, plagio) ----------------------------
CREATE TABLE IF NOT EXISTS reportes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    beat_id         INTEGER NOT NULL REFERENCES beats(id) ON DELETE CASCADE,
    denunciante_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    motivo          TEXT NOT NULL CHECK (motivo IN ('ia_no_declarada','plagio','otro')),
    detalle         TEXT DEFAULT '',
    estado          TEXT NOT NULL DEFAULT 'pendiente'
                    CHECK (estado IN ('pendiente','desestimado','resuelto')),
    resolucion      TEXT DEFAULT '',
    fecha           TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (beat_id, denunciante_id)
);

-- Índices para las consultas más frecuentes
CREATE INDEX IF NOT EXISTS ix_beats_productor   ON beats(productor_id);
CREATE INDEX IF NOT EXISTS ix_beats_publicos    ON beats(es_exclusivo, genero);
CREATE INDEX IF NOT EXISTS ix_encargos_estado   ON encargos_licitacion(estado);
CREATE INDEX IF NOT EXISTS ix_propuestas_enc    ON propuestas(encargo_id);
CREATE INDEX IF NOT EXISTS ix_pedidos_cliente   ON pedidos(cliente_id);
CREATE INDEX IF NOT EXISTS ix_pedidos_productor ON pedidos(productor_id);
CREATE INDEX IF NOT EXISTS ix_notif_usuario     ON notificaciones(usuario_id, leida);
CREATE INDEX IF NOT EXISTS ix_reportes_estado   ON reportes(estado);
"""

# Columnas agregadas después de la primera versión. Si la BD ya existía,
# se agregan con ALTER TABLE para no perder datos (migración mínima).
MIGRACIONES = [
    ("usuarios", "intentos_fallidos", "INTEGER NOT NULL DEFAULT 0"),
    ("usuarios", "bloqueado_hasta", "TEXT"),
    ("beats", "retirado", "INTEGER NOT NULL DEFAULT 0"),
]

TABLAS = [
    "usuarios", "onboarding_productor", "pruebas_autoria", "beats", "servicios",
    "servicios_voz", "encargos_licitacion", "propuestas", "pedidos", "resenas",
    "membresias", "notificaciones", "reportes",
]


# ----------------------------------------------------------------------------
# Conexión
# ----------------------------------------------------------------------------
def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def conexion():
    """Abre una conexión, hace commit si todo sale bien y siempre la cierra."""
    conn = _conectar()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar() -> bool:
    """Crea las tablas si no existen. Devuelve True si la BD estaba vacía."""
    with conexion() as conn:
        # 1) Tablas (las nuevas se crean; las existentes no se tocan)
        tablas_sql, indices_sql = ESQUEMA.split("-- Índices para las consultas más frecuentes")
        conn.executescript(tablas_sql)
        # 2) Migraciones de columnas en BD antiguas
        for tabla, columna, ddl in MIGRACIONES:
            existentes = {f[1] for f in conn.execute(f"PRAGMA table_info({tabla})")}
            if columna not in existentes:
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {ddl}")
        # 3) Índices (después de migrar, por si usan columnas nuevas)
        conn.executescript(indices_sql)
        n = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    return n == 0


# ----------------------------------------------------------------------------
# Helpers de consulta
# ----------------------------------------------------------------------------
def uno(sql: str, params: tuple = ()) -> dict | None:
    with conexion() as conn:
        fila = conn.execute(sql, params).fetchone()
    return dict(fila) if fila else None


def todos(sql: str, params: tuple = ()) -> list[dict]:
    with conexion() as conn:
        return [dict(f) for f in conn.execute(sql, params).fetchall()]


def ejecutar(sql: str, params: tuple = ()) -> int:
    """Ejecuta INSERT/UPDATE/DELETE y devuelve el lastrowid."""
    with conexion() as conn:
        return conn.execute(sql, params).lastrowid


def transaccion(operaciones: list[tuple[str, tuple]]) -> None:
    """Ejecuta varias sentencias de forma atómica (todo o nada)."""
    with conexion() as conn:
        for sql, params in operaciones:
            conn.execute(sql, params)


def df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Devuelve el resultado de una consulta como DataFrame de pandas."""
    with conexion() as conn:
        return pd.read_sql_query(sql, conn, params=params)
