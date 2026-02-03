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

# --- SISTEMA DE DESIGN (MARCO ZERO + MOBILE FORCE v3.15) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; --placeholder-color: rgba(49, 51, 63, 0.4); }
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

# --- INICIALIZAÇÃO DA SESSÃO ---
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visual_tab1' not in st.session_state: st.session_state.df_visual_tab1 = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}
if 'resumo_ia' not in st.session_state: st.session_state.resumo_ia = None

# --- FUNÇÕES AUXILIARES ---
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
        if col_end_idx is None:
            col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
        saida['Gaiola'] = df_filt[col_gaiola_idx]; saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", Fortaleza - CE"
        return {'dataframe': saida, 'pacotes': len(saida), 'paradas': len(mapa_stops), 'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])}
    except Exception: return None

def processar_multiplas_gaiolas(arquivo_excel, codigos_gaiola: List[str]) -> Dict[str, Dict]:
    resultados = {}
    xl = pd.ExcelFile(arquivo_excel)
    for gaiola in codigos_gaiola:
        target_limpo = limpar_string(gaiola); encontrado = False
        for aba in xl.sheet_names:
            df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
            col_gaiola_idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), None)
            if col_gaiola_idx is not None:
                res = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                if res: resultados[gaiola] = {'pacotes': res['pacotes'], 'paradas': res['paradas'], 'comercios': res['comercios'], 'encontrado': True}; encontrado = True; break
        if not encontrado: resultados[gaiola] = {'pacotes': 0, 'paradas': 0, 'comercios': 0, 'encontrado': False}
    return resultados

# --- IA: MOTOR DE ANALISE (v3.21 - DIAGNÓSTICO ATIVADO) ---
def inicializar_ia():
    try: return genai.Client(api_key=st.secrets["GEMINI_API_KEY"], http_options=HttpOptions(api_version='v1'))
    except: return None

def gerar_resumo_estatico_ia(df):
    try:
        col_g_idx = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA', 'CANISTER'])), 0)
        col_e_idx = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['ADDRESS', 'ENDERE', 'LOGRA', 'RUA'])), 0)
        
        temp_df = df.copy()
        temp_df['B_STOP'] = temp_df.iloc[:, col_e_idx].apply(extrair_base_endereco)
        
        resumo = temp_df.groupby(temp_df.columns[col_g_idx]).agg(
            Pacotes=('B_STOP', 'count'),
            Paradas=('B_STOP', 'nunique')
        ).reset_index()
        
        texto_resumo = "TABELA GERAL DE GAIOLAS:\n"
        for _, row in resumo.iterrows():
            texto_resumo += f"- Gaiola {row[0]}: {row['Pacotes']} pacotes, {row['Paradas']} paradas.\n"
        return texto_resumo
    except Exception as e:
        return f"Erro no processamento do resumo: {str(e)}"

def agente_ia_treinado(client, df, pergunta):
    try:
        # 1. Garantir resumo matemático
        if st.session_state.resumo_ia is None:
            st.session_state.resumo_ia = gerar_resumo_estatico_ia(df)

        # 2. Contexto de Bairros (v3.18)
        contexto_bairros = ""
        match_gaiola = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())
        if match_gaiola:
            g_alvo = limpar_string(match_gaiola.group(1))
            col_g_idx = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), 0)
            col_b_idx = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['BAIRRO', 'NEIGHBORHOOD'])), None)
            
            df_target = df[df.iloc[:, col_g_idx].astype(str).apply(limpar_string) == g_alvo]
            if not df_target.empty and col_b_idx is not None:
                bairros = df_target.iloc[:, col_b_idx].dropna().astype(str).apply(remover_acentos).unique().tolist()
                contexto_bairros = f"BAIRROS DA GAIOLA {g_alvo}: {', '.join(bairros)}."

        prompt_base = f"""Você é o Waze Humano, estrategista de logística.
        Use estes dados calculados para responder:
        {st.session_state.resumo_ia}
        {contexto_bairros}
        
        INSTRUÇÕES:
        - Para comparações (mais/menos paradas), use a TABELA GERAL.
        - Se encontrar bairros com grafias parecidas, agrupe-os.
        - Seja direto e profissional.
        """
        
        response = client.models.generate_content(model='gemini-1.5-flash', contents=f"{prompt_base}\nPergunta: {pergunta}")
        return response.text
    except Exception as e:
        # MODO DE DIAGNÓSTICO: Mostra o erro real na tela
        st.error(f"Erro detectado no Agente IA: {str(e)}")
        return "⚠️ Ocorreu um erro técnico. O detalhe foi exibido acima para análise."

# --- INTERFACE ---
arquivo_upload = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed", key="romaneio_upload")

if arquivo_upload:
    if st.session_state.df_cache is None: 
        st.session_state.df_cache = pd.read_excel(arquivo_upload)
        st.session_state.resumo_ia = gerar_resumo_estatico_ia(st.session_state.df_cache)
        
    df_completo = st.session_state.df_cache
    xl = pd.ExcelFile(arquivo_upload)

    tab1, tab2, tab3 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "🤖 Agente IA"])

    with tab1:
        st.markdown('<div class="info-box"><strong>🎯 Gaiola Única:</strong> Gerar rota individual.</div>', unsafe_allow_html=True)
        g_unica = st.text_input("Digite o código", placeholder="Ex: B-50", key="gui_input").strip().upper()
        if st.button("🚀 PROCESSAR GAIOLA", key="btn_u", use_container_width=True):
            st.session_state.modo_atual = 'unica'
            target = limpar_string(g_unica); enc = False
            for aba in xl.sheet_names:
                df_r = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target).any()), None)
                if idx is not None:
                    res = processar_gaiola_unica(df_r, g_unica, idx)
                    if res:
                        enc = True; buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='openpyxl') as w: res['dataframe'].to_excel(w, index=False)
                        st.session_state.dados_prontos = buf.getvalue(); st.session_state.df_visual_tab1 = res['dataframe']; st.session_state.metricas_tab1 = res; break
            if not enc: st.error("Gaiola não encontrada.")
        
        if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
            m = st.session_state.metricas_tab1; c = st.columns(3)
            c[0].metric("📦 Pacotes", m["pacotes"]); c[1].metric("📍 Paradas", m["paradas"]); c[2].metric("🏪 Comércios", m["comercios"])
            st.dataframe(st.session_state.df_visual_tab1, use_container_width=True, hide_index=True)
            st.download_button("📥 BAIXAR ROTA", st.session_state.dados_prontos, f"Rota_{g_unica}.xlsx", use_container_width=True)

    with tab2:
        cod_m = st.text_area("Gaiolas (uma por linha)", placeholder="A-36\nB-50", key="cm_input")
        if st.button("📊 PROCESSAR LOTE", key="btn_m", use_container_width=True):
            st.session_state.modo_atual = 'multiplas'
            lista = [c.strip().upper() for c in cod_m.split('\n') if c.strip()]
            if lista: st.session_state.resultado_multiplas = processar_multiplas_gaiolas(arquivo_upload, lista)

        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            res = st.session_state.resultado_multiplas
            st.dataframe(pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Pacotes': v['pacotes'], 'Paradas': v['paradas']} for k, v in res.items()]), use_container_width=True, hide_index=True)
            
            g_enc = [k for k, v in res.items() if v['encontrado']]
            if g_enc:
                st.markdown("---")
                selecionadas = []
                cols = st.columns(3)
                for i, g in enumerate(g_enc):
                    with cols[i % 3]:
                        if st.checkbox(f"**{g}**", key=f"chk_{g}"): selecionadas.append(g)
                
                if selecionadas and st.button("📥 PREPARAR DOWNLOADS", key="btn_prep"):
                    st.session_state.planilhas_sessao = {}
                    for s in selecionadas:
                        target_l = limpar_string(s)
                        for aba in xl.sheet_names:
                            df_r = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                            idx_g = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target_l).any()), None)
                            if idx_g is not None:
                                r_ind = processar_gaiola_unica(df_r, s, idx_g)
                                if r_ind:
                                    b_ind = io.BytesIO()
                                    with pd.ExcelWriter(b_ind, engine='openpyxl') as w: r_ind['dataframe'].to_excel(w, index=False)
                                    st.session_state.planilhas_sessao[s] = b_ind.getvalue()
                                    break
                
                if st.session_state.planilhas_sessao:
                    st.markdown("##### 📥 Arquivos Gerados:")
                    cols_dl = st.columns(3)
                    for idx, (nome, data) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_dl[idx % 3]:
                            st.download_button(label=f"📄 Rota {nome}", data=data, file_name=f"Rota_{nome}.xlsx", key=f"dl_{nome}", use_container_width=True)

    with tab3:
        p_ia = st.text_input("Dúvida sobre o romaneio:", key="ia_input")
        if st.button("🧠 CONSULTAR AGENTE", use_container_width=True):
            cli = inicializar_ia()
            if cli:
                with st.spinner("O Agente está analisando as rotas..."):
                    st.markdown(f'<div class="success-box">{agente_ia_treinado(cli, df_completo, p_ia)}</div>', unsafe_allow_html=True)
            else: st.error("API Key (Secrets) não configurada.")
else:
    st.info("📁 Aguardando romaneio para iniciar a operação.")