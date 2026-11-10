"""Propriedades de seções e módulos de elasticidade de materiais usuais."""

from __future__ import annotations

import math
from dataclasses import dataclass

AGREGADO_ALFA_E = {"basalto": 1.2, "diabasio": 1.2, "granito": 1.0, "gnaisse": 1.0,
                   "calcario": 0.9, "arenito": 0.7}


@dataclass(frozen=True)
class SecaoRetangular:
    b: float  # largura (m)
    h: float  # altura (m)

    def __post_init__(self) -> None:
        if self.b <= 0 or self.h <= 0:
            raise ValueError("b e h devem ser positivos")

    @property
    def area(self) -> float:
        return self.b * self.h

    @property
    def inercia(self) -> float:
        """Momento de inércia em relação ao eixo horizontal (m⁴): b·h³/12."""
        return self.b * self.h**3 / 12

    @property
    def modulo_resistente(self) -> float:
        """W = I / (h/2) = b·h²/6 (m³)."""
        return self.b * self.h**2 / 6


def modulo_concreto(fck_mpa: float, agregado: str = "granito") -> float:
    """Módulo de elasticidade secante Ecs do concreto (NBR 6118:2023, 8.2.8), em kN/m².

    Válido para fck de 20 a 50 MPa:
        Eci = αE · 5600 · √fck      (MPa)
        αi  = 0,8 + 0,2 · fck / 80  ≤ 1,0
        Ecs = αi · Eci

    >>> round(modulo_concreto(25) / 1e6, 2)   # GPa
    24.15
    """
    if not 20 <= fck_mpa <= 50:
        raise ValueError("Expressão válida para 20 MPa ≤ fck ≤ 50 MPa")
    try:
        alfa_e = AGREGADO_ALFA_E[agregado.lower()]
    except KeyError as exc:
        raise ValueError(f"Agregado desconhecido: {agregado}") from exc
    eci = alfa_e * 5600 * math.sqrt(fck_mpa)
    alfa_i = min(0.8 + 0.2 * fck_mpa / 80, 1.0)
    return alfa_i * eci * 1e3  # MPa → kN/m²


E_ACO = 200e6  # kN/m² (200 GPa, NBR 8800)
