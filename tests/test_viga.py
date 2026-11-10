"""Validação contra soluções analíticas clássicas (Hibbeler, Beer & Johnston, Timoshenko)."""

import math

import numpy as np
import pytest

from vigas import CargaDistribuida, CargaPontual, MomentoAplicado, Viga

L, q, P, EI = 6.0, 10.0, 20.0, 2.4e4  # m, kN/m, kN, kN·m²
REL = 1e-4


def aprox(v):
    return pytest.approx(v, rel=REL, abs=1e-9)


# ---------------------------------------------------------------- biapoiada
def test_biapoiada_carga_uniforme():
    res = Viga(L, EI=EI).adicionar(CargaDistribuida.uniforme(q, 0, L)).analisar()
    assert list(res.reacoes.forcas.values()) == [aprox(q * L / 2)] * 2
    assert res.M_max == (aprox(q * L**2 / 8), aprox(L / 2))
    assert res.flecha_max[0] == aprox(5 * q * L**4 / (384 * EI))
    assert res.flecha_max[1] == pytest.approx(L / 2, abs=0.01)


def test_biapoiada_carga_pontual_centrada():
    res = Viga(L, EI=EI).adicionar(CargaPontual(P, L / 2)).analisar()
    assert res.M_max[0] == aprox(P * L / 4)
    assert res.flecha_max[0] == aprox(P * L**3 / (48 * EI))


@pytest.mark.parametrize("a", [1.0, 2.5, 4.2])
def test_biapoiada_carga_pontual_excentrica(a):
    b = L - a
    res = Viga(L).adicionar(CargaPontual(P, a)).analisar()
    assert res.reacoes.forcas[0.0] == aprox(P * b / L)
    assert res.reacoes.forcas[L] == aprox(P * a / L)
    assert res.M_max == (aprox(P * a * b / L), aprox(a))


def test_biapoiada_carga_triangular():
    res = Viga(L, EI=EI).adicionar(CargaDistribuida(0, q, 0, L)).analisar(n=8001)
    assert res.reacoes.forcas[0.0] == aprox(q * L / 6)
    assert res.reacoes.forcas[L] == aprox(q * L / 3)
    assert res.M_max[0] == pytest.approx(q * L**2 / (9 * math.sqrt(3)), rel=1e-5)
    assert res.M_max[1] == pytest.approx(L / math.sqrt(3), abs=1e-3)
    # flecha máx = 0,00652·q·L⁴/EI em x = 0,5193·L
    assert res.flecha_max[0] == pytest.approx(0.00652 * q * L**4 / EI, rel=1e-3)
    assert res.flecha_max[1] == pytest.approx(0.5193 * L, abs=5e-3)


def test_biapoiada_momento_aplicado_gera_salto():
    M0 = 30.0
    viga = Viga(L).adicionar(MomentoAplicado(M0, L / 2))
    r = viga.reacoes().forcas
    # Momento anti-horário tende a levantar a extremidade direita: Rb puxa para baixo.
    assert r[0.0] == aprox(M0 / L) and r[L] == aprox(-M0 / L)
    eps = 1e-6
    _, M = viga.esforcos(np.array([L / 2 - eps, L / 2 + eps]))
    assert M[0] - M[1] == pytest.approx(M0, rel=1e-5)


def test_biapoiada_com_balanco():
    # Apoios em 1 m e 5 m, carga na ponta do balanço direito
    viga = Viga(L, xa=1.0, xb=5.0).adicionar(CargaPontual(P, L))
    r = viga.reacoes().forcas
    assert r[1.0] == aprox(-P * 1.0 / 4.0)
    assert r[5.0] == aprox(P * 5.0 / 4.0)
    res = viga.analisar()
    assert res.M_min == (aprox(-P * 1.0), aprox(5.0))


# ---------------------------------------------------------------- engastes
def test_engaste_esquerdo_carga_na_ponta():
    res = Viga(L, "engaste_esquerdo", EI=EI).adicionar(CargaPontual(P, L)).analisar()
    assert res.reacoes.forcas[0.0] == aprox(P)
    assert res.reacoes.momentos[0.0] == aprox(P * L)
    assert res.M_min == (aprox(-P * L), aprox(0.0))
    assert res.flecha_max == (aprox(P * L**3 / (3 * EI)), aprox(L))


def test_engaste_direito_carga_uniforme():
    res = Viga(L, "engaste_direito", EI=EI).adicionar(CargaDistribuida.uniforme(q, 0, L)).analisar()
    assert res.reacoes.forcas[L] == aprox(q * L)
    assert res.M_min[0] == aprox(-q * L**2 / 2)
    assert res.flecha_max == (aprox(q * L**4 / (8 * EI)), aprox(0.0))


# ---------------------------------------------------------------- equilíbrio
@pytest.mark.parametrize("apoio", ["biapoiada", "engaste_esquerdo", "engaste_direito"])
def test_equilibrio_global(apoio):
    viga = Viga(L, apoio).adicionar(
        CargaPontual(12, 1.3),
        CargaDistribuida(4, 9, 0.5, 4.0),
        MomentoAplicado(-7, 2.2),
        CargaPontual(-3, 5.1),
    )
    r = viga.reacoes()
    soma_f = sum(r.forcas.values()) - sum(c.resultante() for c in viga.cargas)
    soma_m = sum(R * x for x, R in r.forcas.items()) + sum(r.momentos.values()) + sum(
        c.momento_em(0.0) for c in viga.cargas
    )
    assert soma_f == pytest.approx(0, abs=1e-9)
    assert soma_m == pytest.approx(0, abs=1e-9)


def test_momento_nulo_nas_extremidades_livres_biapoiada():
    res = Viga(L).adicionar(CargaDistribuida(3, 8, 1, 5), CargaPontual(10, 2)).analisar()
    assert res.M[0] == pytest.approx(0, abs=1e-9)
    assert res.M[-1] == pytest.approx(0, abs=1e-9)


def test_dV_dx_igual_menos_q():
    viga = Viga(L).adicionar(CargaDistribuida.uniforme(q, 0, L))
    x = np.linspace(0.5, 5.5, 11)
    V, _ = viga.esforcos(x)
    assert np.allclose(np.diff(V) / np.diff(x), -q)


# ---------------------------------------------------------------- validação
def test_carga_fora_da_viga():
    with pytest.raises(ValueError):
        Viga(L).adicionar(CargaPontual(P, L + 1))


def test_apoios_invalidos():
    with pytest.raises(ValueError):
        Viga(L, xa=4, xb=2)


def test_distribuida_invertida():
    with pytest.raises(ValueError):
        CargaDistribuida.uniforme(q, 3, 1)


def test_limite_flecha_l250():
    res = Viga(L, EI=EI).adicionar(CargaDistribuida.uniforme(q, 0, L)).analisar()
    assert res.limite_flecha == aprox(L / 250)
    assert res.atende_flecha is (res.flecha_max[0] <= L / 250)
    balanco = Viga(2.0, "engaste_esquerdo", EI=EI).analisar()
    assert balanco.limite_flecha == aprox(2 * 2.0 / 250)
