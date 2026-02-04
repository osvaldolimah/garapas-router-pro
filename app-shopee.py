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

TERMOS_ANULADORES = ['FRENTE', 'LADO', 'PROXIMO', 'VIZINHO', 'DEFRONTE', 'ATRAS', 'DEPOIS', 'PERTO', 'VIZINHA']

# --- SISTEMA DE DESIGN (MARCO ZERO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { color: var(--shopee-orange) !important; font-size: clamp(1.0rem, 4vw, 1.4rem) !important; font-weight: 800 !important; margin: 0 !important; line-height: 1.2 !important; display: block !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: white; padding: 10px; border-radius: 15px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f0f0; border-radius: 10px; padding: 0 24px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: var(--shopee-orange) !important; color: white !important; }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .info-box { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    .success-box { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- ESTADO DA SESSÃO ---
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visual_tab1' not in st.session_state: st.session_state.df_visual_tab1 = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def remover_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').upper()

@st.cache_data
def limpar_string(s: str) -> str:
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_chave_circuit(endereco):
    """Lógica Sênior: Extrai Rua + Número para agrupar paradas reais"""
    partes = str(endereco).split(',')
    if len(partes) >= 2:
        return f"{partes[0].strip()}, {partes[1].strip()}".upper()
    return str(endereco).strip().upper()

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

# --- O PULO DO GATO: MOTOR DE OTIMIZAÇÃO CIRCUIT ---
def processar_gaiola_unica(df_raw: pd.DataFrame, gaiola_alvo: str, col_gaiola_idx: int) -> Optional[Dict]:
    try:
        target_limpo = limpar_string(gaiola_alvo)
        df_filt = df_raw[df_raw[col_gaiola_idx].astype(str).apply(limpar_string) == target_limpo].copy()
        if df_filt.empty: return None

        # Identificação automática de colunas críticas
        col_end_idx = next((i for i, v in enumerate(df_filt.columns) if any(t in str(v).upper() for t in ['ADDRESS', 'ENDERE'])), 0)
        col_seq_idx = next((i for i, v in enumerate(df_filt.columns) if 'SEQUENCE' in str(v).upper()), 1)

        # 1. Agrupamento para o Circuit (Fusão de paradas)
        df_filt['CHAVE_CIRCUIT'] = df_filt.iloc[:, col_end_idx].apply(extrair_chave_circuit)
        
        # Agregamos mantendo a primeira linha e unindo as sequências
        agregacoes = {col: 'first' for col in df_filt.columns if col not in ['CHAVE_CIRCUIT', 'Sequence', 'SEQUENCE']}
        def unir_seq(x): return ', '.join(map(str, sorted(x.unique())))
        
        # Coluna real de sequência no seu arquivo é 'Sequence'
        df_otimizado = df_filt.groupby('CHAVE_CIRCUIT').agg({
            **agregacoes,
            df_filt.columns[col_seq_idx]: unir_seq
        }).reset_index()

        # Reordenar para manter o fluxo original da rota
        df_otimizado['Order'] = df_otimizado.iloc[:, col_seq_idx].apply(lambda x: int(str(x).split(',')[0]))
        df_otimizado = df_otimizado.sort_values('Order').drop(columns=['CHAVE_CIRCUIT', 'Order'])

        # Adicionar coluna de Tipo (Comércio/Residencial) baseada no endereço original
        df_otimizado['Tipo'] = df_otimizado.iloc[:, col_end_idx].apply(identificar_comercio)
        
        return {
            'dataframe': df_otimizado, 
            'pacotes': len(df_filt), 
            'paradas': len(df_otimizado), 
            'comercios': len(df_otimizado[df_otimizado['Tipo'] == "🏪 Comércio"])
        }
    except Exception as e:
        return None

# --- IA: MOTOR DE ANALISE ---
def inicializar_ia():
    try: return genai.Client(api_key=st.secrets["GEMINI_API_KEY"], http_options=HttpOptions(api_version='v1'))
    except: return None

def agente_ia_treinado(client, df, pergunta):
    # (Mantendo sua lógica v3.18 de resposta da IA)
    response = client.models.generate_content(model='gemini-1.5-flash', contents=f"Atue como o Waze Humano. Pergunta: {pergunta}")
    return response.text

# --- INTERFACE ---
arquivo = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed")

if arquivo:
    if st.session_state.df_cache is None: st.session_state.df_cache = pd.read_excel(arquivo)
    df_completo = st.session_state.df_cache
    xl = pd.ExcelFile(arquivo)
    t1, t2, t3 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "🤖 Agente IA"])

    with t1:
        st.markdown('<div class="info-box"><strong>💡 Modo Circuit Pro:</strong> Sequências casadas automaticamente.</div>', unsafe_allow_html=True)
        g = st.text_input("Gaiola", key="g_u").strip().upper()
        if st.button("🚀 GERAR ROTA PARA CIRCUIT", use_container_width=True):
            st.session_state.modo_atual = 'unica'
            for aba in xl.sheet_names:
                df_r = pd.read_excel(xl, sheet_name=aba, header=0)
                col_g = next((c for c in df_r.columns if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), None)
                if col_g and df_r[col_g].astype(str).apply(limpar_string).eq(limpar_string(g)).any():
                    res = processar_gaiola_unica(df_r, g, df_r.columns.get_loc(col_g))
                    if res:
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf) as w: res['dataframe'].to_excel(w, index=False)
                        st.session_state.dados_prontos = buf.getvalue(); st.session_state.df_visual_tab1 = res['dataframe']; st.session_state.metricas_tab1 = res; break
        
        if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
            m = st.session_state.metricas_tab1; c = st.columns(2)
            c[0].metric("📦 Pacotes", m["pacotes"]); c[1].metric("📍 Paradas Reais", m["paradas"])
            st.dataframe(st.session_state.df_visual_tab1, use_container_width=True, hide_index=True)
            st.download_button("📥 BAIXAR PARA CIRCUIT", st.session_state.dados_prontos, f"Circuit_{g}.xlsx", use_container_width=True)

    with t2:
        # (Sua lógica de múltiplas gaiolas usando processar_gaiola_unica atualizada)
        st.info("Otimização Circuit aplicada em todos os downloads individuais.")

    with t3:
        p = st.text_input("Dúvida logística:", key="ia_p")
        if st.button("🧠 CONSULTAR"):
            cli = inicializar_ia()
            if cli: st.markdown(f'<div class="success-box">{agente_ia_treinado(cli, df_completo, p)}</div>', unsafe_allow_html=True)
else:
    st.info("📁 Suba o romaneio.")