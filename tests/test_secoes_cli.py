import json
from pathlib import Path

import pytest

from vigas import SecaoRetangular, modulo_concreto
from vigas.cli import main, viga_de_dict

EXEMPLOS = Path(__file__).parent.parent / "exemplos"


def test_secao_retangular():
    s = SecaoRetangular(0.20, 0.50)
    assert s.area == pytest.approx(0.10)
    assert s.inercia == pytest.approx(0.2 * 0.5**3 / 12)
    assert s.modulo_resistente == pytest.approx(0.2 * 0.5**2 / 6)


@pytest.mark.parametrize(("fck", "ecs_gpa"), [(20, 21), (25, 24), (30, 27), (40, 32), (50, 37)])
def test_modulo_concreto_tabela_8_1(fck, ecs_gpa):
    # NBR 6118 Tabela 8.1 (granito), valores arredondados ao GPa
    assert round(modulo_concreto(fck) / 1e6) == ecs_gpa


def test_modulo_concreto_fora_da_faixa():
    with pytest.raises(ValueError):
        modulo_concreto(90)


@pytest.mark.parametrize("arquivo", sorted(EXEMPLOS.glob("*.json")))
def test_exemplos_rodam(arquivo, capsys):
    assert main([str(arquivo)]) == 0
    assert "Reações" in capsys.readouterr().out


def test_saida_json(capsys):
    assert main([str(EXEMPLOS / "viga_biapoiada_concreto.json"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"M_max", "flecha_max_m", "atende_flecha"} <= data.keys()


def test_grafico(tmp_path):
    destino = tmp_path / "viga.png"
    assert main([str(EXEMPLOS / "balanco_aco.json"), "-g", str(destino)]) == 0
    assert destino.stat().st_size > 10_000


def test_material_sem_modulo():
    with pytest.raises(ValueError):
        viga_de_dict({"comprimento": 3, "secao": {"b": 0.2, "h": 0.4}})


def test_arquivo_invalido(tmp_path, capsys):
    ruim = tmp_path / "x.json"
    ruim.write_text("{nao é json")
    assert main([str(ruim)]) == 2
