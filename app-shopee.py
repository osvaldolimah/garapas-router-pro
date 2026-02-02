import streamlit as st
import pandas as pd
import io
import unicodedata
from PIL import Image # Necessário para abrir imagens
import pytesseract # Motor de OCR
import re # Expressões Regulares para achar os códigos

# Configuração da página
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SISTEMA DE DESIGN (CSS RESPONSIVO E CONSISTENTE PARA 2 UPLOADERS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

    :root {
        --shopee-orange: #EE4D2D;
        --shopee-bg: #F6F6F6;
        --placeholder-color: rgba(49, 51, 63, 0.4); 
    }

    .stApp { 
        background-color: var(--shopee-bg);
        font-family: 'Inter', sans-serif;
    }

    /* Cabeçalho */
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

    /* --- ESTILIZAÇÃO PADRONIZADA PARA TODOS OS UPLOADERS --- */
    /* Aplica o estilo base a todos os botões de upload */
    [data-testid="stFileUploader"] section button {
        background-color: white !important;
        border: 2px solid var(--shopee-orange) !important;
        color: var(--shopee-orange) !important;
        border-radius: 10px !important;
        transition: transform 0.1s active !important;
    }
    [data-testid="stFileUploader"] section button:active { transform: scale(0.98) !important; }
    
    /* Esconde o texto original */
    [data-testid="stFileUploader"] section button div[data-testid="stMarkdownContainer"] p { font-size: 0 !important; }
    
    /* Injeta o texto novo (Usa um truque para diferenciar pelo 'label' invisível) */
    /* Uploader de Excel (Passo 1) */
    [data-testid="stFileUploader"]:has(label[aria-label="Upload Romaneio"]) section button p::before {
        content: "📁 Selecionar Romaneio";
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        visibility: visible;
    }
    /* Uploader de Imagem (Passo 2 - Aba Escanear) */
    [data-testid="stFileUploader"]:has(label[aria-label="Upload Imagem Gaiolas"]) section button p::before {
        content: "📸 Selecionar Foto da Lista";
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        visibility: visible;
    }

    /* Instruções de Arraste (Padronizadas) */
    [data-testid="stFileUploaderDropzoneInstructions"] div span { display: none !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] div::after {
        content: "Arraste o arquivo aqui";
        font-family: 'Inter', sans-serif !important;
        font-size: 16px !important;
        color: var(--placeholder-color) !important;
        visibility: visible !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] small { display: none !important; }

    /* Placeholder do Campo de Texto */
    .stTextInput input::placeholder {
        font-family: 'Inter', sans-serif !important;
        font-size: 16px !important;
        color: var(--placeholder-color) !important;
    }

    /* Botão Principal */
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
        transition: all 0.1s ease !important;
    }
    div.stButton > button:active {
        transform: scale(0.96) !important;
        box-shadow: 0 2px 5px rgba(238, 77, 45, 0.2) !important;
    }

    /* Estilo das Métricas */
    div[data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 10px;
        border-bottom: 3px solid var(--shopee-orange);
    }
    /* Estilo das Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: white;
        padding: 5px;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: nowrap;
        background-color: #f0f0f0;
        border-radius: 8px;
        color: #666;
        font-weight: 600;
        flex: 1; /* Ocupa espaço igual no celular */
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--shopee-orange) !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE LÓGICA (ENGINEERING) ---
def remover_acentos(texto):
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').upper()

def limpar_string(s):
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo):
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

# Função de OCR para ler a imagem
def extrair_gaiolas_da_imagem(imagem_upload):
    try:
        image = Image.open(imagem_upload)
        # Usa o Tesseract para extrair texto (pode-se adicionar lang='por' se configurado)
        texto_extraido = pytesseract.image_to_string(image)
        # Regex para encontrar padrões tipo "B-20", "A - 50", etc.
        # O padrão procura: Letra Maiúscula, espaço/hífen opcional, Dígitos
        padrao = re.compile(r'([A-Z]\s*-\s*\d+)')
        matches = padrao.findall(texto_extraido.upper())
        # Limpa os resultados (remove espaços e hífens para ficar B20)
        gaiolas_limpas = [limpar_string(m) for m in matches]
        # Remove duplicatas mantendo a ordem
        return list(dict.fromkeys(gaiolas_limpas))
    except Exception as e:
        st.error(f"Erro ao ler imagem: {e}. Verifique se o Tesseract está instalado no servidor.")
        return []

# --- CABEÇALHO ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- SESSÃO ---
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visualizacao' not in st.session_state: st.session_state.df_visualizacao = None
if 'modo_operacao' not in st.session_state: st.session_state.modo_operacao = None
if 'df_resumo_imagem' not in st.session_state: st.session_state.df_resumo_imagem = None

# --- TUTORIAL ---
st.markdown("""
<div class="tutorial-section">
    <div class="step-item"><div class="step-badge">1</div><span>Selecione o arquivo <b>.xlsx</b> do romaneio.</span></div>
    <div class="step-item"><div class="step-badge">2</div><span>Digite a <b>Gaiola</b> OU envie uma <b>Foto</b> da lista.</span></div>
    <div class="step-item"><div class="step-badge">3</div><span>Veja os resultados e baixe a rota (se for individual).</span></div>
</div>
""", unsafe_allow_html=True)

# --- INPUTS COM ABAS NO PASSO 2 ---
col_file, col_cage = st.columns([1, 1])

with col_file:
    st.markdown("##### 📥 Passo 1: Romaneio")
    # Label invisível usado pelo CSS para estilizar este botão especificamente
    arquivo_upload = st.file_uploader("Upload Romaneio", type=["xlsx"], label_visibility="collapsed")

with col_cage:
    st.markdown("##### 📦 Passo 2: Seleção")
    # Abas para alternar modos
    tab_digitar, tab_escanear = st.tabs(["⌨️ Digitar", "📸 Escanear"])
    
    with tab_digitar:
        gaiola_alvo_input = st.text_input("", placeholder="Digite sua gaiola aqui", label_visibility="collapsed").strip().upper()
        imagem_gaiolas = None # Garante que não há imagem neste modo
        
    with tab_escanear:
        # Label invisível usado pelo CSS para estilizar este botão especificamente
        imagem_gaiolas = st.file_uploader("Upload Imagem Gaiolas", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        gaiola_alvo_input = "" # Garante que não há texto neste modo

st.markdown("<br>", unsafe_allow_html=True)
# Lógica do botão muda dependendo do que foi preenchido
label_botao = "🚀 PROCESSAR LISTA DA FOTO" if imagem_gaiolas else "🚀 GERAR ROTA INDIVIDUAL"
botao_executar = st.button(label_botao)

# --- PROCESSAMENTO ---
if arquivo_upload and botao_executar:
    # --- MODO 1: PROCESSAMENTO DE IMAGEM (Prioritário se houver imagem) ---
    if imagem_gaiolas:
        st.session_state.modo_operacao = "imagem"
        with st.spinner('📸 Lendo imagem e processando lista...'):
            try:
                lista_gaiolas_imagem = extrair_gaiolas_da_imagem(imagem_gaiolas)
                
                if not lista_gaiolas_imagem:
                    st.warning("⚠️ Nenhum código de gaiola padrão (ex: B-20) encontrado na imagem.")
                else:
                    # Carrega o Excel uma única vez
                    xl = pd.ExcelFile(arquivo_upload)
                    resumo_dados = []

                    # Varre todas as abas para encontrar a coluna certa
                    df_raw_base = None
                    col_gaiola_idx_base = None
                    col_end_idx_base = None

                    for aba in xl.sheet_names:
                        df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                        # Tenta achar a coluna usando a primeira gaiola da lista como teste
                        target_teste = lista_gaiolas_imagem[0]
                        col_idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target_teste).any()), None)
                        if col_idx is not None:
                            df_raw_base = df_raw
                            col_gaiola_idx_base = col_idx
                            # Identifica colunas de endereço
                            for r in range(min(15, len(df_raw))):
                                linha = [str(x).upper() for x in df_raw.iloc[r].values]
                                for i, val in enumerate(linha):
                                    if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA']): col_end_idx_base = i
                            if col_end_idx_base is None:
                                # Fallback se não achar cabeçalho: coluna mais larga da primeira gaiola
                                mask_teste = df_raw[col_gaiola_idx_base].astype(str).apply(limpar_string) == target_teste
                                col_end_idx_base = df_raw[mask_teste].apply(lambda x: x.astype(str).map(len).max()).idxmax()
                            break
                    
                    if df_raw_base is None:
                        st.error("❌ Não foi possível encontrar a coluna de gaiolas no Excel.")
                    else:
                        # Loop principal: processa cada gaiola da lista da imagem
                        for target_gaiola in lista_gaiolas_imagem:
                            mask = df_raw_base[col_gaiola_idx_base].astype(str).apply(limpar_string) == target_gaiola
                            df_filt = df_raw_base[mask].copy()
                            
                            if len(df_filt) > 0:
                                # Calcula paradas únicas
                                stops_unicos = df_filt[col_end_idx_base].apply(extrair_base_endereco).unique()
                                resumo_dados.append({
                                    "Gaiola Detetada": target_gaiola,
                                    "📦 Pacotes": len(df_filt),
                                    "📍 Paradas Reais": len(stops_unicos)
                                })
                        
                        if resumo_dados:
                            st.session_state.df_resumo_imagem = pd.DataFrame(resumo_dados)
                        else:
                            st.warning("⚠️ Nenhuma das gaiolas da imagem foi encontrada neste romaneio.")

            except Exception as e:
                st.error(f"⚠️ Erro crítico no processamento de imagem: {e}")

    # --- MODO 2: PROCESSAMENTO INDIVIDUAL (Texto) ---
    elif gaiola_alvo_input:
        st.session_state.modo_operacao = "texto"
        with st.spinner('⚙️ Organizando carga individual...'):
            try:
                xl = pd.ExcelFile(arquivo_upload)
                target_limpo = limpar_string(gaiola_alvo_input)
                encontrado = False
                for aba in xl.sheet_names:
                    df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                    col_gaiola_idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), None)
                    if col_gaiola_idx is not None:
                        encontrado = True
                        df_filt = df_raw[df_raw[col_gaiola_idx].astype(str).apply(limpar_string) == target_limpo].copy()
                        col_end_idx, col_bairro_idx = None, None
                        for r in range(min(15, len(df_raw))):
                            linha = [str(x).upper() for x in df_raw.iloc[r].values]
                            for i, val in enumerate(linha):
                                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA']): col_end_idx = i
                                if any(t in val for t in ['BAIRRO', 'SETOR']): col_bairro_idx = i
                        if col_end_idx is None: col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()

                        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
                        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
                        
                        saida = pd.DataFrame()
                        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
                        saida['Gaiola'] = df_filt[col_gaiola_idx]
                        bairro = (df_filt[col_bairro_idx].astype(str) + ", ") if col_bairro_idx is not None else ""
                        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", " + bairro + "Fortaleza - CE"

                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer: saida.to_excel(writer, index=False)
                        st.session_state.dados_prontos, st.session_state.df_visualizacao, st.session_state.nome_arquivo = buffer.getvalue(), saida, f"Rota_{gaiola_alvo_input}.xlsx"
                        st.session_state.metricas = {"pacotes": len(saida), "paradas": len(mapa_stops)}
                        break
                if not encontrado: st.error(f"❌ Gaiola '{gaiola_alvo_input}' não encontrada.")
            except Exception as e: st.error(f"⚠️ Erro: {e}")

# --- RESULTADOS (Visualização Condicional) ---
st.markdown("---")

# Visualização do Modo Imagem (Resumo)
if st.session_state.modo_operacao == "imagem" and st.session_state.df_resumo_imagem is not None:
    st.markdown("### 📋 Resumo da Lista Escaneada")
    # Calcula totais
    total_pacotes = st.session_state.df_resumo_imagem["📦 Pacotes"].sum()
    total_paradas = st.session_state.df_resumo_imagem["📍 Paradas Reais"].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("📦 Total Pacotes na Lista", total_pacotes)
    c2.metric("📍 Total Paradas na Lista", total_paradas)
    
    st.dataframe(
        st.session_state.df_resumo_imagem, 
        use_container_width=True, 
        hide_index=True,
         column_config={
            "Gaiola Detetada": st.column_config.TextColumn(alignment="left")
        }
    )

# Visualização do Modo Texto (Detalhado + Download)
elif st.session_state.modo_operacao == "texto" and st.session_state.dados_prontos:
    m = st.session_state.metricas
    c1, c2 = st.columns(2)
    c1.metric("📦 Pacotes", m["pacotes"]); c2.metric("📍 Paradas Reais", m["paradas"])
    
    st.markdown("##### 📊 Visualização da Rota")
    st.dataframe(st.session_state.df_visualizacao, use_container_width=True, hide_index=True)

    st.download_button(label="📥 BAIXAR PLANILHA AGORA", data=st.session_state.dados_prontos, file_name=st.session_state.nome_arquivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)