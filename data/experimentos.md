# Resumo Executivo: Grade de Experimentos BESST Trend-Yield Otimizado

**Periodo:** 2012-01-01 a 2026-07-31  
**Total de Cenarios Testados:** 144  
**Benchmark:** Taxa CDI (SGS 12 - Banco Central do Brasil)  
**Data de Geracao:** 2026-08-17 00:20

---

## Estatisticas da Grade

| Metrica | Valor |
|:--------|------:|
| N de experimentos | 144 |
| Sharpe Maximo | 0.2993 |
| Sharpe Medio | -0.0527 |
| Desvio Padrao dos Sharpes | 0.2056 |

---

## Top 3 Parametrizacoes por Indice de Sharpe

| ID | L_trend | N_acoes | Fator SMA | Bazin | Custo | Retorno Acum. | Sharpe | Drawdown | Alpha |
|:---|--------:|--------:|:---------:|:-----:|------:|--------------:|-------:|---------:|------:|
| EXP_049 | 150 | 6 | 1.20 | True | 0 bps | 500.5% | 0.299 | -15.17% | +3.51% |
| EXP_061 | 150 | 8 | 1.20 | True | 0 bps | 445.4% | 0.281 | -15.36% | +2.75% |
| EXP_097 | 200 | 8 | 1.20 | True | 0 bps | 439.6% | 0.267 | -13.47% | +2.67% |

---

## Notas de Implementacao

- **Execucao VWAP Proxy**: Ordens simuladas no preco medio diario (O+H+L+C)/4 em t+1.
- **Slippage Dinamico**: max(0.05%, 0.10 x Vol_21d).
- **Banda de Inércia (Buffer Turnover)**: Reducao do giro mensal exigindo margem minima de dividendo para substituicao.
- **Segmentacao IS/OOS**: In-Sample 2012-2019, Out-of-Sample 2020-2026.
- **Trava Macro Selic**: CDI_12M >= 12% E Ibov < SMA200 => N_acoes reduzido a metade.
- **Sanitizacao de Proventos**: Alertas automaticos para DY_12M > 25%.
