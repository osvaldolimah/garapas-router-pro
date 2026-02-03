import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional
# NOVAS BIBLIOTECAS PARA A IA
from google import genai
from google.genai.types import HttpOptions

# --- MARCO ZERO: CONFIGURAÇÃO (TOTALMENTE PRESERVADO) ---
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONSTANTES (TOTALMENTE PRESERVADO) ---
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

# --- SISTEMA DE DESIGN (CSS ORIGINAL - TOTALMENTE PRESERVADO) ---
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
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { color: var(--shopee-orange); font-size: clamp(1.4rem, 5vw, 2.2rem); font-weight: 800; margin: 0; }
    .tutorial-section { background: white; padding: 15px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
    .step-badge { background: var(--shopee-orange); color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 12px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: white; padding: 10px; border-radius: 15px; }
    .stTabs [aria-selected="true"] { background-color: var(--shopee-orange) !important; color: white !important; }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; height: 60px !important; box-shadow: 0 6px 15px rgba(238, 77, 45, 0.3) !important; border: none !important; }
    .info-box { background: #EFF6FF; border-left: 4px solid var(--info-blue); padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #1E40AF; }
    .codigo-badge { display: inline-block; background: var(--shopee-orange); color: white; padding: 4px 10px; border-radius: 6px; margin: 3px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- SESSÃO ---
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visualizacao' not in st.session_state: st.session_state.df_visualizacao = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None

# --- MARCO ZERO: FUNÇÕES AUXILIARES (TOTALMENTE PRESERVADO) ---
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
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str); saida['Gaiola'] = df_filt[col_gaiola_idx]; saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        bairro = (df_filt[col_bairro_idx].astype(str) + ", ") if col_bairro_idx is not None else ""
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", " + bairro + "Fortaleza - CE"
        return {'dataframe': saida, 'pacotes': len(saida), 'paradas': len(mapa_stops), 'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])}
    except Exception as e: return None

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

# --- IA: AGENTE COM BUSCA FILTRADA (RESOLVE ERRO B-50) ---
def inicializar_ia():
    api_key = st.secrets.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key, http_options=HttpOptions(api_version='v1')) if api_key else None

def agente_ia_treinado(client, df, pergunta):
    # BUSCA INTELIGENTE: Identifica qual gaiola o usuário quer ANTES de falar com a IA
    match_gaiola = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())
    contexto_dados = ""
    
    if match_gaiola:
        g_alvo = limpar_string(match_gaiola.group(1))
        # Varremos todas as colunas para achar o dado real da B-50, por exemplo
        for col in df.columns:
            df_target = df[df[col].astype(str).apply(limpar_string) == g_alvo]
            if not df_target.empty:
                contexto_dados = f"DADOS REAIS DA GAIOLA {g_alvo}:\n{df_target.to_string()}"
                break
    
    if not contexto_dados:
        contexto_dados = f"RESUMO DO ARQUIVO:\n{df.describe().to_string()}\n\nAMOSTRA:\n{df.head(100).to_string()}"

    prompt = f"""Você é o Agente Waze Humano em Fortaleza. 
    REGRAS: Use estes termos comerciais: {TERMOS_COMERCIAIS}.
    Sua missão é analisar o romaneio fornecido. Se o dado estiver abaixo, responda com precisão.
    {contexto_dados}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=f"{prompt}\nPergunta: {pergunta}")
        return response.text
    except Exception as e: return f"Erro na IA: {e}"

# --- INTERFACE (TOTALMENTE PRESERVADO) ---
st.markdown("""<div class="tutorial-section"><div class="step-item"><div class="step-badge">1</div><span>Upload <b>.xlsx</b>.</span></div></div>""", unsafe_allow_html=True)
arquivo_upload = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed", key="romaneio_upload")

if arquivo_upload:
    xl = pd.ExcelFile(arquivo_upload)
    tab1, tab2, tab3 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "🤖 Agente IA"])

    with tab1: # CONTEÚDO ORIGINAL MARCO ZERO
        gaiola_unica = st.text_input("Gaiola", placeholder="Ex: C-42", key="gui").strip().upper()
        if st.button("🚀 GERAR ROTA DA GAIOLA", key="btn_u", use_container_width=True):
            st.session_state.modo_atual = 'unica'
            target = limpar_string(gaiola_unica); enc = False
            for aba in xl.sheet_names:
                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target).any()), None)
                if idx is not None:
                    res = processar_gaiola_unica(df_raw, gaiola_unica, idx)
                    if res:
                        enc = True; buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine='openpyxl') as w: res['dataframe'].to_excel(w, index=False)
                        st.session_state.dados_prontos = buf.getvalue(); st.session_state.df_visualizacao = res['dataframe']
                        st.session_state.nome_arquivo = f"Rota_{gaiola_unica}.xlsx"; st.session_state.metricas = res
                        break
            if not enc: st.error("Não encontrada.")

    with tab2: # CONTEÚDO ORIGINAL MARCO ZERO
        cod_multi = st.text_area("Gaiolas (uma por linha)", key="c_m_a")
        if st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", key="btn_m", use_container_width=True):
            st.session_state.modo_atual = 'multiplas'
            lista = [c.strip().upper() for c in cod_multi.split('\n') if c.strip()]
            if lista: st.session_state.resultado_multiplas = processar_multiplas_gaiolas(arquivo_upload, lista)

    with tab3: # ABA ADICIONAL DO AGENTE IA
        st.markdown('<div class="info-box"><strong>IA Logística:</strong> Enxergando o romaneio completo agora.</div>', unsafe_allow_html=True)
        p_ia = st.text_input("Sua pergunta (Ex: Quais os bairros da B-50?)", key="p_ia")
        if st.button("🧠 CONSULTAR AGENTE", use_container_width=True):
            cli = inicializar_ia()
            if cli:
                df_ia = pd.read_excel(arquivo_upload) # Carregamento total para a busca filtrada
                st.info(agente_ia_treinado(cli, df_ia, p_ia))
            else: st.error("GEMINI_API_KEY faltando.")

    # RESULTADOS GAIOLA ÚNICA (MARCO ZERO)
    if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
        m = st.session_state.metricas; c1, c2, c3 = st.columns(3)
        c1.metric("📦 Pacotes", m["pacotes"]); c2.metric("📍 Paradas", m["paradas"]); c3.metric("🏪 Comércios", m["comercios"])
        st.dataframe(st.session_state.df_visualizacao, use_container_width=True, hide_index=True)
        st.download_button("📥 BAIXAR PLANILHA", st.session_state.dados_prontos, st.session_state.nome_arquivo, use_container_width=True)

    # RESULTADOS MÚLTIPLAS GAIOLAS COM CHECKBOXES (MARCO ZERO)
    if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
        res = st.session_state.resultado_multiplas
        df_res = pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Pacotes': v['pacotes'], 'Paradas': v['paradas'], 'Comércios': v['comercios']} for k, v in res.items()])
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        g_enc = [k for k, v in res.items() if v['encontrado']]
        if g_enc:
            st.markdown("---")
            st.markdown("### 📥 Baixar Planilhas Individuais")
            cols = st.columns(3); selecionadas = []
            for i, g in enumerate(g_enc):
                with cols[i % 3]:
                    if st.checkbox(f"**{g}**", key=f"chk_{g}"): selecionadas.append(g)
            if selecionadas and st.button("📥 GERAR SELECIONADAS"):
                xl_m = pd.ExcelFile(arquivo_upload)
                for s in selecionadas:
                    target_l = limpar_string(s)
                    for aba in xl_m.sheet_names:
                        df_r = pd.read_excel(xl_m, sheet_name=aba, header=None, engine='openpyxl')
                        idx_g = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target_l).any()), None)
                        if idx_g is not None:
                            res_ind = processar_gaiola_unica(df_r, s, idx_g)
                            if res_ind:
                                buf_ind = io.BytesIO()
                                with pd.ExcelWriter(buf_ind, engine='openpyxl') as w: res_ind['dataframe'].to_excel(w, index=False)
                                st.download_button(label=f"📄 Rota {s}", data=buf_ind.getvalue(), file_name=f"Rota_{s}.xlsx", key=f"dl_{s}", use_container_width=True)
                                break
else:
    st.info("Aguardando romaneio.")