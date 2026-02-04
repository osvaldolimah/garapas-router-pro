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
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def limpar_string(s: str) -> str:
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco):
    partes = str(endereco).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def extrair_chave_circuit(endereco):
    partes = str(endereco).split(',')
    if len(partes) >= 2:
        return f"{partes[0].strip()}, {partes[1].strip()}".upper()
    return str(endereco).strip().upper()

def identificar_comercio(endereco: str) -> str:
    end_limpo = "".join(c for c in unicodedata.normalize('NFD', str(endereco)) if unicodedata.category(c) != 'Mn').upper()
    for parte in end_limpo.split(','):
        palavras = parte.split()
        for i, palavra in enumerate(palavras):
            p_limpa = "".join(filter(str.isalnum, palavra))
            if any(termo == p_limpa for termo in TERMOS_COMERCIAIS):
                if not any(anul in " ".join(palavras[:i]) for anul in TERMOS_ANULADORES):
                    return "🏪 Comércio"
    return "🏠 Residencial"

# --- MOTORES DE PROCESSAMENTO ---

def processar_gaiola_padrao(df_raw, gaiola, col_idx):
    target = limpar_string(gaiola)
    df_f = df_raw[df_raw[col_idx].astype(str).apply(limpar_string) == target].copy()
    if df_f.empty: return None
    # Adiciona as colunas informativas para o Marco Zero
    col_end = next((i for i, v in enumerate(df_f.columns) if any(t in str(v).upper() for t in ['ADDRESS', 'ENDERE'])), 0)
    df_f['CHAVE_STOP'] = df_f.iloc[:, col_end].apply(extrair_base_endereco)
    mapa = {end: i + 1 for i, end in enumerate(df_f['CHAVE_STOP'].unique())}
    saida = pd.DataFrame()
    saida['Parada'] = df_f['CHAVE_STOP'].map(mapa).astype(str)
    saida['Gaiola'] = df_f.iloc[:, col_idx]
    saida['Tipo'] = df_f.iloc[:, col_end].apply(identificar_comercio)
    saida['Endereco_Completo'] = df_f.iloc[:, col_end].astype(str) + ", Fortaleza - CE"
    return {'dataframe': saida, 'pacotes': len(df_f), 'paradas': len(mapa), 'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])}

def processar_planilha_circuit(df_raw):
    """Funde paradas da planilha INTEIRA para o Circuit"""
    df_f = df_raw.copy()
    col_end = next((i for i, v in enumerate(df_f.columns) if any(t in str(v).upper() for t in ['ADDRESS', 'ENDERE'])), 0)
    col_seq = next((i for i, v in enumerate(df_f.columns) if 'SEQUENCE' in str(v).upper()), 1)
    
    df_f['CHAVE'] = df_f.iloc[:, col_end].apply(extrair_chave_circuit)
    agreg = {col: 'first' for col in df_f.columns if col not in ['CHAVE', df_f.columns[col_seq]]}
    def unir(x): return ', '.join(map(str, sorted(x.unique())))
    
    df_otimizado = df_f.groupby('CHAVE').agg({**agreg, df_f.columns[col_seq]: unir}).reset_index()
    # Ordenação pela primeira sequência
    df_otimizado['Order'] = df_otimizado.iloc[:, col_seq+1].apply(lambda x: int(str(x).split(',')[0]))
    return df_otimizado.sort_values('Order').drop(columns=['CHAVE', 'Order'])

def processar_multiplas_gaiolas(arquivo_excel, lista_gaiolas):
    resultados = {}
    xl = pd.ExcelFile(arquivo_excel)
    for g in lista_gaiolas:
        target = limpar_string(g); enc = False
        for aba in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=aba)
            col_g = next((c for c in df.columns if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), None)
            if col_g and df[col_g].astype(str).apply(limpar_string).eq(target).any():
                res = processar_gaiola_padrao(df, g, df.columns.get_loc(col_g))
                if res: resultados[g] = {'pacotes': res['pacotes'], 'paradas': res['paradas'], 'encontrado': True}; enc = True; break
        if not enc: resultados[g] = {'pacotes': 0, 'paradas': 0, 'encontrado': False}
    return resultados

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
                    if res:
                        st.metric("📍 Paradas Reais", res['paradas'])
                        st.dataframe(res['dataframe'], use_container_width=True, hide_index=True)
                        break

    with tab2: # RESTAURAÇÃO COMPLETA DA ABA MULTIPLAS
        cod_m = st.text_area("Gaiolas (uma por linha)", placeholder="A-36\nB-50", key="cm_tab2")
        if st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", use_container_width=True):
            st.session_state.modo_atual = 'multiplas'
            lista = [c.strip().upper() for c in cod_m.split('\n') if c.strip()]
            if lista: st.session_state.resultado_multiplas = processar_multiplas_gaiolas(arquivo, lista)

        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            res = st.session_state.resultado_multiplas
            st.dataframe(pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Paks': v['pacotes'], 'Stops': v['paradas']} for k, v in res.items()]), use_container_width=True, hide_index=True)
            g_enc = [k for k, v in res.items() if v['encontrado']]
            if g_enc:
                st.markdown("---")
                selecionadas = []
                cols = st.columns(3)
                for i, g in enumerate(g_enc):
                    with cols[i % 3]:
                        if st.checkbox(f"**{g}**", key=f"chk_m_{g}"): selecionadas.append(g)
                if selecionadas and st.button("📥 PREPARAR ARQUIVOS"):
                    st.session_state.planilhas_sessao = {}
                    for s in selecionadas:
                        for aba in xl.sheet_names:
                            df_r = pd.read_excel(xl, sheet_name=aba)
                            col_idx = next((i for i, c in enumerate(df_r.columns) if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), 0)
                            if df_r.iloc[:, col_idx].astype(str).apply(limpar_string).eq(limpar_string(s)).any():
                                r_ind = processar_gaiola_padrao(df_r, s, col_idx)
                                if r_ind:
                                    b_ind = io.BytesIO()
                                    with pd.ExcelWriter(b_ind) as w: r_ind['dataframe'].to_excel(w, index=False)
                                    st.session_state.planilhas_sessao[s] = b_ind.getvalue()
                                    break
                if st.session_state.planilhas_sessao:
                    cols_dl = st.columns(3)
                    for idx, (n, d) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_dl[idx % 3]: st.download_button(f"📄 {n}", d, f"Rota_{n}.xlsx", key=f"dl_{n}", use_container_width=True)

    with tab3: # ABA CIRCUIT PRO SEM CAMPO GAIOLA
        st.markdown('<div class="success-box"><strong>⚡ Circuit Pro:</strong> Gera a planilha casada do arquivo inteiro.</div>', unsafe_allow_html=True)
        if st.button("🚀 GERAR PLANILHA DAS CASADINHAS", use_container_width=True):
            res_c = processar_planilha_circuit(st.session_state.df_cache)
            if res_c is not None:
                st.write(f"✅ {len(res_c)} paradas reais detectadas no romaneio.")
                buf = io.BytesIO()
                with pd.ExcelWriter(buf) as w: res_c.to_excel(w, index=False)
                st.download_button("📥 BAIXAR PLANILHA CASADINHA", buf.getvalue(), "Circuit_Casadinhas.xlsx", use_container_width=True)
                st.dataframe(res_c, use_container_width=True, hide_index=True)
else:
    st.info("📁 Aguardando romaneio.")