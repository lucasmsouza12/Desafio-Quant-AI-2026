# dashboard.py
# Painel Principal Streamlit - BESST Trend-Yield Otimizado
#
# ABA 1: Painel Comparativo Principal (modelo visual original completo)
# ABA 2: Diagnóstico Avançado & Anti-Viés (DSR, Correlação Top3, OOS/IS, Turnover)
#
# Regra UTF-8: todos os CSV lidos/gravados com encoding='utf-8'.

import sys
import io
import os
import itertools
import warnings
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

warnings.filterwarnings("ignore")

# UTF-8 seguro para Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Importações do projeto
from dados import (
    DATA_DIR,
    gerar_universo_historico_besst,
    baixar_cdi_sgs12,
    baixar_dados_yfinance,
    baixar_benchmarks,
)
from backtest import executar_backtest
from graficos import gerar_graficos, gerar_matriz_correlacao
from analise_distribuicao import analisar_distribuicao_sharpes

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BESST Quant AI – Painel Principal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main-header{font-size:2rem;font-weight:800;color:#0052CC;text-align:center;margin-bottom:.2rem}
.sub-header{font-size:1rem;color:#5E6C84;text-align:center;margin-bottom:1.5rem}
.box-ok{background:#E3FCEF;border-left:5px solid #36B37E;padding:12px;border-radius:6px;margin-bottom:10px}
.box-warn{background:#FFF0B3;border-left:5px solid #FFAB00;padding:12px;border-radius:6px;margin-bottom:10px}
.stButton>button{width:100%;background:#0052CC;color:white;font-weight:bold;border-radius:6px;height:48px}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-header'>📈 Estratégia BESST Trend-Yield Otimizado</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Plataforma Quantitativa Institucional – Experimentos, DSR e Mitigação de Vieses</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.header("⚙️ Grade de Parâmetros")

grid_L_trend = st.sidebar.multiselect(
    "Janela Média Móvel (L_trend)",
    options=[100, 150, 200, 250], default=[150, 200],
    help="Dias úteis para a SMA de tendência."
)
grid_N_acoes = st.sidebar.multiselect(
    "Número Alvo de Ações (N_acoes)",
    options=[4, 6, 8, 10], default=[4, 6]
)

FATOR_MAP = {"1.10 (+10%)": 1.10, "1.20 (+20%)": 1.20, "1.30 (+30%)": 1.30, "Desativado": None}
grid_fator_labels = st.sidebar.multiselect(
    "Trava de Sobrecomprado (Max SMA)",
    options=list(FATOR_MAP.keys()), default=["1.20 (+20%)", "Desativado"]
)
grid_Fator_SMA = [FATOR_MAP[l] for l in grid_fator_labels]

grid_bazin_labels = st.sidebar.multiselect(
    "Filtro Preço Teto Bazin",
    options=["Sim (Ativo)", "Não (Desativado)"], default=["Sim (Ativo)", "Não (Desativado)"]
)
grid_Preco_Teto = [True if "Sim" in l else False for l in grid_bazin_labels]

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Controles Anti-Viés")

janela_sel = st.sidebar.selectbox(
    "Janela Temporal",
    ["Completo (2012-2026)", "In-Sample (2012-2019)", "Out-of-Sample (2020-2026)"]
)
JANELA_MAP = {
    "Completo (2012-2026)":      "Completo",
    "In-Sample (2012-2019)":     "IS",
    "Out-of-Sample (2020-2026)": "OOS",
}
janela_execucao = JANELA_MAP[janela_sel]

buffer_turnover = st.sidebar.select_slider(
    "Banda de Inércia (buffer_turnover)",
    options=[0.0, 0.10, 0.15, 0.20], value=0.15,
    help="Margem mínima de DY para substituir ativo mantido na carteira."
)

filtro_macro_selic = st.sidebar.selectbox(
    "Trava Macro Selic",
    ["Desativado", "Ativado"], index=0
) == "Ativado"

grid_Custos_bps = st.sidebar.multiselect(
    "Níveis de Custo Operacional (bps)",
    options=[0, 5, 8, 15], default=[0, 8],
    help="Custos + slippage em pontos-base."
)

total_comb = (len(grid_L_trend) * len(grid_N_acoes) * len(grid_Fator_SMA)
              * len(grid_Preco_Teto) * len(grid_Custos_bps))
st.sidebar.info(f"📊 Total de cenários: **{total_comb}**")

btn_run = st.sidebar.button("🚀 Executar Grade de Experimentos")


# ─────────────────────────────────────────────
# FUNÇÃO AUXILIAR: carregar dados de mercado
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="Baixando dados históricos...")
def _carregar_dados():
    df_universo = gerar_universo_historico_besst("2012-01-01", "2026-07-31")
    df_cdi      = baixar_cdi_sgs12("2012-01-01", "2026-07-31")
    dados_p, dados_pr = baixar_dados_yfinance("2011-01-01", "2026-07-31")
    df_bench    = baixar_benchmarks("2012-01-01", "2026-07-31")
    return {"df_universo": df_universo, "df_cdi": df_cdi,
            "dados_precos": dados_p, "dados_proventos": dados_pr, "df_bench": df_bench}


# ─────────────────────────────────────────────
# EXECUÇÃO DA GRADE
# ─────────────────────────────────────────────
if btn_run or "df_experimentos" not in st.session_state:
    if total_comb == 0:
        st.warning("⚠️ Selecione pelo menos 1 opção em cada parâmetro na barra lateral.")
        st.stop()

    dados = _carregar_dados()
    combinacoes = list(itertools.product(
        grid_L_trend, grid_N_acoes, grid_Fator_SMA, grid_Preco_Teto, grid_Custos_bps
    ))

    prog  = st.progress(0.0)
    info  = st.empty()
    rows  = []
    detalhes = {}
    t0 = datetime.now()

    for idx, (l_tr, n_ac, fat_sma, pt_act, cbps) in enumerate(combinacoes, 1):
        info.text(f"Rodando {idx}/{total_comb}: L={l_tr}, N={n_ac}, "
                  f"SMA={fat_sma}, Bazin={pt_act}, Custo={cbps}bps …")
        id_exp = f"EXP_{idx:03d}"
        try:
            res = executar_backtest(
                data_inicio="2012-01-01", data_fim="2026-07-31",
                L_trend=l_tr, N_acoes=n_ac,
                Fator_Max_SMA=fat_sma, Ativar_Preco_Teto=pt_act,
                slippage_bps=float(cbps * 0.6), custo_bps=float(cbps * 0.4),
                dados_precarregados=dados,
                buffer_turnover=buffer_turnover,
                filtro_macro_selic=filtro_macro_selic,
                janela_execucao=janela_execucao
            )
        except Exception as e:
            st.warning(f"{id_exp} falhou: {e}")
            prog.progress(idx / total_comb)
            continue

        met  = res["metricas"]
        aloc = res["df_alocacao"]
        rows.append({
            "id_exp":                  id_exp,
            "L_trend":                 l_tr,
            "N_acoes":                 n_ac,
            "Fator_Max_SMA":           "Desativado" if fat_sma is None else f"{fat_sma:.2f}",
            "Ativar_Preco_Teto":       pt_act,
            "Custo_Total_bps":         cbps,
            "Retorno_Acumulado_Pct":   met["Retorno Acumulado Estratégia (%)"],
            "Retorno_Acumulado_CDI":   met["Retorno Acumulado CDI (%)"],
            "Retorno_Anualizado_Pct":  met["Retorno Anualizado Estratégia (% a.a.)"],
            "ALPHA_Anualizado_Pct":    met["ALPHA Anualizado sobre CDI (% a.a.)"],
            "Volatilidade_Pct":        met["Volatilidade Anualizada (% a.a.)"],
            "Sharpe_Ratio":            met["Índice de Sharpe (base CDI)"],
            "Sharpe":                  met["Índice de Sharpe (base CDI)"],  # alias DSR
            "Max_Drawdown_Pct":        met["Drawdown Máximo (%)"],
            "Tempo_Recuperacao_Dias":  met["Tempo de Recuperação Máximo (dias úteis)"],
            "Caixa_Medio_Pct":         float(aloc["pct_caixa_cdi"].mean()),
            "Turnover_Mensal_Pct":     met["Turnover Mensal Médio (%)"],
            "Patrimonio_Final":        met["Patrimônio Final (R$)"],
        })
        detalhes[id_exp] = res
        prog.progress(idx / total_comb)

    info.text(f"✅ {len(rows)}/{total_comb} experimentos em {(datetime.now()-t0).seconds}s.")
    df_exp = pd.DataFrame(rows)

    # Salvar CSV UTF-8
    df_exp.to_csv(
        os.path.join(os.path.dirname(__file__), "experimentos.csv"),
        index=False, encoding="utf-8"
    )
    st.session_state["df_experimentos"] = df_exp
    st.session_state["detalhes"]        = detalhes
    st.session_state["dados_mercado"]   = dados

df_exp   = st.session_state.get("df_experimentos", pd.DataFrame())
detalhes = st.session_state.get("detalhes",        {})
dados    = st.session_state.get("dados_mercado",    None)

if df_exp.empty:
    st.info("Clique em **🚀 Executar Grade de Experimentos** para iniciar.")
    st.stop()

# ─────────────────────────────────────────────
# ABAS
# ─────────────────────────────────────────────
aba1, aba2 = st.tabs([
    "📊 ABA 1 – Painel Comparativo Principal",
    "🧪 ABA 2 – Diagnóstico Avançado & Anti-Viés",
])

# ═══════════════════════════════════════════
# ABA 1 – PAINEL COMPARATIVO PRINCIPAL
# ═══════════════════════════════════════════
with aba1:
    st.markdown("### 🏆 Visão Geral dos Experimentos de Backtest")

    # KPI cards
    top_sh = df_exp.sort_values("Sharpe_Ratio", ascending=False).iloc[0]
    top_al = df_exp.sort_values("ALPHA_Anualizado_Pct", ascending=False).iloc[0]
    top_dd = df_exp.sort_values("Max_Drawdown_Pct", ascending=False).iloc[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Melhor Retorno Acumulado",
              f"{top_al['Retorno_Acumulado_Pct']:.1f}%", f"{top_al['id_exp']}")
    k2.metric("Melhor Sharpe",
              f"{top_sh['Sharpe_Ratio']:.2f}",          f"{top_sh['id_exp']}")
    k3.metric("Menor Drawdown",
              f"{top_dd['Max_Drawdown_Pct']:.2f}%",     f"{top_dd['id_exp']}")
    k4.metric("Maior ALPHA vs CDI",
              f"+{top_al['ALPHA_Anualizado_Pct']:.2f}% a.a.", f"{top_al['id_exp']}")

    st.markdown("---")

    # ── Gráfico de Linhas: Patrimônio e Alpha acumulado ──
    st.markdown("#### 📈 Evolução Patrimonial e Alpha Acumulado – Top 3 vs CDI")
    top3_ids = df_exp.sort_values("Sharpe_Ratio", ascending=False).head(3)["id_exp"].tolist()
    CORES = ["#0052CC", "#FFAB00", "#36B37E"]

    fig_line, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, dpi=150)
    ref = detalhes[top3_ids[0]]["df_diario"]
    b100_cdi = ref["patrimonio_cdi"] / ref["patrimonio_cdi"].iloc[0] * 100.0
    ax1.plot(ref.index, b100_cdi, "--", color="black", lw=1.5, label="CDI (Benchmark)")
    for i, tid in enumerate(top3_ids):
        df_d = detalhes[tid]["df_diario"]
        b100 = df_d["patrimonio_estrategia"] / df_d["patrimonio_estrategia"].iloc[0] * 100.0
        ax1.plot(df_d.index, b100, color=CORES[i], lw=2, label=f"#{i+1} {tid}")
        ax2.plot(df_d.index, b100 - b100_cdi, color=CORES[i], lw=1.5, label=f"Alpha {tid}")
    ax1.set_ylabel("Patrimônio (Base 100)"); ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, ls=":", alpha=.5)
    ax2.set_ylabel("Alpha (p.p.)"); ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, ls=":", alpha=.5); ax2.axhline(0, color="black", lw=.8)
    fig_line.tight_layout()
    st.pyplot(fig_line)

    st.markdown("---")
    col_g1, col_g2 = st.columns(2)

    # ── Dispersão Risco x Retorno ──
    with col_g1:
        st.markdown("#### 🎯 Risco × Retorno (Drawdown × Sharpe)")
        fig_sc, ax_sc = plt.subplots(figsize=(6, 4.5), dpi=150)
        sc = ax_sc.scatter(
            df_exp["Max_Drawdown_Pct"], df_exp["Sharpe_Ratio"],
            c=df_exp["Custo_Total_bps"], cmap="viridis", s=70,
            alpha=.85, edgecolors="black", lw=.4
        )
        plt.colorbar(sc, ax=ax_sc, label="Custos (bps)")
        ax_sc.set_xlabel("Drawdown Máximo (%)"); ax_sc.set_ylabel("Sharpe")
        ax_sc.grid(True, ls=":", alpha=.5)
        fig_sc.tight_layout()
        st.pyplot(fig_sc)

    # ── Boxplot Custo x Sharpe ──
    with col_g2:
        st.markdown("#### 💸 Impacto dos Custos Operacionais no Sharpe")
        fig_bx, ax_bx = plt.subplots(figsize=(6, 4.5), dpi=150)
        sns.boxplot(data=df_exp, x="Custo_Total_bps", y="Sharpe_Ratio",
                    palette="Blues", ax=ax_bx)
        sns.stripplot(data=df_exp, x="Custo_Total_bps", y="Sharpe_Ratio",
                      color="red", alpha=.45, jitter=.2, ax=ax_bx)
        ax_bx.set_xlabel("Custos (bps)"); ax_bx.set_ylabel("Sharpe")
        ax_bx.grid(True, ls=":", alpha=.5)
        fig_bx.tight_layout()
        st.pyplot(fig_bx)

    st.markdown("---")
    st.markdown("#### 📋 Tabela Ranqueada dos Experimentos")
    colunas_exibir = [
        "id_exp","L_trend","N_acoes","Fator_Max_SMA","Ativar_Preco_Teto",
        "Custo_Total_bps","Retorno_Acumulado_Pct","ALPHA_Anualizado_Pct",
        "Sharpe_Ratio","Max_Drawdown_Pct","Turnover_Mensal_Pct",
    ]
    st.dataframe(
        df_exp[colunas_exibir].sort_values("Sharpe_Ratio", ascending=False).style.format({
            "Retorno_Acumulado_Pct":  "{:.1f}%",
            "ALPHA_Anualizado_Pct":   "{:+.2f}%",
            "Sharpe_Ratio":           "{:.3f}",
            "Max_Drawdown_Pct":       "{:.2f}%",
            "Turnover_Mensal_Pct":    "{:.1f}%",
        }),
        use_container_width=True
    )


# ═══════════════════════════════════════════
# ABA 2 – DIAGNÓSTICO AVANÇADO & ANTI-VIÉS
# ═══════════════════════════════════════════
with aba2:
    st.markdown("### 🧪 Diagnóstico Avançado & Mitigação de Vieses Quantitativos")

    # ── 1. Deflated Sharpe Ratio (DSR) ──
    st.markdown("#### 1. Deflated Sharpe Ratio – López de Prado")
    caminho_csv_exp = os.path.join(os.path.dirname(__file__), "experimentos.csv")

    if os.path.exists(caminho_csv_exp):
        try:
            dsr = analisar_distribuicao_sharpes(caminho_csv_exp)
            cd1, cd2, cd3, cd4, cd5 = st.columns(5)
            cd1.metric("Sharpe Máximo (SR_max)",      f"{dsr['sharpe_max']:.4f}")
            cd2.metric("Limiar de Ruído E[max(SR)]",  f"{dsr['expected_max_sharpe']:.4f}")
            cd3.metric("Desvio Padrão (σ_SR)",        f"{dsr['sharpe_std']:.4f}")
            cd4.metric("Assimetria (Skewness)",       f"{dsr['sharpe_skew']:.4f}")
            cd5.metric("Curtose (Kurtosis)",          f"{dsr['sharpe_kurt']:.4f}")
            if dsr["superou_ruido"]:
                st.markdown(
                    f"<div class='box-ok'>✅ <b>VEREDITO DSR</b>: SR_max "
                    f"({dsr['sharpe_max']:.4f}) superou o limiar de acerto aleatório "
                    f"({dsr['expected_max_sharpe']:.4f}). A estratégia demonstra ALPHA genuíno!</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='box-warn'>⚠️ <b>VEREDITO DSR</b>: SR_max não superou o limiar "
                    f"de ruído ({dsr['expected_max_sharpe']:.4f}). Risco de Overfitting / Data Mining.</div>",
                    unsafe_allow_html=True
                )
        except Exception as e:
            st.warning(f"DSR não calculado: {e}")
    else:
        st.info("Rode a grade de experimentos para habilitar a análise DSR.")

    st.markdown("---")
    col_l, col_r = st.columns(2)

    # ── 2. Matriz de Correlação Top 3 vs CDI ──
    with col_l:
        st.markdown("#### 2. Correlação dos Retornos Mensais – Top 3 vs CDI")
        if len(top3_ids) >= 1 and dados is not None:
            dict_ret = {}
            last_res = None
            for i, tid in enumerate(top3_ids):
                if tid in detalhes:
                    r = detalhes[tid]
                    dict_ret[f"Top{i+1}_{tid}"] = r["df_retornos_mensais"]["Estratégia"]
                    last_res = r
            if last_res:
                dict_ret["CDI"] = last_res["df_retornos_mensais"]["CDI"]
                if "Ibovespa" in last_res["df_retornos_mensais"]:
                    dict_ret["Ibovespa"] = last_res["df_retornos_mensais"]["Ibovespa"]

            df_ret_m = pd.DataFrame(dict_ret).dropna()
            if not df_ret_m.empty:
                fig_m = gerar_matriz_correlacao(df_ret_m, salvar_disco=True)
                st.pyplot(fig_m)
            else:
                st.info("Dados insuficientes para a matriz de correlação.")
        else:
            st.info("Execute a grade para gerar a matriz.")

    # ── 3. Retenção OOS vs IS ──
    with col_r:
        st.markdown("#### 3. Retenção do Sharpe Out-of-Sample (OOS vs IS)")
        # Usar o melhor experimento como referência
        top_row = df_exp.sort_values("Sharpe_Ratio", ascending=False).iloc[0]
        best_L  = int(top_row["L_trend"])
        best_N  = int(top_row["N_acoes"])
        best_fat = None if top_row["Fator_Max_SMA"] == "Desativado" else float(top_row["Fator_Max_SMA"])
        best_baz = bool(top_row["Ativar_Preco_Teto"])

        if dados is not None:
            with st.spinner("Calculando IS vs OOS..."):
                try:
                    res_is  = executar_backtest(
                        L_trend=best_L, N_acoes=best_N,
                        Fator_Max_SMA=best_fat, Ativar_Preco_Teto=best_baz,
                        janela_execucao="IS", dados_precarregados=dados
                    )
                    res_oos = executar_backtest(
                        L_trend=best_L, N_acoes=best_N,
                        Fator_Max_SMA=best_fat, Ativar_Preco_Teto=best_baz,
                        janela_execucao="OOS", dados_precarregados=dados
                    )
                    sr_is  = res_is["metricas"]["Índice de Sharpe (base CDI)"]
                    sr_oos = res_oos["metricas"]["Índice de Sharpe (base CDI)"]
                    ret_pct = (sr_oos / sr_is * 100.0) if sr_is != 0 else 0.0

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Sharpe IS (2012-2019)",  f"{sr_is:.2f}")
                    c2.metric("Sharpe OOS (2020-2026)", f"{sr_oos:.2f}")
                    c3.metric("Retenção OOS/IS",        f"{ret_pct:.1f}%",
                              help="Meta institucional ≥ 70%")

                    if ret_pct >= 70.0:
                        st.markdown(
                            "<div class='box-ok'>✅ <b>OOS APROVADO</b>: Retenção de Sharpe ≥ 70%.</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f"<div class='box-warn'>⚠️ <b>ALERTA OOS</b>: Retenção de {ret_pct:.1f}% abaixo "
                            f"da meta de 70%.</div>", unsafe_allow_html=True
                        )
                except Exception as e:
                    st.warning(f"Erro no cálculo IS/OOS: {e}")
        else:
            st.info("Dados de mercado não disponíveis.")

    st.markdown("---")

    # ── 4. Impacto da Banda de Inércia ──
    st.markdown("#### 4. Impacto da Banda de Inércia (Turnover Buffer)")
    if dados is not None:
        with st.spinner("Comparando turnover com e sem buffer..."):
            try:
                res_com = executar_backtest(
                    L_trend=best_L, N_acoes=best_N,
                    Fator_Max_SMA=best_fat, Ativar_Preco_Teto=best_baz,
                    buffer_turnover=buffer_turnover, dados_precarregados=dados
                )
                res_sem = executar_backtest(
                    L_trend=best_L, N_acoes=best_N,
                    Fator_Max_SMA=best_fat, Ativar_Preco_Teto=best_baz,
                    buffer_turnover=0.0, dados_precarregados=dados
                )
                to_com    = res_com["metricas"]["Turnover Mensal Médio (%)"]
                to_sem    = res_sem["metricas"]["Turnover Mensal Médio (%)"]
                alpha_com = res_com["metricas"]["ALPHA Anualizado sobre CDI (% a.a.)"]
                alpha_sem = res_sem["metricas"]["ALPHA Anualizado sobre CDI (% a.a.)"]

                t1, t2, t3, t4 = st.columns(4)
                t1.metric("Turnover COM Buffer",       f"{to_com:.1f}%")
                t2.metric("Turnover SEM Buffer",       f"{to_sem:.1f}%",
                          f"Δ {to_sem - to_com:+.1f} p.p.")
                t3.metric("ALPHA Líquido COM Buffer",  f"+{alpha_com:.2f}% a.a.")
                t4.metric("ALPHA Líquido SEM Buffer",  f"+{alpha_sem:.2f}% a.a.",
                          f"Δ {alpha_sem - alpha_com:+.2f} p.p.")

                reducao_pct = (to_sem - to_com) / max(to_sem, 0.01) * 100.0
                st.markdown(
                    f"<div class='box-ok'>💡 A Banda de Inércia <b>({buffer_turnover*100:.0f}%)</b> "
                    f"reduziu o giro mensal médio de <b>{to_sem:.1f}%</b> para "
                    f"<b>{to_com:.1f}%</b> (redução de {reducao_pct:.0f}%), "
                    f"gerando ganho de Alpha líquido de "
                    f"<b>{alpha_com - alpha_sem:+.2f}% a.a.</b></div>",
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.warning(f"Erro no cálculo do buffer: {e}")
    else:
        st.info("Dados de mercado não disponíveis.")
