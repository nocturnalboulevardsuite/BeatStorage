"""
audio.py — Procesamiento de audio y protección de archivos.

Flujo de protección:
    1. El archivo ORIGINAL se guarda en data/uploads/originales y nunca se envía
       al navegador (salvo descarga autorizada del cliente dueño de un exclusivo).
    2. Se genera una PREESCUCHA: mono, 16 kHz, máximo 45 s y con una marca de
       agua sonora (un "chime" de 3 notas) superpuesta cada 7 segundos.
    3. El reproductor público solo recibe la preescucha.

Solo depende de numpy + la librería estándar. Para MP3 usa pydub (requiere ffmpeg).
"""
import io
import uuid
import wave
from pathlib import Path

import numpy as np

from config import CARPETAS, MARCA_AGUA_CADA_SEG, PREVIEW_MAX_SEG, PREVIEW_SR


class ErrorAudio(Exception):
    """Error legible para mostrar al usuario."""


# ----------------------------------------------------------------------------
# Lectura / escritura
# ----------------------------------------------------------------------------
def _leer_wav(datos: bytes) -> tuple[np.ndarray, int]:
    try:
        with wave.open(io.BytesIO(datos)) as w:
            sr, canales, ancho = w.getframerate(), w.getnchannels(), w.getsampwidth()
            crudo = w.readframes(w.getnframes())
    except wave.Error as e:
        raise ErrorAudio(
            "No se pudo leer el WAV. Usa WAV PCM de 16 o 24 bits (no float de 32 bits)."
        ) from e

    if ancho == 1:
        x = (np.frombuffer(crudo, np.uint8).astype(np.float32) - 128) / 128
    elif ancho == 2:
        x = np.frombuffer(crudo, "<i2").astype(np.float32) / 32768
    elif ancho == 3:
        b = np.frombuffer(crudo, np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v & 0x800000, v - 0x1000000, v)
        x = v.astype(np.float32) / 8_388_608
    elif ancho == 4:
        x = np.frombuffer(crudo, "<i4").astype(np.float32) / 2_147_483_648
    else:
        raise ErrorAudio("Profundidad de bits no soportada.")
    return x.reshape(-1, canales).mean(axis=1), sr


def _leer_mp3(datos: bytes) -> tuple[np.ndarray, int]:
    try:
        from pydub import AudioSegment
    except ImportError as e:
        raise ErrorAudio("Para procesar MP3 instala pydub y ffmpeg (ver README).") from e
    try:
        seg = AudioSegment.from_file(io.BytesIO(datos), format="mp3")
    except Exception as e:
        raise ErrorAudio("No se pudo decodificar el MP3 (¿está instalado ffmpeg?).") from e
    seg = seg.set_channels(1)
    x = np.array(seg.get_array_of_samples(), dtype=np.float32)
    return x / float(1 << (8 * seg.sample_width - 1)), seg.frame_rate


def leer_audio(datos: bytes, extension: str) -> tuple[np.ndarray, int]:
    """Devuelve (muestras mono float32 en [-1, 1], sample rate)."""
    extension = extension.lower().lstrip(".")
    if extension == "wav":
        return _leer_wav(datos)
    if extension == "mp3":
        return _leer_mp3(datos)
    raise ErrorAudio(f"Formato .{extension} no soportado.")


def escribir_wav(ruta: Path, x: np.ndarray, sr: int) -> None:
    """Guarda audio mono float32 como WAV PCM 16-bit."""
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ----------------------------------------------------------------------------
# Remuestreo (con filtro anti-aliasing simple)
# ----------------------------------------------------------------------------
def remuestrear(x: np.ndarray, sr: int, sr_nuevo: int) -> np.ndarray:
    if sr == sr_nuevo:
        return x
    if sr_nuevo < sr:  # filtro pasa-bajos sinc con ventana antes de bajar la tasa
        corte = 0.45 * sr_nuevo / sr
        n = np.arange(-32, 33)
        h = 2 * corte * np.sinc(2 * corte * n) * np.hamming(len(n))
        x = np.convolve(x, h / h.sum(), mode="same")
    t_viejo = np.arange(len(x)) / sr
    t_nuevo = np.arange(int(len(x) * sr_nuevo / sr)) / sr_nuevo
    return np.interp(t_nuevo, t_viejo, x).astype(np.float32)


# ----------------------------------------------------------------------------
# Marca de agua sonora
# ----------------------------------------------------------------------------
def _sello_sonoro(sr: int) -> np.ndarray:
    """Chime de 3 notas ascendentes (C6-E6-G6): identificable y molesto de recortar."""
    partes = []
    for f in (1046.5, 1318.5, 1568.0):
        t = np.arange(int(0.17 * sr)) / sr
        tono = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)
        partes.append(tono * np.exp(-t * 14))
    return (np.concatenate(partes) * 0.42).astype(np.float32)


def aplicar_marca_agua(x: np.ndarray, sr: int, cada_seg: float = MARCA_AGUA_CADA_SEG) -> np.ndarray:
    """Superpone el sello cada N segundos y baja el beat bajo el sello (ducking)."""
    y = x.copy()
    sello = _sello_sonoro(sr)
    for inicio_seg in np.arange(1.5, len(y) / sr, cada_seg):
        i = int(inicio_seg * sr)
        fin = min(len(y), i + len(sello))
        y[i:fin] = y[i:fin] * 0.55 + sello[: fin - i]
    return np.clip(y, -1, 1)


def _fundidos(x: np.ndarray, sr: int, seg: float = 0.6) -> np.ndarray:
    n = min(int(seg * sr), len(x) // 2)
    rampa = np.linspace(0, 1, n, dtype=np.float32)
    x[:n] *= rampa
    x[-n:] *= rampa[::-1]
    return x


def crear_preescucha(x: np.ndarray, sr: int) -> tuple[Path, float]:
    """Genera la preescucha protegida y devuelve (ruta, duración del original)."""
    duracion = len(x) / sr
    x = x[: int(PREVIEW_MAX_SEG * sr)]
    x = remuestrear(x, sr, PREVIEW_SR)
    pico = float(np.max(np.abs(x))) or 1.0
    x = _fundidos(x / pico * 0.85, PREVIEW_SR)
    x = aplicar_marca_agua(x, PREVIEW_SR)
    ruta = CARPETAS["previews"] / f"{uuid.uuid4().hex}.wav"
    escribir_wav(ruta, x, PREVIEW_SR)
    return ruta, duracion


def procesar_subida(datos: bytes, nombre_archivo: str) -> dict:
    """Guarda el original + genera la preescucha. Devuelve rutas y metadatos."""
    extension = Path(nombre_archivo).suffix.lower().lstrip(".")
    x, sr = leer_audio(datos, extension)
    if len(x) < sr * 5:
        raise ErrorAudio("El audio debe durar al menos 5 segundos.")
    ruta_original = CARPETAS["originales"] / f"{uuid.uuid4().hex}.{extension}"
    ruta_original.write_bytes(datos)
    ruta_preview, duracion = crear_preescucha(x, sr)
    return {
        "original": str(ruta_original),
        "preview": str(ruta_preview),
        "formato": extension,
        "duracion": round(duracion, 1),
    }


# ----------------------------------------------------------------------------
# Generador de beats de demostración (para poblar la BD sin archivos externos)
# ----------------------------------------------------------------------------
_ESCALA_MENOR = [0, 2, 3, 5, 7, 8, 10]


def _nota(semitonos_desde_la: float) -> float:
    return 440.0 * 2 ** (semitonos_desde_la / 12)


def generar_beat_demo(semilla: int, bpm: int = 90, segundos: float = 30.0,
                      sr: int = 22_050) -> np.ndarray:
    """Sintetiza un loop sencillo (bombo, caja, hi-hats, bajo, pad y arpegio)."""
    rng = np.random.default_rng(semilla)
    n = int(segundos * sr)
    out = np.zeros(n, np.float32)
    semicorchea = 60 / bpm / 4
    compas = semicorchea * 16

    def sumar(senal, t0):
        i = int(t0 * sr)
        if i >= n:
            return
        fin = min(n, i + len(senal))
        out[i:fin] += senal[: fin - i]

    def env(dur, caida):
        t = np.arange(int(dur * sr)) / sr
        return t, np.exp(-t * caida)

    t, e = env(0.4, 9)
    bombo = np.sin(2 * np.pi * np.cumsum(48 + 110 * np.exp(-t * 28)) / sr) * e * 0.9
    t, e = env(0.25, 20)
    caja = (rng.normal(0, 1, len(t)) * 0.45 + np.sin(2 * np.pi * 190 * t) * 0.3) * e
    t, e = env(0.06, 70)
    hat = np.diff(rng.normal(0, 1, len(t) + 1)) * e * 0.12

    patron_bombo = rng.random(16) < 0.28
    patron_bombo[0] = True
    hat_denso = rng.random() < 0.5
    raiz = int(rng.integers(-21, -14))  # tónica entre C3 y G3 aprox.
    progresion = [rng.choice([0, 3, 5, 4, 6]) for _ in range(4)]
    progresion[0] = 0

    total_compases = int(np.ceil(segundos / compas))
    for c in range(total_compases):
        t0 = c * compas
        grado = int(progresion[c % 4])
        acorde = [raiz + _ESCALA_MENOR[(grado + k) % 7] + 12 * ((grado + k) // 7)
                  for k in (0, 2, 4)]
        # Pad del acorde
        tt = np.arange(int(compas * sr)) / sr
        envp = np.minimum(1, tt / 0.3) * np.minimum(1, (compas - tt) / 0.3)
        pad = sum(np.sin(2 * np.pi * _nota(s + 12) * tt) +
                  0.5 * np.sin(2 * np.pi * _nota(s + 12) * 1.003 * tt) for s in acorde)
        sumar(pad * envp * 0.05, t0)
        for paso in range(16):
            tp = t0 + paso * semicorchea
            if patron_bombo[paso]:
                sumar(bombo, tp)
                tb = np.arange(int(semicorchea * 2 * sr)) / sr
                sumar(np.sin(2 * np.pi * _nota(acorde[0] - 12) * tb) * np.exp(-tb * 4) * 0.35, tp)
            if paso in (4, 12):
                sumar(caja, tp)
            if hat_denso or paso % 2 == 0:
                sumar(hat, tp)
            if paso % 2 == 0 and rng.random() < 0.6:  # arpegio pluck
                ta = np.arange(int(0.3 * sr)) / sr
                f = _nota(acorde[int(rng.integers(0, 3))] + 24)
                sumar(np.sign(np.sin(2 * np.pi * f * ta)) * np.exp(-ta * 12) * 0.05, tp)

    return out / (np.max(np.abs(out)) or 1) * 0.85


def generar_voz_demo(semilla: int, limpia: bool, segundos: float = 12.0,
                     sr: int = 22_050) -> np.ndarray:
    """Simula una toma vocal: 'antes' desafinada y con ruido, 'después' limpia."""
    rng = np.random.default_rng(semilla)
    t = np.arange(int(segundos * sr)) / sr
    notas = rng.choice([-5, -3, 0, 2, 3, 5, 7], size=int(segundos * 2))
    f_obj = np.repeat([_nota(n - 12) for n in notas], len(t) // len(notas) + 1)[: len(t)]
    if not limpia:
        f_obj = f_obj * (1 + 0.025 * np.sin(2 * np.pi * 0.7 * t))  # desafinación
    fase = 2 * np.pi * np.cumsum(f_obj * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t))) / sr
    voz = np.sin(fase) + 0.4 * np.sin(2 * fase) + 0.2 * np.sin(3 * fase)
    voz *= 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 1.0 * t))
    if not limpia:
        voz += rng.normal(0, 0.18, len(t)) + 0.15 * np.sin(2 * np.pi * 50 * t)
    return (voz / np.max(np.abs(voz)) * 0.8).astype(np.float32)
