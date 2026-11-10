"""Análise de vigas isostáticas: reações, esforço cortante, momento fletor e flecha.

Convenções:
    * Eixo x da esquerda (0) para a direita (L).
    * Cortante positivo: resultante das forças à esquerda da seção apontando para cima.
    * Momento fletor positivo: tração nas fibras inferiores (viga "sorrindo").
    * Deslocamento ``v`` positivo para cima; a flecha usual (para baixo) é ``-v``.
    * Hipóteses: material elástico linear, pequenas deformações, Euler-Bernoulli,
      EI constante. Não considera fissuração nem fluência do concreto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from .cargas import Carga, CargaDistribuida, CargaPontual, MomentoAplicado

TipoApoio = Literal["biapoiada", "engaste_esquerdo", "engaste_direito"]


@dataclass
class Reacoes:
    """Reações de apoio. Forças em kN (para cima +), momentos em kN·m (anti-horário +)."""

    forcas: dict[float, float]
    momentos: dict[float, float] = field(default_factory=dict)


@dataclass
class Resultado:
    x: np.ndarray
    V: np.ndarray
    M: np.ndarray
    v: np.ndarray | None
    reacoes: Reacoes
    limite_flecha: float | None = None

    def _extremo(self, arr: np.ndarray, fn) -> tuple[float, float]:
        i = int(fn(arr))
        return float(arr[i]), float(self.x[i])

    @property
    def M_max(self) -> tuple[float, float]:
        """(valor, posição) do maior momento positivo."""
        return self._extremo(self.M, np.argmax)

    @property
    def M_min(self) -> tuple[float, float]:
        """(valor, posição) do momento mais negativo."""
        return self._extremo(self.M, np.argmin)

    @property
    def V_abs_max(self) -> tuple[float, float]:
        i = int(np.argmax(np.abs(self.V)))
        return float(self.V[i]), float(self.x[i])

    @property
    def flecha_max(self) -> tuple[float, float] | None:
        """(flecha, posição) com flecha positiva para baixo."""
        if self.v is None:
            return None
        i = int(np.argmax(np.abs(self.v)))
        return float(-self.v[i]), float(self.x[i])

    @property
    def atende_flecha(self) -> bool | None:
        if self.flecha_max is None or self.limite_flecha is None:
            return None
        return abs(self.flecha_max[0]) <= self.limite_flecha


class Viga:
    """Viga isostática de comprimento ``L``.

    Exemplos:
        >>> from vigas import Viga, CargaDistribuida
        >>> viga = Viga(6.0).adicionar(CargaDistribuida.uniforme(10, 0, 6))
        >>> res = viga.analisar()
        >>> round(res.M_max[0], 3)   # qL²/8
        45.0
    """

    def __init__(
        self,
        L: float,
        apoio: TipoApoio = "biapoiada",
        *,
        xa: float = 0.0,
        xb: float | None = None,
        EI: float | None = None,
    ) -> None:
        if L <= 0:
            raise ValueError("O comprimento L deve ser positivo")
        if apoio not in ("biapoiada", "engaste_esquerdo", "engaste_direito"):
            raise ValueError(f"Tipo de apoio inválido: {apoio}")
        self.L = float(L)
        self.apoio: TipoApoio = apoio
        self.xa = float(xa)
        self.xb = float(L if xb is None else xb)
        if apoio == "biapoiada" and not (0 <= self.xa < self.xb <= self.L):
            raise ValueError("Apoios devem satisfazer 0 ≤ xa < xb ≤ L")
        self.EI = EI
        self.cargas: list[Carga] = []

    # ------------------------------------------------------------------ montagem
    def adicionar(self, *cargas: Carga) -> Viga:
        for c in cargas:
            pos = (c.x1, c.x2) if isinstance(c, CargaDistribuida) else (c.x,)
            if any(p < 0 or p > self.L for p in pos):
                raise ValueError(f"Carga fora da viga: {c}")
            self.cargas.append(c)
        return self

    # ------------------------------------------------------------------ estática
    def reacoes(self) -> Reacoes:
        F = sum(c.resultante() for c in self.cargas)
        if self.apoio == "biapoiada":
            # ΣM_A = 0 → Rb·(xb − xa) + Σ momento das cargas em A = 0
            m_a = sum(c.momento_em(self.xa) for c in self.cargas)
            rb = -m_a / (self.xb - self.xa)
            ra = F - rb
            return Reacoes({self.xa: ra, self.xb: rb})
        x0 = 0.0 if self.apoio == "engaste_esquerdo" else self.L
        m0 = -sum(c.momento_em(x0) for c in self.cargas)
        return Reacoes({x0: F}, {x0: m0})

    # ------------------------------------------------------------------ esforços
    def _malha(self, n: int) -> np.ndarray:
        criticos = {0.0, self.L, self.xa, self.xb}
        for c in self.cargas:
            criticos.update((c.x1, c.x2) if isinstance(c, CargaDistribuida) else (c.x,))
        eps = 1e-9 * self.L
        extra = [p + eps for p in criticos if p + eps < self.L]
        return np.unique(np.concatenate([np.linspace(0, self.L, n), list(criticos), extra]))

    def esforcos(
        self, x: np.ndarray, reacoes: Reacoes | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Cortante V(x) e momento M(x) pelo método das seções (lado esquerdo).

        Elementos exatamente em ``x`` são excluídos (limite pela esquerda), exceto em x = 0.
        """
        x = np.asarray(x, dtype=float)
        r = reacoes or self.reacoes()
        V = np.zeros_like(x)
        M = np.zeros_like(x)

        def esquerda(pos: float) -> np.ndarray:
            return (pos < x) | ((pos == 0.0) & (x == 0.0))

        for pos, R in r.forcas.items():
            m = esquerda(pos)
            V += np.where(m, R, 0.0)
            M += np.where(m, R * (x - pos), 0.0)
        for pos, Mr in r.momentos.items():
            M -= np.where(esquerda(pos), Mr, 0.0)

        for c in self.cargas:
            if isinstance(c, CargaPontual):
                m = esquerda(c.x)
                V -= np.where(m, c.P, 0.0)
                M -= np.where(m, c.P * (x - c.x), 0.0)
            elif isinstance(c, MomentoAplicado):
                M -= np.where(esquerda(c.x), c.M, 0.0)
            else:
                f, mo = c.trecho_a_esquerda(x)
                V -= f
                M -= mo
        return V, M

    # ------------------------------------------------------------------ elástica
    def _elastica(self, x: np.ndarray, M: np.ndarray) -> np.ndarray:
        """Integra EI·v'' = M duas vezes e impõe as condições de contorno."""
        assert self.EI is not None
        kappa = M / self.EI
        dx = np.diff(x)
        theta = np.concatenate([[0.0], np.cumsum((kappa[1:] + kappa[:-1]) / 2 * dx)])
        v = np.concatenate([[0.0], np.cumsum((theta[1:] + theta[:-1]) / 2 * dx)])
        # v_real = v + C1·x + C2
        if self.apoio == "biapoiada":
            va, vb = np.interp([self.xa, self.xb], x, v)
            c1 = -(vb - va) / (self.xb - self.xa)
            c2 = -va - c1 * self.xa
        elif self.apoio == "engaste_esquerdo":
            c1, c2 = 0.0, 0.0
        else:
            c1 = -theta[-1]
            c2 = -v[-1] - c1 * self.L
        return v + c1 * x + c2

    def vao_referencia(self) -> float:
        """Vão para o limite de flecha: vão entre apoios, ou 2× o balanço (NBR 6118, 13.3)."""
        if self.apoio == "biapoiada":
            return max(self.xb - self.xa, 2 * self.xa, 2 * (self.L - self.xb))
        return 2 * self.L

    def analisar(self, n: int = 2001, limite: float = 250.0) -> Resultado:
        """Calcula reações, diagramas e (se ``EI`` foi dado) a linha elástica.

        ``limite`` é o denominador do deslocamento-limite ``l/limite``
        (250 = aceitabilidade sensorial visual, NBR 6118:2023 Tabela 13.3).
        """
        r = self.reacoes()
        x = self._malha(n)
        V, M = self.esforcos(x, r)
        v = self._elastica(x, M) if self.EI else None
        lim = self.vao_referencia() / limite if self.EI else None
        return Resultado(x, V, M, v, r, lim)
