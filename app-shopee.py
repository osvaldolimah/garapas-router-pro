import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional
from google import genai

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

# --- SISTEMA DE DESIGN (MARCO ZERO + MOBILE FORCE v3.15) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { 
        color: var(--shopee-orange) !important; 
        font-size: clamp(1.0rem, 4vw, 1.4rem) !important; 
        font-weight: 800 !important; 
        margin: 0 !important;
        line-height: 1.2 !important;
        display: block !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: white; padding: 10px; border-radius: 15px; }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .success-box { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    .info-box { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- SESSÃO ---
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'resumo_ia' not in st.session_state: st.session_state.resumo_ia = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visual_tab1' not in st.session_state: st.session_state.df_visual_tab1 = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None

# --- FUNÇÕES ---
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
        if col_end_idx is None: col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
        saida['Gaiola'] = df_filt[col_gaiola_idx]
        saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", Fortaleza - CE"
        return {'dataframe': saida, 'pacotes': len(saida), 'paradas': len(mapa_stops), 'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])}
    except: return None

# --- IA (v3.23) ---
def inicializar_ia():
    try:
        # Inicialização limpa para evitar erro 404 de versão
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except:
        return None

def gerar_resumo_estatico_ia(df):
    try:
        col_g = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA', 'CANISTER'])), 0)
        col_e = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['ADDRESS', 'ENDERE', 'RUA'])), 0)
        temp = df.copy()
        temp['B_STOP'] = temp.iloc[:, col_e].apply(extrair_base_endereco)
        resumo = temp.groupby(temp.columns[col_g]).agg(Pacotes=('B_STOP', 'count'), Paradas=('B_STOP', 'nunique')).reset_index()
        texto = "TABELA GERAL:\n"
        for _, row in resumo.iterrows():
            texto += f"- Gaiola {row[0]}: {row['Pacotes']} pacotes, {row['Paradas']} paradas.\n"
        return texto
    except: return "Erro no resumo."

def agente_ia_treinado(client, df, pergunta):
    try:
        if st.session_state.resumo_ia is None: st.session_state.resumo_ia = gerar_resumo_estatico_ia(df)
        contexto_b = ""
        match = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())
        if match:
            g_alvo = limpar_string(match.group(1))
            col_g = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), 0)
            col_b = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['BAIRRO', 'NEIGHBORHOOD'])), None)
            df_target = df[df.iloc[:, col_g].astype(str).apply(limpar_string) == g_alvo]
            if not df_target.empty and col_b is not None:
                bairros = df_target.iloc[:, col_b].dropna().astype(str).apply(remover_acentos).unique().tolist()
                contexto_b = f"BAIRROS DA {g_alvo}: {', '.join(bairros)}."

        prompt = f"Você é o Waze Humano. Dados:\n{st.session_state.resumo_ia}\n{contexto_b}\nResponda logisticamente: {pergunta}"
        # Chamada direta do modelo estável
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        st.error(f"Erro na conexão com a rota da IA: {str(e)}")
        return "⚠️ Erro de sinal. Tente novamente."

# --- INTERFACE ---
arquivo = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed")

if arquivo:
    if st.session_state.df_cache is None:
        st.session_state.df_cache = pd.read_excel(arquivo)
        st.session_state.resumo_ia = gerar_resumo_estatico_ia(st.session_state.df_cache)
    
    df_completo = st.session_state.df_cache
    xl = pd.ExcelFile(arquivo)
    t1, t2, t3 = st.tabs(["🎯 Única", "📊 Lote", "🤖 IA"])

    with t1:
        g = st.text_input("Gaiola", key="g_u").strip().upper()
        if st.button("🚀 GERAR", key="b_u", use_container_width=True):
            st.session_state.modo_atual = 'unica'
            for aba in xl.sheet_names:
                df_r = pd.read_excel(xl, sheet_name=aba, header=None)
                idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(limpar_string(g)).any()), None)
                if idx is not None:
                    res = processar_gaiola_unica(df_r, g, idx)
                    if res:
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf) as w: res['dataframe'].to_excel(w, index=False)
                        st.session_state.dados_prontos = buf.getvalue(); st.session_state.df_visual_tab1 = res['dataframe']; st.session_state.metricas_tab1 = res; break
        if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
            m = st.session_state.metricas_tab1; c = st.columns(3)
            c[0].metric("📦 Pacotes", m["pacotes"]); c[1].metric("📍 Paradas", m["paradas"]); c[2].metric("🏪 Comércios", m["comercios"])
            st.dataframe(st.session_state.df_visual_tab1, use_container_width=True, hide_index=True)
            st.download_button("📥 BAIXAR", st.session_state.dados_prontos, f"Rota_{g}.xlsx", use_container_width=True)

    with t2:
        lista = st.text_area("Gaiolas", key="l_m")
        if st.button("📊 PROCESSAR", key="b_m", use_container_width=True):
            st.session_state.modo_atual = 'multiplas'
            gaiolas = [c.strip().upper() for c in lista.split('\n') if c.strip()]
            if gaiolas:
                res_l = {}
                for gn in gaiolas:
                    target = limpar_string(gn); enc = False
                    for aba in xl.sheet_names:
                        df_r = pd.read_excel(xl, sheet_name=aba, header=None)
                        idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target).any()), None)
                        if idx is not None:
                            r = processar_gaiola_unica(df_r, gn, idx)
                            if r: res_l[gn] = {'pacotes': r['pacotes'], 'paradas': r['paradas'], 'encontrado': True}; enc = True; break
                    if not enc: res_l[gn] = {'pacotes': 0, 'paradas': 0, 'encontrado': False}
                st.session_state.resultado_multiplas = res_l

        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            res = st.session_state.resultado_multiplas
            st.dataframe(pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Paks': v['pacotes'], 'Stops': v['paradas']} for k, v in res.items()]), use_container_width=True, hide_index=True)
            g_enc = [k for k, v in res.items() if v['encontrado']]
            if g_enc:
                sel = []
                cols = st.columns(3)
                for i, gn in enumerate(g_enc):
                    with cols[i % 3]:
                        if st.checkbox(f"{gn}", key=f"c_{gn}"): sel.append(gn)
                if sel and st.button("📥 PREPARAR", key="b_p"):
                    st.session_state.planilhas_sessao = {}
                    for s in sel:
                        for aba in xl.sheet_names:
                            df_r = pd.read_excel(xl, sheet_name=aba, header=None)
                            idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(limpar_string(s)).any()), None)
                            if idx is not None:
                                r = processar_gaiola_unica(df_r, s, idx)
                                if r:
                                    b = io.BytesIO()
                                    with pd.ExcelWriter(b) as w: r['dataframe'].to_excel(w, index=False)
                                    st.session_state.planilhas_sessao[s] = b.getvalue(); break
                if st.session_state.planilhas_sessao:
                    cols_d = st.columns(3)
                    for i, (n, d) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_d[i % 3]: st.download_button(f"📄 {n}", d, f"Rota_{n}.xlsx", key=f"d_{n}", use_container_width=True)

    with t3:
        p = st.text_input("Dúvida:", key="i_p")
        if st.button("🧠 CONSULTAR", use_container_width=True):
            cli = inicializar_ia()
            if cli:
                with st.spinner("Analisando..."):
                    st.markdown(f'<div class="success-box">{agente_ia_treinado(cli, df_completo, p)}</div>', unsafe_allow_html=True)
else:
    st.info("📁 Suba o romaneio para começar.")