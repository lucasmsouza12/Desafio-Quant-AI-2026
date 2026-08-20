# 📈 Aegis BESST Quant AI (Desafio Quant AI 2026)

Este repositório contém o framework quantitativo modular completo do robô **Aegis BESST Quant AI**, focado no mercado de ações brasileiro (B3), combinando os setores de dividendos defensivos (**BESST**: Bancos, Energia/Transmissão, Seguros, Saneamento e Telecomunicações) com **Filtro de Tendência de Alta (SMA200)**, **Preço Teto Bazin Plurianual (36 meses)**, **Trava de Sobrecomprado**, **Banda de Inércia de Turnover** e **Alocação Tática em Caixa CDI**.

---

## 🛠️ Arquitetura dos Módulos do Projeto

- **`dados.py`**: Ingestão e cache de cotações e proventos (`yfinance`), taxa diária do CDI (SGS 12 BCB) e reconstituição dinâmica mensal do universo histórico BESST com filtro de liquidez (`ADTV_21d >= R$ 1MM`).
- **`estrategia.py`**: Implementa o funil quantitativo de 4 etapas (Valuation Bazin, Tendência SMA200, Trava de Sobrecomprado e Ranking DY 12M) com Banda de Inércia (`buffer_turnover = 0.15`).
- **`backtest.py`**: Engine de simulação diária com execução a preços VWAP proxy em $t+1$, slippage dinâmico por volatilidade ($\max(5\text{ bps}, 0,10 \times \sigma_{21\text{d}})$), emolumentos B3 e crédito de proventos em *pay-date*.
- **`analise_distribuicao.py`**: Módulo de auditoria estatística com cálculo do **Deflated Sharpe Ratio (DSR)** de Marcos López de Prado para mitigação de *overfitting*.
- **`figuras.py`**: Script que gera as **5 figuras em alta resolução (300 DPI - Publication Ready)** na pasta `figuras/`.
- **`gerar_pdf.py`**: Script de compilação automatizada e reproduzível do **Relatório Final em PDF (`relatorio_final.pdf`)** em 1 único comando.
- **`dashboard.py`**: Painel visual interativo em Streamlit com suporte a experimentos e diagnósticos anti-viés.
- **`relatorio.md`**: Relatório técnico completo de pesquisa revisado com todas as métricas reais do backtest.
- **`relatorio_final.pdf`**: Documento oficial de submissão do desafio em formato executivo/apresentação institucional.

---

## 🚀 Comandos Rápidos de Execução

### 1. Ativar o Ambiente Virtual (`.venv`)
No PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Gerar as Figuras em Alta Resolução (300 DPI)
```powershell
python figuras.py
```

### 3. Compilar o Relatório Final em PDF (1 Comando)
```powershell
python gerar_pdf.py
```
*(Gera automaticamente `relatorio_final.pdf` na raiz do projeto com capa, mascote, sumário e todas as figuras diagramadas).*

### 4. Abrir o Dashboard Interativo (Streamlit)
```powershell
streamlit run dashboard.py
```

---

## ⚠️ Aviso Legal e Metodológico (Desafio Quant AI 2026)

> **AVISO**: Este projeto foi desenvolvido estritamente para fins educacionais, de pesquisa e análise histórica de finanças quantitativas no âmbito do **Desafio Quant AI 2026**. **NÃO se trata de recomendação de investimento, análise de valores mobiliários ou oferta de compra/venda de ativos.**
