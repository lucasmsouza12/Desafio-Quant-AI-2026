# gerar_pdf.py
# Compilador Oficial do Relatório Final (5 Páginas Widescreen 16:9)
# Formato: Apresentação Executiva 16:9 Densa para o Desafio Quant AI 2026
# Páginas 1 e 3: 100% Intactas
# Páginas 2, 4 e 5: Expandidas, Densas, Tipografia 9.5-10.5pt, Sem Espaços Vazios e Sem Truncamentos

import os
import sys
import io
import base64
import subprocess
import pypdf

# Configuração segura de UTF-8 no Windows
if sys.platform.startswith('win') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURAS_DIR = os.path.join(ROOT_DIR, "figuras")
OUTPUT_PDF = os.path.join(ROOT_DIR, "relatorio_final.pdf")
HTML_TEMP = os.path.join(ROOT_DIR, "relatorio_compilado_16_9.html")


def image_to_base64(img_path):
    if not os.path.exists(img_path):
        return ""
    with open(img_path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(img_path)[1].lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{base64.b64encode(data).decode('utf-8')}"


def encontrar_executavel_edge():
    caminhos = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    for c in caminhos:
        if os.path.exists(c):
            return c
    return None


def construir_html_16_9():
    robo_b64 = image_to_base64(os.path.join(ROOT_DIR, "robo.png"))
    fig1_b64 = image_to_base64(os.path.join(FIGURAS_DIR, "01_curva_de_capital.png"))
    fig2_b64 = image_to_base64(os.path.join(FIGURAS_DIR, "02_alpha_acumulado_cdi.png"))
    fig3_b64 = image_to_base64(os.path.join(FIGURAS_DIR, "03_drawdown_temporal.png"))

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Aegis BESST Quant AI - Relatório Final 16:9</title>
    <style>
        @page {{
            size: 297mm 167.0625mm; /* Proporção Exata 16:9 Horizontal */
            margin: 0;
        }}

        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}

        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            color: #1A202C;
            background-color: #0B192C;
            font-size: 8pt;
            line-height: 1.35;
        }}

        /* CONTAINER DE CADA SLIDE/PÁGINA (EXATAMENTE 16:9) */
        .slide {{
            width: 297mm;
            height: 167.0625mm;
            max-height: 167.0625mm;
            padding: 7.5mm 11mm;
            page-break-after: always;
            position: relative;
            background: #FFFFFF;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        /* CABEÇALHO PADRÃO DAS PÁGINAS 2 A 5 */
        .slide-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2.5px solid #0047AB;
            padding-bottom: 3px;
            margin-bottom: 4px;
        }}

        .slide-title {{
            font-size: 12.5pt;
            font-weight: 800;
            color: #0F2D59;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .slide-badge {{
            background: #EBF4FF;
            color: #0047AB;
            font-size: 7.5pt;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid #BEE3F8;
        }}

        .slide-page-num {{
            font-size: 8.5pt;
            font-weight: 700;
            color: #718096;
        }}

        /* PÁGINA 1: CAPA 100% BACKGROUND + OVERLAY GLASS (100% INTACTA) */
        .slide-capa {{
            padding: 0;
            background-image: url('{robo_b64}');
            background-size: cover;
            background-position: center right;
            position: relative;
        }}

        .capa-overlay-container {{
            width: 58%;
            height: 100%;
            background: linear-gradient(90deg, rgba(10, 25, 47, 0.96) 0%, rgba(10, 25, 47, 0.88) 75%, rgba(10, 25, 47, 0.0) 100%);
            padding: 16mm 14mm 14mm 16mm;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            color: #FFFFFF;
        }}

        .capa-top {{
            border-left: 3.5px solid #00D2FF;
            padding-left: 12px;
        }}

        .capa-tag {{
            font-size: 8pt;
            font-weight: 700;
            letter-spacing: 1.5px;
            color: #00D2FF;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}

        .capa-main-title {{
            font-size: 20pt;
            font-weight: 900;
            line-height: 1.15;
            color: #FFFFFF;
            margin: 0 0 6px 0;
        }}

        .capa-subtitle {{
            font-size: 9.5pt;
            font-weight: 400;
            color: #CBD5E0;
            line-height: 1.3;
            margin: 0;
        }}

        .capa-robot-callout {{
            background: rgba(0, 210, 255, 0.08);
            border: 1px solid rgba(0, 210, 255, 0.25);
            border-radius: 6px;
            padding: 8px 12px;
            margin: 12px 0;
        }}

        .capa-robot-name {{
            font-size: 11pt;
            font-weight: 800;
            color: #00D2FF;
        }}

        .capa-robot-desc {{
            font-size: 7.5pt;
            color: #E2E8F0;
            margin-top: 2px;
        }}

        .capa-toc {{
            background: rgba(15, 45, 89, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 6px;
            padding: 8px 12px;
        }}

        .capa-toc-title {{
            font-size: 8.5pt;
            font-weight: 800;
            color: #00D2FF;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            padding-bottom: 3px;
        }}

        .capa-toc-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 14px;
            font-size: 7.5pt;
            color: #E2E8F0;
        }}

        .capa-toc-item {{
            display: flex;
            justify-content: space-between;
            border-bottom: 1px dotted rgba(255, 255, 255, 0.2);
            padding-bottom: 1px;
        }}

        .capa-toc-item span.pag {{
            font-weight: bold;
            color: #00D2FF;
            margin-left: 4px;
        }}

        /* GRIDS DE LAYOUT */
        .grid-2col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 9px;
            flex-grow: 1;
        }}

        .col {{
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 5px;
        }}

        /* CARDS E BLOCOS DAS PÁGINAS EXPANDIDAS (2, 4 E 5) */
        .card-dense {{
            background: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-radius: 5px;
            padding: 5.5px 8.5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            flex-grow: 1;
        }}

        .card-dense-header {{
            font-size: 10.2pt;
            font-weight: 800;
            color: #0F2D59;
            margin-bottom: 3px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1.5px solid #E2E8F0;
            padding-bottom: 2px;
        }}

        .card-dense-body {{
            font-size: 9.3pt;
            color: #2D3748;
            line-height: 1.29;
        }}

        .card-dense-body p {{
            margin: 0 0 3.5px 0;
            text-align: justify;
        }}

        .card-dense-body p:last-child {{
            margin-bottom: 0;
        }}

        .card-highlight-blue {{
            background: #F0F7FF;
            border-left: 4px solid #0047AB;
        }}

        .card-highlight-orange {{
            background: #FFFDF7;
            border-left: 4px solid #DD6B20;
        }}

        .card-highlight-green {{
            background: #F2FDF5;
            border-left: 4px solid #2E7D32;
        }}

        .formula-dense {{
            background: #E2E8F0;
            padding: 1px 4px;
            border-radius: 3px;
            font-family: 'Cambria Math', 'Consolas', monospace;
            font-size: 8.8pt;
            color: #0F2D59;
            font-weight: 700;
        }}

        /* ESTILOS DA PÁGINA 3 (MANTIDA 100% INTACTA) */
        table.table-compact {{
            width: 100%;
            border-collapse: collapse;
            font-size: 6.8pt;
            margin: 3px 0;
        }}

        table.table-compact th, table.table-compact td {{
            padding: 3.5px 5px;
            border: 1px solid #CBD5E0;
            text-align: left;
        }}

        table.table-compact th {{
            background-color: #0F2D59;
            color: #FFFFFF;
            font-weight: 700;
            text-align: center;
        }}

        table.table-compact tr:nth-child(even) {{
            background-color: #F7FAFC;
        }}

        .text-center {{ text-align: center !important; }}
        .text-right {{ text-align: right !important; }}
        .text-green {{ color: #22543D; font-weight: 800; }}
        .text-red {{ color: #742A2A; font-weight: 800; }}

        .fig-box {{
            text-align: center;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 4px;
            padding: 3px;
        }}

        .fig-img {{
            max-width: 100%;
            height: auto;
            border-radius: 3px;
        }}

        .fig-caption {{
            font-size: 6.5pt;
            font-weight: 700;
            color: #4A5568;
            margin-top: 2px;
        }}

        /* ESTILOS DAS TABELAS DA PÁGINA 5 EXPANDIDA */
        table.table-expanded {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.2pt;
            margin: 2px 0;
        }}

        table.table-expanded th, table.table-expanded td {{
            padding: 3px 5px;
            border: 1px solid #CBD5E1;
            text-align: left;
        }}

        table.table-expanded th {{
            background-color: #0F2D59;
            color: #FFFFFF;
            font-weight: 700;
            text-align: center;
            font-size: 8.2pt;
        }}

        table.table-expanded tr:nth-child(even) {{
            background-color: #F8FAFC;
        }}

        ul.dense-list, ol.dense-list {{
            margin: 0 0 0 13px;
            padding: 0;
        }}

        ul.dense-list li, ol.dense-list li {{
            margin-bottom: 2.5px;
            text-align: justify;
            font-size: 9.1pt;
            line-height: 1.26;
        }}

        ul.dense-list li:last-child, ol.dense-list li:last-child {{
            margin-bottom: 0;
        }}
    </style>
</head>
<body>

<!-- ========================================== -->
<!-- PÁGINA 1: CAPA COM ROBÔ SPARKY E SUMÁRIO (100% INTACTA) -->
<!-- ========================================== -->
<div class="slide slide-capa">
    <div class="capa-overlay-container">
        <div class="capa-top">
            <div class="capa-tag">Desafio Quant AI 2026 • Apresentação Técnica Oficial</div>
            <h1 class="capa-main-title">Aegis BESST Quant AI</h1>
            <p class="capa-subtitle">Estratégia Quantitativa de Renda Defensiva, Trend-Following e Preservação Sistemática de Capital na B3</p>
        </div>

        <div class="capa-robot-callout">
            <div class="capa-robot-name">🤖 Robô Sparky</div>
            <div class="capa-robot-desc">Agente Autônomo de Alocação em Ativos Essenciais e Blindagem Macroeconômica</div>
        </div>

        <div class="capa-toc">
            <div class="capa-toc-title">Sumário Executivo do Relatório</div>
            <div class="capa-toc-grid">
                <div class="capa-toc-item"><span>1. Identidade e Design do Robô Sparky</span><span class="pag">Pág. 2</span></div>
                <div class="capa-toc-item"><span>5. Resultados Consolidados do Backtest</span><span class="pag">Pág. 3</span></div>
                <div class="capa-toc-item"><span>2. Resumo Executivo e Funil Operacional</span><span class="pag">Pág. 2</span></div>
                <div class="capa-toc-item"><span>6. Diagnóstico da Janela Out-of-Sample</span><span class="pag">Pág. 4</span></div>
                <div class="capa-toc-item"><span>3. Hipótese Teórica (BESST, Bazin e Trend)</span><span class="pag">Pág. 2</span></div>
                <div class="capa-toc-item"><span>7. Auditoria DSR e Controle de Overfitting</span><span class="pag">Pág. 5</span></div>
                <div class="capa-toc-item"><span>4. Metodologia e Mitigação de 4 Vieses</span><span class="pag">Pág. 2</span></div>
                <div class="capa-toc-item"><span>8. Arquitetura de IA Generativa (Aegis NLP)</span><span class="pag">Pág. 5</span></div>
            </div>
        </div>
    </div>
</div>

<!-- ========================================== -->
<!-- PÁGINA 2: TÓPICOS 1 A 4 EXPANDIDOS E DENSOS -->
<!-- ========================================== -->
<div class="slide">
    <div class="slide-header">
        <div class="slide-title">
            <span>🛡️ Fundamentação, Identidade e Arquitetura do Robô</span>
            <span class="slide-badge">Tópicos 1 a 4</span>
        </div>
        <div class="slide-page-num">Página 2 de 5</div>
    </div>

    <div class="grid-2col">
        <!-- COLUNA ESQUERDA: TÓPICO 1 E TÓPICO 2 -->
        <div class="col">
            <!-- TÓPICO 1: IDENTIDADE SPARKY EXPANDIDO -->
            <div class="card-dense card-highlight-blue">
                <div class="card-dense-header">
                    <span>1. Identidade, Semiótica e Design Visual do Robô 'Sparky'</span>
                </div>
                <div class="card-dense-body">
                    <p>
                        O agente autônomo foi batizado de <strong>Sparky</strong> em homenagem direta à tríade da <strong>Engenharia Elétrica do Instituto Militar de Engenharia (IME)</strong> e suas três especialidades: (1) <em>Sistemas de Energia Elétrica</em> (seleção de concessionárias e utilities BESST com fluxos previsíveis); (2) <em>Eletrônica de Processamento</em> (mecanismo quantitativo algorítmico, cálculo de sinais de tendência e gestão de risco); e (3) <em>Telecomunicações</em> (ingestão contínua de cotações via API e pipelines LLM em tempo real).
                    </p>
                    <p>
                        <strong>Semiótica dos Elementos Visuais:</strong><br>
                        • <strong>Corpo em Cerâmica Prateada e Circuitos:</strong> Precisão computacional, atrito reduzido e imunidade a vieses emocionais.<br>
                        • <strong>Escudo Holográfico Aegis:</strong> Proteção e contenção de perdas via ativos de utilidade pública contra choques macro.<br>
                        • <strong>Antena de Luz Azul:</strong> Recepção e processamento de sinal em tempo real (mercado, Atas Copom e Fatos Relevantes).<br>
                        • <strong>Display Peitoral com Gráfico e Moedas de Ouro:</strong> Simbiose entre <em>Trend-Following</em> (Momentum) e extração de renda (Yield).
                    </p>
                </div>
            </div>

            <!-- TÓPICO 2: RESUMO EXECUTIVO DO FUNIL EXPANDIDO -->
            <div class="card-dense">
                <div class="card-dense-header">
                    <span>2. Resumo Executivo e Funil Operacional Alocacional</span>
                </div>
                <div class="card-dense-body">
                    <p>
                        O modelo quantitativo <em>Long-Only</em> opera através de um funil algorítmico em 6 camadas estritas:
                    </p>
                    <ul class="dense-list">
                        <li><strong>Filtro 1 (Liquidez Institucional):</strong> <span class="formula-dense">ADTV<sub>21d</sub> &ge; R$ 1.000.000,00</span>;</li>
                        <li><strong>Filtro 2 (Valuation Bazin 36M):</strong> <span class="formula-dense">Preço Teto<sub>t</sub> = DPA<sub>36M,t</sub> / 0,06 &nbsp;&rArr;&nbsp; Preço<sub>t</sub> &le; Preço Teto<sub>t</sub></span>;</li>
                        <li><strong>Filtro 3 (Tendência Temporal):</strong> <span class="formula-dense">Preço<sub>t</sub> &gt; SMA<sub>200d,t</sub></span> (confirmação por fluxo institucional);</li>
                        <li><strong>Filtro 4 (Controle de Esticamento):</strong> <span class="formula-dense">Preço<sub>t</sub> &le; 1,20 &times; SMA<sub>200d,t</sub></span> (prevenção a sobrecomprados);</li>
                        <li><strong>Filtro 5 (Banda de Inércia / Buffer):</strong> Histerese de 15% na ordenação de ranking para contenção de giro;</li>
                        <li><strong>Filtro 6 (Trava Tática Selic):</strong> Migração de 50% para Caixa CDI se <span class="formula-dense">CDI<sub>12M</sub> &ge; 12,0% a.a.</span> e <span class="formula-dense">Ibov &lt; SMA<sub>200d</sub></span>.</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- COLUNA DIREITA: TÓPICO 3 E TÓPICO 4 -->
        <div class="col">
            <!-- TÓPICO 3: HIPÓTESE TEÓRICA EXPANDIDO -->
            <div class="card-dense">
                <div class="card-dense-header">
                    <span>3. Hipótese Teórica: Fundamentos BESST, Bazin e Trend</span>
                </div>
                <div class="card-dense-body">
                    <p>
                        <strong>Resiliência Setorial BESST:</strong> Bancos, Energia, Seguros, Saneamento e Telecomunicações operam como monopólios ou oligopólios regulados com demanda inelástica, contratos reajustados por índices inflacionários (IPCA e IGP-M) e alta taxa de conversão em dividendos.
                    </p>
                    <p>
                        <strong>Preço Teto Bazin Plurianual (36 Meses):</strong> O dividendo médio trienal (<span class="formula-dense">DPA<sub>36M</sub></span>) suaviza o valuation, eliminando distorções de proventos extraordinários atípicos.
                    </p>
                    <p>
                        <strong>Trend-Following e Anti-Value Traps:</strong> A fusão dos fatores <em>Value</em> (Dividend Yield) e <em>Momentum</em> (Time-Series Trend) elimina empresas baratas em declínio estrutural (<em>Value Traps</em>), combinando prêmios descorrelacionados (Moskowitz et al., 2012; Asness et al., 2013).
                    </p>
                </div>
            </div>

            <!-- TÓPICO 4: MITIGAÇÃO DE 4 VIESES EXPANDIDO -->
            <div class="card-dense card-highlight-green">
                <div class="card-dense-header">
                    <span>4. Metodologia e Mitigação Estrita de 4 Vieses Quants</span>
                </div>
                <div class="card-dense-body">
                    <ul class="dense-list">
                        <li><strong>Viés de Sobrevivência Zero:</strong> Reconstituição histórica <em>Point-in-Time</em> via <code>besst_universo_historico.csv</code>, incluindo papéis deslistados/incorporados (ENBR3, AESB3, SULA11), com liquidação e Caixa CDI no evento;</li>
                        <li><strong>Look-Ahead Bias Zero & Execução VWAP:</strong> Geração de sinais no fechamento de $t$ e execução no dia $t+1$ pela proxy VWAP diária <span class="formula-dense">(Abertura + Máxima + Mínima + Fechamento) / 4</span>;</li>
                        <li><strong>Fricções Realistas e Slippage Dinâmico:</strong> Desconto de emolumentos B3 (8 bps) e slippage por volatilidade <span class="formula-dense">max(5 bps, 0,10 &times; &sigma;<sub>21d</sub>)</span>;</li>
                        <li><strong>Crédito de Proventos em Pay-Date:</strong> Lançamento estrito na data oficial de pagamento (<em>Pay-Date</em>) e rentabilização a 100% do CDI até o rebalanceamento.</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- ========================================== -->
<!-- PÁGINA 3: TÓPICO 5 - RESULTADOS DO BACKTEST (100% INTACTA) -->
<!-- ========================================== -->
<div class="slide">
    <div class="slide-header">
        <div class="slide-title">
            <span>📈 Resultados Consolidados do Backtest (2012–2026)</span>
            <span class="slide-badge">Tópico 5</span>
        </div>
        <div class="slide-page-num">Página 3 de 5</div>
    </div>

    <!-- TABELA 1 CONSOLIDADA -->
    <div style="margin-bottom: 4px;">
        <div style="font-size: 7.5pt; font-weight: bold; color: #0F2D59; margin-bottom: 2px;">
            Tabela 1: Quadro Comparativo Consolidado de Desempenho e Risco — Aegis BESST Quant AI vs Benchmarks (2012–2026)
        </div>
        <table class="table-compact">
            <thead>
                <tr>
                    <th>Métrica Quantitativa</th>
                    <th>Aegis Completo (2012–26)</th>
                    <th>In-Sample (IS: 2012–19)</th>
                    <th>Out-of-Sample (OOS: 2020–26)</th>
                    <th>CDI (Benchmark)</th>
                    <th>Ibovespa (^BVSP)</th>
                    <th>IDIV (Dividendos)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Retorno Acumulado</strong></td>
                    <td class="text-center text-green"><strong>+424,8%</strong></td>
                    <td class="text-center text-green">+194,8%</td>
                    <td class="text-center">+77,8%</td>
                    <td class="text-center">+282,0%</td>
                    <td class="text-center">+130,6%</td>
                    <td class="text-center">+280,9%</td>
                </tr>
                <tr>
                    <td><strong>Retorno Anualizado (CAGR)</strong></td>
                    <td class="text-center"><strong>12,23% a.a.</strong></td>
                    <td class="text-center">14,72% a.a.</td>
                    <td class="text-center">9,26% a.a.</td>
                    <td class="text-center">9,77% a.a.</td>
                    <td class="text-center">5,87% a.a.</td>
                    <td class="text-center">9,75% a.a.</td>
                </tr>
                <tr>
                    <td><strong>ALPHA vs CDI (Anualizado)</strong></td>
                    <td class="text-center text-green"><strong>+2,45% a.a.</strong></td>
                    <td class="text-center text-green">+5,15% a.a.</td>
                    <td class="text-center text-red">-0,76% a.a.</td>
                    <td class="text-center">0,00%</td>
                    <td class="text-center text-red">-3,90% a.a.</td>
                    <td class="text-center">-0,02% a.a.</td>
                </tr>
                <tr>
                    <td><strong>Volatilidade Anualizada</strong></td>
                    <td class="text-center"><strong>12,22% a.a.</strong></td>
                    <td class="text-center">9,68% a.a.</td>
                    <td class="text-center">14,71% a.a.</td>
                    <td class="text-center">0,55% a.a.</td>
                    <td class="text-center">23,48% a.a.</td>
                    <td class="text-center">18,24% a.a.</td>
                </tr>
                <tr>
                    <td><strong>Índice de Sharpe (Base CDI)</strong></td>
                    <td class="text-center"><strong>0,201</strong></td>
                    <td class="text-center">0,532</td>
                    <td class="text-center">-0,052</td>
                    <td class="text-center">0,000</td>
                    <td class="text-center">-0,166</td>
                    <td class="text-center">-0,001</td>
                </tr>
                <tr>
                    <td><strong>Drawdown Máximo</strong></td>
                    <td class="text-center text-green"><strong>-18,09%</strong></td>
                    <td class="text-center">-18,09%</td>
                    <td class="text-center">-15,96%</td>
                    <td class="text-center">0,00%</td>
                    <td class="text-center text-red">-49,17%</td>
                    <td class="text-center text-red">-38,50%</td>
                </tr>
                <tr>
                    <td><strong>Tempo de Recuperação</strong></td>
                    <td class="text-center"><strong>431 dias</strong></td>
                    <td class="text-center">431 dias</td>
                    <td class="text-center">319 dias</td>
                    <td class="text-center">0 dias</td>
                    <td class="text-center">&gt; 1.200 dias</td>
                    <td class="text-center">&gt; 800 dias</td>
                </tr>
                <tr>
                    <td><strong>Turnover Mensal Médio</strong></td>
                    <td class="text-center"><strong>42,0%</strong></td>
                    <td class="text-center">27,9%</td>
                    <td class="text-center">59,4%</td>
                    <td class="text-center">0,0%</td>
                    <td class="text-center">—</td>
                    <td class="text-center">—</td>
                </tr>
                <tr>
                    <td><strong>Patrimônio Final (R$ 100k)</strong></td>
                    <td class="text-center"><strong>R$ 524.776,40</strong></td>
                    <td class="text-center">R$ 294.790,60</td>
                    <td class="text-center">R$ 177.812,06</td>
                    <td class="text-center">R$ 382.039,89</td>
                    <td class="text-center">R$ 230.600,00</td>
                    <td class="text-center">R$ 380.900,00</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- FIGURAS 1 E 2 LADO A LADO -->
    <div class="grid-2col" style="flex-grow: 1; align-items: center;">
        <div class="fig-box">
            <img class="fig-img" src="{fig1_b64}" alt="Figura 1: Curva de Capital">
            <div class="fig-caption">Figura 1: Curva de Capital (Base 100) — Aegis (+424,8%) vs CDI (+282,0%), IDIV (+280,9%) e Ibovespa (+130,6%).</div>
        </div>
        <div class="fig-box">
            <img class="fig-img" src="{fig2_b64}" alt="Figura 2: Alpha Acumulado sobre CDI">
            <div class="fig-caption">Figura 2 (Figura Central): ALPHA Acumulado sobre a Taxa CDI (pontos percentuais) com destaque aos ciclos macroeconômicos.</div>
        </div>
    </div>
</div>

<!-- ========================================== -->
<!-- PÁGINA 4: PERFIL DE RISCO E OUT-OF-SAMPLE EXPANDIDOS -->
<!-- ========================================== -->
<div class="slide">
    <div class="slide-header">
        <div class="slide-title">
            <span>📉 Perfil de Risco e Diagnóstico Out-of-Sample (2020–2026)</span>
            <span class="slide-badge">Tópicos 5 (Cont.) e 6</span>
        </div>
        <div class="slide-page-num">Página 4 de 5</div>
    </div>

    <div class="grid-2col">
        <!-- COLUNA ESQUERDA: FIGURA 3 EM DESTAQUE E PERFIL DE RISCO -->
        <div class="col">
            <div class="fig-box" style="padding: 3px;">
                <img class="fig-img" src="{fig3_b64}" alt="Figura 3: Curvas de Drawdown Temporal" style="max-height: 52mm;">
                <div class="fig-caption" style="font-size: 7pt;">Figura 3: Curvas de Drawdown Temporal ao Longo do Ciclo Completo (Aegis -18,09% vs IDIV -38,50% e Ibov -49,17%).</div>
            </div>

            <div class="card-dense card-highlight-green">
                <div class="card-dense-header">
                    <span>Perfil de Risco e Preservação Sistemática de Capital</span>
                </div>
                <div class="card-dense-body">
                    <p>
                        A disciplina algorítmica do <strong>Sparky</strong> conteve as perdas patrimoniais nos maiores testes de estresse da história da B3:
                    </p>
                    <ul class="dense-list">
                        <li><strong>Crise Fiscal de 2014–2016:</strong> Drawdown máximo contido em <strong>-18,09%</strong> contra colapso de <strong>-49,17%</strong> do Ibovespa;</li>
                        <li><strong>Corona Crash de 2020:</strong> Queda limitada a <strong>-15,96%</strong> (vs <strong>-38,50%</strong> do IDIV e <strong>-45,0%</strong> do Ibov), com recuperação completa em apenas 319 dias;</li>
                        <li><strong>Mitigação de Volatilidade:</strong> Volatilidade anualizada de <strong>12,22% a.a.</strong> (redução de 48% frente aos 23,48% a.a. do Ibovespa), garantindo conforto ao investidor.</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- COLUNA DIREITA: TÓPICO 6 - DIAGNÓSTICO OOS EXPANDIDO -->
        <div class="col">
            <div class="card-dense card-highlight-orange">
                <div class="card-dense-header">
                    <span>6. Diagnóstico Transparente da Janela Out-of-Sample (OOS 2020–2026)</span>
                </div>
                <div class="card-dense-body">
                    <p>
                        Com total transparência perante a banca, reporta-se a perda de Alpha na janela OOS: CAGR de <strong>9,26% a.a.</strong> (vs 9,77% a.a. do CDI e 9,75% a.a. do IDIV), Alpha OOS de <span class="text-red"><strong>-0,76% a.a.</strong></span>, Sharpe de <span class="text-red"><strong>-0,052</strong></span> e turnover médio de <strong>59,4%/mês</strong>.
                    </p>
                </div>
            </div>

            <div class="card-dense">
                <div class="card-dense-header">
                    <span>Três Vetores Econométricos do Underperformance Recente</span>
                </div>
                <div class="card-dense-body">
                    <ol class="dense-list">
                        <li>
                            <strong>Choque de Juros Reais & Efeito Duration:</strong> A rápida elevação da Selic de 2,0% para 13,75% a.a. elevou a taxa de desconto aplicada aos fluxos de caixa de longo prazo das empresas de concessão pública (<em>utilities</em>), provocando forte contração de múltiplos de mercado;
                        </li>
                        <li>
                            <strong>Rigidez da Taxa de Desconto de Bazin (6,0% Fixo):</strong> A exigência estática de 6,0% de yield tornou-se permissiva em um cenário de CDI de dois dígitos (13,75% a.a.), reduzindo o prêmio de risco relativo exigido para a alocação em ações;
                        </li>
                        <li>
                            <strong>Atrito de Rebalanceamento em Mercados Laterais (Whipsaw Effect):</strong> A ausência de tendência direcional na B3 provocou rotações limítrofes recorrentes entre ativos elegíveis, gerando turnover de 712% anualizado e erosão de retorno por custos.
                        </li>
                    </ol>
                </div>
            </div>

            <div class="card-dense card-highlight-blue">
                <div class="card-dense-header">
                    <span>Proposta Integrada de Aprimoramento Futuro</span>
                </div>
                <div class="card-dense-body">
                    <p>
                        (1) <strong>Preço Teto Dinâmico:</strong> <span class="formula-dense">Yield<sub>mín,t</sub> = max(6%, CDI<sub>meta,t</sub> &times; 0,60 + 2%)</span>; (2) <strong>Holding Period Obrigatório:</strong> Janela mínima de 3 meses para amortecer o turnover para a meta de 10% a 15%/mês; (3) <strong>Volatility Targeting:</strong> Redimensionamento de posições inversamente proporcional à volatilidade realizada.
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- ========================================== -->
<!-- PÁGINA 5: AUDITORIA DSR E IA GENERATIVA EXPANDIDOS -->
<!-- ========================================== -->
<div class="slide">
    <div class="slide-header">
        <div class="slide-title">
            <span>🧪 Auditoria Estatística DSR e Arquitetura de IA Generativa</span>
            <span class="slide-badge">Tópicos 7 e 8</span>
        </div>
        <div class="slide-page-num">Página 5 de 5</div>
    </div>

    <div class="grid-2col">
        <!-- COLUNA ESQUERDA: TÓPICO 7 - DSR E OVERFITTING EXPANDIDO -->
        <div class="col">
            <div class="card-dense">
                <div class="card-dense-header">
                    <span>7. Auditoria Estatística da Grade e Deflated Sharpe Ratio (DSR)</span>
                </div>
                <div class="card-dense-body">
                    <div style="font-size: 8pt; font-weight: bold; color: #0F2D59; margin-bottom: 2px;">
                        Tabela 2: Top 5 Parametrizações da Grade Experimental (N = 144)
                    </div>
                    <table class="table-expanded">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>L_trend</th>
                                <th>N_ações</th>
                                <th>SMA / Bazin</th>
                                <th>Custos</th>
                                <th>Retorno</th>
                                <th>ALPHA</th>
                                <th>Sharpe</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><code>EXP_049</code></td>
                                <td class="text-center">150d</td>
                                <td class="text-center">6</td>
                                <td class="text-center">1.20 / On</td>
                                <td class="text-center">0 bps</td>
                                <td class="text-center">+500,5%</td>
                                <td class="text-center text-green">+3,51%</td>
                                <td class="text-center"><strong>0.299</strong></td>
                            </tr>
                            <tr>
                                <td><code>EXP_061</code></td>
                                <td class="text-center">150d</td>
                                <td class="text-center">8</td>
                                <td class="text-center">1.20 / On</td>
                                <td class="text-center">0 bps</td>
                                <td class="text-center">+445,4%</td>
                                <td class="text-center text-green">+2,75%</td>
                                <td class="text-center"><strong>0.281</strong></td>
                            </tr>
                            <tr>
                                <td><code>EXP_097</code>*</td>
                                <td class="text-center">200d</td>
                                <td class="text-center">8</td>
                                <td class="text-center">1.20 / On</td>
                                <td class="text-center">0 bps</td>
                                <td class="text-center">+439,6%</td>
                                <td class="text-center text-green">+2,67%</td>
                                <td class="text-center"><strong>0.267</strong></td>
                            </tr>
                            <tr>
                                <td><code>EXP_050</code></td>
                                <td class="text-center">150d</td>
                                <td class="text-center">6</td>
                                <td class="text-center">1.20 / On</td>
                                <td class="text-center">8 bps</td>
                                <td class="text-center">+462,8%</td>
                                <td class="text-center text-green">+3,00%</td>
                                <td class="text-center"><strong>0.264</strong></td>
                            </tr>
                            <tr>
                                <td><code>EXP_001</code></td>
                                <td class="text-center">100d</td>
                                <td class="text-center">4</td>
                                <td class="text-center">1.20 / On</td>
                                <td class="text-center">0 bps</td>
                                <td class="text-center">+522,1%</td>
                                <td class="text-center text-green">+3,79%</td>
                                <td class="text-center"><strong>0.263</strong></td>
                            </tr>
                        </tbody>
                    </table>

                    <p style="margin-top: 3px;">
                        <strong>Framework de López de Prado (2014):</strong><br>
                        Grade: <span class="formula-dense">N<sub>trials</sub> = 144</span>, <span class="formula-dense">SR<sub>max</sub> = 0,2993</span>, <span class="formula-dense">SR<sub>médio</sub> = -0,0527</span>, <span class="formula-dense">&sigma;<sub>SR</sub> = 0,2056</span>, <span class="formula-dense">Skew = +0,0669</span>, <span class="formula-dense">Kurt = -1,5472</span> e Sharpe Esperado ao Acaso <span class="formula-dense">E[max(SR)] = 0,5461</span>.
                    </p>
                    <p>
                        <strong>Rigor Anti-Overfitting:</strong> Como <span class="formula-dense">SR<sub>max</sub> (0,2993) &lt; E[max(SR)] (0,5461)</span>, a econometria quantitativa alerta que seleção cega de parâmetros infla o risco de <em>data snooping</em>. Rejeitamos modelos sem fricção e fixamos o robô em parâmetros clássicos e defensivos.
                    </p>
                </div>
            </div>
        </div>

        <!-- COLUNA DIREITA: TÓPICO 8 - IA GENERATIVA EXPANDIDO -->
        <div class="col">
            <div class="card-dense card-highlight-blue">
                <div class="card-dense-header">
                    <span>8. Arquitetura de IA Generativa: Sparky NLP e Red Teaming</span>
                </div>
                <div class="card-dense-body">
                    <p>
                        <strong>Módulo Sparky Regulatory & Macro AI:</strong> Pipeline de LLM integrada à esteira:
                    </p>
                    <ul class="dense-list">
                        <li><strong>Análise de Atas Copom e Focus:</strong> Extração de sentimento macro via NLP para parametrização dinâmica da taxa de desconto do Preço Teto Bazin;</li>
                        <li><strong>Triagem de Fatos Relevantes (CVM, ANEEL, ARSESP, SUSEP):</strong> Score de Risco Qualitativo (<span class="formula-dense">S<sub>LLM,i,t</sub> &isin; [0,1]</span>) para veto preventivo a litígios e revisões adversas.</li>
                    </ul>

                    <div style="font-size: 8pt; font-weight: bold; color: #0F2D59; margin: 3px 0 2px 0;">
                        Tabela 3: Esteira Multi-Agente de Engenharia, Auditoria e Red Teaming
                    </div>
                    <table class="table-expanded">
                        <thead>
                            <tr>
                                <th>Etapa da Esteira</th>
                                <th>Modelo / Agente</th>
                                <th>Aplicação Prática no Projeto</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><strong>Engenharia de Software</strong></td>
                                <td><em>Claude 3.7 / Antigravity</em></td>
                                <td>Desenvolvimento modular dos engines Python (<code>dados.py</code>, <code>estrategia.py</code>, <code>backtest.py</code> e gerador PDF).</td>
                            </tr>
                            <tr>
                                <td><strong>Auditoria de Vieses Quants</strong></td>
                                <td><em>Gemini 3.7 / LLM Agent</em></td>
                                <td>Implementação do DSR de López de Prado e eliminação estrita de look-ahead bias e survivorship bias.</td>
                            </tr>
                            <tr>
                                <td><strong>Red Teaming & Defesa</strong></td>
                                <td><em>LLM Evaluator / Critic</em></td>
                                <td>Simulação de banca avaliadora, detecção da perda de Alpha no OOS e formulação das defesas econométricas.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

</body>
</html>
"""
    return html


def gerar_pdf_16_9():
    print("=" * 70)
    print("  COMPILANDO RELATÓRIO FINAL 16:9 EXPANDIDO (relatorio_final.pdf)")
    print("=" * 70)

    print("1. Gerando documento estruturado em HTML Widescreen 16:9 denso...")
    html = construir_html_16_9()
    with open(HTML_TEMP, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   HTML gerado: {HTML_TEMP}")

    edge_exe = encontrar_executavel_edge()
    if not edge_exe:
        print("   [ERRO] Microsoft Edge não encontrado!")
        return False

    print(f"2. Utilizando motor Headless do Microsoft Edge: {edge_exe}")

    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={OUTPUT_PDF}",
        HTML_TEMP
    ]

    print(f"3. Compilando {OUTPUT_PDF}...")
    res = subprocess.run(cmd, capture_output=True, text=True)

    if os.path.exists(OUTPUT_PDF) and os.path.getsize(OUTPUT_PDF) > 1000:
        reader = pypdf.PdfReader(OUTPUT_PDF)
        total_p = len(reader.pages)
        print("\n" + "=" * 70)
        print(f"  ✅ SUCESSO! RELATÓRIO FINAL GERADO: {OUTPUT_PDF}")
        print(f"  Total Exato de Páginas: {total_p} páginas (Limite do Edital: 5)")
        print(f"  Tamanho do PDF: {os.path.getsize(OUTPUT_PDF)/1024:.1f} KB")
        print("=" * 70)
        return True
    else:
        print(f"   [ERRO] Falha ao gerar PDF. Saída: {res.stderr}")
        return False


if __name__ == "__main__":
    gerar_pdf_16_9()
