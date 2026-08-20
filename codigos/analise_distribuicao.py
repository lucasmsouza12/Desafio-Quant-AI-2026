# analise_distribuicao.py
# Módulo de Análise Estatística da Distribuição de Sharpes
# Implementa o Deflated Sharpe Ratio (DSR) de Marcos López de Prado.

import sys
import os
import numpy as np
import pandas as pd
import scipy.stats as stats

# Configuração segura de encoding UTF-8 no stdout para Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def analisar_distribuicao_sharpes(caminho_csv='experimentos.csv'):
    """
    Lê experimentos.csv (UTF-8) e calcula a distribuição dos Sharpes da grade.
    
    Implementa a fórmula de López de Prado para o limiar de acerto por mero acaso:
    
        E[max(SR)] = sigma_SR * (
            (1 - gamma) * Phi^-1(1 - 1/N) +
            gamma        * Phi^-1(1 - 1/(N*e))
        )
    
    onde gamma = 0.5772... (constante de Euler-Mascheroni).
    
    Retorna dicionário com todas as estatísticas e veredito de overfitting.
    """
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(
            f"Arquivo '{caminho_csv}' não encontrado. "
            "Execute gerar_base_experimentos.py primeiro."
        )

    df_exp = pd.read_csv(caminho_csv, encoding='utf-8')

    # Suporte flexível para variações de nome de coluna
    col_sharpe = None
    for c in ['Sharpe', 'Sharpe_Ratio', 'sharpe_ratio', 'sharpe']:
        if c in df_exp.columns:
            col_sharpe = c
            break
    if col_sharpe is None:
        raise KeyError("Coluna Sharpe não encontrada em experimentos.csv")

    s = df_exp[col_sharpe].dropna()
    n_testes  = len(s)
    if n_testes == 0:
        raise ValueError("Nenhum dado válido de Sharpe encontrado.")

    sharpe_max  = float(s.max())
    sharpe_mean = float(s.mean())
    sharpe_std  = float(s.std(ddof=1)) if n_testes > 1 else 0.0
    sharpe_skew = float(s.skew())      if n_testes > 2 else 0.0
    sharpe_kurt = float(s.kurtosis())  if n_testes > 3 else 0.0

    # Fórmula de López de Prado
    euler_mascheroni = 0.5772156649
    if n_testes > 1 and sharpe_std > 0:
        z1 = stats.norm.ppf(1.0 - 1.0 / float(n_testes))
        z2 = stats.norm.ppf(1.0 - 1.0 / (float(n_testes) * np.e))
        expected_max_sharpe = float(
            sharpe_std * ((1.0 - euler_mascheroni) * z1 + euler_mascheroni * z2)
        )
    else:
        expected_max_sharpe = sharpe_mean

    superou_ruido = bool(sharpe_max > expected_max_sharpe)

    # DSR p-value aproximado
    if sharpe_std > 0 and n_testes > 1:
        dsr_stat   = (sharpe_max - expected_max_sharpe) / (sharpe_std / np.sqrt(n_testes))
        dsr_pvalue = float(1.0 - stats.norm.cdf(dsr_stat))
    else:
        dsr_pvalue = 0.5

    print(f"--- DSR: GRADE DE EXPERIMENTOS (N={n_testes}) ---")
    print(f"Sharpe Maximo         : {sharpe_max:.4f}")
    print(f"Sharpe Medio          : {sharpe_mean:.4f}")
    print(f"Desvio Padrao (sigma) : {sharpe_std:.4f}")
    print(f"Skewness              : {sharpe_skew:.4f}")
    print(f"Kurtosis              : {sharpe_kurt:.4f}")
    print(f"Limiar de Ruido E[max]: {expected_max_sharpe:.4f}")
    print(f"Veredito              : {'[OK] ALPHA GENUINO' if superou_ruido else '[AVISO] RISCO DE OVERFITTING'}")

    return {
        'n_testes': n_testes,
        'sharpe_max': sharpe_max,
        'sharpe_mean': sharpe_mean,
        'sharpe_std': sharpe_std,
        'sharpe_skew': sharpe_skew,
        'sharpe_kurt': sharpe_kurt,
        'expected_max_sharpe': expected_max_sharpe,
        'superou_ruido': superou_ruido,
        'dsr_pvalue': dsr_pvalue
    }


if __name__ == "__main__":
    analisar_distribuicao_sharpes()
