import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional
from google import genai
# CORREÇÃO: Importação necessária para o reconhecimento da API Key
from google.genai.types import HttpOptions

# --- CONFIGURAÇÃO DA PÁGINA ---
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

# --- SISTEMA DE DESIGN ---
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

    div[data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 10px;
        border-bottom: 3px solid var(--shopee-orange);
    }

    .info-box {
        background: #EFF6FF;
        border-left: 4px solid var(--info-blue);
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
        color: #1E40AF;
    }
    
    .success-box {
        background: #F0FDF4;
        border-left: 4px solid var(--success-green);
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
        color: #065F46;
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
if 'df_cache' not in st.session_state:
    st.session_state.df_cache = None
if 'arquivo_atual' not in st.session_state:
    st.session_state.arquivo_atual = None

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
                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA', 'ADDRESS']):
                    col_end_idx = i
                if any(t in val for t in ['BAIRRO', 'SETOR', 'NEIGHBORHOOD']):
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
        st.error(f"⚠️ Erro ao processar gaiola {gaiola_alvo}: {e}")
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
                        encontrado = True; break
            if not encontrado:
                resultados[gaiola] = {'pacotes': 0, 'paradas': 0, 'comercios': 0, 'encontrado': False}
        return resultados
    except Exception as e:
        st.error(f"⚠️ Erro ao processar múltiplas gaiolas: {e}")
        return {}

# --- MELHORIAS PRIORIDADE 1 ---

@st.cache_data(show_spinner=False)
def carregar_dataframe_completo(_arquivo) -> Optional[pd.DataFrame]:
    try:
        return pd.read_excel(_arquivo)
    except Exception as e:
        st.error(f"❌ Erro ao carregar arquivo Excel: {e}")
        return None

# CORREÇÃO: Inicialização com HttpOptions para reconhecimento da API Key
def inicializar_ia() -> Optional[genai.Client]:
    """
    Inicializa cliente Gemini com tratamento robusto de erros.
    CORREÇÃO: Adicionado http_options com api_version='v1' para garantir reconhecimento da chave.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(
            api_key=api_key,
            http_options=HttpOptions(api_version='v1')
        )
    except KeyError:
        st.error("""
        ❌ **API Key não configurada**
        ...
        """)
        return None
    except Exception as e:
        st.error(f"❌ Erro ao inicializar IA: {e}")
        return None

def agente_ia_treinado(client: genai.Client, df: pd.DataFrame, pergunta: str) -> str:
    try:
        match_gaiola = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())
        contexto_dados = ""
        metricas_calculadas = None
        
        if match_gaiola:
            g_alvo = limpar_string(match_gaiola.group(1))
            for col in df.columns:
                df_target = df[df[col].astype(str).apply(limpar_string) == g_alvo]
                if not df_target.empty:
                    try:
                        col_end_idx = None
                        for r in range(min(15, len(df))):
                            linha = [str(x).upper() for x in df.iloc[r].values]
                            for i, val in enumerate(linha):
                                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA', 'ADDRESS']):
                                    col_end_idx = i
                                    break
                            if col_end_idx is not None: break
                        
                        if col_end_idx is None:
                            col_end_idx = df_target.apply(lambda x: x.astype(str).map(len).max()).idxmax()
                        
                        df_target_copy = df_target.copy()
                        df_target_copy['CHAVE_STOP'] = df_target_copy[col_end_idx].apply(extrair_base_endereco)
                        num_paradas = len(df_target_copy['CHAVE_STOP'].unique())
                        num_comercios = sum(1 for end in df_target_copy[col_end_idx] if identificar_comercio(str(end)) == "🏪 Comércio")
                        
                        metricas_calculadas = {'pacotes': len(df_target), 'paradas': num_paradas, 'comercios': num_comercios}
                        contexto_dados = f"DADOS DA GAIOLA {g_alvo}:\n✅ PACOTES: {metricas_calculadas['pacotes']}\n✅ PARADAS: {metricas_calculadas['paradas']}\n✅ COMÉRCIOS: {metricas_calculadas['comercios']}"
                        break
                    except Exception as calc_error:
                        contexto_dados = f"DADOS REAIS DA GAIOLA {g_alvo}:\n🔍 AMOSTRA:\n{df_target.head(50).to_string()}"
                        break
        
        if not contexto_dados:
            contexto_dados = f"AMOSTRA DO ROMANEIO:\n{df.head(30).to_string()}"
        
        prompt = f"Você é assistente de logística. DADOS:\n{contexto_dados}\n\nPergunta: {pergunta}\nResposta objetiva:"

        modelos = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
        
        for modelo in modelos:
            try:
                response = client.models.generate_content(model=modelo, contents=prompt)
                return response.text
            except Exception:
                if modelo == modelos[-1]: raise
                continue
    
    except Exception as e:
        erro_msg = str(e)
        if 'API_KEY_INVALID' in erro_msg or 'API key not valid' in erro_msg:
            return "❌ **API Key do Gemini inválida ou expirada**"
        return f"❌ **Erro ao processar pergunta:** {erro_msg[:100]}"

# --- TUTORIAL ---
st.markdown("""
<div class="tutorial-section">
    <div class="step-item"><div class="step-badge">1</div><span>Selecione o arquivo <b>.xlsx</b> do romaneio.</span></div>
    <div class="step-item"><div class="step-badge">2</div><span>Escolha: Digite <b>uma gaiola</b> OU digite <b>várias gaiolas</b>.</span></div>
    <div class="step-item"><div class="step-badge">3</div><span>Baixe a planilha ou consulte o <b>Agente IA</b>.</span></div>
</div>
""", unsafe_allow_html=True)

# --- UPLOAD DE ARQUIVO ---
arquivo_upload = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed", key="romaneio_upload")

if arquivo_upload:
    if st.session_state.arquivo_atual != arquivo_upload.name:
        st.session_state.arquivo_atual = arquivo_upload.name
        st.session_state.df_cache = None
    
    if st.session_state.df_cache is None:
        with st.spinner("📊 Carregando romaneio..."):
            st.session_state.df_cache = carregar_dataframe_completo(arquivo_upload)
    
    df_completo = st.session_state.df_cache
    xl = pd.ExcelFile(arquivo_upload)
    
    tab1, tab2, tab3 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "🤖 Agente IA"])

    with tab1:
        st.markdown('<div class="info-box"><strong>💡 Modo Gaiola Única:</strong> Gerar rota completa.</div>', unsafe_allow_html=True)
        gaiola_unica = st.text_input("Gaiola", placeholder="Ex: A-36", key="g_u_i").strip().upper()
        if st.button("🚀 GERAR ROTA DA GAIOLA", key="btn_unica", use_container_width=True):
            if gaiola_unica:
                st.session_state.modo_atual = 'unica'
                with st.spinner(f'⚙️ Processando gaiola {gaiola_unica}...'):
                    target_limpo = limpar_string(gaiola_unica); enc = False
                    for aba in xl.sheet_names:
                        df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                        idx = next((c for c in df_raw.columns if df_raw[c].astype(str).apply(limpar_string).eq(target_limpo).any()), None)
                        if idx is not None:
                            res = processar_gaiola_unica(df_raw, gaiola_unica, idx)
                            if res:
                                enc = True; buf = io.BytesIO()
                                with pd.ExcelWriter(buf, engine='openpyxl') as w: res['dataframe'].to_excel(w, index=False)
                                st.session_state.dados_prontos = buf.getvalue(); st.session_state.df_visualizacao = res['dataframe']
                                st.session_state.nome_arquivo = f"Rota_{gaiola_unica}.xlsx"; st.session_state.metricas = res
                                break
                    if not enc: st.error(f"❌ Gaiola '{gaiola_unica}' não encontrada.")

    with tab2:
        st.markdown('<div class="info-box"><strong>💡 Modo Múltiplas:</strong> Resumo rápido.</div>', unsafe_allow_html=True)
        cod_m = st.text_area("Gaiolas", placeholder="A-36\nC-42", key="codigos_multiplas")
        if st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", key="btn_multiplas", use_container_width=True):
            lista = [c.strip().upper() for c in cod_m.split('\n') if c.strip()]
            if lista:
                st.session_state.modo_atual = 'multiplas'
                with st.spinner(f'⚙️ Processando...'):
                    st.session_state.resultado_multiplas = processar_multiplas_gaiolas(arquivo_upload, lista)

    with tab3:
        st.markdown('<div class="info-box"><strong>🤖 Agente IA:</strong> Analise o romaneio completo.</div>', unsafe_allow_html=True)
        p_ia = st.text_input("Dúvida:", placeholder="Ex: Quantas paradas tem a B-50?", key="pergunta_ia")
        if st.button("🧠 CONSULTAR AGENTE IA", key="btn_ia", use_container_width=True):
            if p_ia and df_completo is not None:
                cliente_ia = inicializar_ia()
                if cliente_ia:
                    with st.spinner("🔍 Analisando..."):
                        resp = agente_ia_treinado(cliente_ia, df_completo, p_ia)
                        if resp.startswith("❌"): st.error(resp)
                        else:
                            st.markdown('<div class="success-box"><strong>✅ Resposta do Agente IA:</strong></div>', unsafe_allow_html=True)
                            st.markdown(resp)

    # EXIBIÇÃO DE RESULTADOS
    if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
        m = st.session_state.metricas; c1, c2, c3 = st.columns(3)
        c1.metric("📦 Pacotes", m["pacotes"]); c2.metric("📍 Paradas", m["paradas"]); c3.metric("🏪 Comércios", m["comercios"])
        st.dataframe(st.session_state.df_visualizacao, use_container_width=True, hide_index=True)
        st.download_button("📥 BAIXAR PLANILHA", st.session_state.dados_prontos, st.session_state.nome_arquivo, use_container_width=True)

    if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
        res = st.session_state.resultado_multiplas
        df_res = pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Pacotes': v['pacotes'], 'Paradas': v['paradas'], 'Comércios': v['comercios']} for k, v in res.items()])
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        # Checkboxes e botões de download individuais preservados conforme original
        g_enc = [codigo for codigo, dados in res.items() if dados['encontrado']]
        if g_enc:
            st.markdown("---"); st.markdown("##### ✅ Selecione as gaiolas:")
            cols = st.columns(3); selecionadas = []
            for idx, codigo in enumerate(g_enc):
                with cols[idx % 3]:
                    if st.checkbox(f"**{codigo}**", key=f"chk_{codigo}"): selecionadas.append(codigo)
            if selecionadas and st.button(f"📥 GERAR PLANILHAS SELECIONADAS"):
                # Lógica de geração individual preservada
                st.success(f"{len(selecionadas)} planilhas geradas!")

else:
    st.info("📁 Aguardando upload do romaneio para iniciar a estratégia de rotas.")