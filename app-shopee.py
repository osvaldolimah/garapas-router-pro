import streamlit as st
import pandas as pd
import io
import unicodedata
import re
import math
from typing import List, Dict, Optional

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
TERMOS_ANULADORES = ['FRENTE', 'LADO', 'PROXIMO', 'VIZINHO', 'DEFRONTE', 'ATRAS', 'DEPOIS', 'PERTO', 'VIZINHA']

# --- SISTEMA DE DESIGN (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; --placeholder-color: rgba(49, 51, 63, 0.4); }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { color: var(--shopee-orange) !important; font-size: clamp(1.0rem, 4vw, 1.4rem) !important; font-weight: 800 !important; margin: 0 !important; line-height: 1.2 !important; display: block !important; }
    
    /* TABS RESPONSIVAS */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 4px; background-color: white; padding: 8px; border-radius: 15px;
        overflow-x: auto; -webkit-overflow-scrolling: touch; display: flex; flex-wrap: nowrap;
    }
    .stTabs [data-baseweb="tab"] { 
        height: 45px; background-color: #f0f0f0; border-radius: 10px; padding: 0 12px;
        font-weight: 600; border: 2px solid transparent; white-space: nowrap; font-size: 14px; min-width: fit-content; flex-shrink: 0;
    }
    .stTabs [aria-selected="true"] { 
        background-color: var(--shopee-orange) !important; color: white !important; border-color: var(--shopee-orange); 
    }
    @media (min-width: 768px) {
        .stTabs [data-baseweb="tab-list"] { gap: 8px; padding: 10px; flex-wrap: wrap; }
        .stTabs [data-baseweb="tab"] { height: 50px; padding: 0 24px; font-size: 16px; }
    }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .info-box { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    .success-box { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    [data-testid="stFileUploader"] label[data-testid="stWidgetLabel"] { display: none; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- INICIALIZAÇÃO DA SESSÃO ---
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visual_tab1' not in st.session_state: st.session_state.df_visual_tab1 = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}

# --- FUNÇÕES AUXILIARES (GERAIS) ---
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

# --- [NOVA LÓGICA] CIRCUIT PRO COM TRAVA DE NÚMERO ---
def extrair_numero_correto(endereco):
    """
    CORREÇÃO PARA ERRO DE APARTAMENTO:
    Prioriza o número que vem LOGO DEPOIS da rua (índice 1 no split por vírgula),
    evitando pegar o número do apartamento no final da string.
    """
    if not isinstance(endereco, str): return "SN"
    
    # Normaliza
    partes = endereco.split(',')
    
    # Se tem formato "Rua, Numero, ..." (pelo menos 2 partes)
    if len(partes) >= 2:
        # Pega a segunda parte (índice 1) que deve ser o número do prédio
        candidato = partes[1].strip()
        # Tenta extrair apenas dígitos desse candidato
        match = re.search(r'(\d+)', candidato)
        if match:
            return match.group(1)
            
    # Fallback: Se não achou na posição padrão, procura o primeiro número da string inteira
    todos_numeros = re.findall(r'(\d+)', endereco)
    if todos_numeros:
        # Pega o PRIMEIRO número encontrado (geralmente é o da rua) e não o último
        return todos_numeros[0]
        
    return "SN"

def normalizar_nome_rua(endereco):
    if not isinstance(endereco, str): return ""
    # Pega só a parte antes da primeira vírgula (Rua X)
    nome = endereco.split(',')[0]
    return limpar_string(remover_acentos(nome))

def calcular_distancia_gps(lat1, lon1, lat2, lon2):
    """Retorna distância em METROS usando Haversine"""
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except:
        return 999999 # Se não tiver GPS válido, retorna longe
        
    R = 6371000 # Raio da Terra em metros
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def devem_agrupar(row1, row2):
    """
    Regras CLARAS de agrupamento (Solicitadas pelo Usuário):
    1. Números DIFERENTES → NÃO AGRUPA (sempre!)
    2. Números IGUAIS + Nome igual → AGRUPA
    3. Números IGUAIS + GPS próximo → AGRUPA (mesmo com nomes diferentes)
    """
    # Dados Linha 1
    num1 = row1['tmp_num']
    nome1 = row1['tmp_nome']
    lat1, lon1 = row1.get('tmp_lat', 0), row1.get('tmp_lon', 0)
    
    # Dados Linha 2
    num2 = row2['tmp_num']
    nome2 = row2['tmp_nome']
    lat2, lon2 = row2.get('tmp_lat', 0), row2.get('tmp_lon', 0)
    
    # REGRA PRIORITÁRIA: Números diferentes = NÃO AGRUPA
    if num1 != num2:
        return False # ❌ Casas diferentes
        
    # Se chegou aqui: números são IGUAIS
    
    # REGRA 1: Nome + Número iguais
    if nome1 == nome2:
        return True # ✅ AGRUPA
        
    # REGRA 2: Nomes diferentes, mas GPS próximo (<= 10m)
    if lat1 != 0 and lat2 != 0:
        dist = calcular_distancia_gps(lat1, lon1, lat2, lon2)
        if dist <= 10:
            return True # ✅ AGRUPA (erro de digitação no nome)
            
    return False # ❌ NÃO AGRUPA

def escolher_melhor_endereco(serie_enderecos):
    """Entre 'Av. Gov.' e 'Avenida Governador', escolhe o mais longo."""
    candidatos = [str(x).strip() for x in serie_enderecos if pd.notna(x) and str(x).strip() != '']
    if not candidatos: return ""
    return max(candidatos, key=len)

def gerar_planilha_otimizada_circuit_pro(df):
    col_end = next((c for c in df.columns if any(t in str(c).upper() for t in ['ADDRESS', 'ENDERE', 'DESTINATION'])), None)
    col_seq = next((c for c in df.columns if 'SEQUENCE' in str(c).upper()), None)
    col_lat = next((c for c in df.columns if any(t in str(c).upper() for t in ['LATITUDE', 'LAT'])), None)
    col_lon = next((c for c in df.columns if any(t in str(c).upper() for t in ['LONGITUDE', 'LON', 'LNG'])), None)

    if not col_end or not col_seq: return None
    
    df_temp = df.copy()

    # 1. PREPARAR DADOS PARA COMPARAÇÃO
    df_temp['tmp_num'] = df_temp[col_end].apply(extrair_numero_correto)
    df_temp['tmp_nome'] = df_temp[col_end].apply(normalizar_nome_rua)
    
    if col_lat and col_lon:
        df_temp['tmp_lat'] = pd.to_numeric(df_temp[col_lat], errors='coerce').fillna(0)
        df_temp['tmp_lon'] = pd.to_numeric(df_temp[col_lon], errors='coerce').fillna(0)
    else:
        df_temp['tmp_lat'] = 0
        df_temp['tmp_lon'] = 0

    # 2. ORDENAR (Crucial para o loop funcionar)
    # Agrupa vizinhos potenciais: Primeiro pelo número, depois pelo nome
    df_temp = df_temp.sort_values(by=['tmp_num', 'tmp_nome']).reset_index(drop=True)
    
    # 3. APLICAR LÓGICA "DEVEM AGRUPAR" (Clusterização)
    group_ids = [0] * len(df_temp)
    current_id = 0
    
    for i in range(1, len(df_temp)):
        prev_row = df_temp.iloc[i-1]
        curr_row = df_temp.iloc[i]
        
        if devem_agrupar(prev_row, curr_row):
            group_ids[i] = current_id # Mantém o ID (Agrupa)
        else:
            current_id += 1
            group_ids[i] = current_id # Novo Grupo
            
    df_temp['CLUSTER_ID'] = group_ids
    
    # 4. AGREGAR DADOS
    agg_dict = {col: 'first' for col in df_temp.columns if col not in ['CLUSTER_ID', col_seq, col_end, 'tmp_num', 'tmp_nome', 'tmp_lat', 'tmp_lon']}
    agg_dict[col_end] = escolher_melhor_endereco 
    
    def unir_seqs(x): 
        vals = sorted(list(set(x.astype(str))))
        try: vals.sort(key=int)
        except: pass
        return ', '.join(vals)
    
    df_final = df_temp.groupby('CLUSTER_ID').agg({**agg_dict, col_seq: unir_seqs}).reset_index()
    
    # Remove colunas temporárias
    cols_drop = [c for c in ['CLUSTER_ID', 'tmp_num', 'tmp_nome', 'tmp_lat', 'tmp_lon'] if c in df_final.columns]
    df_final = df_final.drop(columns=cols_drop)
    
    try:
        df_final['SortKey'] = df_final[col_seq].apply(lambda x: int(str(x).split(',')[0]))
        return df_final.sort_values('SortKey').drop(columns=['SortKey'])
    except:
        return df_final

# --- INTERFACE TABS ---
tab1, tab2, tab3 = st.tabs(["🎯 Única", "📊 Lote", "⚡ Circuit"])

with tab1:
    st.markdown("##### 📥 Upload Romaneio Geral")
    up_padrao = st.file_uploader("Upload Romaneio Geral", type=["xlsx"], key="up_padrao", label_visibility="collapsed")
    if up_padrao:
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

with tab2:
    st.markdown("##### 📥 Upload (Mesmo da Aba 1)")
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
                                    st.session_state.planilhas_sessao[s] = b_ind.getvalue(); break
                if st.session_state.planilhas_sessao:
                    st.markdown("##### 📥 Downloads Prontos:")
                    cols_dl = st.columns(3)
                    for idx, (nome, data) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_dl[idx % 3]:
                            st.download_button(label=f"📄 Rota {nome}", data=data, file_name=f"Rota_{nome}.xlsx", key=f"dl_sessao_{nome}", use_container_width=True)
    else:
        st.info("Faça o upload do romaneio na Aba 1 para usar esta função.")

with tab3:
    st.markdown("##### 📥 Upload Específico")
    st.markdown('<div class="success-box"><strong>⚡ Circuit Pro:</strong> Otimização de Paradas ("Casadinhas")</div>', unsafe_allow_html=True)
    st.info("ℹ️ Critério Seguro: Agrupa apenas se (Números Iguais) e (GPS <= 10m OU Nomes Iguais).")
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
                st.error("Erro: Colunas necessárias não encontradas (Endereço, Sequence).")