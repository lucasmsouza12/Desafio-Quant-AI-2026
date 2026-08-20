# gerar_base_experimentos.py
# Script auxiliar para rodar a grade de experimentos e preencher automaticamente
# experimentos.csv e experimentos.md

import sys
import io
import os
import itertools
import numpy as np
import pandas as pd
from datetime import datetime

# Configuração segura de encoding UTF-8 no stdout para Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dados import (
    DATA_DIR,
    gerar_universo_historico_besst,
    baixar_cdi_sgs12,
    baixar_dados_yfinance,
    baixar_benchmarks
)
from backtest import executar_backtest


def gerar_relatorio_experimentos_md(df_exp, data_inicio, data_fim):
    """
    Gera o relatório em Markdown com o resumo da grade de experimentos.
    Salvo em experimentos.md para consulta institucional.
    """
    top3 = df_exp.sort_values("Sharpe_Ratio", ascending=False).head(3)
    n = len(df_exp)
    sr_max = df_exp["Sharpe_Ratio"].max()
    sr_med = df_exp["Sharpe_Ratio"].mean()
    sr_std = df_exp["Sharpe_Ratio"].std()
    
    linhas_top3 = ""
    for _, r in top3.iterrows():
        linhas_top3 += (
            f"| {r['id_exp']} | {r['L_trend']} | {r['N_acoes']} | "
            f"{r['Fator_Max_SMA']} | {r['Ativar_Preco_Teto']} | {r['Custo_Total_bps']} bps | "
            f"{r['Retorno_Acumulado_Pct']:.1f}% | {r['Sharpe_Ratio']:.3f} | "
            f"{r['Max_Drawdown_Pct']:.2f}% | +{r['ALPHA_Anualizado_Pct']:.2f}% |\n"
        )

    md = f"""# Resumo Executivo: Grade de Experimentos BESST Trend-Yield Otimizado

**Periodo:** {data_inicio} a {data_fim}  
**Total de Cenarios Testados:** {n}  
**Benchmark:** Taxa CDI (SGS 12 - Banco Central do Brasil)  
**Data de Geracao:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Estatisticas da Grade

| Metrica | Valor |
|:--------|------:|
| N de experimentos | {n} |
| Sharpe Maximo | {sr_max:.4f} |
| Sharpe Medio | {sr_med:.4f} |
| Desvio Padrao dos Sharpes | {sr_std:.4f} |

---

## Top 3 Parametrizacoes por Indice de Sharpe

| ID | L_trend | N_acoes | Fator SMA | Bazin | Custo | Retorno Acum. | Sharpe | Drawdown | Alpha |
|:---|--------:|--------:|:---------:|:-----:|------:|--------------:|-------:|---------:|------:|
{linhas_top3}
---

## Notas de Implementacao

- **Execucao VWAP Proxy**: Ordens simuladas no preco medio diario (O+H+L+C)/4 em t+1.
- **Slippage Dinamico**: max(0.05%, 0.10 x Vol_21d).
- **Banda de Inércia (Buffer Turnover)**: Reducao do giro mensal exigindo margem minima de dividendo para substituicao.
- **Segmentacao IS/OOS**: In-Sample 2012-2019, Out-of-Sample 2020-2026.
- **Trava Macro Selic**: CDI_12M >= 12% E Ibov < SMA200 => N_acoes reduzido a metade.
- **Sanitizacao de Proventos**: Alertas automaticos para DY_12M > 25%.
"""
    return md


def main():
    print("=" * 70)
    print("  GERANDO BASE COMPLETA DE EXPERIMENTOS (experimentos.csv / experimentos.md)")
    print("=" * 70)
    
    data_inicio = "2012-01-01"
    data_fim = "2026-07-31"
    
    print("Carregando universo e cotacoes de mercado...")
    df_universo = gerar_universo_historico_besst(data_inicio, data_fim)
    df_cdi = baixar_cdi_sgs12(data_inicio, data_fim)
    dados_precos, dados_proventos = baixar_dados_yfinance(data_inicio="2011-01-01", data_fim=data_fim)
    df_bench = baixar_benchmarks(data_inicio, data_fim)
    
    dados_precarregados = {
        "df_universo": df_universo,
        "df_cdi": df_cdi,
        "dados_precos": dados_precos,
        "dados_proventos": dados_proventos,
        "df_bench": df_bench
    }
    
    # Grade representativa de experimentos
    grid_L_trend    = [100, 150, 200, 250]
    grid_N_acoes    = [4, 6, 8]
    grid_Fator_SMA  = [1.20, None]
    grid_Preco_Teto = [True, False]
    grid_Custos_bps = [0, 8, 15]
    
    combinacoes = list(itertools.product(
        grid_L_trend, grid_N_acoes, grid_Fator_SMA, grid_Preco_Teto, grid_Custos_bps
    ))
    total = len(combinacoes)
    print(f"Rodando {total} combinacoes de hiperparametros na grade...")
    
    resultados = []
    
    for idx, (l_tr, n_ac, fat_sma, pt_act, cust_tot_bps) in enumerate(combinacoes, start=1):
        id_exp = f"EXP_{idx:03d}"
        slipp_bps = float(cust_tot_bps * 0.6)
        cst_bps   = float(cust_tot_bps * 0.4)
        
        try:
            res = executar_backtest(
                data_inicio=data_inicio,
                data_fim=data_fim,
                L_trend=l_tr,
                N_acoes=n_ac,
                Fator_Max_SMA=fat_sma,
                Ativar_Preco_Teto=pt_act,
                slippage_bps=slipp_bps,
                custo_bps=cst_bps,
                dados_precarregados=dados_precarregados
            )
            met = res["metricas"]
            pct_caixa = float(res["df_alocacao"]["pct_caixa_cdi"].mean())
        except Exception as e:
            print(f"  [ERRO] {id_exp}: {e}")
            continue
        
        resultados.append({
            "id_exp": id_exp,
            "L_trend": l_tr,
            "N_acoes": n_ac,
            "Fator_Max_SMA": "Desativado" if fat_sma is None else f"{fat_sma:.2f}",
            "Ativar_Preco_Teto": pt_act,
            "Custo_bps": cst_bps,
            "Slippage_bps": slipp_bps,
            "Custo_Total_bps": cust_tot_bps,
            "Retorno_Acumulado_Pct":    met["Retorno Acumulado Estratégia (%)"],
            "Retorno_Acumulado_CDI_Pct":met["Retorno Acumulado CDI (%)"],
            "Retorno_Anualizado_Pct":   met["Retorno Anualizado Estratégia (% a.a.)"],
            "Retorno_Anualizado_CDI_Pct":met["Retorno Anualizado CDI (% a.a.)"],
            "ALPHA_Anualizado_Pct":     met["ALPHA Anualizado sobre CDI (% a.a.)"],
            "Volatilidade_Anualizada_Pct":met["Volatilidade Anualizada (% a.a.)"],
            "Sharpe_Ratio": met["Índice de Sharpe (base CDI)"],
            "Sharpe":       met["Índice de Sharpe (base CDI)"],  # alias para DSR
            "Max_Drawdown_Pct": met["Drawdown Máximo (%)"],
            "Tempo_Recuperacao_Dias": met["Tempo de Recuperação Máximo (dias úteis)"],
            "Alocacao_Media_Caixa_Pct": pct_caixa,
            "Turnover_Mensal_Medio_Pct": met["Turnover Mensal Médio (%)"],
            "Patrimonio_Final_R$": met["Patrimônio Final (R$)"]
        })
        
        if idx % 10 == 0 or idx == total:
            print(f"  Progresso: {idx}/{total} experimentos concluidos...")
    
    df_exp_final = pd.DataFrame(resultados)
    
    # Salvar CSV com encoding UTF-8 explícito
    caminho_csv = os.path.join(os.path.dirname(__file__), "experimentos.csv")
    df_exp_final.to_csv(caminho_csv, index=False, encoding="utf-8")
    print(f"Salvo: {caminho_csv}")
    
    # Gerar e salvar Markdown
    texto_md = gerar_relatorio_experimentos_md(df_exp_final, data_inicio, data_fim)
    caminho_md = os.path.join(os.path.dirname(__file__), "experimentos.md")
    with open(caminho_md, "w", encoding="utf-8") as f:
        f.write(texto_md)
    print(f"Salvo: {caminho_md}")
    
    print("=" * 70)
    print("  GRADE FINALIZADA COM SUCESSO!")
    print("=" * 70)


if __name__ == "__main__":
    main()
