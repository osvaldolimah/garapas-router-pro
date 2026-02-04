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

# --- DESIGN (MARCO ZERO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { color: var(--shopee-orange) !important; font-size: clamp(1.0rem, 4vw, 1.4rem) !important; font-weight: 800 !important; margin: 0 !important; line-height: 1.2 !important; display: block !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: white; padding: 10px; border-radius: 15px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f0f0; border-radius: 10px; padding: 0 20px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: var(--shopee-orange) !important; color: white !important; }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .info-box { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    .success-box { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- SESSÃO ---
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'

# --- FUNÇÕES (MARCO ZERO) ---
@st.cache_data
def limpar_string(s: str) -> str:
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco):
    partes = str(endereco).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def processar_gaiola_padrao(df_raw, gaiola, col_idx):
    """Lógica Marco Zero: Filtragem pura sem fusão de linhas"""
    target = limpar_string(gaiola)
    df_f = df_raw[df_raw[col_idx].astype(str).apply(limpar_string) == target].copy()
    if df_f.empty: return None
    return df_f

# --- FUNÇÕES (NOVA FUNÇÃO CIRCUIT) ---
def extrair_chave_circuit(endereco):
    partes = str(endereco).split(',')
    if len(partes) >= 2:
        return f"{partes[0].strip()}, {partes[1].strip()}".upper()
    return str(endereco).strip().upper()

def processar_gaiola_circuit(df_raw, gaiola, col_idx):
    """Nova Lógica: Funde paradas para o Circuit"""
    df_f = processar_gaiola_padrao(df_raw, gaiola, col_idx)
    if df_f is None: return None
    
    col_end = next((i for i, v in enumerate(df_f.columns) if any(t in str(v).upper() for t in ['ADDRESS', 'ENDERE'])), 0)
    col_seq = next((i for i, v in enumerate(df_f.columns) if 'SEQUENCE' in str(v).upper()), 1)
    
    df_f['CHAVE'] = df_f.iloc[:, col_end].apply(extrair_chave_circuit)
    agreg = {col: 'first' for col in df_f.columns if col not in ['CHAVE', df_f.columns[col_seq]]}
    def unir(x): return ', '.join(map(str, sorted(x.unique())))
    
    df_otimizado = df_f.groupby('CHAVE').agg({**agreg, df_f.columns[col_seq]: unir}).reset_index()
    df_otimizado['Order'] = df_otimizado.iloc[:, col_seq+1].apply(lambda x: int(str(x).split(',')[0]))
    return df_otimizado.sort_values('Order').drop(columns=['CHAVE', 'Order'])

# --- INTERFACE ---
arquivo = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed")

if arquivo:
    if st.session_state.df_cache is None: st.session_state.df_cache = pd.read_excel(arquivo)
    xl = pd.ExcelFile(arquivo)
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas", "⚡ Circuit Pro", "🤖 IA"])

    with tab1:
        st.markdown('<div class="info-box"><strong>🎯 Marco Zero:</strong> Filtragem padrão por gaiola.</div>', unsafe_allow_html=True)
        g_u = st.text_input("Gaiola", key="g_u").upper()
        if st.button("🚀 FILTRAR GAIOLA"):
            for aba in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=aba)
                col_g = next((c for c in df.columns if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), None)
                if col_g and df[col_g].astype(str).apply(limpar_string).eq(limpar_string(g_u)).any():
                    res = processar_gaiola_padrao(df, g_u, df.columns.get_loc(col_g))
                    st.dataframe(res, use_container_width=True)
                    break

    with tab3:
        st.markdown('<div class="success-box"><strong>⚡ Circuit Pro:</strong> Paradas casadas para o App Circuit.</div>', unsafe_allow_html=True)
        g_c = st.text_input("Gaiola para Circuit", key="g_c").upper()
        if st.button("🚀 OTIMIZAR PARA CIRCUIT"):
            for aba in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=aba)
                col_g = next((c for c in df.columns if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), None)
                if col_g and df[col_g].astype(str).apply(limpar_string).eq(limpar_string(g_c)).any():
                    res = processar_gaiola_circuit(df, g_c, df.columns.get_loc(col_g))
                    if res is not None:
                        st.write(f"✅ {len(res)} paradas reais detectadas.")
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf) as w: res.to_excel(w, index=False)
                        st.download_button("📥 BAIXAR CIRCUIT", buf.getvalue(), f"Circuit_{g_c}.xlsx", use_container_width=True)
                        st.dataframe(res, use_container_width=True)
                        break
else:
    st.info("📁 Aguardando romaneio.")