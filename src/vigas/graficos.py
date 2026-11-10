"""Diagramas de esforços (DEC, DMF) e linha elástica com matplotlib."""

from __future__ import annotations

from pathlib import Path

from .viga import Resultado, Viga


def plotar(viga: Viga, res: Resultado, arquivo: str | Path | None = None, titulo: str = ""):
    import matplotlib

    if arquivo:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = 3 if res.v is not None else 2
    fig, axes = plt.subplots(n, 1, figsize=(9, 2.6 * n), sharex=True)

    ax = axes[0]
    ax.fill_between(res.x, res.V, step=None, alpha=0.35, color="tab:blue")
    ax.plot(res.x, res.V, color="tab:blue")
    ax.set_ylabel("V (kN)")
    ax.set_title("Diagrama de esforço cortante (DEC)", loc="left")
    if titulo:
        fig.suptitle(titulo, fontweight="bold")

    ax = axes[1]
    # Convenção brasileira: momento positivo desenhado para baixo (lado tracionado).
    ax.fill_between(res.x, res.M, alpha=0.35, color="tab:red")
    ax.plot(res.x, res.M, color="tab:red")
    ax.margins(y=0.15)
    ax.invert_yaxis()
    ax.set_ylabel("M (kN·m)")
    ax.set_title("Diagrama de momento fletor (DMF) — positivo para baixo", loc="left")
    for valor, pos in {res.M_max, res.M_min}:
        if abs(valor) > 1e-9:
            ax.annotate(f"{valor:.2f}", (pos, valor), textcoords="offset points",
                        xytext=(0, -14 if valor < 0 else 8), ha="center", fontsize=9,
                        bbox={"fc": "white", "ec": "none", "alpha": 0.8, "pad": 1})

    if res.v is not None:
        ax = axes[2]
        ax.plot(res.x, res.v * 1000, color="tab:green")
        ax.axhline(0, color="gray", lw=0.8)
        fl, pos = res.flecha_max
        ax.set_ylabel("v (mm)")
        ax.set_title(f"Linha elástica — flecha máx. {fl * 1000:.2f} mm em x = {pos:.2f} m",
                     loc="left")

    for ax in axes:
        ax.axhline(0, color="black", lw=0.8)
        ax.grid(alpha=0.3)
        for x_ap in res.reacoes.forcas:
            ax.axvline(x_ap, color="gray", ls=":", lw=0.8)
    axes[-1].set_xlabel("x (m)")
    axes[-1].set_xlim(0, viga.L)
    fig.tight_layout()

    if arquivo:
        fig.savefig(arquivo, dpi=150)
        plt.close(fig)
    return fig
