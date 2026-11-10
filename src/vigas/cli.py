"""Linha de comando: ``vigas exemplos/viga_biapoiada.json --grafico viga.png``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .cargas import CargaDistribuida, CargaPontual, MomentoAplicado
from .secoes import E_ACO, SecaoRetangular, modulo_concreto
from .viga import Resultado, Viga


def viga_de_dict(d: dict) -> Viga:
    """Monta uma :class:`Viga` a partir do formato JSON documentado no README."""
    apoio = d.get("apoio", {"tipo": "biapoiada"})
    tipo = apoio.get("tipo", "biapoiada")
    if tipo == "engaste":
        tipo = "engaste_" + apoio.get("lado", "esquerdo")

    EI = d.get("EI_kNm2")
    if EI is None and ("secao" in d or "I_m4" in d):
        inercia = d.get("I_m4") or SecaoRetangular(d["secao"]["b"], d["secao"]["h"]).inercia
        if "E_kN_m2" in d:
            E = d["E_kN_m2"]
        elif "fck_MPa" in d:
            E = modulo_concreto(d["fck_MPa"], d.get("agregado", "granito"))
        elif d.get("material") == "aco":
            E = E_ACO
        else:
            raise ValueError("Informe E_kN_m2, fck_MPa ou material='aco' para calcular a flecha")
        EI = E * inercia

    viga = Viga(d["comprimento"], tipo, xa=apoio.get("a", 0.0), xb=apoio.get("b"), EI=EI)
    for c in d.get("cargas", []):
        t = c["tipo"]
        if t == "pontual":
            viga.adicionar(CargaPontual(c["P"], c["x"]))
        elif t == "distribuida":
            x1, x2 = c.get("x1", 0.0), c.get("x2", viga.L)
            if "q" in c:
                viga.adicionar(CargaDistribuida.uniforme(c["q"], x1, x2))
            else:
                viga.adicionar(CargaDistribuida(c["q1"], c["q2"], x1, x2))
        elif t == "momento":
            viga.adicionar(MomentoAplicado(c["M"], c["x"]))
        else:
            raise ValueError(f"Tipo de carga desconhecido: {t}")
    return viga


def relatorio(viga: Viga, res: Resultado) -> str:
    linhas = [f"Viga {viga.apoio}, L = {viga.L:.2f} m, {len(viga.cargas)} carga(s)", "", "Reações:"]
    for pos, R in res.reacoes.forcas.items():
        linhas.append(f"  R(x={pos:.2f} m) = {R:9.3f} kN")
    for pos, M in res.reacoes.momentos.items():
        linhas.append(f"  M(x={pos:.2f} m) = {M:9.3f} kN·m (anti-horário +)")
    v, xv = res.V_abs_max
    mp, xp = res.M_max
    mn, xn = res.M_min
    linhas += [
        "",
        "Esforços:",
        f"  |V| máx = {abs(v):9.3f} kN     em x = {xv:.3f} m",
        f"  M+  máx = {mp:9.3f} kN·m   em x = {xp:.3f} m",
        f"  M−  máx = {mn:9.3f} kN·m   em x = {xn:.3f} m",
    ]
    if res.flecha_max is not None:
        f, xf = res.flecha_max
        ok = "ATENDE" if res.atende_flecha else "NÃO ATENDE"
        linhas += [
            "",
            "Flecha elástica imediata (sem fissuração/fluência):",
            f"  flecha máx = {f * 1000:.2f} mm em x = {xf:.3f} m",
            f"  limite l/250 = {res.limite_flecha * 1000:.2f} mm → {ok}",
        ]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="vigas", description="Análise de vigas isostáticas.")
    p.add_argument("arquivo", type=Path, help="arquivo JSON com a viga")
    p.add_argument("-g", "--grafico", type=Path, help="salvar diagramas (PNG/SVG/PDF)")
    p.add_argument("--json", action="store_true", help="saída em JSON")
    p.add_argument(
        "-V",
        "--version",
        action="version",
        version=(
            f"%(prog)s {__version__} — desenvolvido por carlpit "
            f"(https://github.com/carlpit)"
        ),
    )
    args = p.parse_args(argv)

    try:
        viga = viga_de_dict(json.loads(args.arquivo.read_text(encoding="utf-8")))
        res = viga.analisar()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    if args.json:
        saida = {
            "reacoes_kN": {str(k): v for k, v in res.reacoes.forcas.items()},
            "reacoes_momento_kNm": {str(k): v for k, v in res.reacoes.momentos.items()},
            "V_abs_max": res.V_abs_max,
            "M_max": res.M_max,
            "M_min": res.M_min,
            "flecha_max_m": res.flecha_max,
            "limite_flecha_m": res.limite_flecha,
            "atende_flecha": res.atende_flecha,
        }
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(relatorio(viga, res))

    if args.grafico:
        try:
            from .graficos import plotar
        except ImportError:
            print(
                "erro: matplotlib não está instalado. "
                "Instale com: pip install 'vigas-isostaticas[graficos]'",
                file=sys.stderr,
            )
            return 2
        plotar(viga, res, args.grafico, titulo=args.arquivo.stem)
        print(f"\nDiagramas salvos em {args.grafico}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
