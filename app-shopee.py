import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional

# --- [IMUTÁVEL] CONFIGURAÇÃO DA PÁGINA (MARCO ZERO) ---
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- [IMUTÁVEL] CONSTANTES (MARCO ZERO) ---
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

# --- [IMUTÁVEL] SISTEMA DE DESIGN (MARCO ZERO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; --placeholder-color: rgba(49, 51, 63, 0.4); }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { color: var(--shopee-orange) !important; font-size: clamp(1.0rem, 4vw, 1.4rem) !important; font-weight: 800 !important; margin: 0 !important; line-height: 1.2 !important; display: block !important; }
    
    /* TABS RESPONSIVAS - MOBILE FIRST */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 4px;
        background-color: white;
        padding: 8px;
        border-radius: 15px;
        overflow-x: auto; /* Permite scroll horizontal se necessário */
        -webkit-overflow-scrolling: touch; /* Scroll suave no iOS */
        display: flex;
        flex-wrap: nowrap; /* Não quebra linha */
    }
    
    .stTabs [data-baseweb="tab"] { 
        height: 45px;
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 0 12px; /* Reduzido para mobile */
        font-weight: 600;
        border: 2px solid transparent;
        white-space: nowrap; /* Texto não quebra */
        font-size: 14px; /* Tamanho menor no mobile */
        min-width: fit-content; /* Ajusta ao conteúdo */
        flex-shrink: 0; /* Não encolhe */
    }
    
    .stTabs [aria-selected="true"] { 
        background-color: var(--shopee-orange) !important; 
        color: white !important; 
        border-color: var(--shopee-orange); 
    }
    
    /* RESPONSIVIDADE PARA TELAS MAIORES */
    @media (min-width: 768px) {
        .stTabs [data-baseweb="tab-list"] { 
            gap: 8px;
            padding: 10px;
            flex-wrap: wrap; /* Permite quebra em telas maiores se necessário */
        }
        
        .stTabs [data-baseweb="tab"] { 
            height: 50px;
            padding: 0 24px;
            font-size: 16px;
        }
    }
    
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .info-box { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    .success-box { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    
    /* CSS ESPECÍFICO PARA O SEGUNDO UPLOAD (CIRCUIT) */
    [data-testid="stFileUploader"] label[data-testid="stWidgetLabel"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- [IMUTÁVEL] INICIALIZAÇÃO DA SESSÃO ---
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visual_tab1' not in st.session_state: st.session_state.df_visual_tab1 = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}

# --- [IMUTÁVEL] FUNÇÕES AUXILIARES MARCO ZERO ---
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
    except Exception as e:
        st.error(f"⚠️ Erro ao processar gaiola {gaiola_alvo}: {str(e)}")
        return None

def processar_multiplas_gaiolas(arquivo_excel, codigos_gaiola: List[str]) -> Dict[str, Dict]:
    resultados = {}
    try:
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
    except Exception as e:
        st.error(f"⚠️ Erro ao processar múltiplas gaiolas: {str(e)}")
        return {}

# --- [NOVO] FUNÇÕES ISOLADAS PARA A ABA CIRCUIT PRO ---
def extrair_chave_circuit_pro(endereco):
    """Extrai Rua + Número para casar sequências"""
    partes = str(endereco).split(',')
    if len(partes) >= 2:
        return f"{partes[0].strip()}, {partes[1].strip()}".upper()
    return str(endereco).strip().upper()

def gerar_planilha_otimizada_circuit_pro(df):
    """Funde linhas de mesmo endereço e une sequências"""
    # Identifica colunas dinamicamente
    col_end = next((c for c in df.columns if any(t in str(c).upper() for t in ['ADDRESS', 'ENDERE', 'DESTINATION'])), None)
    col_seq = next((c for c in df.columns if 'SEQUENCE' in str(c).upper()), None)
    
    if not col_end or not col_seq: return None
    
    df_temp = df.copy()
    df_temp['CHAVE_END'] = df_temp[col_end].apply(extrair_chave_circuit_pro)
    
    # Agregação: Mantém a primeira linha, junta as sequências
    agg_dict = {col: 'first' for col in df_temp.columns if col not in ['CHAVE_END', col_seq]}
    def unir_seqs(x): return ', '.join(map(str, sorted(x.unique())))
    
    df_final = df_temp.groupby('CHAVE_END').agg({**agg_dict, col_seq: unir_seqs}).reset_index()
    
    # Reordena numericamente pela primeira sequência
    try:
        df_final['SortKey'] = df_final[col_seq].apply(lambda x: int(str(x).split(',')[0]))
        return df_final.sort_values('SortKey').drop(columns=['CHAVE_END', 'SortKey'])
    except:
        return df_final.drop(columns=['CHAVE_END'])

# --- INTERFACE TABS ---
tab1, tab2, tab3 = st.tabs(["🎯 Única", "📊 Lote", "⚡ Circuit"])

with tab1: # MARCO ZERO
    st.markdown("##### 📥 Upload Romaneio Geral")
    up_padrao = st.file_uploader("Upload Romaneio Geral", type=["xlsx"], key="up_padrao", label_visibility="collapsed")
    if up_padrao:
        # MELHORIA #3: Loading state ao carregar DataFrame pela primeira vez
        if st.session_state.df_cache is None:
            with st.spinner("📊 Carregando romaneio..."):
                st.session_state.df_cache = pd.read_excel(up_padrao)
        
        df_completo = st.session_state.df_cache
        xl = pd.ExcelFile(up_padrao)
        
        st.markdown('<div class="info-box"><strong>💡 Modo Gaiola Única:</strong> Gerar rota detalhada.</div>', unsafe_allow_html=True)
        g_unica = st.text_input("Gaiola", placeholder="Ex: B-50", key="gui_tab1").strip().upper()
        if st.button("🚀 GERAR ROTA DA GAIOLA", key="btn_u_tab1", use_container_width=True):
            if not g_unica:
                st.warning("⚠️ Por favor, digite o código da gaiola.")
            else:
                st.session_state.modo_atual = 'unica'
                target = limpar_string(g_unica); enc = False
                
                with st.spinner(f"⚙️ Processando gaiola {g_unica}..."):
                    for aba in xl.sheet_names:
                        df_r = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                        idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target).any()), None)
                        if idx is not None:
                            res = processar_gaiola_unica(df_r, g_unica, idx)
                            if res:
                                enc = True; buf = io.BytesIO()
                                with pd.ExcelWriter(buf, engine='openpyxl') as w: res['dataframe'].to_excel(w, index=False)
                                st.session_state.dados_prontos = buf.getvalue(); st.session_state.df_visual_tab1 = res['dataframe']; st.session_state.metricas_tab1 = res; break
                
                if not enc: st.error(f"❌ Gaiola '{g_unica}' não encontrada.")
        
        if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
            m = st.session_state.metricas_tab1; c = st.columns(3)
            c[0].metric("📦 Pacotes", m["pacotes"]); c[1].metric("📍 Paradas", m["paradas"]); c[2].metric("🏪 Comércios", m["comercios"])
            st.dataframe(st.session_state.df_visual_tab1, use_container_width=True, hide_index=True)
            st.download_button("📥 BAIXAR PLANILHA", st.session_state.dados_prontos, f"Rota_{g_unica}.xlsx", use_container_width=True)

with tab2: # MARCO ZERO
    st.markdown("##### 📥 Upload (Mesmo da Aba 1)")
    # MELHORIA #3: Usar session_state ao invés de locals() para evitar race condition
    if st.session_state.df_cache is not None and 'up_padrao' in locals() and up_padrao:
        xl = pd.ExcelFile(up_padrao)
        st.markdown('<div class="info-box"><strong>💡 Modo Múltiplas Gaiolas:</strong> Resumo rápido.</div>', unsafe_allow_html=True)
        cod_m = st.text_area("Gaiolas (uma por linha)", placeholder="A-36\nB-50", key="cm_tab2")
        if st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", key="btn_m_tab2", use_container_width=True):
            lista = [c.strip().upper() for c in cod_m.split('\n') if c.strip()]
            
            if not lista:
                st.warning("⚠️ Por favor, digite pelo menos um código de gaiola.")
            else:
                st.session_state.modo_atual = 'multiplas'
                
                with st.spinner(f"⚙️ Processando {len(lista)} gaiola(s)..."):
                    st.session_state.resultado_multiplas = processar_multiplas_gaiolas(up_padrao, lista)
        
        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            res = st.session_state.resultado_multiplas
            st.dataframe(pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Pacotes': v['pacotes'], 'Paradas': v['paradas']} for k, v in res.items()]), use_container_width=True, hide_index=True)
            
            g_enc = [k for k, v in res.items() if v['encontrado']]
            if g_enc:
                st.markdown("---"); st.markdown("##### ✅ Selecione para download individual:")
                selecionadas = []
                cols = st.columns(3)
                for i, g in enumerate(g_enc):
                    with cols[i % 3]:
                        if st.checkbox(f"**{g}**", key=f"chk_m_{g}"): selecionadas.append(g)
                
                if selecionadas and st.button("📥 PREPARAR ARQUIVOS CIRCUIT"):
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
                    st.markdown("##### 📥 Downloads Prontos:")
                    cols_dl = st.columns(3)
                    for idx, (nome, data) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_dl[idx % 3]:
                            st.download_button(label=f"📄 Rota {nome}", data=data, file_name=f"Rota_{nome}.xlsx", key=f"dl_sessao_{nome}", use_container_width=True)
    else:
        st.info("Faça o upload do romaneio na Aba 1 para usar esta função.")

with tab3: # NOVA ABA ISOLADA - CIRCUIT PRO
    st.markdown("##### 📥 Upload Específico")
    st.markdown('<div class="success-box"><strong>⚡ Circuit Pro:</strong> Ferramenta isolada. Carregue o arquivo da gaiola já filtrada.</div>', unsafe_allow_html=True)
    up_circuit = st.file_uploader("Upload Romaneio Específico", type=["xlsx"], key="up_circuit")
    
    if up_circuit:
        df_c = pd.read_excel(up_circuit)
        if st.button("🚀 GERAR PLANILHA DAS CASADINHAS", use_container_width=True):
            res_c = gerar_planilha_otimizada_circuit_pro(df_c)
            if res_c is not None:
                st.success(f"✅ Otimização concluída! {len(df_c)} pacotes reduzidos para {len(res_c)} paradas reais.")
                buf_c = io.BytesIO()
                with pd.ExcelWriter(buf_c, engine='openpyxl') as w: res_c.to_excel(w, index=False)
                st.download_button("📥 BAIXAR PARA CIRCUIT", buf_c.getvalue(), "Circuit_Otimizado.xlsx", use_container_width=True)
                st.dataframe(res_c, use_container_width=True, hide_index=True)
            else:
                st.error("Erro: Colunas 'Address/Endereço' ou 'Sequence' não encontradas.")