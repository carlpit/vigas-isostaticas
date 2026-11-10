"""Tipos de carregamento.

Convenção de sinais (unidades: kN, m, kN·m):
    * Forças e cargas distribuídas positivas apontam **para baixo** (gravidade).
    * Momentos aplicados positivos são **anti-horários**.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CargaPontual:
    P: float  # kN, positivo para baixo
    x: float  # m

    def resultante(self) -> float:
        return self.P

    def momento_em(self, p: float) -> float:
        """Momento da carga em relação ao ponto ``p`` (anti-horário +)."""
        return -self.P * (self.x - p)


@dataclass(frozen=True)
class CargaDistribuida:
    """Carga linearmente variável (trapezoidal) entre ``x1`` e ``x2``.

    Uniforme quando ``q1 == q2``; triangular quando um dos extremos é zero.
    """

    q1: float  # kN/m em x1
    q2: float  # kN/m em x2
    x1: float
    x2: float

    def __post_init__(self) -> None:
        if self.x2 <= self.x1:
            raise ValueError("Carga distribuída exige x2 > x1")

    @classmethod
    def uniforme(cls, q: float, x1: float, x2: float) -> CargaDistribuida:
        return cls(q, q, x1, x2)

    @property
    def _k(self) -> float:
        return (self.q2 - self.q1) / (self.x2 - self.x1)

    def _integrais(self, t: np.ndarray, d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Para o trecho [x1, x1 + t] devolve (∫q ds, ∫q·(x1 + d − s) ds)."""
        q1, k = self.q1, self._k
        forca = q1 * t + k * t**2 / 2
        momento = q1 * (d * t - t**2 / 2) + k * (d * t**2 / 2 - t**3 / 3)
        return forca, momento

    def resultante(self) -> float:
        return (self.q1 + self.q2) / 2 * (self.x2 - self.x1)

    def momento_em(self, p: float) -> float:
        t = np.asarray(self.x2 - self.x1, dtype=float)
        _, m = self._integrais(t, np.asarray(p - self.x1, dtype=float))
        # ∫q(s)·(p − s) ds já é o momento anti-horário da carga (para baixo) em torno de p.
        return float(m)

    def trecho_a_esquerda(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Força e momento (em torno de cada seção ``x``) da parcela à esquerda de ``x``."""
        t = np.clip(np.minimum(x, self.x2) - self.x1, 0.0, None)
        return self._integrais(t, x - self.x1)


@dataclass(frozen=True)
class MomentoAplicado:
    M: float  # kN·m, anti-horário positivo
    x: float

    def resultante(self) -> float:
        return 0.0

    def momento_em(self, p: float) -> float:
        return self.M


Carga = CargaPontual | CargaDistribuida | MomentoAplicado
