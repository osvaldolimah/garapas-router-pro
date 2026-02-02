import streamlit as st
import pandas as pd
import io
import unicodedata
from PIL import Image
import pytesseract
import re

# --- CONFIGURAÇÃO DO TESSERACT NO WINDOWS ---
# Se você instalou no caminho padrão, essa linha permite que o código funcione no seu PC.
# Se estiver no Linux/Cloud, o próprio sistema gerencia isso.
import platform
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configuração da página
st.set_page_config(page_title="Filtro de Rotas e Paradas", page_icon="🚚", layout="wide")

# --- SISTEMA DE DESIGN (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px; background-color: white; border-bottom: 4px solid var(--shopee-orange); border-radius: 0 0 20px 20px; margin-bottom: 20px; }
    .main-title { color: var(--shopee-orange); font-weight: 800; }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-weight: 700; border-radius: 12px; height: 60px; width: 100%; border: none; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: var(--shopee-orange) !important; color: white !important; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---
def limpar_string(s):
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo):
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def extrair_gaiolas_da_imagem(imagem_upload):
    try:
        image = Image.open(imagem_upload)
        # Extrai o texto da imagem
        texto_extraido = pytesseract.image_to_string(image, lang='por')
        
        # REGEX MELHORADO: Procura Letra + Hífen (opcional) + Números (ex: B-20, B20, A-01)
        padrao = re.compile(r'([A-Z]\s*-?\s*\d+)')
        matches = padrao.findall(texto_extraido.upper())
        
        gaiolas_encontradas = [limpar_string(m) for m in matches]
        return list(dict.fromkeys(gaiolas_encontradas)), texto_extraido
    except Exception as e:
        st.error(f"Erro no motor OCR: {e}")
        return [], ""

# --- INTERFACE ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# Inicialização da memória do App
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visualizacao' not in st.session_state: st.session_state.df_visualizacao = None
if 'df_resumo_imagem' not in st.session_state: st.session_state.df_resumo_imagem = None

col_file, col_cage = st.columns([1, 1])

with col_file:
    st.markdown("##### 📥 Passo 1: Romaneio")
    arquivo_upload = st.file_uploader("Selecione o Excel", type=["xlsx"], label_visibility="collapsed")

with col_cage:
    st.markdown("##### 📦 Passo 2: Seleção")
    tab_digitar, tab_escanear = st.tabs(["⌨️ Digitar", "📸 Escanear"])
    
    with tab_digitar:
        gaiola_manual = st.text_input("Código da Gaiola", placeholder="Ex: B-20").strip().upper()
    with tab_escanear:
        imagem_upload = st.file_uploader("Tire foto da lista", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)
executar = st.button("🚀 PROCESSAR AGORA")

# --- LÓGICA DE PROCESSAMENTO ---
if arquivo_upload and executar:
    xl = pd.ExcelFile(arquivo_upload)
    
    # MODO IMAGEM
    if imagem_upload:
        with st.spinner('📸 Analisando foto...'):
            lista_gaiolas, texto_bruto = extrair_gaiolas_da_imagem(imagem_upload)
            
            if not lista_gaiolas:
                st.warning("Não encontrei códigos de gaiola na foto.")
                with st.expander("🔍 Ver o que o computador leu na foto"):
                    st.text(texto_bruto)
            else:
                resumo = []
                # Processamento simplificado para o resumo
                df_raw = pd.read_excel(xl, sheet_name=xl.sheet_names[0], header=None)
                
                # Acha a coluna da gaiola (mesma lógica anterior)
                col_gaiola = next((c for c in df_raw.columns if df_raw[c].astype(str).apply(limpar_string).isin(lista_gaiolas).any()), None)
                
                if col_gaiola is not None:
                    for g in lista_gaiolas:
                        df_g = df_raw[df_raw[col_gaiola].astype(str).apply(limpar_string) == g]
                        if not df_g.empty:
                            # Tenta achar a coluna de endereço para contar paradas
                            col_end = df_g.apply(lambda x: x.astype(str).map(len).max()).idxmax()
                            paradas = len(df_g[col_end].apply(extrair_base_endereco).unique())
                            resumo.append({"Gaiola": g, "Pacotes": len(df_g), "Paradas": paradas})
                    
                    st.session_state.df_resumo_imagem = pd.DataFrame(resumo)
                    st.session_state.modo = "imagem"

    # MODO MANUAL
    elif gaiola_manual:
        # (Aqui entra a sua lógica de filtrar uma única gaiola e gerar download que já funcionava)
        st.info(f"Processando gaiola {gaiola_manual}...")
        # ... (código anterior de filtragem individual)

# --- EXIBIÇÃO ---
if st.session_state.df_resumo_imagem is not None:
    st.markdown("### 📋 Resumo das Gaiolas na Foto")
    st.dataframe(st.session_state.df_resumo_imagem, use_container_width=True, hide_index=True)