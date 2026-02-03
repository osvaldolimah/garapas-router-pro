import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from google import genai
from google.genai.types import HttpOptions
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
    try:
        target_limpo = limpar_string(gaiola_alvo)
        df_filt = df_raw[df_raw[col_gaiola_idx].astype(str).apply(limpar_string) == target_limpo].copy()
        
        if df_filt.empty:
            return None
        
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
        
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        
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
    resultados = {}
    try:
        xl = pd.ExcelFile(arquivo_excel)
        for gaiola in codigos_gaiola:
            target_limpo = limpar_string(gaiola)
            encontrado = False
            for aba in xl.sheet_names:
                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                col_gaiola_idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), None)
                if col_gaiola_idx is not None:
                    resultado = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                    if resultado:
                        resultados[gaiola] = {'pacotes': resultado['pacotes'], 'paradas': resultado['paradas'], 'comercios': resultado['comercios'], 'encontrado': True}
                        encontrado = True
                        break
            if not encontrado:
                resultados[gaiola] = {'pacotes': 0, 'paradas': 0, 'comercios': 0, 'encontrado': False}
        return resultados
    except Exception as e:
        st.error(f"Erro ao processar múltiplas gaiolas: {e}")
        return {}

# --- FUNÇÕES DO AGENTE IA ---
def inicializar_ia():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None
    return genai.Client(api_key=api_key, http_options=HttpOptions(api_version='v1'))

def agente_treinado_ia(client, df, pergunta):
    # Ensinando a IA com os termos do Marco Zero
    regras = f"Você é o Waze Humano. Use estes termos comerciais: {TERMOS_COMERCIAIS}. Considere estes anuladores: {TERMOS_ANULADORES}. Gaiolas seguem padrão C-XX."
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{regras}\nDados: {df.head(100).to_string()}\nPergunta: {pergunta}"
        )
        return response.text
    except Exception as e: return f"IA fora de rota: {e}"

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
arquivo_upload = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"], label_visibility="collapsed", key="romaneio_upload")

st.markdown("<br>", unsafe_allow_html=True)

# --- PASSO 2: ESCOLHA DO MODO ---
if arquivo_upload is not None:
    st.markdown("##### 📦 Passo 2: Escolha o Modo de Processamento")
    # ADICIONADA A TERCEIRA ABA PARA IA
    tab1, tab2, tab3 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "🤖 Agente IA"])

    with tab1:
        st.markdown('<div class="info-box"><strong>💡 Modo Gaiola Única:</strong> Digite o código de uma gaiola.</div>', unsafe_allow_html=True)
        gaiola_unica = st.text_input("Gaiola", placeholder="Ex: C-42", label_visibility="collapsed", key="g_u_i").strip().upper()
        botao_gaiola_unica = st.button("🚀 GERAR ROTA DA GAIOLA", key="btn_u", use_container_width=True)
        if botao_gaiola_unica:
            st.session_state.modo_atual = 'unica'
            # PROCESSAMENTO DIRETO (SEM MUDAR UMA LINHA DA LÓGICA)
            with st.spinner('⚙️ Organizando carga...'):
                xl = pd.ExcelFile(arquivo_upload)
                target_limpo = limpar_string(gaiola_unica)
                encontrado = False
                for aba in xl.sheet_names:
                    df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                    col_gaiola_idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), None)
                    if col_gaiola_idx is not None:
                        resultado = processar_gaiola_unica(df_raw, gaiola_unica, col_gaiola_idx)
                        if resultado:
                            encontrado = True; saida = resultado['dataframe']
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='openpyxl') as writer: saida.to_excel(writer, index=False)
                            st.session_state.dados_prontos = buffer.getvalue()
                            st.session_state.df_visualizacao = saida
                            st.session_state.nome_arquivo = f"Rota_{gaiola_unica}.xlsx"
                            st.session_state.metricas = {"pacotes": resultado['pacotes'], "paradas": resultado['paradas'], "comercios": resultado['comercios']}
                            break
                if not encontrado: st.error(f"❌ Gaiola '{gaiola_unica}' não encontrada.")

    with tab2:
        st.markdown('<div class="info-box"><strong>💡 Modo Múltiplas Gaiolas:</strong> Resumo rápido por linha.</div>', unsafe_allow_html=True)
        codigos_multiplas = st.text_area("Gaiolas", placeholder="C-42\nC-06", height=200, key="c_m", label_visibility="collapsed")
        botao_multiplas = st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", key="btn_m", use_container_width=True)
        if botao_multiplas:
            st.session_state.modo_atual = 'multiplas'
            with st.spinner('⚙️ Processando...'):
                lista = [c.strip().upper() for c in codigos_multiplas.split('\n') if c.strip()]
                if lista: st.session_state.resultado_multiplas = processar_multiplas_gaiolas(arquivo_upload, lista)

    with tab3:
        st.markdown('<div class="info-box"><strong>🤖 Agente IA:</strong> Pergunte sobre o romaneio usando a lógica do Marco Zero.</div>', unsafe_allow_html=True)
        pergunta_ia = st.text_input("O que deseja saber?", placeholder="Ex: Quais gaiolas têm mais comércios?", key="p_ia")
        if st.button("🧠 CONSULTAR AGENTE", use_container_width=True):
            client = inicializar_ia()
            if client:
                df_ia = pd.read_excel(arquivo_upload)
                with st.spinner("IA analisando..."):
                    resp = agente_treinado_ia(client, df_ia, pergunta_ia)
                    st.info(resp)
            else: st.error("GEMINI_API_KEY não configurada nos Secrets.")

    # EXIBIÇÃO DE RESULTADOS (LÓGICA MARCO ZERO PRESERVADA)
    if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
        st.markdown("---")
        m = st.session_state.metricas
        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Pacotes", m["pacotes"]); c2.metric("📍 Paradas", m["paradas"]); c3.metric("🏪 Comércios", m["comercios"])
        st.dataframe(st.session_state.df_visualizacao, use_container_width=True, hide_index=True)
        st.download_button("📥 BAIXAR PLANILHA", st.session_state.dados_prontos, st.session_state.nome_arquivo, use_container_width=True)

    if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
        res = st.session_state.resultado_multiplas
        df_res = pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Pacotes': v['pacotes'], 'Paradas': v['paradas'], 'Comércios': v['comercios']} for k, v in res.items()])
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        buf_res = io.BytesIO()
        with pd.ExcelWriter(buf_res, engine='openpyxl') as w: df_res.to_excel(w, index=False)
        st.download_button("📥 BAIXAR RESUMO", buf_res.getvalue(), "Resumo.xlsx", use_container_width=True)
else:
    st.info("Aguardando romaneio.")