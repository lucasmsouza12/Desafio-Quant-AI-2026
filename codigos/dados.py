# dados.py
# Módulo de coleta, tratamento e cache de dados de mercado para o Backtest BESST
# Contém integração com yfinance, Banco Central do Brasil (SGS 12 - CDI) e universo BESST.

import sys
import io
import os
import pickle
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta

# Configuração segura de encoding UTF-8 no stdout para Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Diretório base para armazenamento de cache e dados
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Mapeamento do Universo BESST (Bancos, Energia, Seguros, Saneamento)
# Inclui datas de IPO/Listagem e Fechamento de Capital/Fusão para eliminar viés de sobrevivência
UNIVERSO_BESST_CONFIG = {
    # BANCOS
    "ITUB4.SA": {"nome": "Itaú Unibanco PN", "setor": "Bancos", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "BBDC4.SA": {"nome": "Bradesco PN", "setor": "Bancos", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "BBAS3.SA": {"nome": "Banco do Brasil ON", "setor": "Bancos", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "SANB11.SA": {"nome": "Santander Brasil Unit", "setor": "Bancos", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "BPAC11.SA": {"nome": "BTG Pactual Unit", "setor": "Bancos", "inicio": "2012-05-03", "fim": "2026-12-31"},
    "ABCB4.SA": {"nome": "Banco ABC Brasil PN", "setor": "Bancos", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "BRSR6.SA": {"nome": "Banrisul PN", "setor": "Bancos", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "ITSA4.SA": {"nome": "Itaúsa PN", "setor": "Bancos", "inicio": "2012-01-01", "fim": "2026-12-31"},
    
    # ENERGIA / TRANSMISSÃO
    "TAEE11.SA": {"nome": "Taesa Unit", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "TRPL4.SA": {"nome": "ISA CTEEP PN", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "EGIE3.SA": {"nome": "Engie Brasil ON", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "CPLE6.SA": {"nome": "Copel PNB", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "ELET3.SA": {"nome": "Eletrobras ON", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "ELET6.SA": {"nome": "Eletrobras PNB", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "EQTL3.SA": {"nome": "Equatorial Energia ON", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "CMIG4.SA": {"nome": "Cemig PN", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "CPFE3.SA": {"nome": "CPFL Energia ON", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "ALUP11.SA": {"nome": "Alupar Unit", "setor": "Energia", "inicio": "2013-04-23", "fim": "2026-12-31"},
    "ENGI11.SA": {"nome": "Energisa Unit", "setor": "Energia", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "ENBR3.SA": {"nome": "EDP Brasil ON (Deslistada)", "setor": "Energia", "inicio": "2012-01-01", "fim": "2023-08-30"},
    "AESB3.SA": {"nome": "AES Brasil ON (Incorporada)", "setor": "Energia", "inicio": "2021-03-29", "fim": "2024-10-31"},
    "AURE3.SA": {"nome": "Auren Energia ON", "setor": "Energia", "inicio": "2022-03-28", "fim": "2026-12-31"},
    
    # SEGUROS
    "BBSE3.SA": {"nome": "BB Seguridade ON", "setor": "Seguros", "inicio": "2013-04-29", "fim": "2026-12-31"},
    "PSSA3.SA": {"nome": "Porto Seguro ON", "setor": "Seguros", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "CXSE3.SA": {"nome": "Caixa Seguridade ON", "setor": "Seguros", "inicio": "2021-04-29", "fim": "2026-12-31"},
    "WIZC3.SA": {"nome": "Wiz Soluções ON", "setor": "Seguros", "inicio": "2015-06-04", "fim": "2026-12-31"},
    "SULA11.SA": {"nome": "SulAmérica Unit (Incorporada)", "setor": "Seguros", "inicio": "2012-01-01", "fim": "2022-12-22"},
    
    # SANEAMENTO
    "SBSP3.SA": {"nome": "Sabesp ON", "setor": "Saneamento", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "SAPR11.SA": {"nome": "Sanepar Unit", "setor": "Saneamento", "inicio": "2016-12-20", "fim": "2026-12-31"},
    "SAPR4.SA": {"nome": "Sanepar PN", "setor": "Saneamento", "inicio": "2012-01-01", "fim": "2026-12-31"},
    "CSMG3.SA": {"nome": "Copasa ON", "setor": "Saneamento", "inicio": "2012-01-01", "fim": "2026-12-31"}
}


def gerar_universo_historico_besst(data_inicio="2012-01-01", data_fim="2026-07-31"):
    """
    Gera e salva o arquivo data/besst_universo_historico.csv com a fotografia mensal
    dos ativos BESST elegíveis em cada mês t, incluindo status de vigência para evitar viés de sobrevivência.
    """
    caminho_csv = os.path.join(DATA_DIR, "besst_universo_historico.csv")
    
    datas_mensais = pd.date_range(start=data_inicio, end=data_fim, freq="ME")
    registros = []
    
    for dt in datas_mensais:
        str_mes = dt.strftime("%Y-%m")
        str_dt = dt.strftime("%Y-%m-%d")
        
        for ticker, info in UNIVERSO_BESST_CONFIG.items():
            dt_inicio = info["inicio"]
            dt_fim = info["fim"]
            
            # Verifica se o ativo estava ativo na data do mês t
            if dt_inicio <= str_dt <= dt_fim:
                status = "Ativo"
            elif str_dt < dt_inicio:
                status = "Pre-IPO"
            else:
                status = "Deslistado/Incorporado"
                
            registros.append({
                "mes": str_mes,
                "ticker": ticker,
                "setor": info["setor"],
                "nome": info["nome"],
                "status_liquidez": status
            })
            
    df_universo = pd.DataFrame(registros)
    df_universo.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
    return df_universo


def baixar_cdi_sgs12(data_inicio="2012-01-01", data_fim="2026-07-31"):
    """
    Baixa a série temporal diária da taxa CDI (série 12 SGS do Banco Central do Brasil).
    Retorna um DataFrame com a taxa diária em percentual e decimal, utilizando cache local.
    Faz a requisição em blocos de no máximo 5 anos para respeitar a trava da API do BCB.
    """
    caminho_cache = os.path.join(DATA_DIR, "cdi_sgs12.csv")
    
    if os.path.exists(caminho_cache):
        try:
            df_cdi = pd.read_csv(caminho_cache, parse_dates=["data"], index_col="data")
            df_cdi = df_cdi[(df_cdi.index >= pd.to_datetime(data_inicio)) & (df_cdi.index <= pd.to_datetime(data_fim))]
            if not df_cdi.empty:
                return df_cdi
        except Exception:
            pass
            
    dt_start = pd.to_datetime(data_inicio)
    dt_end = pd.to_datetime(data_fim)
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    todos_dados = []
    curr_start = dt_start
    
    while curr_start < dt_end:
        curr_end = min(curr_start + pd.DateOffset(years=5), dt_end)
        str_in = curr_start.strftime("%d/%m/%Y")
        str_fim = curr_end.strftime("%d/%m/%Y")
        
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial={str_in}&dataFinal={str_fim}"
        res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code == 200:
            dados_chunk = res.json()
            if isinstance(dados_chunk, list):
                todos_dados.extend(dados_chunk)
        else:
            raise ValueError(f"Erro ao baixar dados do CDI no Banco Central (HTTP {res.status_code}): {res.text}")
            
        curr_start = curr_end + pd.Timedelta(days=1)
        
    if not todos_dados:
        raise ValueError("API do Banco Central retornou lista vazia para o período especificado de CDI.")
        
    df_cdi = pd.DataFrame(todos_dados)
    df_cdi.drop_duplicates(subset=["data"], inplace=True)
    df_cdi["data"] = pd.to_datetime(df_cdi["data"], format="%d/%m/%Y")
    df_cdi["valor"] = df_cdi["valor"].astype(float)
    df_cdi["cdi_diario"] = df_cdi["valor"] / 100.0
    df_cdi.set_index("data", inplace=True)
    df_cdi.sort_index(inplace=True)
    
    df_cdi.to_csv(caminho_cache, encoding="utf-8-sig")
    return df_cdi


def baixar_dados_yfinance(data_inicio="2011-01-01", data_fim="2026-07-31", forcar_download=False):
    """
    Baixa cotações diárias (Open, High, Low, Close, Adj Close, Volume) e histórico de proventos
    para todos os ativos do universo BESST via yfinance, com cache local.
    Data inicial padrão definida para 2011 para garantir histórico de 36M antes de 2014/2015.
    """
    caminho_precos = os.path.join(DATA_DIR, "precos_cache.pkl")
    caminho_proventos = os.path.join(DATA_DIR, "proventos_cache.pkl")
    
    if os.path.exists(caminho_precos) and os.path.exists(caminho_proventos) and not forcar_download:
        try:
            with open(caminho_precos, "rb") as f:
                dados_precos = pickle.load(f)
            with open(caminho_proventos, "rb") as f:
                dados_proventos = pickle.load(f)
            return dados_precos, dados_proventos
        except Exception:
            pass
            
    tickers = list(UNIVERSO_BESST_CONFIG.keys())
    
    print("Baixando cotações diárias do yfinance...")
    # Baixar cotações sem ajuste automático para manter Close e Adj Close separados se necessário
    df_raw = yf.download(
        tickers,
        start=data_inicio,
        end=data_fim,
        group_by="ticker",
        auto_adjust=False,
        progress=False
    )
    
    dados_precos = {
        "Close": pd.DataFrame(),
        "Adj Close": pd.DataFrame(),
        "Open": pd.DataFrame(),
        "High": pd.DataFrame(),
        "Low": pd.DataFrame(),
        "Volume": pd.DataFrame()
    }
    
    # Organizar dicionário de DataFrames por tipo de preço
    for campo in ["Close", "Adj Close", "Open", "High", "Low", "Volume"]:
        df_campo = pd.DataFrame()
        for t in tickers:
            if (t, campo) in df_raw.columns:
                df_campo[t] = df_raw[(t, campo)]
            elif len(df_raw.columns.levels) > 1 and campo in df_raw.columns.levels[0]:
                df_campo[t] = df_raw[campo][t]
        dados_precos[campo] = df_campo
        
    # VIÉS 1: Pré-calcular Volatilidade Móvel de 21 dias (vol_21d)
    # vol_21d = retorno_diario.rolling(21).std() * np.sqrt(252)
    df_ret_diario = dados_precos["Close"].pct_change()
    dados_precos["Vol_21d"] = df_ret_diario.rolling(21).std() * np.sqrt(252.0)
    
    # VIÉS 3: Proxy diária de VWAP = (Open + High + Low + Close) / 4.0
    dados_precos["VWAP"] = (dados_precos["Open"] + dados_precos["High"] + dados_precos["Low"] + dados_precos["Close"]) / 4.0
        
    print("Baixando histórico de dividendos e proventos...")
    dados_proventos = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            divs = tk.dividends
            if isinstance(divs, pd.Series) and not divs.empty:
                divs.index = divs.index.tz_localize(None)
                divs.sort_index(inplace=True)
                dados_proventos[t] = divs
            else:
                dados_proventos[t] = pd.Series(dtype=float)
        except Exception:
            dados_proventos[t] = pd.Series(dtype=float)
            
    # Salvar cache
    with open(caminho_precos, "wb") as f:
        pickle.dump(dados_precos, f)
    with open(caminho_proventos, "wb") as f:
        pickle.dump(dados_proventos, f)
        
    return dados_precos, dados_proventos


def baixar_benchmarks(data_inicio="2012-01-01", data_fim="2026-07-31"):
    """
    Baixa cotações do Ibovespa (^BVSP) e do IDIV (Índice de Dividendos - IDIV.SA / ^IDIV) para benchmarking.
    Garante o cálculo da SMA200 do Ibovespa para a trava macroeconômica da Selic.
    """
    caminho_bench = os.path.join(DATA_DIR, "benchmarks_cache.pkl")
    if os.path.exists(caminho_bench):
        try:
            with open(caminho_bench, "rb") as f:
                df_b = pickle.load(f)
                if isinstance(df_b, pd.DataFrame) and "^BVSP" in df_b.columns:
                    return df_b
        except Exception:
            pass
            
    df_bench = yf.download(["^BVSP", "IDIV.SA"], start=data_inicio, end=data_fim, auto_adjust=True, progress=False)["Close"]
    
    if isinstance(df_bench, pd.DataFrame) and "^BVSP" in df_bench.columns:
        df_bench["BVSP_SMA200"] = df_bench["^BVSP"].rolling(200).mean()
        
    with open(caminho_bench, "wb") as f:
        pickle.dump(df_bench, f)
    return df_bench


def validar_sanidade_proventos(dados_proventos, dados_precos, limiar_alerta_dy=0.25):
    """
    VIÉS 5: Rotina de sanidade que calcula o DY_12M mensal e emite um alerta
    caso algum ativo apresente DY_12M > 25% em qualquer mês histórico (desacoplamento ou desdobramento).
    """
    df_close = dados_precos["Close"]
    alertas_anomalias = []
    
    # Amostrar mensalmente as datas de teste
    datas_mensais = df_close.resample("ME").last().index
    
    for dt in datas_mensais:
        for ticker in df_close.columns:
            if ticker in dados_proventos and not dados_proventos[ticker].empty:
                s_close = df_close[ticker].loc[:dt].dropna()
                if not s_close.empty:
                    prc_close = s_close.iloc[-1]
                    if prc_close > 0:
                        dy_12m = calcular_dy_12m(ticker, dados_proventos, prc_close, dt)
                        if dy_12m > limiar_alerta_dy:
                            msg = f"⚠️ ALERTA DE SANIDADE (VIÉS 5): {ticker} apresentou DY_12M de {dy_12m*100.0:.1f}% na data {dt.strftime('%Y-%m-%d')} (Preço: R$ {prc_close:.2f})."
                            print(msg)
                            alertas_anomalias.append({
                                "ticker": ticker,
                                "data": dt.strftime("%Y-%m-%d"),
                                "dy_12m_pct": dy_12m * 100.0,
                                "preco_close": prc_close,
                                "mensagem": msg
                            })
                            
    return alertas_anomalias


def calcular_adtv21(dados_precos, data_t, min_adtv=1000000.0):
    """
    Calcula o Volume Financeiro Médio Diário dos últimos 21 dias úteis (ADTV21d) até a data t.
    Retorna uma lista de tickers que atendem ao critério de liquidez (ADTV21d >= min_adtv).
    """
    df_close = dados_precos["Close"]
    df_vol = dados_precos["Volume"]
    
    # Filtra dados estritamente até a data t (Zero Look-Ahead)
    close_sub = df_close.loc[:data_t]
    vol_sub = df_vol.loc[:data_t]
    
    if len(close_sub) < 21:
        return []
        
    vol_financeiro = close_sub.iloc[-21:] * vol_sub.iloc[-21:]
    adtv21 = vol_financeiro.mean(axis=0)
    
    tickers_aprovados = adtv21[adtv21 >= min_adtv].index.tolist()
    return tickers_aprovados


def calcular_dpa_3a(ticker, proventos, preco_atual, data_t):
    """
    Calcula o DPA Médio de 3 Anos (DPA_3a) e o Preço Teto Bazin até a data t:
    - Considera os proventos pagos/declarados nos 36 meses móveis anteriores a data_t.
    - Se histórico entre 12 e 36 meses, divide a soma pelo número proporcional de anos.
    - Se histórico < 12 meses ou DPA_3a == 0, atribui Preço Teto Bazin = +infinito.
    """
    if ticker not in proventos or proventos[ticker].empty:
        return 0.0, np.inf # Sem histórico -> Preço Teto Infinito (elegível)
        
    serie_div = proventos[ticker]
    
    # Filtrar proventos até a data t
    dt_limite_sup = pd.to_datetime(data_t)
    dt_limite_inf_36m = dt_limite_sup - pd.DateOffset(years=3)
    dt_limite_inf_12m = dt_limite_sup - pd.DateOffset(years=1)
    
    divs_36m = serie_div[(serie_div.index >= dt_limite_inf_36m) & (serie_div.index <= dt_limite_sup)]
    
    if divs_36m.empty:
        return 0.0, np.inf
        
    # Verificar extensão de histórico disponível do ativo
    primeira_data_div = serie_div[serie_div.index <= dt_limite_sup].index.min()
    if pd.isna(primeira_data_div):
        return 0.0, np.inf
        
    dias_historico = (dt_limite_sup - primeira_data_div).days
    
    if dias_historico < 365:
        # Menos de 12 meses de histórico -> Preço Teto Infinito
        return 0.0, np.inf
        
    anos_proporcionais = min(3.0, max(1.0, dias_historico / 365.25))
    soma_divs_36m = divs_36m.sum()
    
    dpa_3a = soma_divs_36m / anos_proporcionais
    
    if dpa_3a <= 0:
        return 0.0, np.inf
        
    preco_teto_bazin = dpa_3a / 0.06
    return dpa_3a, preco_teto_bazin


def calcular_dy_12m(ticker, proventos, preco_atual, data_t):
    """
    Calcula o Dividend Yield dos últimos 12 meses móveis (DY_12M) até a data t:
    DY_12M = (Soma dos proventos nos últimos 12M anteriores a t) / Preço Fechamento no dia t.
    """
    if ticker not in proventos or proventos[ticker].empty or preco_atual <= 0:
        return 0.0
        
    serie_div = proventos[ticker]
    dt_limite_sup = pd.to_datetime(data_t)
    dt_limite_inf = dt_limite_sup - pd.DateOffset(years=1)
    
    divs_12m = serie_div[(serie_div.index >= dt_limite_inf) & (serie_div.index <= dt_limite_sup)]
    
    if divs_12m.empty:
        return 0.0
        
    soma_12m = divs_12m.sum()
    dy_12m = soma_12m / preco_atual
    return float(dy_12m)
