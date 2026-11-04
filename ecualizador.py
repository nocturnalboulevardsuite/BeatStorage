"""
ecualizador.py — Ecualizador decorativo de BeatStorage.

Barras por segmentos (rojo abajo, naranjo arriba) que suben y bajan lento, cada una a su
ritmo, como si estuviera sintonizando una canción. El estilo (.bs-eq) lo pone app.py.

Uso en cualquier vista:
    from ecualizador import ecualizador_html
    st.markdown(ecualizador_html(), unsafe_allow_html=True)
"""
import numpy as np


def ecualizador_html(barras: int = 64, alto: int = 56, semilla: int = 7) -> str:
    """Ecualizador decorativo: barras por segmentos (rojo abajo, naranjo arriba) que suben y bajan
    lento, cada una a su ritmo, como si estuviera sintonizando una canción."""
    import random
    azar = random.Random(semilla)      # misma semilla, mismo dibujo
    piezas = []
    for i in range(barras):
        # Curva tipo espectro musical: más energía en graves y medios, menos en agudos
        base = 0.55 + 0.35 * np.sin(i / barras * np.pi * 1.4 + 0.4) * (1 - i / barras * 0.45)
        a, b, c3 = (min(1, max(.12, base + azar.uniform(-.35, .3))) for _ in range(3))
        piezas.append(f'<i style="--a:{a * 100:.0f}%;--b:{b * 100:.0f}%;--c:{c3 * 100:.0f}%;'
                      f'animation-duration:{azar.uniform(2.2, 4.2):.2f}s;animation-delay:-{azar.uniform(0, 4):.2f}s"></i>')
    return f'<div class="bs-eq" style="height:{alto}px" aria-hidden="true">{"".join(piezas)}</div>'
