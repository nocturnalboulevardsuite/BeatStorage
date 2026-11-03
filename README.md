# BeatStorage LATAM (MVP en Streamlit)

Plataforma para conectar beatmakers, productores e ingenieros de Latinoamérica con artistas independientes.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
# Para subir MP3 se necesita ffmpeg (macOS: brew install ffmpeg / Ubuntu: apt install ffmpeg)
streamlit run app.py
```

La primera vez se crea `data/beatstorage.db` y se generan beats, voces y capturas de DAW de demostración (unos 5 segundos). Para reiniciar la demo, borra la carpeta `data/`.

| Usuario | Contraseña | Qué muestra |
|---|---|---|
| `sandyy88` | demo1234 | Cliente con Comprador Real, dueña de un beat exclusivo |
| `artista_lima` | demo1234 | Cliente con un encargo a punto de vencer (día 6 de 7) |
| `lofi_valpo` | demo1234 | Productor Real, 12 beats, trabajo exclusivo y beat a medida |
| `mezclas_bogota` | demo1234 | Productor con servicios Fix my Vocal (antes/después) |
| `trapsur` | demo1234 | Productor pendiente de revisión, declara uso de IA |
| `admin` | admin1234 | Revisión anti-IA, pagos, suspensiones, base de datos |

En Streamlit Cloud, `packages.txt` instala ffmpeg automáticamente.

### Con Docker

```bash
docker build -t beatstorage .
docker run -p 8501:8501 -v beatstorage_data:/app/data beatstorage
```

El volumen `beatstorage_data` guarda la base de datos y los audios entre despliegues.

### Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
```

Son 34 pruebas: reglas de negocio (registro, bloqueo de login, filtro anti-IA, regla de 7 días, membresías, reseñas, denuncias, marca de agua, migración de BD) y de interfaz (todas las páginas para cada rol, compra, login). Usan una base de datos temporal, nunca `data/`.

## Novedades de la versión 5

**Logo:** una "b" minúscula formada por un mástil y un disco de vinilo, con el nombre en minúsculas.

**Productores estilo SoundCloud:** directorio de artistas con foto circular y perfil con portada, botones de acción (Reproducir, Contactar, Beat a medida), cifras y secciones en píldoras. Cada pista muestra su forma de onda real (calculada del audio). Al reproducir, la onda se colorea a medida que avanza y se puede hacer clic en ella para saltar.

**Registro estilo Spotify:** tres pasos centrados (correo, contraseña con reglas visibles, perfil y cómo usarás la plataforma) con barra de progreso. El inicio de sesión también tiene su propia pantalla.

**Navegación:** botones en la barra lateral en vez de opciones de radio.

## Estructura

```
app.py              Punto de entrada: sidebar con sesión y navegación por rol
config.py           Tarifas CLP, plazos, mínimos y catálogos (todo ajustable)
db.py               Esquema SQL relacional + helpers (dict / DataFrame de pandas)
auth.py             Registro y login (PBKDF2-SHA256 con sal)
core.py             Reglas de negocio: 7 días, membresías, pedidos, reseñas
audio.py            Lectura WAV/MP3, marca de agua, preescuchas, audio de demo
components.py       Reproductor protegido, tarjetas, insignias, contacto P2P
styles.py           CSS inyectado (claro/oscuro)
seed.py             Datos de demostración
tests/              Pruebas automatizadas (pytest + streamlit AppTest)
Dockerfile          Imagen lista para desplegar
vistas/
  catalogo.py       Home + catálogo con filtros
  servicios.py      Fix my Vocal + beat por encargo
  productores.py    Perfil público, exclusivos, reseñas
  licitaciones.py   Tablón de encargos con cuenta regresiva
  onboarding.py     Verificación de productor (filtro anti-IA)
  panel.py          Panel de cliente/productor y membresías
  admin.py          Administración
```

## Base de datos

Tablas pedidas: `usuarios`, `beats`, `servicios` (más la vista `servicios_voz`), `encargos_licitacion`, `resenas`.
Tablas de soporte: `onboarding_productor`, `pruebas_autoria`, `propuestas`, `pedidos`, `membresias`, `notificaciones`, `reportes`.

Si ya tenías una base de datos de la versión anterior, `db.inicializar()` agrega las columnas nuevas con `ALTER TABLE` sin borrar datos.
El esquema completo está comentado en `db.py` y es compatible con PostgreSQL con cambios mínimos.

## Cómo se implementó cada regla

**Visibilidad del productor.** Un productor queda `activo` (visible y con permiso para postular) solo con pruebas de autoría aprobadas por un admin **y** 10 beats públicos. Antes de eso puede subir beats, pero no aparecen.

**Productor Real.** Se puede solicitar solo después de aprobar el filtro anti-IA. Da insignia, prioridad en el orden del catálogo y permite subir WAV; sin membresía solo se acepta MP3.

**Pagos P2P.** "Comprar" o "Pedir servicio" registra un pedido y abre WhatsApp o correo con un mensaje prellenado. El productor marca el pedido como confirmado cuando recibe el pago; recién ahí el cliente puede dejar una reseña (una por pedido). Las membresías también se pagan por transferencia y un admin las activa.

**Regla de 7 días.** El reloj parte con la primera propuesta recibida. El día 5 se envía un recordatorio. El día 7, si no eligió productor ni cerró el encargo, el encargo vence y la cuenta pasa a `aviso_suspension` con un aviso formal (no puede publicar ni pedir). Un admin confirma la suspensión permanente o levanta el aviso. "Cerrar encargo sin elegir" cuenta como respuesta. En Administración → Inactividad hay un simulador para adelantar el reloj y probarlo.

**Gestión del catálogo.** El productor puede editar título, género, BPM, tonalidad y precio, pausar servicios y retirar beats. Retirar es un borrado lógico: el beat desaparece del catálogo pero se conserva para pedidos y reseñas. Si al retirar queda bajo 10 beats, el perfil vuelve a pendiente (la app lo advierte antes). Los trabajos exclusivos no se pueden retirar, y un beat marcado con IA solo lo desmarca moderación.

**Denuncias de la comunidad.** Al escuchar un beat aparece "Denunciar este beat" (IA no declarada, plagio u otro). Una denuncia por persona y beat; el productor no ve quién denunció. En Administración → Denuncias se agrupan por beat para escucharlo, ver la declaración de IA del productor y decidir: desestimar, marcar con IA o retirar.

**Inicio de sesión.** Tras 5 intentos fallidos seguidos la cuenta se bloquea 15 minutos. El mensaje de error es el mismo exista o no el usuario.

**Protección del audio.** El original nunca llega al navegador. La preescucha pública se degrada a 16 kHz mono, máximo 45 s, con un sello sonoro de tres notas cada 7 s. El reproductor no usa controles nativos (sin botón de descarga ni menú contextual) y carga el audio como Blob en memoria.

## Limitaciones conocidas del MVP

La protección del reproductor es disuasiva: alguien con conocimientos técnicos puede grabar lo que suena. Lo que protege de verdad es que el público solo recibe la preescucha con marca de agua y baja calidad. Para producción conviene servir audio por streaming con URLs firmadas que expiren (por ejemplo, S3/R2 + HLS).

Las tareas periódicas (vencimientos y regla de 7 días) se ejecutan en cada carga de página. En producción deben ir en un cron o un scheduler.

SQLite sirve para una demo con pocos usuarios simultáneos. Para producción: PostgreSQL, almacenamiento de objetos para los archivos, y verificación de correo y teléfono en el registro.

La tipografía usa Google Fonts (Bricolage Grotesque e Instrument Sans) con fuentes del sistema como respaldo. Hay dos temas definidos en `.streamlit/config.toml`: oscuro con rosa oscuro (#C2185B) y claro en blanco con rojo (#C8102E). La app sigue el tema del sistema y se puede cambiar en el menú ⋮ → Settings → Theme. No se usan emojis: los íconos son SVG en línea o íconos Material de Streamlit.
