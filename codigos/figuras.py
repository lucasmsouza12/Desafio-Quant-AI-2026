# figuras.py
# Script de geração de gráficos em alta resolução (300 DPI - Publication Ready)
# Gera as figuras para o Relatório Técnico Final do Desafio Quant AI Itaú
# Salva todas as figuras na pasta figuras/

import os
import sys
import io
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

warnings.filterwarnings("ignore")

# Configuração segura de UTF-8 no Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dados import (
    gerar_universo_historico_besst,
    baixar_cdi_sgs12,
    baixar_dados_yfinance,
    baixar_benchmarks
)
from backtest import executar_backtest

# Diretório de saída
FIGURAS_DIR = os.path.join(os.path.dirname(__file__), "figuras")
os.makedirs(FIGURAS_DIR, exist_ok=True)

# Paleta Institucional Harmonizada
COLOR_ESTRATEGIA = "#0047AB"   # Azul Cobalto Institucional
COLOR_CDI        = "#2E7D32"   # Verde Floresta Sóbrio
COLOR_IBOV       = "#757575"   # Cinza Neutro
COLOR_IDIV       = "#E65100"   # Laranja Âmbar
COLOR_DRAWDOWN   = "#C62828"   # Vermelho Carmim
COLOR_ALPHA      = "#00838F"   # Ciano / Petróleo Profundo
COLOR_GRID       = "#E0E0E0"

# Configuração global de fontes e estilo
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["axes.edgecolor"] = "#BDBDBD"
plt.rcParams["axes.linewidth"] = 0.8


def gerar_todas_as_figuras():
    print("=" * 70)
    print("  GERANDO FIGURAS EM ALTA RESOLUÇÃO (300 DPI) PARA O RELATÓRIO FINAL")
    print("=" * 70)
    
    print("\n1. Carregando dados de mercado e executando backtest padrão...")
    data_inicio = "2012-01-01"
    data_fim = "2026-07-31"
    
    df_universo = gerar_universo_historico_besst(data_inicio, data_fim)
    df_cdi = baixar_cdi_sgs12(data_inicio, data_fim)
    dados_precos, dados_proventos = baixar_dados_yfinance("2011-01-01", data_fim)
    df_bench = baixar_benchmarks(data_inicio, data_fim)
    
    dados_prec = {
        "df_universo": df_universo,
        "df_cdi": df_cdi,
        "dados_precos": dados_precos,
        "dados_proventos": dados_proventos,
        "df_bench": df_bench
    }
    
    # Executa Backtest Completo
    res_full = executar_backtest(
        data_inicio=data_inicio,
        data_fim=data_fim,
        L_trend=200,
        N_acoes=6,
        Fator_Max_SMA=1.20,
        Ativar_Preco_Teto=True,
        slippage_bps=5.0,
        custo_bps=3.0,
        buffer_turnover=0.15,
        filtro_macro_selic=False,
        dados_precarregados=dados_prec,
        janela_execucao="Completo"
    )
    
    # Executa Backtest In-Sample e Out-of-Sample para métricas comparativas
    res_is = executar_backtest(
        L_trend=200, N_acoes=6, Fator_Max_SMA=1.20, Ativar_Preco_Teto=True,
        slippage_bps=5.0, custo_bps=3.0, buffer_turnover=0.15,
        dados_precarregados=dados_prec, janela_execucao="IS"
    )
    res_oos = executar_backtest(
        L_trend=200, N_acoes=6, Fator_Max_SMA=1.20, Ativar_Preco_Teto=True,
        slippage_bps=5.0, custo_bps=3.0, buffer_turnover=0.15,
        dados_precarregados=dados_prec, janela_execucao="OOS"
    )
    
    df_diario = res_full["df_diario"].copy()
    met = res_full["metricas"]
    
    # Base 100
    b100_est = (df_diario["patrimonio_estrategia"] / df_diario["patrimonio_estrategia"].iloc[0]) * 100.0
    b100_cdi = (df_diario["patrimonio_cdi"] / df_diario["patrimonio_cdi"].iloc[0]) * 100.0
    
    s_ibov = df_bench["^BVSP"].reindex(df_diario.index).ffill().bfill()
    b100_ibov = (s_ibov / s_ibov.iloc[0]) * 100.0
    
    s_idiv = df_bench["IDIV.SA"].reindex(df_diario.index).ffill().bfill()
    b100_idiv = (s_idiv / s_idiv.iloc[0]) * 100.0
    
    alpha_acum = b100_est - b100_cdi
    
    # -------------------------------------------------------------
    # (a) CURVA DE CAPITAL - ESTRATÉGIA VS CDI (COM BENCHMARKS)
    # -------------------------------------------------------------
    print("2. Gerando Figura (a): Curva de Capital (01_curva_de_capital.png)...")
    fig1, ax1 = plt.subplots(figsize=(11, 5.8), dpi=300)
    
    ax1.plot(df_diario.index, b100_est, label=f"BESST Trend-Yield ({met['Retorno Acumulado Estratégia (%)']:.1f}%)", color=COLOR_ESTRATEGIA, linewidth=2.2, zorder=5)
    ax1.plot(df_diario.index, b100_cdi, label=f"CDI Benchmark ({met['Retorno Acumulado CDI (%)']:.1f}%)", color=COLOR_CDI, linewidth=2.0, linestyle="--", zorder=4)
    ax1.plot(df_diario.index, b100_idiv, label=f"IDIV - Índice Dividendos ({(b100_idiv.iloc[-1]-100):.1f}%)", color=COLOR_IDIV, linewidth=1.2, alpha=0.75, zorder=3)
    ax1.plot(df_diario.index, b100_ibov, label=f"Ibovespa ^BVSP ({(b100_ibov.iloc[-1]-100):.1f}%)", color=COLOR_IBOV, linewidth=1.1, linestyle=":", alpha=0.7, zorder=2)
    
    ax1.set_title("Evolução Patrimonial Acumulada: BESST Trend-Yield Otimizado vs CDI (2012–2026)", fontsize=13, fontweight="bold", pad=12, color="#212121")
    ax1.set_ylabel("Patrimônio Acumulado (Base 100 = Jan/2012)", fontsize=11, fontweight="semibold", labelpad=8)
    ax1.set_xlabel("Ano", fontsize=11, fontweight="semibold", labelpad=8)
    
    ax1.xaxis.set_major_locator(mdates.YearLocator(2))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.grid(True, linestyle="--", alpha=0.5, color=COLOR_GRID)
    ax1.legend(loc="upper left", frameon=True, framealpha=0.9, facecolor="white", edgecolor="#E0E0E0", fontsize=9.5)
    
    # Anotação final de valor
    ax1.annotate(f"R$ {df_diario['patrimonio_estrategia'].iloc[-1]:,.0f}".replace(",", "."),
                 xy=(df_diario.index[-1], b100_est.iloc[-1]),
                 xytext=(10, 0), textcoords="offset points",
                 fontweight="bold", color=COLOR_ESTRATEGIA, fontsize=10, va="center")
    
    fig1.tight_layout()
    fig1_path = os.path.join(FIGURAS_DIR, "01_curva_de_capital.png")
    fig1.savefig(fig1_path, dpi=300)
    plt.close(fig1)
    
    # -------------------------------------------------------------
    # (b) ALPHA ACUMULADO SOBRE O CDI (FIGURA CENTRAL)
    # -------------------------------------------------------------
    print("3. Gerando Figura (b): ALPHA Acumulado sobre CDI (02_alpha_acumulado_cdi.png)...")
    fig2, ax2 = plt.subplots(figsize=(11, 5.8), dpi=300)
    
    ax2.plot(df_diario.index, alpha_acum, label="ALPHA Acumulado sobre CDI (p.p.)", color=COLOR_ALPHA, linewidth=2.2, zorder=4)
    ax2.axhline(0, color="#424242", linestyle="-", linewidth=1.0, zorder=3)
    
    # Preenchimento sombreado onde o alpha é positivo vs negativo
    ax2.fill_between(df_diario.index, alpha_acum, 0, where=(alpha_acum >= 0), color=COLOR_ALPHA, alpha=0.18, zorder=2, label="Alpha Positivo (+p.p.)")
    ax2.fill_between(df_diario.index, alpha_acum, 0, where=(alpha_acum < 0), color=COLOR_DRAWDOWN, alpha=0.15, zorder=2)
    
    # Destaque de Regimes de Mercado
    ax2.axvspan(pd.to_datetime("2014-01-01"), pd.to_datetime("2016-12-31"), color="#FFF3E0", alpha=0.4, label="Crise Fiscal / Recessão (2014-16)")
    ax2.axvspan(pd.to_datetime("2020-02-01"), pd.to_datetime("2020-06-30"), color="#FFEBEE", alpha=0.4, label="Choque COVID-19 (2020)")
    ax2.axvspan(pd.to_datetime("2021-03-01"), pd.to_datetime("2024-03-01"), color="#E8F5E9", alpha=0.4, label="Ciclo Selic 2% -> 13.75% (2021-24)")
    
    ax2.set_title("ALPHA Acumulado da Estratégia BESST sobre a Taxa CDI (2012–2026)", fontsize=13, fontweight="bold", pad=12, color="#212121")
    ax2.set_ylabel("Alpha Acumulado (% pontos percentuais)", fontsize=11, fontweight="semibold", labelpad=8)
    ax2.set_xlabel("Ano", fontsize=11, fontweight="semibold", labelpad=8)
    
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.grid(True, linestyle="--", alpha=0.5, color=COLOR_GRID)
    ax2.legend(loc="upper left", frameon=True, framealpha=0.9, facecolor="white", edgecolor="#E0E0E0", fontsize=9.5)
    
    # Anotação final de Alpha
    alpha_final = alpha_acum.iloc[-1]
    ax2.annotate(f"{alpha_final:+.1f} p.p. (+{met['ALPHA Anualizado sobre CDI (% a.a.)']:.2f}% a.a.)",
                 xy=(df_diario.index[-1], alpha_final),
                 xytext=(10, 0), textcoords="offset points",
                 fontweight="bold", color=COLOR_ALPHA, fontsize=10, va="center")
    
    fig2.tight_layout()
    fig2_path = os.path.join(FIGURAS_DIR, "02_alpha_acumulado_cdi.png")
    fig2.savefig(fig2_path, dpi=300)
    plt.close(fig2)
    
    # -------------------------------------------------------------
    # (c) DRAWDOWN AO LONGO DO TEMPO
    # -------------------------------------------------------------
    print("4. Gerando Figura (c): Drawdown ao Longo do Tempo (03_drawdown_temporal.png)...")
    fig3, ax3 = plt.subplots(figsize=(11, 5.0), dpi=300)
    
    dd_est = df_diario["drawdown"] * 100.0
    
    pk_ibov = s_ibov.cummax()
    dd_ibov = ((s_ibov - pk_ibov) / pk_ibov) * 100.0
    
    pk_idiv = s_idiv.cummax()
    dd_idiv = ((s_idiv - pk_idiv) / pk_idiv) * 100.0
    
    ax3.plot(df_diario.index, dd_ibov, label=f"Ibovespa (Max DD: {dd_ibov.min():.1f}%)", color=COLOR_IBOV, linewidth=1.0, alpha=0.6)
    ax3.plot(df_diario.index, dd_idiv, label=f"IDIV (Max DD: {dd_idiv.min():.1f}%)", color=COLOR_IDIV, linewidth=1.1, alpha=0.7)
    ax3.plot(df_diario.index, dd_est, label=f"BESST Trend-Yield (Max DD: {met['Drawdown Máximo (%)']:.1f}%)", color=COLOR_DRAWDOWN, linewidth=1.8)
    ax3.fill_between(df_diario.index, dd_est, 0, color=COLOR_DRAWDOWN, alpha=0.2)
    
    ax3.set_title("Perfil de Risco Subjacente: Curvas de Drawdown ao Longo do Tempo (2012–2026)", fontsize=13, fontweight="bold", pad=12, color="#212121")
    ax3.set_ylabel("Drawdown (%)", fontsize=11, fontweight="semibold", labelpad=8)
    ax3.set_xlabel("Ano", fontsize=11, fontweight="semibold", labelpad=8)
    ax3.set_ylim(min(dd_ibov.min() * 1.1, -55), 3)
    
    ax3.xaxis.set_major_locator(mdates.YearLocator(2))
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax3.grid(True, linestyle="--", alpha=0.5, color=COLOR_GRID)
    ax3.legend(loc="lower left", frameon=True, framealpha=0.9, facecolor="white", edgecolor="#E0E0E0", fontsize=9.5)
    
    fig3.tight_layout()
    fig3_path = os.path.join(FIGURAS_DIR, "03_drawdown_temporal.png")
    fig3.savefig(fig3_path, dpi=300)
    plt.close(fig3)
    
    # -------------------------------------------------------------
    # (d) MAPA DE CALOR DOS RETORNOS MENSAIS (HEATMAP ANO X MÊS)
    # -------------------------------------------------------------
    print("4. Gerando Figura (d): Mapa de Calor de Retornos Mensais (04_mapa_calor_retornos_mensais.png)...")
    
    # Série de retornos mensais da estratégia
    s_ret_m = df_diario["patrimonio_estrategia"].resample("ME").last().pct_change().dropna() * 100.0
    
    df_hm = pd.DataFrame({
        "Ano": s_ret_m.index.year,
        "Mes": s_ret_m.index.month,
        "Retorno": s_ret_m.values
    })
    
    tabela_pivot = df_hm.pivot(index="Ano", columns="Mes", values="Retorno")
    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    tabela_pivot.columns = [nomes_meses[m-1] for m in tabela_pivot.columns]
    
    # Retorno Anual Composto (YTD)
    s_ano = df_diario["patrimonio_estrategia"].resample("YE").last().pct_change()
    s_ano.iloc[0] = (df_diario["patrimonio_estrategia"].loc[f"{df_diario.index[0].year}"].iloc[-1] / df_diario["patrimonio_estrategia"].iloc[0]) - 1.0
    
    # Ajusta o ano corrente parcial 2026
    val_2026 = (df_diario["patrimonio_estrategia"].loc["2026"].iloc[-1] / df_diario["patrimonio_estrategia"].loc["2025"].iloc[-1]) - 1.0
    
    ytd_dict = {}
    for y in tabela_pivot.index:
        if y == 2026:
            ytd_dict[y] = val_2026 * 100.0
        else:
            ts_y = df_diario["patrimonio_estrategia"].loc[str(y)]
            ytd_dict[y] = ((ts_y.iloc[-1] / ts_y.iloc[0]) - 1.0) * 100.0 if not ts_y.empty else 0.0
            
    tabela_pivot["Ano (YTD)"] = pd.Series(ytd_dict)
    
    fig4, ax4 = plt.subplots(figsize=(12, 7.0), dpi=300)
    
    # Máscara visual para diferenciar os meses do YTD
    cmap_heatmap = sns.diverging_palette(10, 130, s=85, l=45, n=11, as_cmap=True)
    
    sns.heatmap(
        tabela_pivot,
        annot=True,
        fmt=".1f",
        cmap=cmap_heatmap,
        center=0.0,
        cbar_kws={"label": "Retorno Mensal (%)", "shrink": 0.8},
        linewidths=0.7,
        linecolor="white",
        ax=ax4,
        annot_kws={"size": 9.5, "weight": "bold"}
    )
    
    ax4.set_title("Matriz de Retornos Mensais e Anuais da Estratégia BESST Trend-Yield (%)", fontsize=13, fontweight="bold", pad=12, color="#212121")
    ax4.set_ylabel("Ano", fontsize=11, fontweight="semibold")
    ax4.set_xlabel("Mês", fontsize=11, fontweight="semibold")
    
    fig4.tight_layout()
    fig4_path = os.path.join(FIGURAS_DIR, "04_mapa_calor_retornos_mensais.png")
    fig4.savefig(fig4_path, dpi=300)
    plt.close(fig4)
    
    # -------------------------------------------------------------
    # (e) TABELA-RESUMO DAS MÉTRICAS COMO IMAGEM PUBLICATION READY
    # -------------------------------------------------------------
    print("5. Gerando Figura (e): Tabela-Resumo de Métricas (05_tabela_resumo_metricas.png)...")
    
    # Dados da tabela comparativa
    met_is = res_is["metricas"]
    met_oos = res_oos["metricas"]
    
    cagr_ibov = ((b100_ibov.iloc[-1]/100.0) ** (1.0 / (len(df_diario)/252.0))) - 1.0
    cagr_idiv = ((b100_idiv.iloc[-1]/100.0) ** (1.0 / (len(df_diario)/252.0))) - 1.0
    
    dados_tabela = [
        ["Período Analisado", "2012–2026 (14,6 anos)", "2012–2019 (8 anos)", "2020–2026 (6,6 anos)"],
        ["Retorno Acumulado", f"{met['Retorno Acumulado Estratégia (%)']:.1f}% (CDI: {met['Retorno Acumulado CDI (%)']:.1f}%)", f"{met_is['Retorno Acumulado Estratégia (%)']:.1f}% (CDI: {met_is['Retorno Acumulado CDI (%)']:.1f}%)", f"{met_oos['Retorno Acumulado Estratégia (%)']:.1f}% (CDI: {met_oos['Retorno Acumulado CDI (%)']:.1f}%)"],
        ["Retorno Anualizado (CAGR)", f"{met['Retorno Anualizado Estratégia (% a.a.)']:.2f}% a.a.", f"{met_is['Retorno Anualizado Estratégia (% a.a.)']:.2f}% a.a.", f"{met_oos['Retorno Anualizado Estratégia (% a.a.)']:.2f}% a.a."],
        ["Retorno CDI Anualizado", f"{met['Retorno Anualizado CDI (% a.a.)']:.2f}% a.a.", f"{met_is['Retorno Anualizado CDI (% a.a.)']:.2f}% a.a.", f"{met_oos['Retorno Anualizado CDI (% a.a.)']:.2f}% a.a."],
        ["ALPHA Anualizado sobre CDI", f"+{met['ALPHA Anualizado sobre CDI (% a.a.)']:.2f}% a.a.", f"+{met_is['ALPHA Anualizado sobre CDI (% a.a.)']:.2f}% a.a.", f"{met_oos['ALPHA Anualizado sobre CDI (% a.a.)']:.2f}% a.a."],
        ["Volatilidade Anualizada", f"{met['Volatilidade Anualizada (% a.a.)']:.2f}% a.a.", f"{met_is['Volatilidade Anualizada (% a.a.)']:.2f}% a.a.", f"{met_oos['Volatilidade Anualizada (% a.a.)']:.2f}% a.a."],
        ["Índice de Sharpe (Base CDI)", f"{met['Índice de Sharpe (base CDI)']:.3f}", f"{met_is['Índice de Sharpe (base CDI)']:.3f}", f"{met_oos['Índice de Sharpe (base CDI)']:.3f}"],
        ["Drawdown Máximo", f"{met['Drawdown Máximo (%)']:.2f}%", f"{met_is['Drawdown Máximo (%)']:.2f}%", f"{met_oos['Drawdown Máximo (%)']:.2f}%"],
        ["Tempo de Recuperação Máx.", f"{met['Tempo de Recuperação Máximo (dias úteis)']} dias úteis", f"{met_is['Tempo de Recuperação Máximo (dias úteis)']} dias úteis", f"{met_oos['Tempo de Recuperação Máximo (dias úteis)']} dias úteis"],
        ["Turnover Mensal Médio", f"{met['Turnover Mensal Médio (%)']:.1f}% ao mês", f"{met_is['Turnover Mensal Médio (%)']:.1f}% ao mês", f"{met_oos['Turnover Mensal Médio (%)']:.1f}% ao mês"],
        ["Patrimônio Final (R$ 100k)", f"R$ {met['Patrimônio Final (R$)']:,.2f}".replace(",", "."), f"R$ {met_is['Patrimônio Final (R$)']:,.2f}".replace(",", "."), f"R$ {met_oos['Patrimônio Final (R$)']:,.2f}".replace(",", ".")]
    ]
    
    colunas_header = ["Métrica Quantitativa", "Período Completo", "In-Sample (IS)", "Out-of-Sample (OOS)"]
    
    fig5, ax5 = plt.subplots(figsize=(11, 5.6), dpi=300)
    ax5.axis("tight")
    ax5.axis("off")
    
    table = ax5.table(
        cellText=dados_tabela,
        colLabels=colunas_header,
        loc="center",
        cellLoc="center"
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1.1, 1.45)
    
    # Estilização das células
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#CFD8DC")
        if row == 0:
            cell.set_facecolor(COLOR_ESTRATEGIA)
            cell.set_text_props(color="white", weight="bold", fontsize=10.5)
        elif row % 2 == 0:
            cell.set_facecolor("#F5F7FA")
            cell.set_text_props(color="#263238")
        else:
            cell.set_facecolor("#FFFFFF")
            cell.set_text_props(color="#263238")
            
        if col == 0:
            cell.set_text_props(weight="semibold", ha="left")
            
    ax5.set_title("Quadro Comparativo de Performance e Risco: BESST Trend-Yield Otimizado", fontsize=12.5, fontweight="bold", pad=15, color="#212121")
    
    fig5.tight_layout()
    fig5_path = os.path.join(FIGURAS_DIR, "05_tabela_resumo_metricas.png")
    fig5.savefig(fig5_path, dpi=300)
    plt.close(fig5)
    
    print("\n" + "=" * 70)
    print(f"  TODAS AS 5 FIGURAS FORAM GERADAS COM SUCESSO EM: {FIGURAS_DIR}")
    print("=" * 70)
    print(f"  1. {fig1_path}")
    print(f"  2. {fig2_path}")
    print(f"  3. {fig3_path}")
    print(f"  4. {fig4_path}")
    print(f"  5. {fig5_path}")
    print("=" * 70)


if __name__ == "__main__":
    gerar_todas_as_figuras()
