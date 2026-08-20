import sys
import io
import numpy as np
import pandas as pd
from dados import calcular_dpa_3a, calcular_dy_12m, calcular_adtv21

# Configuração segura de encoding UTF-8 no stdout para Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def selecionar_carteira_com_buffer(carteira_atual, ativos_elegiveis_df, n_acoes=6, buffer_turnover=0.15):
    """
    TESTE 3 & VIÉS 1: Seleção de carteira utilizando Banda de Inércia (Turnover Buffer).
    Evita substituições desnecessárias se o dividendo do novo candidato não superar
    o dividendo do ativo atualmente mantido em carteira por uma margem de buffer (ex: 15%).
    """
    if ativos_elegiveis_df.empty:
        return []

    col_dy = 'dy_12m' if 'dy_12m' in ativos_elegiveis_df.columns else ('DY_12M' if 'DY_12M' in ativos_elegiveis_df.columns else ativos_elegiveis_df.columns[-1])

    # 1. Separar mantidos que continuam elegíveis nos filtros
    mantidos = [t for t in carteira_atual if t in ativos_elegiveis_df['ticker'].values]
    
    # 2. Identificar novos candidatos fora da carteira atual
    candidatos_novos = ativos_elegiveis_df[~ativos_elegiveis_df['ticker'].isin(mantidos)].copy()
    
    # 3. Preencher vagas abertas por saídas nos filtros de risco
    vagas = n_acoes - len(mantidos)
    selecionados = mantidos.copy()
    
    if vagas > 0 and not candidatos_novos.empty:
        adicionados = candidatos_novos.head(vagas)['ticker'].tolist()
        selecionados.extend(adicionados)
        candidatos_novos = candidatos_novos.iloc[vagas:]

    # 4. Troca com Banda de Inércia para ativos mantidos
    for i, ativo_atual in enumerate(selecionados):
        if ativo_atual in carteira_atual and not candidatos_novos.empty:
            dy_atual = ativos_elegiveis_df.loc[ativos_elegiveis_df['ticker'] == ativo_atual, col_dy].values[0]
            melhor_novo = candidatos_novos.iloc[0]
            
            if melhor_novo[col_dy] > dy_atual * (1.0 + buffer_turnover):
                selecionados[i] = melhor_novo['ticker']
                candidatos_novos = candidatos_novos.iloc[1:]
                
    return selecionados


def executar_funil_selecao(
    data_t,
    dados_precos,
    dados_proventos,
    universo_t,
    L_trend=200,
    N_acoes=6,
    Fator_Max_SMA=1.20,
    Ativar_Preco_Teto=True,
    min_adtv=1000000.0,
    carteira_atual=None,
    buffer_turnover=0.15,
    filtro_macro_selic=False,
    df_cdi=None,
    df_bench=None
):
    """
    Executa o funil de seleção quantitativa no fechamento do último dia útil do mês t.
    Inclui suporte para Banda de Inércia (buffer_turnover) e Trava Macro SELIC.
    """
    if carteira_atual is None:
        carteira_atual = []
        
    df_close = dados_precos["Close"]
    df_adj_close = dados_precos["Adj Close"]
    
    # VIÉS 4: Trava Macro Selic Alta (CDI 12m >= 12% a.a. E Ibov < SMA200)
    n_acoes_efetivo = N_acoes
    trava_macro_ativada = False
    
    if filtro_macro_selic and df_cdi is not None and df_bench is not None:
        dt_lim_inf = pd.to_datetime(data_t) - pd.DateOffset(years=1)
        s_cdi_12m = df_cdi[(df_cdi.index >= dt_lim_inf) & (df_cdi.index <= pd.to_datetime(data_t))]["cdi_diario"]
        cdi_acum_12m = (1.0 + s_cdi_12m).prod() - 1.0 if not s_cdi_12m.empty else 0.0
        
        ibov_close = df_bench["^BVSP"].loc[:data_t].dropna().iloc[-1] if isinstance(df_bench, pd.DataFrame) and "^BVSP" in df_bench.columns else 0.0
        ibov_sma200 = df_bench["BVSP_SMA200"].loc[:data_t].dropna().iloc[-1] if isinstance(df_bench, pd.DataFrame) and "BVSP_SMA200" in df_bench.columns else 0.0
        
        if cdi_acum_12m >= 0.12 and ibov_close > 0 and ibov_close < ibov_sma200:
            trava_macro_ativada = True
            n_acoes_efetivo = max(1, int(np.floor(N_acoes / 2.0)))
    
    # 1. Filtro de Liquidez (ADTV 21d >= R$ 1.000.000,00)
    tickers_liquidos = calcular_adtv21(dados_precos, data_t, min_adtv=min_adtv)
    tickers_candidatos = [t for t in universo_t if t in tickers_liquidos and t in df_close.columns]
    
    resultados_analise = []
    
    for ticker in tickers_candidatos:
        s_close = df_close[ticker].loc[:data_t].dropna()
        s_adj = df_adj_close[ticker].loc[:data_t].dropna()
        
        if len(s_adj) < L_trend or s_close.empty:
            continue
            
        preco_close_t = s_close.iloc[-1]
        preco_adj_t = s_adj.iloc[-1]
        
        sma_200 = s_adj.iloc[-L_trend:].mean()
        dpa_3a, preco_teto_bazin = calcular_dpa_3a(ticker, dados_proventos, preco_close_t, data_t)
        
        passou_filtro_1 = (preco_close_t <= preco_teto_bazin) if Ativar_Preco_Teto else True
        passou_filtro_2 = (preco_adj_t > sma_200)
        passou_filtro_3 = (preco_adj_t <= Fator_Max_SMA * sma_200) if (Fator_Max_SMA is not None and Fator_Max_SMA > 0) else True
            
        dy_12m = calcular_dy_12m(ticker, dados_proventos, preco_close_t, data_t)
        aprovado_geral = passou_filtro_1 and passou_filtro_2 and passou_filtro_3
        margem_seguranca_pct = ((preco_teto_bazin - preco_close_t) / preco_close_t * 100.0) if np.isfinite(preco_teto_bazin) else 999.0
        
        resultados_analise.append({
            "ticker": ticker,
            "preco_close": preco_close_t,
            "preco_adj": preco_adj_t,
            "sma_200": sma_200,
            "extensao_sma_pct": (preco_adj_t / sma_200 - 1.0) * 100.0,
            "dpa_3a": dpa_3a,
            "preco_teto_bazin": preco_teto_bazin,
            "margem_seguranca_pct": margem_seguranca_pct,
            "dy_12m": dy_12m,
            "passou_bazin": passou_filtro_1,
            "passou_tendencia": passou_filtro_2,
            "passou_sobrecomprado": passou_filtro_3,
            "aprovado": aprovado_geral
        })
        
    df_analise = pd.DataFrame(resultados_analise)
    
    if df_analise.empty:
        return {
            "acoes_selecionadas": [],
            "pesos": {},
            "peso_caixa_cdi": 1.0,
            "tabela_elegiveis": pd.DataFrame(),
            "trava_macro_ativada": trava_macro_ativada
        }
        
    df_aprovados = df_analise[df_analise["aprovado"]].copy()
    df_aprovados.sort_values(by="dy_12m", ascending=False, inplace=True)
    
    if buffer_turnover > 0 and carteira_atual:
        acoes_selecionadas = selecionar_carteira_com_buffer(
            carteira_atual=carteira_atual,
            ativos_elegiveis_df=df_aprovados,
            n_acoes=n_acoes_efetivo,
            buffer_turnover=buffer_turnover
        )
    else:
        acoes_selecionadas = df_aprovados.head(n_acoes_efetivo)["ticker"].tolist()
        
    K = len(acoes_selecionadas)
    fatia_padrao = 1.0 / float(N_acoes) # Fatias dimensionadas pela capacidade total N_acoes
    
    pesos = {}
    for t in acoes_selecionadas:
        pesos[t] = fatia_padrao
        
    peso_caixa_cdi = 1.0 - sum(pesos.values())
    peso_caixa_cdi = max(0.0, float(peso_caixa_cdi))
    
    return {
        "acoes_selecionadas": acoes_selecionadas,
        "pesos": pesos,
        "peso_caixa_cdi": peso_caixa_cdi,
        "tabela_elegiveis": df_analise,
        "trava_macro_ativada": trava_macro_ativada
    }
