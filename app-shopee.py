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

# --- SISTEMA DE DESIGN MODERNO (INSPIRADO NA IMAGEM) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap');
    
    /* VARIÁVEIS DE COR */
    :root {
        --azul-principal: #0D3B66;
        --azul-escuro: #082744;
        --azul-medio: #1A5490;
        --branco: #FFFFFF;
        --cinza-claro: #F5F7FA;
        --cinza-texto: #6B7280;
        --sombra-card: 0 10px 30px rgba(13, 59, 102, 0.15);
    }
    
    /* RESET E GLOBAL */
    * {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0D3B66 0%, #1A5490 50%, #0D3B66 100%);
        position: relative;
        overflow-x: hidden;
    }
    
    /* FORMAS GEOMÉTRICAS DECORATIVAS */
    .stApp::before {
        content: '';
        position: fixed;
        top: -10%;
        right: -5%;
        width: 500px;
        height: 500px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%;
        z-index: 0;
        pointer-events: none;
    }
    
    .stApp::after {
        content: '';
        position: fixed;
        bottom: -10%;
        left: -5%;
        width: 600px;
        height: 600px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 60% 40% 30% 70% / 60% 50% 40% 50%;
        z-index: 0;
        pointer-events: none;
    }
    
    /* CONTAINER PRINCIPAL */
    .main .block-container {
        padding: 2rem 1rem;
        max-width: 1200px;
        position: relative;
        z-index: 1;
    }
    
    /* HEADER MODERNO */
    .header-container {
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.98) 100%);
        backdrop-filter: blur(10px);
        padding: 2rem 1.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: var(--sombra-card);
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .header-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #0D3B66, #1A5490, #0D3B66);
    }
    
    .main-title {
        color: var(--azul-principal) !important;
        font-size: clamp(1.5rem, 5vw, 2rem) !important;
        font-weight: 800 !important;
        margin: 0 !important;
        letter-spacing: -0.5px !important;
    }
    
    /* TABS MODERNAS */
    .stTabs {
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.1);
        padding: 0.5rem;
        border-radius: 15px;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background: rgba(255, 255, 255, 0.15);
        border-radius: 10px;
        padding: 0 1.5rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.7);
        border: 2px solid transparent;
        transition: all 0.3s ease;
        font-size: 14px;
        backdrop-filter: blur(5px);
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.25);
        color: rgba(255, 255, 255, 0.9);
    }
    
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: var(--azul-principal) !important;
        border-color: white;
        box-shadow: 0 4px 15px rgba(255, 255, 255, 0.3);
    }
    
    /* CARDS BRANCOS */
    .card-branco {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: var(--sombra-card);
        margin-bottom: 1.5rem;
    }
    
    /* INFO BOX MODERNA */
    .info-box {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border-left: 4px solid #3B82F6;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-size: 0.9rem;
        color: #1E40AF;
        box-shadow: 0 2px 10px rgba(59, 130, 246, 0.1);
    }
    
    .success-box {
        background: linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%);
        border-left: 4px solid #22C55E;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: #15803D;
        box-shadow: 0 2px 10px rgba(34, 197, 94, 0.1);
    }
    
    /* BOTÕES MODERNOS */
    div.stButton > button {
        background: linear-gradient(135deg, #0D3B66 0%, #1A5490 100%) !important;
        color: white !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 55px !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(13, 59, 102, 0.3) !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.5px !important;
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(13, 59, 102, 0.4) !important;
    }
    
    /* INPUTS MODERNOS */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 10px !important;
        border: 2px solid #E5E7EB !important;
        padding: 0.75rem !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #1A5490 !important;
        box-shadow: 0 0 0 3px rgba(26, 84, 144, 0.1) !important;
    }
    
    /* FILE UPLOADER MODERNO */
    [data-testid="stFileUploader"] {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: var(--sombra-card);
    }
    
    [data-testid="stFileUploader"] label {
        color: var(--azul-principal) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    
    /* DATAFRAME MODERNO */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 15px rgba(0, 0, 0, 0.08);
    }
    
    /* MÉTRICAS MODERNAS */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: var(--azul-principal) !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: var(--cinza-texto) !important;
    }
    
    /* PIT STOP CARDS */
    .pit-card {
        background: white;
        padding: 1.25rem;
        border-radius: 12px;
        border-left: 4px solid var(--azul-principal);
        box-shadow: 0 2px 10px rgba(13, 59, 102, 0.1);
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .pit-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 20px rgba(13, 59, 102, 0.15);
    }
    
    .pit-title {
        font-weight: 700;
        color: #1F2937;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .pit-meta {
        color: #6B7280;
        font-size: 0.9rem;
        margin-bottom: 0.75rem;
    }
    
    .pit-link {
        text-decoration: none;
        color: var(--azul-principal);
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        transition: all 0.3s ease;
    }
    
    .pit-link:hover {
        color: var(--azul-medio);
    }
    
    /* RESPONSIVIDADE */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem 0.5rem;
        }
        
        .header-container {
            padding: 1.5rem 1rem;
        }
        
        .main-title {
            font-size: 1.5rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 1rem;
            font-size: 13px;
        }
    }
    
    /* SCROLLBAR CUSTOMIZADA */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.5);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">🚚 Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

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
            logger.warning("Overpass retornou status %s", response.status_code)
            return []
    except Exception as e:
        logger.exception("Erro ao consultar Overpass")
        return []

def buscar_com_raio_progressivo(lat, lon, max_tentativas=3):
    lat_r = round(lat, 3); lon_r = round(lon, 3)
    raios = [1500, 3000, 5000]
    for tentativa, raio in enumerate(raios):
        try:
            logger.info(f"Tentativa {tentativa + 1}/{len(raios)}: Buscando em {raio}m")
            locais = buscar_locais_osm_cached(lat_r, lon_r, raio)
            if locais:
                logger.info(f"Encontrados {len(locais)} locais em {raio}m")
                return locais, raio
            if tentativa < len(raios) - 1: time.sleep(1)
        except Exception as e:
            logger.exception(f"Erro na tentativa {tentativa + 1}")
            if tentativa < len(raios) - 1: time.sleep(2)
    return [], 0

# --- INTERFACE TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "⚡ Circuit Pro", "📍 Pit Stop"])

with tab1:
    st.markdown('<div class="card-branco">', unsafe_allow_html=True)
    st.markdown("##### 📥 Upload do Romaneio")
    up_padrao = st.file_uploader("Envie o arquivo Excel com o romaneio completo", type=["xlsx"], key="up_padrao")
    st.markdown('</div>', unsafe_allow_html=True)
    
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
                df_completo = st.session_state.df_cache
                try:
                    xl = pd.ExcelFile(io.BytesIO(raw_bytes), engine='openpyxl')
                except Exception:
                    xl = pd.ExcelFile(io.BytesIO(raw_bytes))
                
                st.markdown('<div class="card-branco">', unsafe_allow_html=True)
                st.markdown('<div class="info-box"><strong>💡 Modo Gaiola Única:</strong> Filtre e gere a rota detalhada de uma gaiola específica.</div>', unsafe_allow_html=True)
                g_unica = st.text_input("📦 Código da Gaiola", placeholder="Ex: B-50, A-36, C-12", key="gui_tab1").strip().upper()
                if st.button("🚀 GERAR ROTA DA GAIOLA", key="btn_u_tab1", use_container_width=True):
                    if not g_unica:
                        st.warning("⚠️ Por favor, digite o código da gaiola.")
                    else:
                        st.session_state.modo_atual = 'unica'
                        target = limpar_string(g_unica); enc = False
                        with st.spinner(f"⚙️ Processando gaiola {g_unica}..."):
                            try:
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
                            except Exception:
                                logger.exception("Erro ao processar gaiola única")
                                st.error("Erro interno ao processar. Ver logs.")
                        if not enc:
                            st.error(f"❌ Gaiola '{g_unica}' não encontrada.")
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            logger.exception("Erro ao ler upload padrão")
            st.error("Erro ao processar o arquivo enviado. Verifique o formato e tente novamente.")
    
    if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
        st.markdown('<div class="card-branco">', unsafe_allow_html=True)
        m = st.session_state.metricas_tab1
        c = st.columns(3)
        c[0].metric("📦 Pacotes", m["pacotes"])
        c[1].metric("📍 Paradas", m["paradas"])
        c[2].metric("🏪 Comércios", m["comercios"])
        st.dataframe(st.session_state.df_visual_tab1, use_container_width=True, hide_index=True)
        st.download_button("📥 BAIXAR PLANILHA", st.session_state.dados_prontos, f"Rota_{g_unica}.xlsx", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="card-branco">', unsafe_allow_html=True)
    st.markdown("##### 📥 Processamento em Lote")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.df_cache is not None and st.session_state.get('up_padrao_bytes') is not None:
        raw_bytes = st.session_state.up_padrao_bytes
        try:
            xl = pd.ExcelFile(io.BytesIO(raw_bytes), engine='openpyxl')
        except Exception:
            xl = pd.ExcelFile(io.BytesIO(raw_bytes))
        
        st.markdown('<div class="card-branco">', unsafe_allow_html=True)
        st.markdown('<div class="info-box"><strong>💡 Modo Múltiplas Gaiolas:</strong> Processe várias gaiolas de uma vez e obtenha um resumo rápido.</div>', unsafe_allow_html=True)
        cod_m = st.text_area("📦 Códigos das Gaiolas (uma por linha)", placeholder="A-36\nB-50\nC-12\nD-08", key="cm_tab2", height=150)
        if st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", key="btn_m_tab2", use_container_width=True):
            lista = [c.strip().upper() for c in cod_m.split('\n') if c.strip()]
            if not lista:
                st.warning("⚠️ Por favor, digite pelo menos um código de gaiola.")
            else:
                st.session_state.modo_atual = 'multiplas'
                with st.spinner(f"⚙️ Processando {len(lista)} gaiola(s)..."):
                    st.session_state.resultado_multiplas = processar_multiplas_gaiolas(raw_bytes, lista)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            st.markdown('<div class="card-branco">', unsafe_allow_html=True)
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
                        logger.exception("Erro ao preparar arquivos circuit para download")
                        st.error("Erro ao preparar arquivos. Ver logs.")
                if st.session_state.planilhas_sessao:
                    st.markdown("##### 📥 Downloads Prontos:")
                    cols_dl = st.columns(3)
                    for idx, (nome, data) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_dl[idx % 3]:
                            st.download_button(label=f"📄 {nome}", data=data, file_name=f"Rota_{nome}.xlsx", key=f"dl_sessao_{nome}", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📤 Faça o upload do romaneio na aba 'Gaiola Única' primeiro.")

with tab3:
    st.markdown('<div class="card-branco">', unsafe_allow_html=True)
    st.markdown("##### ⚡ Circuit Pro - Otimização de Casadinhas")
    st.markdown('<div class="success-box"><strong>🎯 Funcionalidade:</strong> Agrupa pacotes para o mesmo endereço, otimizando suas paradas.</div>', unsafe_allow_html=True)
    st.info("ℹ️ **Critério Inteligente:** Agrupa apenas se (Números Iguais) E (GPS ≤ 10m OU Nomes Iguais)")
    up_circuit = st.file_uploader("📤 Upload do Romaneio Específico (já filtrado)", type=["xlsx"], key="up_circuit")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if up_circuit:
        try:
            raw_c = up_circuit.read()
            if len(raw_c) > MAX_UPLOAD_BYTES:
                st.error(f"Arquivo muito grande. Limite {MAX_UPLOAD_BYTES // (1024*1024)} MB.")
            else:
                try:
                    df_c = pd.read_excel(io.BytesIO(raw_c), engine='openpyxl')
                except Exception:
                    df_c = pd.read_excel(io.BytesIO(raw_c))
                
                st.markdown('<div class="card-branco">', unsafe_allow_html=True)
                if st.button("🚀 GERAR PLANILHA DAS CASADINHAS", use_container_width=True):
                    res_c = gerar_planilha_otimizada_circuit_pro(df_c)
                    if res_c is not None:
                        reducao = len(df_c) - len(res_c)
                        st.success(f"✅ Otimização concluída! **{len(df_c)} pacotes** reduzidos para **{len(res_c)} paradas reais** (economia de {reducao} paradas)")
                        buf_c = io.BytesIO()
                        with pd.ExcelWriter(buf_c, engine='openpyxl') as w:
                            res_c.to_excel(w, index=False)
                        st.download_button("📥 BAIXAR PLANILHA OTIMIZADA", buf_c.getvalue(), "Circuit_Otimizado.xlsx", use_container_width=True)
                        st.dataframe(res_c, use_container_width=True, hide_index=True)
                    else:
                        st.error("❌ Erro: Colunas necessárias não encontradas (Endereço, Sequence).")
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            logger.exception("Erro ao processar upload Circuit")
            st.error("Erro ao processar o arquivo enviado. Verifique o formato e tente novamente.")

with tab4:
    st.markdown('<div class="card-branco">', unsafe_allow_html=True)
    st.markdown("##### 📍 Pit Stop - Serviços Próximos")
    st.markdown('<div class="success-box"><strong>🔍 Busca Inteligente:</strong> Localiza postos, restaurantes e mercados próximos à sua localização.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if not GPS_AVAILABLE:
        st.error("⚠️ Biblioteca de GPS não encontrada. Adicione 'streamlit-js-eval' ao requirements.txt.")
    else:
        st.markdown('<div class="card-branco">', unsafe_allow_html=True)
        st.info("📱 Permita o acesso à localização do navegador para buscar serviços próximos.")
        location = get_geolocation(component_key='get_geo')
        st.markdown('</div>', unsafe_allow_html=True)

        if location:
            lat = location['coords']['latitude']
            lon = location['coords']['longitude']
            
            st.markdown('<div class="card-branco">', unsafe_allow_html=True)
            st.success(f"📍 Localização encontrada: {lat:.5f}, {lon:.5f}")
            
            if st.button("🔍 BUSCAR SERVIÇOS PRÓXIMOS", use_container_width=True, key="btn_buscar_pit"):
                status_placeholder = st.empty()
                status_placeholder.info("🔍 Consultando mapa... (pode levar até 10s)")
                locais_proximos, raio_usado = buscar_com_raio_progressivo(lat, lon)
                status_placeholder.empty()
                
                if locais_proximos:
                    raio_km = raio_usado / 1000
                    st.success(f"✅ Encontrados **{len(locais_proximos)}** serviços em até **{raio_km:.1f} km**")
                    st.markdown("---")
                    st.markdown("### 📍 Serviços Encontrados")
                    
                    for local in locais_proximos:
                        dist_m = int(local['distancia'])
                        if dist_m < 1000:
                            dist_fmt = f"{dist_m} metros"
                        else:
                            dist_km = dist_m / 1000
                            dist_fmt = f"{dist_km:.1f} km"
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
                    st.warning("⚠️ Nenhum serviço encontrado em até 5 km.")
                    st.info("""
                    **Isso pode acontecer se:**
                    - A região tem poucos estabelecimentos cadastrados no OpenStreetMap
                    - Os servidores da API estão sobrecarregados
                    - Você está em uma área muito afastada
                    
                    **💡 Dicas:**
                    - Tente novamente em alguns segundos
                    - Verifique se permitiu acesso à localização
                    - A busca funciona melhor em áreas urbanas
                    """)
            st.markdown('</div>', unsafe_allow_html=True)