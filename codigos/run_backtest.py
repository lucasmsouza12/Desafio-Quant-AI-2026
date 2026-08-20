# run_backtest.py
# Script de execução rápida via CLI do Backtest BESST Trend-Yield Otimizado
# Executa a simulação padrão, gera gráficos em /graficos e exibe o relatório de métricas no terminal.

import sys
import io

# Configuração segura de encoding UTF-8 no stdout para Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backtest import executar_backtest
from graficos import gerar_graficos

def main():
    print("=" * 70)
    print("  EXECUTANDO BACKTEST PADRÃO: BESST Trend-Yield Otimizado (2012 - 2026)")
    print("=" * 70)
    
    res = executar_backtest(
        data_inicio="2012-01-01",
        data_fim="2026-07-31",
        L_trend=200,
        N_acoes=6,
        Fator_Max_SMA=1.20,
        Ativar_Preco_Teto=True,
        slippage_bps=5.0,
        custo_bps=3.0
    )
    
    print("\nGerando gráficos em /graficos...")
    gerar_graficos(res, salvar_disco=True)
    
    metricas = res["metricas"]
    print("\n" + "=" * 70)
    print("  RESULTADOS E MÉTRICAS QUANTITATIVAS DO BACKTEST")
    print("=" * 70)
    for k, v in metricas.items():
        if isinstance(v, float):
            print(f"  {k:<45}: {v:>12.2f}")
        else:
            print(f"  {k:<45}: {v:>12}")
    print("=" * 70)
    print("Gráficos salvos com sucesso na pasta /graficos.")

if __name__ == "__main__":
    main()
