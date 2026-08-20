# graficos.py
# Módulo de Geração e Salvamento de Gráficos Financeiros
# Produz visualizações para o relatório e para o dashboard em /graficos

import sys
import io
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np

# Configuração segura de encoding UTF-8 no stdout para Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Diretório para salvar imagens PNG
GRAFICOS_DIR = os.path.join(os.path.dirname(__file__), "graficos")
os.makedirs(GRAFICOS_DIR, exist_ok=True)

# Estilo gráfico moderno
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
COLOR_ESTRATEGIA = "#0052CC" # Azul vibrante
COLOR_CDI = "#36B37E"        # Verde esmeralda
COLOR_DRAWDOWN = "#FF5630"   # Vermelho coral
COLOR_CAIXA = "#FFAB00"      # Amarelo/Dourado


def gerar_graficos(resultados, salvar_disco=True):
    """
    Gera todos os 6 gráficos solicitados e salva em PNG na pasta /graficos.
    
    Retorna um dicionário com os objetos de figura do Matplotlib (fig1..fig6).
    """
    df_diario = resultados["df_diario"]
    df_alocacao = resultados["df_alocacao"]
    df_bench = resultados.get("df_bench", pd.DataFrame())
    tabela_ultimo_rebalance = resultados.get("tabela_ultimo_rebalance", pd.DataFrame())
    
    figuras = {}
    
    # ---------------------------------------------------------
    # (a) Curva de Patrimônio (Estratégia vs CDI vs IDIV/IBOV)
    # ---------------------------------------------------------
    fig1, ax1 = plt.subplots(figsize=(10, 5), dpi=300)
    
    # Normalizar para base 100 no início
    base100_est = (df_diario["patrimonio_estrategia"] / df_diario["patrimonio_estrategia"].iloc[0]) * 100.0
    base100_cdi = (df_diario["patrimonio_cdi"] / df_diario["patrimonio_cdi"].iloc[0]) * 100.0
    
    ax1.plot(df_diario.index, base100_est, label="Estratégia BESST Trend-Yield", color=COLOR_ESTRATEGIA, linewidth=2)
    ax1.plot(df_diario.index, base100_cdi, label="Benchmark CDI", color=COLOR_CDI, linewidth=1.8, linestyle="--")
    
    if isinstance(df_bench, pd.DataFrame) and not df_bench.empty:
        if "IDIV.SA" in df_bench.columns:
            s_idiv = df_bench["IDIV.SA"].reindex(df_diario.index).ffill().bfill()
            if not s_idiv.empty and s_idiv.iloc[0] > 0:
                base100_idiv = (s_idiv / s_idiv.iloc[0]) * 100.0
                ax1.plot(df_diario.index, base100_idiv, label="Índice IDIV", color="#6554C0", linewidth=1.2, alpha=0.7, linestyle=":")
                
    ax1.set_title("Curva de Patrimônio Acumulado (Base 100)", fontsize=14, fontweight="bold", pad=12)
    ax1.set_ylabel("Evolução do Capital (Base 100)", fontsize=11)
    ax1.set_xlabel("Data", fontsize=11)
    ax1.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9)
    ax1.grid(True, linestyle=":", alpha=0.6)
    fig1.tight_layout()
    
    if salvar_disco:
        fig1.savefig(os.path.join(GRAFICOS_DIR, "curva_patrimonio.png"), dpi=300)
    figuras["curva_patrimonio"] = fig1
    
    # ---------------------------------------------------------
    # (b) ALPHA Acumulado sobre o CDI ao longo do tempo
    # ---------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(10, 4), dpi=300)
    
    alpha_acumulado_pct = (base100_est - base100_cdi)
    
    ax2.plot(df_diario.index, alpha_acumulado_pct, color="#008DA6", linewidth=1.8, label="Alpha em Relação ao CDI (%)")
    ax2.axhline(0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax2.fill_between(df_diario.index, alpha_acumulado_pct, 0, where=(alpha_acumulado_pct >= 0), color="#008DA6", alpha=0.2)
    ax2.fill_between(df_diario.index, alpha_acumulado_pct, 0, where=(alpha_acumulado_pct < 0), color=COLOR_DRAWDOWN, alpha=0.2)
    
    ax2.set_title("ALPHA Acumulado sobre o CDI ao Longo do Tempo (% P.P.)", fontsize=14, fontweight="bold", pad=12)
    ax2.set_ylabel("Alpha Acumulado (%)", fontsize=11)
    ax2.set_xlabel("Data", fontsize=11)
    ax2.legend(loc="upper left", frameon=True)
    ax2.grid(True, linestyle=":", alpha=0.6)
    fig2.tight_layout()
    
    if salvar_disco:
        fig2.savefig(os.path.join(GRAFICOS_DIR, "alpha_acumulado.png"), dpi=300)
    figuras["alpha_acumulado"] = fig2
    
    # ---------------------------------------------------------
    # (c) Gráfico de Drawdown / Underwater
    # ---------------------------------------------------------
    fig3, ax3 = plt.subplots(figsize=(10, 4), dpi=300)
    
    drawdown_pct = df_diario["drawdown"] * 100.0
    
    ax3.plot(df_diario.index, drawdown_pct, color=COLOR_DRAWDOWN, linewidth=1.2)
    ax3.fill_between(df_diario.index, drawdown_pct, 0, color=COLOR_DRAWDOWN, alpha=0.35)
    
    ax3.set_title("Gráfico de Drawdown (Underwater Period)", fontsize=14, fontweight="bold", pad=12)
    ax3.set_ylabel("Queda do Topo (%)", fontsize=11)
    ax3.set_xlabel("Data", fontsize=11)
    ax3.grid(True, linestyle=":", alpha=0.6)
    fig3.tight_layout()
    
    if salvar_disco:
        fig3.savefig(os.path.join(GRAFICOS_DIR, "drawdown.png"), dpi=300)
    figuras["drawdown"] = fig3
    
    # ---------------------------------------------------------
    # (d) Mapa de Calor dos Retornos Mensais (Ano x Mês)
    # ---------------------------------------------------------
    fig4, ax4 = plt.subplots(figsize=(10, 5), dpi=300)
    
    df_m = df_diario["patrimonio_estrategia"].resample("ME").last()
    ret_mensal = df_m.pct_change() * 100.0
    
    df_ret_m = pd.DataFrame({
        "Ano": ret_mensal.index.year,
        "Mes": ret_mensal.index.month,
        "Retorno": ret_mensal.values
    }).dropna()
    
    piv = df_ret_m.pivot(index="Ano", columns="Mes", values="Retorno")
    piv.columns = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    
    sns.heatmap(
        piv,
        annot=True,
        fmt=".1f",
        cmap="RdYlGn",
        center=0,
        cbar=True,
        ax=ax4,
        linewidths=0.5,
        annot_kws={"size": 9}
    )
    
    ax4.set_title("Mapa de Calor de Retornos Mensais (%)", fontsize=14, fontweight="bold", pad=12)
    ax4.set_ylabel("Ano", fontsize=11)
    ax4.set_xlabel("Mês", fontsize=11)
    fig4.tight_layout()
    
    if salvar_disco:
        fig4.savefig(os.path.join(GRAFICOS_DIR, "heatmap_retornos.png"), dpi=300)
    figuras["heatmap_retornos"] = fig4
    
    # ---------------------------------------------------------
    # (e) Alocação Histórica (% Ações BESST vs % Caixa/CDI)
    # ---------------------------------------------------------
    fig5, ax5 = plt.subplots(figsize=(10, 4), dpi=300)
    
    ax5.stackplot(
        df_alocacao.index,
        df_alocacao["pct_acoes"],
        df_alocacao["pct_caixa_cdi"],
        labels=["Ações BESST", "Caixa / CDI (Renda Fixa)"],
        colors=[COLOR_ESTRATEGIA, COLOR_CAIXA],
        alpha=0.85
    )
    
    ax5.set_title("Alocação Histórica Tática da Carteira (% Ações vs % Caixa CDI)", fontsize=14, fontweight="bold", pad=12)
    ax5.set_ylabel("Alocação (% Patrimonio)", fontsize=11)
    ax5.set_xlabel("Data", fontsize=11)
    ax5.set_ylim(0, 100)
    ax5.legend(loc="lower left", frameon=True, facecolor="white", framealpha=0.9)
    ax5.grid(True, linestyle=":", alpha=0.6)
    fig5.tight_layout()
    
    if salvar_disco:
        fig5.savefig(os.path.join(GRAFICOS_DIR, "alocacao_historica.png"), dpi=300)
    figuras["alocacao_historica"] = fig5
    
    # ---------------------------------------------------------
    # (f) Composição da Carteira no Último Rebalance (Margem de Segurança Bazin)
    # ---------------------------------------------------------
    fig6, ax6 = plt.subplots(figsize=(10, 4.5), dpi=300)
    
    if isinstance(tabela_ultimo_rebalance, pd.DataFrame) and not tabela_ultimo_rebalance.empty:
        df_aprov = tabela_ultimo_rebalance[tabela_ultimo_rebalance["aprovado"]].copy()
        if df_aprov.empty:
            df_aprov = tabela_ultimo_rebalance.head(6).copy()
            
        df_aprov["margem_plot"] = df_aprov["margem_seguranca_pct"].apply(lambda x: min(x, 150.0) if np.isfinite(x) else 150.0)
        
        tickers = df_aprov["ticker"].tolist()
        margens = df_aprov["margem_plot"].tolist()
        precos_close = df_aprov["preco_close"].tolist()
        precos_teto = df_aprov["preco_teto_bazin"].tolist()
        
        x = np.arange(len(tickers))
        width = 0.35
        
        rects1 = ax6.bar(x - width/2, precos_close, width, label="Preço de Fechamento", color=COLOR_ESTRATEGIA)
        rects2 = ax6.bar(x + width/2, [p if np.isfinite(p) else 0 for p in precos_teto], width, label="Preço Teto Bazin", color=COLOR_CDI)
        
        ax6.set_ylabel("Preço (R$)", fontsize=11)
        ax6.set_title("Margem de Segurança (Preço vs Preço Teto Bazin) no Último Rebalance", fontsize=14, fontweight="bold", pad=12)
        ax6.set_xticks(x)
        ax6.set_xticklabels(tickers, rotation=25)
        ax6.legend(loc="upper left")
        ax6.grid(True, linestyle=":", alpha=0.6)
    else:
        ax6.text(0.5, 0.5, "100% Alocado em Caixa (CDI) no último rebalance", fontsize=12, ha="center")
        ax6.set_title("Composição da Carteira no Último Rebalance", fontsize=14, fontweight="bold")
        
    fig6.tight_layout()
    
    if salvar_disco:
        fig6.savefig(os.path.join(GRAFICOS_DIR, "composicao_carteira.png"), dpi=300)
    figuras["composicao_carteira"] = fig6
    
    return figuras


def gerar_matriz_correlacao(df_retornos, salvar_disco=True):
    """
    TESTE 2: Gera e salva em graficos/matriz_correlacao_top3.png a matriz de correlação
    entre os retornos mensais das melhores parametrizações e a taxa CDI.
    """
    if df_retornos.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "Sem dados suficientes para correlação", ha="center")
        return fig
        
    df_corr = df_retornos.corr()
    
    fig_corr, ax_corr = plt.subplots(figsize=(8, 6), dpi=300)
    sns.heatmap(
        df_corr,
        annot=True,
        fmt=".3f",
        cmap="coolwarm",
        vmin=-1.0,
        vmax=1.0,
        center=0,
        linewidths=1.0,
        cbar=True,
        ax=ax_corr,
        annot_kws={"size": 10, "weight": "bold"}
    )
    
    ax_corr.set_title("Matriz de Correlação dos Retornos Mensais (Top 3 vs CDI)", fontsize=13, fontweight="bold", pad=12)
    fig_corr.tight_layout()
    
    if salvar_disco:
        fig_corr.savefig(os.path.join(GRAFICOS_DIR, "matriz_correlacao_top3.png"), dpi=300)
        
    return fig_corr

