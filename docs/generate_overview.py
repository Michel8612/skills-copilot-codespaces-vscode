"""Genera un PDF de resumen del proyecto Fondeo Bot, con mapa visual del flujo.

Uso:  python docs/generate_overview.py
Requisitos: matplotlib  (pip install matplotlib)
Salida:  docs/Fondeo_Bot_Resumen.pdf
"""

from __future__ import annotations

import datetime
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# Paleta
BG = "#0f1419"
CARD = "#1a2029"
ACCENT = "#2d9cdb"
GREEN = "#27ae60"
AMBER = "#f2c94c"
RED = "#eb5757"
TEXT = "#e6e9ee"
MUTED = "#8b95a3"

A4 = (8.27, 11.69)


def new_page(pdf):
    fig = plt.figure(figsize=A4)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, color=CARD, edge=ACCENT, fs=10, tcolor=TEXT, bold=False):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.6,rounding_size=2",
        linewidth=1.4, edgecolor=edge, facecolor=color, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tcolor, weight="bold" if bold else "normal", zorder=3, wrap=True)


def arrow(ax, x1, y1, x2, y2, color=MUTED, style="-|>"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
        linewidth=1.6, color=color, zorder=1))


def heading(ax, text, y=92, sub=None):
    ax.text(8, y, text, fontsize=20, color=TEXT, weight="bold")
    if sub:
        ax.text(8, y - 5, sub, fontsize=11, color=MUTED)


def bullets(ax, lines, x=9, y=80, dy=6.2, fs=11, color=TEXT):
    for i, line in enumerate(lines):
        ax.text(x, y - i * dy, line, fontsize=fs, color=color, va="top")


# ---------------------------------------------------------------------------

def page_cover(pdf):
    fig, ax = new_page(pdf)
    ax.add_patch(FancyBboxPatch((6, 58), 88, 30, boxstyle="round,pad=1,rounding_size=3",
                 linewidth=2, edgecolor=ACCENT, facecolor=CARD))
    ax.text(50, 80, "FONDEO BOT", ha="center", fontsize=34, color=TEXT, weight="bold")
    ax.text(50, 72, "Trading algorítmico + empresa de fondeo honesta", ha="center", fontsize=13, color=ACCENT)
    ax.text(50, 65, "Resumen del proyecto · documento para revisión", ha="center", fontsize=11, color=MUTED)

    ax.text(50, 48,
            "Una empresa que gana dinero ayudando a la gente a obtener cuentas de\n"
            "trading financiadas, con un bot automático cuyo rendimiento se comprueba\n"
            "de forma objetiva y auditable. Sin trucos, sin promesas falsas.",
            ha="center", fontsize=12, color=TEXT)

    box(ax, 12, 28, 24, 10, "Servicio\nde pase", edge=AMBER, fs=11, bold=True)
    box(ax, 38, 28, 24, 10, "Venta\ndel bot", edge=GREEN, fs=11, bold=True)
    box(ax, 64, 28, 24, 10, "Empresa\nde fondeo", edge=ACCENT, fs=11, bold=True)
    ax.text(50, 22, "Las 3 líneas de negocio comparten el mismo bot y motor de evaluación", ha="center", fontsize=10, color=MUTED)

    ax.text(50, 10, datetime.date.today().strftime("Generado el %d/%m/%Y"), ha="center", fontsize=9, color=MUTED)
    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def page_what(pdf):
    fig, ax = new_page(pdf)
    heading(ax, "¿A qué se dedica la empresa?", sub="El negocio, en lenguaje claro")
    bullets(ax, [
        "El \"fondeo\" (prop firms): empresas que te dan una cuenta con SU dinero",
        "(50K, 100K USD...) si superas una prueba (challenge) con reglas estrictas:",
        "ganar X% sin perder más de Y% al día ni Z% en total.",
        "",
        "Mucha gente paga por intentar esas pruebas y la mayoría falla. Ahí está el",
        "negocio, en tres líneas que se complementan:",
    ], y=83)

    box(ax, 9, 40, 82, 8, "1.  Servicio de pase  —  pasamos el challenge POR el cliente (cuota + comisión)", edge=AMBER, fs=11)
    box(ax, 9, 30, 82, 8, "2.  Venta del bot  —  el bot como producto con licencia (suscripción)", edge=GREEN, fs=11)
    box(ax, 9, 20, 82, 8, "3.  Empresa de fondeo  —  nuestra propia prop firm con reglas propias", edge=ACCENT, fs=11)

    ax.text(9, 12, "Las tres dependen de lo mismo: un bot fiable + una forma de DEMOSTRAR que funciona.",
            fontsize=10.5, color=MUTED)
    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def page_flow(pdf):
    fig, ax = new_page(pdf)
    heading(ax, "Mapa del flujo: el ecosistema", sub="Cómo se alimentan las 3 líneas (el 'volante')")

    # Bot central
    box(ax, 35, 70, 30, 11, "EL BOT\n(validado)", edge=ACCENT, fs=13, bold=True)

    # 3 líneas
    box(ax, 6, 50, 24, 9, "Venta del bot", edge=GREEN, fs=10)
    box(ax, 38, 50, 24, 9, "Empresa de fondeo", edge=ACCENT, fs=10)
    box(ax, 70, 50, 24, 9, "Servicio de pase", edge=AMBER, fs=10)
    arrow(ax, 45, 70, 22, 59, GREEN)
    arrow(ax, 50, 70, 50, 59, ACCENT)
    arrow(ax, 55, 70, 82, 59, AMBER)

    # Base de datos
    box(ax, 30, 32, 40, 9, "BASE DE DATOS PROPIA\n(cada operación genera datos reales)", edge=TEXT, fs=10)
    arrow(ax, 18, 50, 38, 41, GREEN)
    arrow(ax, 50, 50, 50, 41, ACCENT)
    arrow(ax, 82, 50, 62, 41, AMBER)

    # Mejora -> vuelve al bot (flywheel), ruta limpia por el lateral derecho
    box(ax, 30, 16, 40, 8, "Mejora el bot y calibra reglas justas", edge=GREEN, fs=10)
    arrow(ax, 50, 32, 50, 24, MUTED)
    ax.add_patch(FancyArrowPatch((70, 20), (96, 20), arrowstyle="-", linewidth=1.6, color=MUTED))
    ax.add_patch(FancyArrowPatch((96, 20), (96, 75.5), arrowstyle="-", linewidth=1.6, color=MUTED))
    arrow(ax, 96, 75.5, 65, 75.5, MUTED)
    ax.text(91, 12, "↻ el volante gira más fuerte en cada ciclo", fontsize=9, color=MUTED, ha="right")

    ax.text(8, 8, "Resultado: más datos → mejor bot → mejor producto → más clientes → más datos.",
            fontsize=10, color=MUTED)
    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def page_journey(pdf):
    fig, ax = new_page(pdf)
    heading(ax, "Recorrido de un cliente", sub="De principio a fin, cuando esté terminado")

    steps = [
        ("Cliente entra\ny se registra", ACCENT),
        ("Elige una línea\n(pase / bot / fondeo)", GREEN),
        ("El bot opera\nrespetando las reglas", AMBER),
        ("El MOTOR evalúa\n(mismo veredicto\npara todos)", ACCENT),
        ("Resultado:\npasó / falló\ncon detalle exacto", GREEN),
        ("Cuenta financiada\ny reparto de\nbeneficios", ACCENT),
    ]
    ys = [76, 64, 52, 40, 28, 16]
    for i, ((label, color), y) in enumerate(zip(steps, ys)):
        box(ax, 22, y, 56, 9.5, label, edge=color, fs=11)
        if i < len(steps) - 1:
            arrow(ax, 50, y, 50, ys[i + 1] + 9.5, MUTED)

    ax.text(8, 6, "La evaluación es automática, determinista y auditable: el cliente ve qué regla tocó y cuándo.",
            fontsize=9.5, color=MUTED)
    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def page_status(pdf):
    fig, ax = new_page(pdf)
    heading(ax, "Estado actual y honestidad", sub="Qué ya funciona y los principios del negocio")

    ax.text(9, 84, "Ya construido y probado (37 tests):", fontsize=12, color=GREEN, weight="bold")
    bullets(ax, [
        "✓  Motor de trading + backtesting (sin 'mirar el futuro')",
        "✓  Motor de reglas de challenge (auditable y reproducible)",
        "✓  Agencia de IA que asesora sobre los dilemas del proyecto",
        "✓  Empresa de fondeo con base de datos propia",
        "✓  Las 3 líneas de negocio + panel de cliente (registro/login)",
        "✓  Conector de datos reales de crypto (Binance)",
    ], y=79, dy=5.4, fs=10.5)

    ax.text(9, 45, "Principios de honestidad (sin estafar a nadie):", fontsize=12, color=ACCENT, weight="bold")
    bullets(ax, [
        "•  Reglas públicas e iguales para todos, congeladas por cuenta",
        "•  Veredicto determinista y auditable (mismo motor para todos)",
        "•  Reparto de beneficios y reintentos/reembolsos transparentes",
        "•  El mismo bot que se vende es el que se usa",
    ], y=40, dy=5.4, fs=10.5)

    ax.text(9, 16, "Pendiente / con cautela:", fontsize=11, color=AMBER, weight="bold")
    bullets(ax, [
        "–  Validar 'edge' real con datos reales · pasarela de pagos · marco legal",
    ], y=11.5, dy=5, fs=10)
    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def page_roadmap(pdf):
    fig, ax = new_page(pdf)
    heading(ax, "Hoja de ruta")

    phases = [
        ("Fase 0 — Núcleo", "Motor, reglas, base de datos, 3 líneas y panel", "Completado", GREEN),
        ("Fase 1 — Validación de edge", "Datos reales + métricas de robustez (walk-forward, Monte Carlo)", "En curso", AMBER),
        ("Fase 2 — Ejecución demo", "Conexión a broker/exchange en cuenta de práctica", "Pendiente", MUTED),
        ("Fase 3 — Pagos", "Pasarela y facturación", "Pendiente", MUTED),
        ("Fase 4 — Lanzamiento", "Marco legal y operativa comercial", "Pendiente", MUTED),
    ]
    y = 78
    for title, desc, status, color in phases:
        box(ax, 9, y, 62, 9.5, "", edge=color)
        ax.text(12, y + 6.4, title, fontsize=11, color=TEXT, weight="bold")
        ax.text(12, y + 2.6, desc, fontsize=8.5, color=MUTED)
        ax.text(74, y + 4.5, status, fontsize=10, color=color, weight="bold")
        y -= 13

    ax.add_patch(FancyBboxPatch((9, 8), 82, 16, boxstyle="round,pad=0.6,rounding_size=2",
                 linewidth=1.4, edgecolor=AMBER, facecolor=CARD))
    ax.text(50, 19, "Nota de realismo", ha="center", fontsize=11, color=AMBER, weight="bold")
    ax.text(50, 13.5,
            "El rendimiento pasado no garantiza resultados futuros y ningún sistema asegura superar\n"
            "un challenge. La Fase 1 mide y demuestra si la estrategia tiene ventaja estadística (edge)\n"
            "sobre datos reales antes de comprometer capital o lanzar comercialmente.",
            ha="center", fontsize=8.5, color=TEXT)
    pdf.savefig(fig, facecolor=BG)
    plt.close(fig)


def main():
    out = os.path.join(os.path.dirname(__file__), "Fondeo_Bot_Resumen.pdf")
    with PdfPages(out) as pdf:
        page_cover(pdf)
        page_what(pdf)
        page_flow(pdf)
        page_journey(pdf)
        page_status(pdf)
        page_roadmap(pdf)
        meta = pdf.infodict()
        meta["Title"] = "Fondeo Bot — Resumen del proyecto"
        meta["Author"] = "Fondeo Bot"
    print(f"PDF generado: {out}")


if __name__ == "__main__":
    main()
