import streamlit as st
import pandas as pd
import io
import unicodedata
from typing import List, Dict, Optional

# Configuração da página
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONSTANTES ---
TERMOS_COMERCIAIS = [
    'LOJA', 'MERCADO', 'MERCEARIA', 'FARMACIA', 'DROGARIA', 'SHOPPING', 
    'CLINICA', 'HOSPITAL', 'POSTO', 'OFICINA', 'RESTAURANTE', 'LANCHONETE', 
    'PADARIA', 'PANIFICADORA', 'ACADEMIA', 'ESCOLA', 'COLEGIO', 'FACULDADE', 
    'IGREJA', 'TEMPLO', 'EMPRESA', 'LTDA', 'MEI', 'SALA', 'SALAO', 'BARBEARIA', 
    'ESTACIONAMENTO', 'HOTEL', 'SUPERMERCADO', 'AMC', 'ATACADO', 'DISTRIBUIDORA', 
    'AUTOPECAS', 'VIDRAÇARIA', 'LABORATORIO', 'CLUBE', 'ASSOCIACAO', 'BOUTIQUE', 
    'MERCANTIL', 'DEPARTAMENTO', 'VARIEDADES', 'PIZZARIA', 'CHURRASCARIA', 
    'CARNES', 'PEIXARIA', 'FRUTARIA', 'HORTIFRUTI', 'FLORICULTURA'
]

TERMOS_ANULADORES = [
    'FRENTE', 'LADO', 'PROXIMO', 'VIZINHO', 'DEFRONTE', 'ATRAS', 
    'DEPOIS', 'PERTO', 'VIZINHA'
]

# --- SISTEMA DE DESIGN (CSS RESPONSIVO E TRADUÇÃO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

    :root {
        --shopee-orange: #EE4D2D;
        --shopee-bg: #F6F6F6;
        --placeholder-color: rgba(49, 51, 63, 0.4); 
        --success-green: #10B981;
        --info-blue: #3B82F6;
    }

    .stApp { 
        background-color: var(--shopee-bg);
        font-family: 'Inter', sans-serif;
    }

    /* Cabeçalho Responsivo */
    .header-container {
        text-align: center;
        padding: 20px 10px;
        background-color: white;
        border-bottom: 4px solid var(--shopee-orange);
        margin-bottom: 20px;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    .main-title {
        color: var(--shopee-orange);
        font-size: clamp(1.4rem, 5vw, 2.2rem);
        font-weight: 800;
        margin: 0;
    }

    /* Tutorial Section */
    .tutorial-section {
        background: white;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }

    .step-item {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        font-size: 0.9rem;
        color: #555;
    }

    .step-badge {
        background: var(--shopee-orange);
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 12px;
        flex-shrink: 0;
    }

    /* Tabs Customizados */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: white;
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 0 24px;
        font-weight: 600;
        border: 2px solid transparent;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--shopee-orange) !important;
        color: white !important;
        border-color: var(--shopee-orange);
    }

    /* Tradução do Botão de Seleção de Arquivo */
    [data-testid="stFileUploader"] section button div[data-testid="stMarkdownContainer"] p {
        font-size: 0 !important;
    }
    [data-testid="stFileUploader"] section button div[data-testid="stMarkdownContainer"] p::before {
        content: "📁 Selecionar Romaneio";
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        visibility: visible;
    }

    /* Tradução Instrução de Arraste */
    [data-testid="stFileUploaderDropzoneInstructions"] div span {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] div::after {
        content: "Arraste o Romaneio aqui";
        font-family: 'Inter', sans-serif !important;
        font-size: 16px !important;
        color: var(--placeholder-color) !important;
        visibility: visible !important;
        display: block !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] small {
        display: none !important;
    }

    /* Botão Principal Shopee com Efeito de Clique */
    div.stButton > button {
        background-color: var(--shopee-orange) !important;
        color: white !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 60px !important;
        box-shadow: 0 6px 15px rgba(238, 77, 45, 0.3) !important;
        border: none !important;
        transition: all 0.1s ease;
    }
    div.stButton > button:active { transform: scale(0.96); }

    /* Estilo das Métricas */
    div[data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 10px;
        border-bottom: 3px solid var(--shopee-orange);
    }

    /* Info Box */
    .info-box {
        background: #EFF6FF;
        border-left: 4px solid var(--info-blue);
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
        color: #1E40AF;
    }

    .info-box strong {
        color: var(--info-blue);
    }

    /* Badge de Código */
    .codigo-badge {
        display: inline-block;
        background: var(--shopee-orange);
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        margin: 3px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- INICIALIZAÇÃO DA SESSÃO ---
if 'dados_prontos' not in st.session_state:
    st.session_state.dados_prontos = None
if 'df_visualizacao' not in st.session_state:
    st.session_state.df_visualizacao = None
if 'modo_atual' not in st.session_state:
    st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state:
    st.session_state.resultado_multiplas = None

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def remover_acentos(texto: str) -> str:
    """Remove acentos de uma string."""
    return "".join(
        c for c in unicodedata.normalize('NFD', str(texto)) 
        if unicodedata.category(c) != 'Mn'
    ).upper()

@st.cache_data
def limpar_string(s: str) -> str:
    """Remove caracteres não alfanuméricos e converte para maiúsculas."""
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo: str) -> str:
    """Extrai a base do endereço para agrupamento de paradas."""
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def identificar_comercio(endereco: str) -> str:
    """Identifica se o endereço é comercial ou residencial."""
    end_limpo = remover_acentos(endereco)
    for parte in end_limpo.split(','):
        palavras = parte.split()
        for i, palavra in enumerate(palavras):
            p_limpa = "".join(filter(str.isalnum, palavra))
            if any(termo == p_limpa for termo in TERMOS_COMERCIAIS):
                if not any(anul in " ".join(palavras[:i]) for anul in TERMOS_ANULADORES):
                    return "🏪 Comércio"
    return "🏠 Residencial"

def processar_gaiola_unica(df_raw: pd.DataFrame, gaiola_alvo: str, col_gaiola_idx: int) -> Optional[Dict]:
    """
    Processa uma única gaiola e retorna os dados processados.
    
    Returns:
        Dicionário com dados processados ou None se houver erro
    """
    try:
        target_limpo = limpar_string(gaiola_alvo)
        df_filt = df_raw[df_raw[col_gaiola_idx].astype(str).apply(limpar_string) == target_limpo].copy()
        
        if df_filt.empty:
            return None
        
        # Identificar colunas
        col_end_idx, col_bairro_idx = None, None
        for r in range(min(15, len(df_raw))):
            linha = [str(x).upper() for x in df_raw.iloc[r].values]
            for i, val in enumerate(linha):
                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA']):
                    col_end_idx = i
                if any(t in val for t in ['BAIRRO', 'SETOR']):
                    col_bairro_idx = i
        
        if col_end_idx is None:
            col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()
        
        # Processar endereços
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        
        # Criar DataFrame de saída
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
        saida['Gaiola'] = df_filt[col_gaiola_idx]
        saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        bairro = (df_filt[col_bairro_idx].astype(str) + ", ") if col_bairro_idx is not None else ""
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", " + bairro + "Fortaleza - CE"
        
        return {
            'dataframe': saida,
            'pacotes': len(saida),
            'paradas': len(mapa_stops),
            'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])
        }
    
    except Exception as e:
        st.error(f"Erro ao processar gaiola {gaiola_alvo}: {e}")
        return None

def processar_multiplas_gaiolas(arquivo_excel, codigos_gaiola: List[str]) -> Dict[str, Dict]:
    """
    Processa múltiplas gaiolas e retorna resumo de cada uma.
    
    Returns:
        Dicionário com código da gaiola como chave e métricas como valor
    """
    resultados = {}
    
    try:
        xl = pd.ExcelFile(arquivo_excel)
        
        for gaiola in codigos_gaiola:
            target_limpo = limpar_string(gaiola)
            encontrado = False
            
            for aba in xl.sheet_names:
                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                
                # Procurar coluna da gaiola
                col_gaiola_idx = next(
                    (col for col in df_raw.columns 
                     if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), 
                    None
                )
                
                if col_gaiola_idx is not None:
                    resultado = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                    if resultado:
                        resultados[gaiola] = {
                            'pacotes': resultado['pacotes'],
                            'paradas': resultado['paradas'],
                            'comercios': resultado['comercios'],
                            'encontrado': True
                        }
                        encontrado = True
                        break
            
            if not encontrado:
                resultados[gaiola] = {
                    'pacotes': 0,
                    'paradas': 0,
                    'comercios': 0,
                    'encontrado': False
                }
        
        return resultados
    
    except Exception as e:
        st.error(f"Erro ao processar múltiplas gaiolas: {e}")
        return {}

# --- TUTORIAL ---
st.markdown("""
<div class="tutorial-section">
    <div class="step-item"><div class="step-badge">1</div><span>Selecione o arquivo <b>.xlsx</b> do romaneio.</span></div>
    <div class="step-item"><div class="step-badge">2</div><span>Escolha: Digite <b>uma gaiola</b> OU digite <b>várias gaiolas</b>.</span></div>
    <div class="step-item"><div class="step-badge">3</div><span>Baixe a planilha ou visualize o resumo.</span></div>
</div>
""", unsafe_allow_html=True)

# --- PASSO 1: UPLOAD DO ROMANEIO ---
st.markdown("##### 📥 Passo 1: Upload do Romaneio")
arquivo_upload = st.file_uploader(
    "Selecione o arquivo Excel", 
    type=["xlsx"], 
    label_visibility="collapsed",
    key="romaneio_upload"
)

st.markdown("<br>", unsafe_allow_html=True)

# --- PASSO 2: ESCOLHA DO MODO ---
st.markdown("##### 📦 Passo 2: Escolha o Modo de Processamento")

tab1, tab2 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas"])

with tab1:
    st.markdown("""
    <div class="info-box">
        <strong>💡 Modo Gaiola Única:</strong> Digite o código de uma gaiola para gerar 
        a rota completa com endereços detalhados e pré-visualização.
    </div>
    """, unsafe_allow_html=True)
    
    gaiola_unica = st.text_input(
        "Digite o código da gaiola", 
        placeholder="Ex: A-38, C-42, ABC123",
        label_visibility="collapsed",
        key="gaiola_unica_input"
    ).strip().upper()
    
    botao_gaiola_unica = st.button(
        "🚀 GERAR ROTA DA GAIOLA", 
        key="btn_unica",
        use_container_width=True
    )
    
    if botao_gaiola_unica:
        st.session_state.modo_atual = 'unica'

with tab2:
    st.markdown("""
    <div class="info-box">
        <strong>💡 Modo Múltiplas Gaiolas:</strong> Digite os códigos de várias gaiolas 
        (um por linha) para obter um resumo rápido com pacotes e paradas de cada uma. 
        <b>Não inclui pré-visualização de endereços.</b>
    </div>
    """, unsafe_allow_html=True)
    
    codigos_multiplas = st.text_area(
        "Digite os códigos das gaiolas (um por linha)",
        placeholder="A-38\nA-41\nA-47\nA-48\nC-6\nA-3\nC-42",
        height=200,
        key="codigos_multiplas",
        label_visibility="collapsed"
    )
    
    # Mostrar preview dos códigos detectados
    if codigos_multiplas:
        codigos_lista = [c.strip().upper() for c in codigos_multiplas.split('\n') if c.strip()]
        
        if codigos_lista:
            codigos_html = "".join([f'<span class="codigo-badge">{cod}</span>' for cod in codigos_lista])
            st.markdown(
                f"<div style='margin: 10px 0;'>✅ <b>{len(codigos_lista)} código(s) detectado(s):</b><br>{codigos_html}</div>", 
                unsafe_allow_html=True
            )
    
    botao_multiplas = st.button(
        "📊 PROCESSAR MÚLTIPLAS GAIOLAS", 
        key="btn_multiplas",
        use_container_width=True
    )
    
    if botao_multiplas:
        st.session_state.modo_atual = 'multiplas'

# --- PROCESSAMENTO ---

# MODO: GAIOLA ÚNICA
if arquivo_upload is not None and gaiola_unica and st.session_state.modo_atual == 'unica' and botao_gaiola_unica:
    with st.spinner('⚙️ Organizando carga da gaiola...'):
        try:
            xl = pd.ExcelFile(arquivo_upload)
            target_limpo = limpar_string(gaiola_unica)
            encontrado = False
            
            for aba in xl.sheet_names:
                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                col_gaiola_idx = next(
                    (col for col in df_raw.columns 
                     if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), 
                    None
                )
                
                if col_gaiola_idx is not None:
                    resultado = processar_gaiola_unica(df_raw, gaiola_unica, col_gaiola_idx)
                    
                    if resultado:
                        encontrado = True
                        saida = resultado['dataframe']
                        
                        # Gerar arquivo Excel
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            saida.to_excel(writer, index=False)
                        
                        st.session_state.dados_prontos = buffer.getvalue()
                        st.session_state.df_visualizacao = saida
                        st.session_state.nome_arquivo = f"Rota_{gaiola_unica}.xlsx"
                        st.session_state.metricas = {
                            "pacotes": resultado['pacotes'],
                            "paradas": resultado['paradas'],
                            "comercios": resultado['comercios']
                        }
                        break
            
            if not encontrado:
                st.error(f"❌ Gaiola '{gaiola_unica}' não encontrada no romaneio.")
        
        except Exception as e:
            st.error(f"⚠️ Erro ao processar: {e}")

# MODO: MÚLTIPLAS GAIOLAS
if arquivo_upload is not None and codigos_multiplas and st.session_state.modo_atual == 'multiplas' and botao_multiplas:
    codigos_lista = [c.strip().upper() for c in codigos_multiplas.split('\n') if c.strip()]
    
    if not codigos_lista:
        st.warning("⚠️ Por favor, digite pelo menos um código de gaiola.")
    else:
        with st.spinner(f'⚙️ Processando {len(codigos_lista)} gaiola(s)...'):
            try:
                resultados = processar_multiplas_gaiolas(arquivo_upload, codigos_lista)
                st.session_state.resultado_multiplas = resultados
            except Exception as e:
                st.error(f"⚠️ Erro ao processar: {e}")

# --- EXIBIÇÃO DE RESULTADOS ---

# Resultado para GAIOLA ÚNICA
if st.session_state.dados_prontos and st.session_state.modo_atual == 'unica':
    st.markdown("---")
    st.markdown("### 📊 Resultado da Rota")
    
    m = st.session_state.metricas
    c1, c2, c3 = st.columns(3)
    c1.metric("📦 Pacotes", m["pacotes"])
    c2.metric("📍 Paradas", m["paradas"])
    c3.metric("🏪 Comércios", m["comercios"])
    
    st.markdown("##### 📋 Visualização Completa da Rota")
    st.dataframe(
        st.session_state.df_visualizacao, 
        use_container_width=True, 
        hide_index=True,
        height=400
    )
    
    st.download_button(
        label="📥 BAIXAR PLANILHA COMPLETA", 
        data=st.session_state.dados_prontos, 
        file_name=st.session_state.nome_arquivo, 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        use_container_width=True
    )

# Resultado para MÚLTIPLAS GAIOLAS
if st.session_state.resultado_multiplas and st.session_state.modo_atual == 'multiplas':
    st.markdown("---")
    st.markdown("### 📊 Resumo das Gaiolas Processadas")
    
    resultados = st.session_state.resultado_multiplas
    
    # Contagem de gaiolas encontradas
    gaiolas_encontradas = sum(1 for r in resultados.values() if r['encontrado'])
    
    # Métrica de gaiolas encontradas
    st.metric("🎯 Gaiolas Encontradas", f"{gaiolas_encontradas}/{len(resultados)}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabela detalhada
    st.markdown("##### 📋 Detalhamento por Gaiola")
    
    df_resumo = pd.DataFrame([
        {
            'Gaiola': codigo,
            'Status': '✅ Encontrada' if dados['encontrado'] else '❌ Não encontrada',
            'Pacotes': dados['pacotes'],
            'Paradas': dados['paradas'],
            'Comércios': dados['comercios']
        }
        for codigo, dados in resultados.items()
    ])
    
    st.dataframe(
        df_resumo,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Opção de exportar resumo
    buffer_resumo = io.BytesIO()
    with pd.ExcelWriter(buffer_resumo, engine='openpyxl') as writer:
        df_resumo.to_excel(writer, index=False, sheet_name='Resumo')
    
    st.download_button(
        label="📥 BAIXAR RESUMO EM EXCEL", 
        data=buffer_resumo.getvalue(), 
        file_name="Resumo_Multiplas_Gaiolas.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        use_container_width=True
    )
    
    # Avisos sobre gaiolas não encontradas
    nao_encontradas = [codigo for codigo, dados in resultados.items() if not dados['encontrado']]
    if nao_encontradas:
        st.warning(f"⚠️ Gaiolas não encontradas no romaneio: {', '.join(nao_encontradas)}")
    
    # --- SEÇÃO DE DOWNLOAD INDIVIDUAL ---
    st.markdown("---")
    st.markdown("### 📥 Baixar Planilhas Individuais para Circuit")
    
    st.markdown("""
    <div class="info-box">
        <strong>💡 Selecione as gaiolas:</strong> Marque as caixas abaixo para gerar planilhas 
        completas (com endereços) no formato do Circuit.
    </div>
    """, unsafe_allow_html=True)
    
    # Filtrar apenas gaiolas encontradas
    gaiolas_encontradas_lista = [codigo for codigo, dados in resultados.items() if dados['encontrado']]
    
    if not gaiolas_encontradas_lista:
        st.info("ℹ️ Nenhuma gaiola encontrada para gerar planilhas individuais.")
    else:
        # Criar checkboxes para cada gaiola encontrada
        st.markdown("##### ✅ Selecione as gaiolas:")
        
        # Organizar em colunas para melhor visual
        num_colunas = 3
        colunas = st.columns(num_colunas)
        
        gaiolas_selecionadas = []
        for idx, codigo in enumerate(gaiolas_encontradas_lista):
            col_idx = idx % num_colunas
            with colunas[col_idx]:
                pacotes = resultados[codigo]['pacotes']
                paradas = resultados[codigo]['paradas']
                
                if st.checkbox(
                    f"**{codigo}** ({pacotes} pacotes, {paradas} paradas)",
                    key=f"checkbox_{codigo}"
                ):
                    gaiolas_selecionadas.append(codigo)
        
        # Botão para gerar planilhas das selecionadas
        if gaiolas_selecionadas:
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button(
                f"📥 GERAR PLANILHAS DAS {len(gaiolas_selecionadas)} GAIOLA(S) SELECIONADA(S)",
                key="btn_gerar_individuais",
                use_container_width=True
            ):
                with st.spinner(f'⚙️ Gerando planilhas de {len(gaiolas_selecionadas)} gaiola(s)...'):
                    try:
                        xl = pd.ExcelFile(arquivo_upload)
                        planilhas_geradas = {}
                        
                        for gaiola in gaiolas_selecionadas:
                            target_limpo = limpar_string(gaiola)
                            
                            # Buscar e processar a gaiola
                            for aba in xl.sheet_names:
                                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                                
                                col_gaiola_idx = next(
                                    (col for col in df_raw.columns 
                                     if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), 
                                    None
                                )
                                
                                if col_gaiola_idx is not None:
                                    resultado = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                                    
                                    if resultado:
                                        # Gerar Excel individual
                                        buffer_individual = io.BytesIO()
                                        with pd.ExcelWriter(buffer_individual, engine='openpyxl') as writer:
                                            resultado['dataframe'].to_excel(writer, index=False)
                                        
                                        planilhas_geradas[gaiola] = buffer_individual.getvalue()
                                        break
                        
                        # Mostrar planilhas geradas
                        if planilhas_geradas:
                            st.success(f"✅ {len(planilhas_geradas)} planilha(s) gerada(s) com sucesso!")
                            
                            st.markdown("##### 📥 Download das Planilhas:")
                            
                            # Criar colunas para os botões de download
                            cols_download = st.columns(min(3, len(planilhas_geradas)))
                            
                            for idx, (gaiola, dados_excel) in enumerate(planilhas_geradas.items()):
                                col_idx = idx % 3
                                with cols_download[col_idx]:
                                    st.download_button(
                                        label=f"📄 {gaiola}",
                                        data=dados_excel,
                                        file_name=f"Rota_{gaiola}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key=f"download_{gaiola}",
                                        use_container_width=True
                                    )
                        else:
                            st.error("❌ Erro ao gerar planilhas. Tente novamente.")
                    
                    except Exception as e:
                        st.error(f"⚠️ Erro ao gerar planilhas: {e}")