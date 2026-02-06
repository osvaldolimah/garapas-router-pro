import streamlit as st
import pandas as pd
import io
import unicodedata
import re
import math
import requests
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Dict, Optional

# --- LOGGING ---
logger = logging.getLogger("filtro_rotas")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- SESSÃO DE REQUESTS COM RETRY (HTTPS) ---
SESSION = requests.Session()
retries = Retry(total=3, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)

# Tenta importar a lib de GPS
try:
    from streamlit_js_eval import get_geolocation
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False

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

# Limite de upload (bytes)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

# --- SISTEMA DE DESIGN (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; --placeholder-color: rgba(49, 51, 63, 0.4); }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { color: var(--shopee-orange) !important; font-size: clamp(1.0rem, 4vw, 1.4rem) !important; font-weight: 800 !important; margin: 0 !important; line-height: 1.2 !important; display: block !important; }

    /* TABS: sem rolagem horizontal, permite quebra em linhas */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        background-color: white;
        padding: 6px;
        border-radius: 15px;
        width: 100%;
        box-sizing: border-box;
        overflow-x: hidden;
    }

    /* Cada aba: ocupa espaço proporcional, permite até 2 colunas em mobile */
    .stTabs [data-baseweb="tab"] {
        flex: 1 1 48%;
        min-width: 0;
        max-width: 48%;
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 6px 8px;
        font-weight: 600;
        border: 2px solid transparent;
        white-space: normal;
        text-align: center;
        font-size: 13px;
        line-height: 1.1;
        box-sizing: border-box;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Aba selecionada */
    .stTabs [aria-selected="true"] {
        background-color: var(--shopee-orange) !important;
        color: white !important;
        border-color: var(--shopee-orange);
    }

    /* Ajustes para telas maiores: volta ao layout de uma linha com abas maiores */
    @media (min-width: 768px) {
        .stTabs [data-baseweb="tab-list"] { gap: 8px; padding: 10px; flex-wrap: nowrap; }
        .stTabs [data-baseweb="tab"] { flex: 0 0 auto; min-width: 140px; max-width: none; padding: 0 24px; font-size: 16px; height: 50px; white-space: nowrap; }
    }

    /* Botão principal e cards mantidos */
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .info-box { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    .success-box { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    [data-testid="stFileUploader"] label[data-testid="stWidgetLabel"] { display: none; }
    .pit-card { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #EE4D2D; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .pit-title { font-weight: 800; color: #333; font-size: 1.1rem; }
    .pit-meta { color: #666; font-size: 0.9rem; }
    .pit-link { text-decoration: none; color: #2563EB; font-weight: bold; font-size: 0.9rem; }
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
if 'up_padrao_bytes' not in st.session_state: st.session_state.up_padrao_bytes = None

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
            if col_end_idx is not None:
                break
        if col_end_idx is None:
            try:
                col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).mean()).idxmax()
            except Exception:
                col_end_idx = df_filt.columns[0]
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
        saida['Gaiola'] = df_filt[col_gaiola_idx]
        saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", Fortaleza - CE"
        return {'dataframe': saida, 'pacotes': len(saida), 'paradas': len(mapa_stops), 'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])}
    except Exception as e:
        logger.exception("Erro ao processar gaiola %s", gaiola_alvo)
        st.error(f"⚠️ Erro ao processar gaiola {gaiola_alvo}. Ver logs para detalhes.")
        return None

def carregar_abas_excel(arquivo_bytes: bytes) -> Dict[str, pd.DataFrame]:
    try:
        xl = pd.ExcelFile(io.BytesIO(arquivo_bytes), engine='openpyxl')
        abas = {}
        for sheet in xl.sheet_names:
            try:
                abas[sheet] = pd.read_excel(xl, sheet_name=sheet, header=None, engine='openpyxl')
            except Exception:
                abas[sheet] = pd.read_excel(io.BytesIO(arquivo_bytes), sheet_name=sheet, header=None)
        return abas
    except Exception as e:
        logger.exception("Falha ao carregar abas do Excel")
        raise

def processar_multiplas_gaiolas(arquivo_bytes: bytes, codigos_gaiola: List[str]) -> Dict[str, Dict]:
    resultados = {}
    try:
        abas = carregar_abas_excel(arquivo_bytes)
        for gaiola in codigos_gaiola:
            target_limpo = limpar_string(gaiola)
            encontrado = False
            for aba, df_raw in abas.items():
                try:
                    col_gaiola_idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), None)
                except Exception:
                    col_gaiola_idx = None
                if col_gaiola_idx is not None:
                    res = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                    if res:
                        resultados[gaiola] = {'pacotes': res['pacotes'], 'paradas': res['paradas'], 'comercios': res['comercios'], 'encontrado': True}
                        encontrado = True
                        break
            if not encontrado:
                resultados[gaiola] = {'pacotes': 0, 'paradas': 0, 'comercios': 0, 'encontrado': False}
        return resultados
    except Exception as e:
        logger.exception("Erro ao processar múltiplas gaiolas")
        st.error("⚠️ Erro ao processar múltiplas gaiolas. Ver logs para detalhes.")
        return {}

# --- LÓGICA CIRCUIT PRO ---
def extrair_numero_correto(endereco):
    if not isinstance(endereco, str): return "SN"
    partes = endereco.split(',')
    if len(partes) >= 2:
        candidato = partes[1].strip()
        match = re.search(r'(\d+)', candidato)
        if match: return match.group(1)
    todos_numeros = re.findall(r'(\d+)', endereco)
    if todos_numeros: return todos_numeros[0]
    return "SN"

def normalizar_nome_rua(endereco):
    if not isinstance(endereco, str): return ""
    nome = endereco.split(',')[0]
    return limpar_string(remover_acentos(nome))

def calcular_distancia_gps(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except Exception:
        return 999999
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def devem_agrupar(row1, row2):
    num1 = row1['tmp_num']; nome1 = row1['tmp_nome']
    lat1, lon1 = row1.get('tmp_lat', 0), row1.get('tmp_lon', 0)
    num2 = row2['tmp_num']; nome2 = row2['tmp_nome']
    lat2, lon2 = row2.get('tmp_lat', 0), row2.get('tmp_lon', 0)
    
    if num1 != num2: return False
    if nome1 == nome2: return True
    if lat1 != 0 and lat2 != 0:
        dist = calcular_distancia_gps(lat1, lon1, lat2, lon2)
        if dist <= 10: return True
    return False

def escolher_melhor_endereco(serie_enderecos):
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
    df_temp['tmp_num'] = df_temp[col_end].apply(extrair_numero_correto)
    df_temp['tmp_nome'] = df_temp[col_end].apply(normalizar_nome_rua)
    if col_lat and col_lon:
        df_temp['tmp_lat'] = pd.to_numeric(df_temp[col_lat], errors='coerce').fillna(0)
        df_temp['tmp_lon'] = pd.to_numeric(df_temp[col_lon], errors='coerce').fillna(0)
    else:
        df_temp['tmp_lat'] = 0; df_temp['tmp_lon'] = 0
    df_temp = df_temp.sort_values(by=['tmp_num', 'tmp_nome']).reset_index(drop=True)
    group_ids = [0] * len(df_temp); current_id = 0
    for i in range(1, len(df_temp)):
        if devem_agrupar(df_temp.iloc[i-1], df_temp.iloc[i]): group_ids[i] = current_id
        else: current_id += 1; group_ids[i] = current_id
    df_temp['CLUSTER_ID'] = group_ids
    agg_dict = {col: 'first' for col in df_temp.columns if col not in ['CLUSTER_ID', col_seq, col_end, 'tmp_num', 'tmp_nome', 'tmp_lat', 'tmp_lon']}
    agg_dict[col_end] = escolher_melhor_endereco 
    def unir_seqs(x): 
        vals = sorted(list(set(x.astype(str)))); 
        try: vals.sort(key=int)
        except: pass
        return ', '.join(vals)
    df_final = df_temp.groupby('CLUSTER_ID').agg({**agg_dict, col_seq: unir_seqs}).reset_index()
    cols_drop = [c for c in ['CLUSTER_ID', 'tmp_num', 'tmp_nome', 'tmp_lat', 'tmp_lon'] if c in df_final.columns]
    df_final = df_final.drop(columns=cols_drop)
    try:
        df_final['SortKey'] = df_final[col_seq].apply(lambda x: int(str(x).split(',')[0]))
        return df_final.sort_values('SortKey').drop(columns=['SortKey'])
    except Exception:
        return df_final

# --- FUNÇÕES OSM MELHORADAS ---
@st.cache_data(ttl=3600)
def buscar_locais_osm_cached(lat_round, lon_round, raio):
    return buscar_locais_osm_base(lat_round, lon_round, raio)

def buscar_locais_osm_base(lat, lon, raio):
    try:
        overpass_url = "https://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json][timeout:10];
        (
          nwr["amenity"~"^(restaurant|fuel|cafe|fast_food)$"](around:{raio},{lat},{lon});
          nwr["shop"~"^(convenience|supermarket)$"](around:{raio},{lat},{lon});
        );
        out center;
        """
        response = SESSION.get(overpass_url, params={'data': overpass_query}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            locais = []
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                nome = tags.get('name', 'Sem Nome')
                amenity = tags.get('amenity', '')
                shop = tags.get('shop', '')
                
                # Categorização
                if amenity == 'fuel' or 'posto' in nome.lower():
                    tipo_fmt = "⛽ Posto"; icone = "⛽"
                elif amenity in ['restaurant', 'cafe', 'fast_food']:
                    tipo_fmt = "🍴 Restaurante"; icone = "🍴"
                elif shop in ['convenience', 'supermarket']:
                    tipo_fmt = "🏪 Mercado"; icone = "🏪"
                else:
                    continue
                
                e_lat, e_lon = None, None
                if 'lat' in element and 'lon' in element:
                    e_lat = element.get('lat'); e_lon = element.get('lon')
                elif 'center' in element:
                    e_lat = element['center'].get('lat'); e_lon = element['center'].get('lon')
                
                if e_lat is None or e_lon is None: continue
                dist = calcular_distancia_gps(lat, lon, e_lat, e_lon)
                locais.append({'nome': nome, 'tipo': tipo_fmt, 'icone': icone, 'distancia': dist, 'lat': e_lat, 'lon': e_lon})
            locais.sort(key=lambda x: x['distancia'])
            return locais[:10]
        else:
            return []
    except Exception as e:
        logger.exception("Erro ao consultar Overpass")
        return []

def buscar_com_raio_progressivo(lat, lon, max_tentativas=3):
    lat_r = round(lat, 3); lon_r = round(lon, 3)
    raios = [1500, 3000, 5000]
    for tentativa, raio in enumerate(raios):
        try:
            locais = buscar_locais_osm_cached(lat_r, lon_r, raio)
            if locais:
                return locais, raio
            if tentativa < len(raios) - 1: time.sleep(1)
        except Exception as e:
            if tentativa < len(raios) - 1: time.sleep(2)
    return [], 0

# --- INTERFACE TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "⚡ Circuit Pro", "📍 Pit Stop", "🧭 Radar"])

with tab1:
    st.markdown("##### 📥 Upload do Romaneio")
    up_padrao = st.file_uploader("Envie o arquivo Excel", type=["xlsx"], key="up_padrao")
    
    if up_padrao:
        try:
            raw_bytes = up_padrao.read()
            if len(raw_bytes) > MAX_UPLOAD_BYTES:
                st.error(f"Arquivo muito grande. Limite {MAX_UPLOAD_BYTES // (1024*1024)} MB.")
            else:
                if st.session_state.get('up_padrao_bytes') != raw_bytes:
                    st.session_state.up_padrao_bytes = raw_bytes
                    st.session_state.df_cache = None
                
                if st.session_state.df_cache is None:
                    with st.spinner("📊 Carregando romaneio..."):
                        try:
                            st.session_state.df_cache = pd.read_excel(io.BytesIO(raw_bytes), engine='openpyxl')
                        except Exception:
                            st.session_state.df_cache = pd.read_excel(io.BytesIO(raw_bytes))
                
                st.markdown('<div class="info-box"><strong>💡 Modo Gaiola Única:</strong> Filtre e gere a rota detalhada.</div>', unsafe_allow_html=True)
                g_unica = st.text_input("📦 Código da Gaiola", placeholder="Ex: B-50", key="gui_tab1").strip().upper()
                
                if st.button("🚀 GERAR ROTA DA GAIOLA", key="btn_u_tab1", use_container_width=True):
                    if not g_unica:
                        st.warning("⚠️ Digite o código da gaiola.")
                    else:
                        st.session_state.modo_atual = 'unica'
                        target = limpar_string(g_unica); enc = False
                        with st.spinner(f"⚙️ Processando gaiola {g_unica}..."):
                            abas = carregar_abas_excel(raw_bytes)
                            for aba, df_r in abas.items():
                                idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target).any()), None)
                                if idx is not None:
                                    res = processar_gaiola_unica(df_r, g_unica, idx)
                                    if res:
                                        enc = True
                                        buf = io.BytesIO()
                                        with pd.ExcelWriter(buf, engine='openpyxl') as w:
                                            res['dataframe'].to_excel(w, index=False)
                                        st.session_state.dados_prontos = buf.getvalue()
                                        st.session_state.df_visual_tab1 = res['dataframe']
                                        st.session_state.metricas_tab1 = res
                                        break
                            if not enc:
                                st.error(f"❌ Gaiola '{g_unica}' não encontrada.")
        except Exception:
            st.error("Erro ao ler arquivo.")
    
    if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
        m = st.session_state.metricas_tab1
        c = st.columns(3)
        c[0].metric("📦 Pacotes", m["pacotes"])
        c[1].metric("📍 Paradas", m["paradas"])
        c[2].metric("🏪 Comércios", m["comercios"])
        st.dataframe(st.session_state.df_visual_tab1, use_container_width=True, hide_index=True)
        st.download_button("📥 BAIXAR PLANILHA", st.session_state.dados_prontos, f"Rota_{g_unica}.xlsx", use_container_width=True)

with tab2:
    st.markdown("##### 📥 Processamento em Lote")
    
    if st.session_state.df_cache is not None and st.session_state.get('up_padrao_bytes') is not None:
        raw_bytes = st.session_state.up_padrao_bytes
        st.markdown('<div class="info-box"><strong>💡 Modo Múltiplas Gaiolas:</strong> Resumo rápido de várias cargas.</div>', unsafe_allow_html=True)
        cod_m = st.text_area("📦 Códigos das Gaiolas (uma por linha)", placeholder="A-36\nB-50", key="cm_tab2", height=150)
        
        if st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", key="btn_m_tab2", use_container_width=True):
            lista = [c.strip().upper() for c in cod_m.split('\n') if c.strip()]
            if not lista:
                st.warning("⚠️ Digite pelo menos um código.")
            else:
                st.session_state.modo_atual = 'multiplas'
                with st.spinner(f"⚙️ Processando {len(lista)} gaiola(s)..."):
                    st.session_state.resultado_multiplas = processar_multiplas_gaiolas(raw_bytes, lista)
        
        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            res = st.session_state.resultado_multiplas
            st.dataframe(pd.DataFrame([{'Gaiola': k, 'Status': '✅' if v['encontrado'] else '❌', 'Pacotes': v['pacotes'], 'Paradas': v['paradas']} for k, v in res.items()]), use_container_width=True, hide_index=True)
            g_enc = [k for k, v in res.items() if v['encontrado']]
            if g_enc:
                st.markdown("---")
                st.markdown("##### ✅ Selecione para download individual:")
                selecionadas = []
                cols = st.columns(3)
                for i, g in enumerate(g_enc):
                    with cols[i % 3]:
                        if st.checkbox(f"**{g}**", key=f"chk_m_{g}"): selecionadas.append(g)
                if selecionadas and st.button("📥 PREPARAR ARQUIVOS CIRCUIT"):
                    st.session_state.planilhas_sessao = {}
                    try:
                        abas = carregar_abas_excel(raw_bytes)
                        for s in selecionadas:
                            target_l = limpar_string(s)
                            for aba, df_r in abas.items():
                                idx_g = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target_l).any()), None)
                                if idx_g is not None:
                                    r_ind = processar_gaiola_unica(df_r, s, idx_g)
                                    if r_ind:
                                        b_ind = io.BytesIO()
                                        with pd.ExcelWriter(b_ind, engine='openpyxl') as w:
                                            r_ind['dataframe'].to_excel(w, index=False)
                                        st.session_state.planilhas_sessao[s] = b_ind.getvalue()
                                        break
                    except Exception:
                        st.error("Erro ao preparar arquivos.")
                if st.session_state.planilhas_sessao:
                    st.markdown("##### 📥 Downloads Prontos:")
                    cols_dl = st.columns(3)
                    for idx, (nome, data) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_dl[idx % 3]:
                            st.download_button(label=f"📄 {nome}", data=data, file_name=f"Rota_{nome}.xlsx", key=f"dl_sessao_{nome}", use_container_width=True)
    else:
        st.info("📤 Faça o upload do romaneio na aba 'Gaiola Única' primeiro.")

with tab3:
    st.markdown("##### ⚡ Circuit Pro - Otimização de Casadinhas")
    st.info("ℹ️ **Critério Inteligente:** Agrupa apenas se (Números Iguais) E (GPS ≤ 10m OU Nomes Iguais)")
    up_circuit = st.file_uploader("📤 Upload do Romaneio Específico", type=["xlsx"], key="up_circuit")
    
    if up_circuit:
        try:
            raw_c = up_circuit.read()
            if len(raw_c) > MAX_UPLOAD_BYTES:
                st.error("Arquivo muito grande.")
            else:
                try:
                    df_c = pd.read_excel(io.BytesIO(raw_c), engine='openpyxl')
                except Exception:
                    df_c = pd.read_excel(io.BytesIO(raw_c))
                
                if st.button("🚀 GERAR PLANILHA DAS CASADINHAS", use_container_width=True):
                    res_c = gerar_planilha_otimizada_circuit_pro(df_c)
                    if res_c is not None:
                        reducao = len(df_c) - len(res_c)
                        st.success(f"✅ Otimização concluída! Economia de {reducao} paradas.")
                        buf_c = io.BytesIO()
                        with pd.ExcelWriter(buf_c, engine='openpyxl') as w:
                            res_c.to_excel(w, index=False)
                        st.download_button("📥 BAIXAR PLANILHA OTIMIZADA", buf_c.getvalue(), "Circuit_Otimizado.xlsx", use_container_width=True)
                        st.dataframe(res_c, use_container_width=True, hide_index=True)
                    else:
                        st.error("❌ Erro: Colunas necessárias não encontradas.")
        except Exception:
            st.error("Erro ao processar arquivo.")

with tab4:
    st.markdown("##### 📍 Pit Stop - Serviços Próximos")
    
    if not GPS_AVAILABLE:
        st.error("⚠️ Biblioteca de GPS não encontrada. Adicione 'streamlit-js-eval' ao requirements.txt.")
    else:
        st.info("📱 Permita o acesso à localização do navegador.")
        location = get_geolocation(component_key='get_geo')

        if location:
            lat = location['coords']['latitude']
            lon = location['coords']['longitude']
            
            st.success(f"📍 Localização encontrada!")
            
            if st.button("🔍 BUSCAR SERVIÇOS PRÓXIMOS", use_container_width=True, key="btn_buscar_pit"):
                with st.spinner("🔍 Consultando mapa..."):
                    locais_proximos, raio_usado = buscar_com_raio_progressivo(lat, lon)
                
                if locais_proximos:
                    raio_km = raio_usado / 1000
                    st.success(f"✅ Encontrados **{len(locais_proximos)}** serviços em até **{raio_km:.1f} km**")
                    
                    for local in locais_proximos:
                        dist_m = int(local['distancia'])
                        dist_fmt = f"{dist_m} metros" if dist_m < 1000 else f"{dist_m/1000:.1f} km"
                        link_maps = f"https://www.google.com/maps/search/?api=1&query={local['lat']},{local['lon']}"
                        st.markdown(f"""
                        <div class="pit-card">
                            <div class="pit-title">{local['icone']} {local['nome']}</div>
                            <div class="pit-meta">{local['tipo']} • a <strong>{dist_fmt}</strong></div>
                            <a href="{link_maps}" target="_blank" class="pit-link">🗺️ Abrir no Google Maps</a>
                        </div>
                        """, unsafe_allow_html=True)
                    st.caption("🗺️ Dados fornecidos pelo OpenStreetMap")
                else:
                    st.warning("⚠️ Nenhum serviço encontrado.")

# --- ABA 5: RADAR DE BAIRROS ---
with tab5:
    st.markdown("##### 🧭 Radar de Bairros")
    st.markdown('<div class="info-box"><strong>🎯 Estratégia:</strong> Descubra quais gaiolas passam pelos bairros que você prefere.</div>', unsafe_allow_html=True)
    
    # Inputs
    bairros_txt = st.text_area("Digite os bairros (separados por vírgula)", placeholder="Ex: Maraponga, Jardim Cearense, Aerolândia", height=80)
    
    if st.button("🔍 RASTREAR GAIOLAS", key="btn_radar", use_container_width=True):
        if not bairros_txt:
            st.warning("⚠️ Digite pelo menos um bairro.")
        elif st.session_state.get('up_padrao_bytes') is None:
            st.warning("⚠️ Faça o upload do romaneio na Aba 1 primeiro.")
        else:
            bairros_lista = [limpar_string(b) for b in bairros_txt.split(',')]
            raw_bytes = st.session_state.up_padrao_bytes
            
            with st.spinner("Varrendo todas as rotas..."):
                try:
                    abas = carregar_abas_excel(raw_bytes)
                    gaiolas_identificadas = set()
                    
                    # 1. Identificar Gaiolas que passam nos bairros
                    for sheet_name, df in abas.items():
                        # Lógica Inteligente para encontrar cabeçalho (Linha 0 a 5)
                        col_bairro_idx = None
                        col_gaiola_idx = None
                        
                        # Varre as primeiras 5 linhas para achar os índices das colunas
                        for r in range(min(5, len(df))):
                            row_values = [str(x).upper() for x in df.iloc[r].values]
                            
                            # Procura índice da coluna BAIRRO
                            if col_bairro_idx is None:
                                for i, val in enumerate(row_values):
                                    if any(t in val for t in ['BAIRRO', 'NEIGHBORHOOD']):
                                        col_bairro_idx = i
                                        break
                            
                            # Procura índice da coluna GAIOLA
                            if col_gaiola_idx is None:
                                for i, val in enumerate(row_values):
                                    if any(t in val for t in ['GAIOLA', 'LETRA', 'ROTA', 'CAGE', 'LPN']):
                                        col_gaiola_idx = i
                                        break
                            
                            # Se achou ambos, para a busca
                            if col_bairro_idx is not None and col_gaiola_idx is not None:
                                break
                        
                        if col_bairro_idx is not None and col_gaiola_idx is not None:
                            # Normaliza coluna Bairro para busca (usando o índice encontrado)
                            mask = df[col_bairro_idx].astype(str).apply(limpar_string).apply(lambda x: any(b in x for b in bairros_lista))
                            gaiolas_encontradas = df[mask][col_gaiola_idx].astype(str).unique()
                            for g in gaiolas_encontradas:
                                # Filtra lixo (se houver cabeçalho repetido ou células vazias)
                                g_limpo = limpar_string(g)
                                if len(g_limpo) > 1 and "GAIOLA" not in g_limpo: 
                                    gaiolas_identificadas.add(g)
                    
                    # 2. Processar métricas dessas gaiolas
                    resultados_radar = []
                    for g in sorted(list(gaiolas_identificadas)):
                         # Reutiliza lógica de busca da Tab 2
                        target_l = limpar_string(g)
                        for sheet_name, df in abas.items():
                             # Acha coluna da gaiola nesta aba (varrendo conteúdo, não cabeçalho)
                            idx_g = next((c for c in df.columns if df[c].astype(str).apply(limpar_string).eq(target_l).any()), None)
                            if idx_g is not None:
                                res = processar_gaiola_unica(df, g, idx_g)
                                if res:
                                    # Calcula otimização
                                    otimizacao = res['pacotes'] - res['paradas']
                                    pct = (otimizacao / res['pacotes']) * 100 if res['pacotes'] > 0 else 0
                                    
                                    resultados_radar.append({
                                        'Gaiola': g,
                                        'Pacotes': res['pacotes'],
                                        'Paradas Reais': res['paradas'],
                                        'Economia': f"{otimizacao} ({int(pct)}%)",
                                        'Comércios': res['comercios']
                                    })
                                break # Processou a gaiola, vai para a próxima
                    
                    if resultados_radar:
                        st.success(f"✅ Encontradas {len(resultados_radar)} gaiolas na região!")
                        df_radar = pd.DataFrame(resultados_radar)
                        st.dataframe(df_radar, use_container_width=True, hide_index=True)
                    else:
                        st.warning("❌ Nenhuma gaiola encontrada para esses bairros.")
                        
                except Exception as e:
                    logger.exception("Erro no Radar de Bairros")
                    st.error("Erro ao processar. Verifique o arquivo.")