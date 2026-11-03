"""
config.py — Configuración central de BeatStorage LATAM.

Todas las reglas de negocio "duras" (tarifas, plazos, mínimos) viven aquí
para que se puedan ajustar sin tocar la lógica de la app.
"""
from pathlib import Path

# ----------------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "beatstorage.db"
UPLOADS_DIR = DATA_DIR / "uploads"

CARPETAS = {
    "originales": UPLOADS_DIR / "originales",   # audio original (NUNCA se sirve en público)
    "previews": UPLOADS_DIR / "previews",       # preescuchas con marca de agua
    "pruebas": UPLOADS_DIR / "pruebas",         # capturas de DAW (filtro anti-IA)
    "fotos": UPLOADS_DIR / "fotos",             # fotos de perfil
}
for _carpeta in CARPETAS.values():
    _carpeta.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Marca
# ----------------------------------------------------------------------------
APP_NOMBRE = "BeatStorage LATAM"
APP_LEMA = "Beats, voces y mezclas hechas por personas de Latinoamérica."

# ----------------------------------------------------------------------------
# Membresías de verificación (precios en CLP)
# ----------------------------------------------------------------------------
TARIFAS = {
    "comprador_real": {"mensual": 3_000, "anual": 15_000},
    "productor_real": {"mensual": 5_000, "anual": 20_000},
}
DIAS_POR_PLAN = {"mensual": 30, "anual": 365}
NOMBRE_MEMBRESIA = {
    "comprador_real": "Comprador Real",
    "productor_real": "Productor Real / Humano",
}

# Datos de pago P2P para membresías (reemplazar por los datos reales)
ADMIN_WHATSAPP = "56900000000"
ADMIN_EMAIL = "pagos@beatstorage.lat"
DATOS_TRANSFERENCIA = (
    "Banco Ejemplo · Cuenta Vista N° 000-000-000 · RUT 11.111.111-1 · "
    "BeatStorage LATAM SpA · pagos@beatstorage.lat"
)

# ----------------------------------------------------------------------------
# Reglas de negocio
# ----------------------------------------------------------------------------
MIN_BEATS_PRODUCTOR = 10          # beats públicos mínimos para aparecer en el catálogo
DIAS_INACTIVIDAD = 7              # plazo para responder propuestas del tablón
DIAS_RECORDATORIO = 5             # aviso preventivo antes del vencimiento
# Si es True, solo los productores con membresía "Productor Real" pueden
# postular al tablón. Si es False, basta con haber pasado el filtro anti-IA.
SOLO_PRODUCTOR_REAL_POSTULA = False

# Seguridad del inicio de sesión
MAX_INTENTOS_LOGIN = 5            # intentos fallidos seguidos antes de bloquear
MINUTOS_BLOQUEO = 15              # duración del bloqueo temporal
CATALOGO_POR_PAGINA = 24          # beats por "página" en el catálogo

# Denuncias de la comunidad
MOTIVOS_REPORTE = {
    "ia_no_declarada": "Parece generado con IA y no está declarado",
    "plagio": "Usa material de otra persona sin permiso",
    "otro": "Otro motivo",
}

PRECIO_BEAT_SUGERIDO = (10, 30)   # USD
PRECIO_BEAT_PERSONALIZADO = 50    # USD

# ----------------------------------------------------------------------------
# Audio / protección
# ----------------------------------------------------------------------------
PREVIEW_SR = 16_000               # las preescuchas se degradan a 16 kHz mono
PREVIEW_MAX_SEG = 45              # duración máxima de la preescucha pública
MARCA_AGUA_CADA_SEG = 7           # la marca de agua suena cada N segundos
FORMATOS_ESTANDAR = ["mp3"]       # productores sin membresía
FORMATOS_VERIFICADO = ["mp3", "wav"]  # Productor Real puede subir WAV original

# ----------------------------------------------------------------------------
# Catálogos
# ----------------------------------------------------------------------------
GENEROS = [
    "Trap", "Reggaetón", "Drill", "Boom Bap", "Lo-Fi", "Cumbia",
    "R&B", "Synthwave", "Afrobeat", "Dembow", "Corridos tumbados",
    "Pop", "Rock", "Electrónica", "Otro",
]
TONALIDADES = [
    "C", "Cm", "C#", "C#m", "D", "Dm", "D#", "D#m", "E", "Em", "F", "Fm",
    "F#", "F#m", "G", "Gm", "G#", "G#m", "A", "Am", "A#", "A#m", "B", "Bm",
]
DAWS = [
    "FL Studio", "Ableton Live", "Logic Pro", "Pro Tools", "Studio One",
    "Reaper", "Cubase", "Bitwig", "GarageBand", "Otro",
]
AREAS_IA = [
    "Generación de melodías", "Generación de samples / loops",
    "Separación de stems", "Voces sintéticas", "Masterización automática",
    "Mezcla asistida", "Otra",
]
TIPOS_SERVICIO_VOZ = {
    "afinacion": "Afinación (Melodyne / Auto-Tune)",
    "limpieza": "Limpieza de ruido de fondo",
    "deessing": "De-essing y control de sibilancias",
    "mezcla": "Mezcla de voces",
    "master": "Masterización",
    "mezcla_master": "Mezcla + master completo",
}
PAISES = [
    "Chile", "Argentina", "México", "Colombia", "Perú", "Venezuela",
    "Ecuador", "Uruguay", "Paraguay", "Bolivia", "Puerto Rico",
    "República Dominicana", "Costa Rica", "Guatemala", "Otro",
]
