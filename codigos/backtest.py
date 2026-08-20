# backtest.py
# Engine Principal do Backtest com Loop Diário Otimizado
# Executa a simulação dia a dia com atualização do CDI, crédito de proventos no dia de pagamento,
# rebalanceamento mensal no 1º dia útil (com VWAP proxy e fallback), slippage dinâmico,
# banda de inércia (buffer_turnover), trava macro SELIC e cálculo de métricas quantitativas completas.

import sys
import io
import os
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
    gerar_universo_historico_besst,
    baixar_cdi_sgs12,
    baixar_dados_yfinance,
    baixar_benchmarks
)
from estrategia import executar_funil_selecao


def executar_backtest(
    data_inicio="2012-01-01",
    data_fim="2026-07-31",
    L_trend=200,
    N_acoes=6,
    Fator_Max_SMA=1.20,
    Ativar_Preco_Teto=True,
    slippage_bps=5.0, # 5 bps = 0.05%
    custo_bps=3.0,    # 3 bps = 0.03%
    patrimonio_inicial=100000.0,
    forcar_redownload=False,
    dados_precarregados=None,
    buffer_turnover=0.15,
    filtro_macro_selic=False,
    modo_execucao="VWAP_Proxy", # "VWAP_Proxy" ou "Open"
    usar_slippage_dinamico=True,
    janela_execucao="Completo"  # "Completo", "IS" (In-Sample), "OOS" (Out-of-Sample)
):
    """
    Roda a simulação completa do backtest diário da estratégia BESST Trend-Yield Otimizado.
    Suporta segmentação In-Sample (IS) / Out-of-Sample (OOS), Slippage Dinâmico, VWAP proxy e Banda de Inércia.
    """
    # VIÉS 2: Segmentação de Janela Temporal
    if janela_execucao == "IS":
        data_inicio = "2012-01-01"
        data_fim = "2019-12-31"
    elif janela_execucao == "OOS":
        data_inicio = "2020-01-01"
        data_fim = "2026-07-31"

    taxa_slippage_padrao = slippage_bps / 10000.0
    taxa_custo = custo_bps / 10000.0
    
    # 1. Carregar universo histórico BESST e dados de mercado
    if dados_precarregados is not None:
        df_universo = dados_precarregados["df_universo"]
        df_cdi = dados_precarregados["df_cdi"]
        dados_precos = dados_precarregados["dados_precos"]
        dados_proventos = dados_precarregados["dados_proventos"]
        df_bench = dados_precarregados.get("df_bench", pd.DataFrame())
    else:
        df_universo = gerar_universo_historico_besst(data_inicio, data_fim)
        df_cdi = baixar_cdi_sgs12(data_inicio, data_fim)
        dados_precos, dados_proventos = baixar_dados_yfinance(
            data_inicio="2011-01-01",
            data_fim=data_fim,
            forcar_download=forcar_redownload
        )
        df_bench = baixar_benchmarks(data_inicio, data_fim)
    
    df_close = dados_precos["Close"]
    df_open = dados_precos["Open"]
    df_vwap = dados_precos.get("VWAP", df_open)
    df_vol21d = dados_precos.get("Vol_21d", None)
    
    # Datas de negociação no período do backtest
    datas_backtest = df_close.index[(df_close.index >= pd.to_datetime(data_inicio)) & (df_close.index <= pd.to_datetime(data_fim))]
    if len(datas_backtest) < 20:
        raise ValueError("Número de dias úteis no período selecionado é insuficiente para o backtest.")
        
    # Identificar o último dia útil de cada mês (Datas de Sinal t) e 1º dia útil de t+1 (Execução)
    df_datas = pd.DataFrame(index=datas_backtest)
    df_datas["ano_mes"] = df_datas.index.strftime("%Y-%m")
    
    ultimos_dias_mes = df_datas.groupby("ano_mes").apply(lambda x: x.index[-1]).tolist()
    primeiros_dias_mes = df_datas.groupby("ano_mes").apply(lambda x: x.index[0]).tolist()
    
    dias_rebalance_map = {}
    for i in range(len(ultimos_dias_mes) - 1):
        dt_sinal = ultimos_dias_mes[i]
        dt_exec = primeiros_dias_mes[i+1]
        dias_rebalance_map[dt_exec] = dt_sinal
        
    saldo_caixa = float(patrimonio_inicial)
    posicoes_acoes = {} # {ticker: qtd_cotas}
    
    registros_diarios = []
    registros_alocacao = []
    historico_rebalanceamento = []
    tabela_ultimo_rebalance = pd.DataFrame()
    turnovers_mensais = []
    
    patrimonio_cdi = float(patrimonio_inicial)
    
    # Dicionário pré-processado de proventos por data de pagamento
    eventos_proventos_por_data = {}
    for ticker, s_divs in dados_proventos.items():
        if isinstance(s_divs, pd.Series) and not s_divs.empty:
            for dt_pag, val in s_divs.items():
                dt_p = pd.to_datetime(dt_pag)
                if dt_p not in eventos_proventos_por_data:
                    eventos_proventos_por_data[dt_p] = []
                eventos_proventos_por_data[dt_p].append((ticker, float(val)))
                
    for i, data_d in enumerate(datas_backtest):
        # A. Atualizar CDI diário
        taxa_cdi_dia = 0.0
        if data_d in df_cdi.index:
            taxa_cdi_dia = float(df_cdi.loc[data_d, "cdi_diario"])
            
        saldo_caixa *= (1.0 + taxa_cdi_dia)
        patrimonio_cdi *= (1.0 + taxa_cdi_dia)
        
        # B. Creditar proventos na DATA DE PAGAMENTO
        if data_d in eventos_proventos_por_data:
            for ticker, val_div in eventos_proventos_por_data[data_d]:
                if ticker in posicoes_acoes and posicoes_acoes[ticker] > 0:
                    valor_recebido = posicoes_acoes[ticker] * val_div
                    saldo_caixa += valor_recebido
                    
        # C. Tratar deslistagem/fusão de ativos em carteira no meio do mês
        tickers_para_remover = []
        for ticker, qtd in posicoes_acoes.items():
            if qtd > 0:
                prc_close = df_close.loc[data_d, ticker] if ticker in df_close.columns else np.nan
                if pd.isna(prc_close) or prc_close <= 0:
                    s_hist = df_close[ticker].loc[:data_d].dropna()
                    if not s_hist.empty:
                        prc_liq = s_hist.iloc[-1]
                        valor_resgate = qtd * prc_liq * (1.0 - taxa_slippage_padrao - taxa_custo)
                        saldo_caixa += valor_resgate
                        tickers_para_remover.append(ticker)
        for t_rem in tickers_para_remover:
            posicoes_acoes.pop(t_rem, None)
            
        # D. Avaliar Rebalanceamento no 1º dia útil do mês (data_d) com base no sinal de t
        if data_d in dias_rebalance_map:
            dt_sinal_t = dias_rebalance_map[data_d]
            str_mes_t = dt_sinal_t.strftime("%Y-%m")
            
            universo_t = df_universo[
                (df_universo["mes"] == str_mes_t) & (df_universo["status_liquidez"] == "Ativo")
            ]["ticker"].tolist()
            
            if not universo_t:
                universo_t = df_universo["ticker"].unique().tolist()
                
            # Executar Funil Quantitativo com Banda de Inércia e Trava Macro SELIC
            carteira_atual_lista = list(posicoes_acoes.keys())
            
            resultado_funil = executar_funil_selecao(
                data_t=dt_sinal_t,
                dados_precos=dados_precos,
                dados_proventos=dados_proventos,
                universo_t=universo_t,
                L_trend=L_trend,
                N_acoes=N_acoes,
                Fator_Max_SMA=Fator_Max_SMA,
                Ativar_Preco_Teto=Ativar_Preco_Teto,
                carteira_atual=carteira_atual_lista,
                buffer_turnover=buffer_turnover,
                filtro_macro_selic=filtro_macro_selic,
                df_cdi=df_cdi,
                df_bench=df_bench
            )
            
            pesos_alvo = resultado_funil["pesos"]
            peso_caixa_alvo = resultado_funil["peso_caixa_cdi"]
            tabela_ultimo_rebalance = resultado_funil["tabela_elegiveis"]
            
            # VIÉS 3: Preço de Execução ao preço VWAP Proxy de t+1 (com fallback)
            valor_acoes_exec = 0.0
            precos_execucao = {}
            slippage_efetivo_map = {}
            
            for ticker in set(list(posicoes_acoes.keys()) + list(pesos_alvo.keys())):
                if modo_execucao == "VWAP_Proxy" and "VWAP" in dados_precos and ticker in dados_precos["VWAP"].columns:
                    prc_exec = dados_precos["VWAP"].loc[data_d, ticker]
                else:
                    prc_exec = df_open.loc[data_d, ticker] if ticker in df_open.columns else np.nan
                    
                if pd.isna(prc_exec) or prc_exec <= 0:
                    prc_exec = df_close.loc[data_d, ticker] if ticker in df_close.columns else np.nan
                if pd.isna(prc_exec) or prc_exec <= 0:
                    s_valid = df_close[ticker].loc[:data_d].dropna()
                    prc_exec = s_valid.iloc[-1] if not s_valid.empty else 0.0
                    
                precos_execucao[ticker] = float(prc_exec)
                
                # VIÉS 1: Slippage Dinâmico = max(0.0005, 0.10 * vol_21d_t)
                if usar_slippage_dinamico and df_vol21d is not None and ticker in df_vol21d.columns:
                    v21 = df_vol21d.loc[dt_sinal_t, ticker] if dt_sinal_t in df_vol21d.index else np.nan
                    if not pd.isna(v21) and v21 > 0:
                        slippage_efetivo_map[ticker] = max(0.0005, float(0.10 * v21))
                    else:
                        slippage_efetivo_map[ticker] = taxa_slippage_padrao
                else:
                    slippage_efetivo_map[ticker] = taxa_slippage_padrao
                
            for ticker, qtd in posicoes_acoes.items():
                valor_acoes_exec += qtd * precos_execucao.get(ticker, 0.0)
                
            patrimonio_exec = saldo_caixa + valor_acoes_exec
            
            # Execução de Ordens e Ajuste de Posições
            novas_posicoes = {}
            turnover_financeiro_bruto = 0.0
            custos_totais_rebalance = 0.0
            
            # 1. Vender posições eliminadas ou reduzidas
            for ticker, qtd_antiga in posicoes_acoes.items():
                peso_target = pesos_alvo.get(ticker, 0.0)
                valor_alvo = patrimonio_exec * peso_target
                prc_exec = precos_execucao.get(ticker, 0.0)
                slp = slippage_efetivo_map.get(ticker, taxa_slippage_padrao)
                
                if prc_exec > 0:
                    qtd_alvo = np.floor(valor_alvo / prc_exec) if peso_target > 0 else 0
                    if qtd_alvo < qtd_antiga:
                        qtd_venda = qtd_antiga - qtd_alvo
                        prc_venda_efetivo = prc_exec * (1.0 - slp)
                        receita_venda = qtd_venda * prc_venda_efetivo
                        custo_op = receita_venda * taxa_custo
                        
                        saldo_caixa += (receita_venda - custo_op)
                        turnover_financeiro_bruto += (qtd_venda * prc_exec)
                        custos_totais_rebalance += custo_op + (qtd_venda * prc_exec * slp)
                        
                        if qtd_alvo > 0:
                            novas_posicoes[ticker] = qtd_alvo
                    else:
                        novas_posicoes[ticker] = qtd_antiga
                        
            # 2. Comprar novas posições
            for ticker, peso_target in pesos_alvo.items():
                prc_exec = precos_execucao.get(ticker, 0.0)
                slp = slippage_efetivo_map.get(ticker, taxa_slippage_padrao)
                
                if prc_exec > 0 and peso_target > 0:
                    valor_alvo = patrimonio_exec * peso_target
                    qtd_alvo = np.floor(valor_alvo / prc_exec)
                    qtd_atual = novas_posicoes.get(ticker, 0)
                    
                    if qtd_alvo > qtd_atual:
                        qtd_compra = qtd_alvo - qtd_atual
                        prc_compra_efetivo = prc_exec * (1.0 + slp)
                        custo_compra = qtd_compra * prc_compra_efetivo
                        custo_op = custo_compra * taxa_custo
                        
                        custo_total_saida_caixa = custo_compra + custo_op
                        
                        if saldo_caixa >= custo_total_saida_caixa:
                            saldo_caixa -= custo_total_saida_caixa
                            novas_posicoes[ticker] = qtd_alvo
                            turnover_financeiro_bruto += (qtd_compra * prc_exec)
                            custos_totais_rebalance += custo_op + (qtd_compra * prc_exec * slp)
                        else:
                            qtd_possivel = np.floor(saldo_caixa / (prc_compra_efetivo * (1.0 + taxa_custo)))
                            if qtd_possivel > 0:
                                custo_compra = qtd_possivel * prc_compra_efetivo
                                custo_op = custo_compra * taxa_custo
                                saldo_caixa -= (custo_compra + custo_op)
                                novas_posicoes[ticker] = qtd_atual + qtd_possivel
                                turnover_financeiro_bruto += (qtd_possivel * prc_exec)
                                
            posicoes_acoes = novas_posicoes
            turnover_pct = (turnover_financeiro_bruto / patrimonio_exec) * 100.0 if patrimonio_exec > 0 else 0.0
            turnovers_mensais.append(turnover_pct)
            
            historico_rebalanceamento.append({
                "data_sinal": dt_sinal_t,
                "data_execucao": data_d,
                "acoes_compradas": list(pesos_alvo.keys()),
                "peso_caixa_cdi": peso_caixa_alvo,
                "turnover_pct": turnover_pct,
                "custos_totais_r": custos_totais_rebalance
            })
            
        # E. Valorização diária do patrimônio
        valor_acoes_fechamento = 0.0
        for ticker, qtd in posicoes_acoes.items():
            if qtd > 0 and ticker in df_close.columns:
                prc_c = df_close.loc[data_d, ticker]
                if not pd.isna(prc_c):
                    valor_acoes_fechamento += qtd * prc_c
                    
        patrimonio_estrategia = saldo_caixa + valor_acoes_fechamento
        
        registros_diarios.append({
            "data": data_d,
            "patrimonio_estrategia": patrimonio_estrategia,
            "patrimonio_cdi": patrimonio_cdi,
            "saldo_caixa": saldo_caixa,
            "valor_acoes": valor_acoes_fechamento
        })
        
        registros_alocacao.append({
            "data": data_d,
            "pct_acoes": (valor_acoes_fechamento / patrimonio_estrategia) * 100.0 if patrimonio_estrategia > 0 else 0.0,
            "pct_caixa_cdi": (saldo_caixa / patrimonio_estrategia) * 100.0 if patrimonio_estrategia > 0 else 100.0
        })
        
    df_diario = pd.DataFrame(registros_diarios).set_index("data")
    df_alocacao = pd.DataFrame(registros_alocacao).set_index("data")
    
    # F. Cálculo de Métricas Quantitativas Finais
    df_diario["ret_estrategia"] = df_diario["patrimonio_estrategia"].pct_change().fillna(0.0)
    df_diario["ret_cdi"] = df_diario["patrimonio_cdi"].pct_change().fillna(0.0)
    
    ret_acum_estrategia = (df_diario["patrimonio_estrategia"].iloc[-1] / patrimonio_inicial) - 1.0
    ret_acum_cdi = (df_diario["patrimonio_cdi"].iloc[-1] / patrimonio_inicial) - 1.0
    
    dias_totais = len(df_diario)
    anos = dias_totais / 252.0
    
    cagr_estrategia = ((1.0 + ret_acum_estrategia) ** (1.0 / anos)) - 1.0 if anos > 0 else 0.0
    cagr_cdi = ((1.0 + ret_acum_cdi) ** (1.0 / anos)) - 1.0 if anos > 0 else 0.0
    
    alpha_anualizado = cagr_estrategia - cagr_cdi
    vol_anualizada = float(df_diario["ret_estrategia"].std() * np.sqrt(252.0))
    sharpe_ratio = (cagr_estrategia - cagr_cdi) / vol_anualizada if vol_anualizada > 0 else 0.0
    
    pk = df_diario["patrimonio_estrategia"].cummax()
    df_diario["drawdown"] = (df_diario["patrimonio_estrategia"] - pk) / pk
    max_drawdown = float(df_diario["drawdown"].min())
    
    underwater = (df_diario["drawdown"] < 0)
    underwater_groups = (~underwater).cumsum()
    cur_underwater_lengths = underwater.groupby(underwater_groups).cumsum()
    max_underwater_days = int(cur_underwater_lengths.max()) if not cur_underwater_lengths.empty else 0
    
    turnover_medio = float(np.mean(turnovers_mensais)) if turnovers_mensais else 0.0
    
    # TESTE 2: Série Temporal de Retornos Mensais para Matriz de Correlação
    df_m_est = df_diario["patrimonio_estrategia"].resample("ME").last().pct_change().dropna()
    df_m_cdi = df_diario["patrimonio_cdi"].resample("ME").last().pct_change().dropna()
    
    df_retornos_mensais = pd.DataFrame({
        "Estratégia": df_m_est,
        "CDI": df_m_cdi
    })
    
    if isinstance(df_bench, pd.DataFrame) and not df_bench.empty:
        if "^BVSP" in df_bench.columns:
            s_ibov = df_bench["^BVSP"].reindex(df_diario.index).ffill().bfill()
            df_retornos_mensais["Ibovespa"] = s_ibov.resample("ME").last().pct_change().dropna()
        if "IDIV.SA" in df_bench.columns:
            s_idiv = df_bench["IDIV.SA"].reindex(df_diario.index).ffill().bfill()
            df_retornos_mensais["IDIV"] = s_idiv.resample("ME").last().pct_change().dropna()
            
    metricas = {
        "Retorno Acumulado Estratégia (%)": ret_acum_estrategia * 100.0,
        "Retorno Acumulado CDI (%)": ret_acum_cdi * 100.0,
        "Retorno Anualizado Estratégia (% a.a.)": cagr_estrategia * 100.0,
        "Retorno Anualizado CDI (% a.a.)": cagr_cdi * 100.0,
        "ALPHA Anualizado sobre CDI (% a.a.)": alpha_anualizado * 100.0,
        "Volatilidade Anualizada (% a.a.)": vol_anualizada * 100.0,
        "Índice de Sharpe (base CDI)": sharpe_ratio,
        "Drawdown Máximo (%)": max_drawdown * 100.0,
        "Tempo de Recuperação Máximo (dias úteis)": max_underwater_days,
        "Turnover Mensal Médio (%)": turnover_medio,
        "Patrimônio Final (R$)": df_diario["patrimonio_estrategia"].iloc[-1],
        "Janela Executada": janela_execucao
    }
    
    return {
        "metricas": metricas,
        "df_diario": df_diario,
        "df_alocacao": df_alocacao,
        "df_retornos_mensais": df_retornos_mensais,
        "historico_rebalanceamento": historico_rebalanceamento,
        "tabela_ultimo_rebalance": tabela_ultimo_rebalance,
        "df_bench": df_bench
    }
