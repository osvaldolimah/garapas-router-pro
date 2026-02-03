import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional
from google import genai
from google.genai.types import HttpOptions

# --- CONFIGURAÇÃO DA PÁGINA (MARCO ZERO) ---
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONSTANTES (MARCO ZERO) ---
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

# --- SISTEMA DE DESIGN (MARCO ZERO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; --placeholder-color: rgba(49, 51, 63, 0.4); }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { color: var(--shopee-orange); font-size: clamp(1.4rem, 5vw, 2.2rem); font-weight: 800; margin: 0; }
    .tutorial-section { background: white; padding: 15px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: white; padding: 10px; border-radius: 15px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f0f0; border-radius: 10px; padding: 0 24px; font-weight: 600; border: 2px solid transparent; }
    .stTabs [aria-selected="true"] { background-color: var(--shopee-orange) !important; color: white !important; border-color: var(--shopee-orange); }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .info-box { background: #EFF6FF; border-left: 4px solid var(--info-blue); padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    .success-box { background: #F0FDF4; border-left: 4px solid var(--success-green); padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- SESSÃO ---
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visualizacao' not in st.session_state: st.session_state.df_visualizacao = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'arquivo_atual' not in st.session_state: st.session_state.arquivo_atual = None

# --- FUNÇÕES AUXILIARES (LOGICA MARCO ZERO) ---
@st.cache_data
def remover_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').upper()

@st.cache_data
def limpar_string(s: str) -> str:
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo: str) -> str:
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def identificar_comercio(endereco: str) -> str:
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
        if df_filt.empty: return None
        col_end_idx = None
        for r in range(min(15, len(df_raw))):
            linha = [str(x).upper() for x in df_raw.iloc[r].values]
            for i, val in enumerate(linha):
                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA', 'ADDRESS']):
                    col_end_idx = i; break
            if col_end_idx is not None: break
        if col_end_idx is None: col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
        saida['Gaiola'] = df_filt[col_gaiola_idx]; saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", Fortaleza - CE"
        return {'dataframe': saida, 'pacotes': len(saida), 'paradas': len(mapa_stops), 'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])}
    except Exception as e: return None

# --- IA: INICIALIZAÇÃO CORRIGIDA PARA 2026 ---
def inicializar_ia() -> Optional[genai.Client]:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key, http_options=HttpOptions(api_version='v1'))
    except Exception: return None

def agente_ia_treinado(client: genai.Client, df: pd.DataFrame, pergunta: str) -> str:
    try:
        match_gaiola = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())
        contexto_dados = ""
        if match_gaiola:
            g_alvo = limpar_string(match_gaiola.group(1))
            for col in df.columns:
                df_target = df[df[col].astype(str).apply(limpar_string) == g_alvo]
                if not df_target.empty:
                    contexto_dados = f"DADOS DA GAIOLA {g_alvo}:\n{df_target.head(100).to_string()}"
                    break
        if not contexto_dados: contexto_dados = f"AMOSTRA:\n{df.head(50).to_string()}"
        
        prompt = f"Você é o Waze Humano em Fortaleza. Use estes termos comerciais: {TERMOS_COMERCIAIS}. Romaneio: {contexto_dados}"
        response = client.models.generate_content(model='gemini-2.5-flash', contents=f"{prompt}\nPergunta: {pergunta}")
        return response.text
    except Exception as e:
        if "API_KEY_INVALID" in str(e) or "403" in str(e):
            return "❌ **API Key do Gemini inválida ou expirada**. Verifique os Secrets do Streamlit."
        return f"❌ **Erro na IA:** {str(e)[:100]}"

# --- INTERFACE ---
arquivo_upload = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed", key="romaneio_upload")

if arquivo_upload:
    if st.session_state.df_cache is None:
        st.session_state.df_cache = pd.read_excel(arquivo_upload)
    
    df_completo = st.session_state.df_cache
    tab1, tab2, tab3 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "🤖 Agente IA"])

    with tab1: # MARCO ZERO
        g_unica = st.text_input("Gaiola única", key="gui").strip().upper()
        if st.button("🚀 GERAR ROTA", key="btn_u"):
            # Lógica original de processamento...
            st.info("Processando...")

    with tab3: # AGENTE IA
        p_ia = st.text_input("Pergunta para a IA:", key="pergunta_ia")
        if st.button("🧠 CONSULTAR AGENTE IA", key="btn_ia", use_container_width=True):
            cliente = inicializar_ia()
            if cliente:
                resp = agente_ia_treinado(cliente, df_completo, p_ia)
                if "inválida" in resp: st.error(resp)
                else: st.markdown(f'<div class="success-box"><strong>✅ Resposta:</strong><br>{resp}</div>', unsafe_allow_html=True)
            else: st.error("❌ API Key não encontrada nos Secrets.")
else:
    st.info("📁 Aguardando romaneio para iniciar.")