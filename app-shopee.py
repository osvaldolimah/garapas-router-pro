import streamlit as st
import pandas as pd
import io
import unicodedata
from PIL import Image
import pytesseract
import re
import cv2
import numpy as np
import platform

# --- CONFIGURAÇÃO DO TESSERACT (WINDOWS) ---
if platform.system() == "Windows":
    # Ajuste o caminho abaixo se você instalou em local diferente
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configuração da página
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SISTEMA DE DESIGN (CSS SEGURO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root {
        --shopee-orange: #EE4D2D;
        --shopee-bg: #F6F6F6;
        --placeholder-color: rgba(49, 51, 63, 0.4); 
    }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container {
        text-align: center; padding: 20px 10px; background-color: white;
        border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px;
        border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .main-title { color: var(--shopee-orange); font-size: 2.2rem; font-weight: 800; margin: 0; }
    .tutorial-section { background: white; padding: 15px; border-radius: 15px; margin-bottom: 20px; }
    
    /* Botões e Inputs */
    div.stButton > button {
        background-color: var(--shopee-orange) !important; color: white !important;
        font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important;
        width: 100% !important; height: 60px !important; border: none !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: var(--shopee-orange) !important; color: white !important; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES TÉCNICAS ---
def limpar_string(s):
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo):
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def processar_imagem_avancado(imagem_upload):
    try:
        # Converter imagem para OpenCV
        file_bytes = np.asarray(bytearray(imagem_upload.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # --- TRATAMENTO DE IMAGEM (PARA LER TODAS AS GAIOLAS) ---
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) # Tons de cinza
        # Binarização: Deixa o fundo branco e o texto preto puro (melhora 200% o OCR)
        _, threshold = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Leitura OCR com configuração de "Bloco de Texto" (PSM 6)
        texto_extraido = pytesseract.image_to_string(threshold, lang='por', config='--psm 6')
        
        # Filtro Regex Flexível: Pega A10, B-20, C 30, Gaiola D40
        padrao = re.compile(r'([A-Z]\s*[:\-\s]?\s*\d+)')
        matches = padrao.findall(texto_extraido.upper())
        
        gaiolas_limpas = list(dict.fromkeys([limpar_string(m) for m in matches if m]))
        return gaiolas_limpas, texto_extraido
    except Exception as e:
        st.error(f"Erro no processamento de imagem: {e}")
        return [], ""

# --- INTERFACE ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# Inicialização de variáveis
if 'df_resumo' not in st.session_state: st.session_state.df_resumo = None
if 'df_individual' not in st.session_state: st.session_state.df_individual = None
if 'binario_excel' not in st.session_state: st.session_state.binario_excel = None

st.markdown("""
<div class="tutorial-section">
    <span><b>Passo 1:</b> Suba o Excel. <b>Passo 2:</b> Escolha entre digitar uma gaiola ou tirar foto da lista.</span>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### 📥 Passo 1: Romaneio")
    arquivo_excel = st.file_uploader("Excel", type=["xlsx"], label_visibility="collapsed")

with col2:
    st.markdown("##### 📦 Passo 2: Seleção")
    t1, t2 = st.tabs(["⌨️ Digitar", "📸 Escanear"])
    with t1:
        gaiola_manual = st.text_input("Gaiola", placeholder="Ex: B-20").strip().upper()
    with t2:
        foto_lista = st.file_uploader("Foto", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)
btn_processar = st.button("🚀 INICIAR PROCESSAMENTO")

# --- LÓGICA DE EXECUÇÃO ---
if arquivo_excel and btn_processar:
    try:
        xl = pd.ExcelFile(arquivo_excel)
        df_raw = pd.read_excel(xl, sheet_name=xl.sheet_names[0], header=None)
        
        # --- CENÁRIO A: FOTO DA LISTA (OCR) ---
        if foto_lista:
            with st.spinner('📸 Escaneando lista completa...'):
                gaiolas_detectadas, texto_bruto = processar_imagem_avancado(foto_lista)
                
                if not gaiolas_detectadas:
                    st.warning("Não identifiquei códigos na imagem.")
                    with st.expander("Ver o que o PC leu"): st.text(texto_bruto)
                else:
                    # Acha a coluna da gaiola no Excel
                    col_g_idx = next((c for c in df_raw.columns if df_raw[c].astype(str).apply(limpar_string).isin(gaiolas_detectadas).any()), None)
                    
                    if col_g_idx is not None:
                        resumo_final = []
                        for g in gaiolas_detectadas:
                            df_g = df_raw[df_raw[col_g_idx].astype(str).apply(limpar_string) == g]
                            if not df_g.empty:
                                # Acha coluna de endereço para contar paradas reais
                                col_end = df_g.apply(lambda x: x.astype(str).map(len).max()).idxmax()
                                paradas = len(df_g[col_end].apply(extrair_base_endereco).unique())
                                resumo_final.append({"Gaiola": g, "📦 Pacotes": len(df_g), "📍 Paradas Reais": paradas})
                        
                        st.session_state.df_resumo = pd.DataFrame(resumo_final)
                        st.session_state.df_individual = None # Limpa o outro modo

        # --- CENÁRIO B: DIGITAÇÃO MANUAL ---
        elif gaiola_manual:
            with st.spinner('⚙️ Gerando rota individual...'):
                target = limpar_string(gaiola_manual)
                col_g_idx = next((c for c in df_raw.columns if df_raw[c].astype(str).apply(limpar_string).eq(target).any()), None)
                
                if col_g_idx is not None:
                    df_f = df_raw[df_raw[col_g_idx].astype(str).apply(limpar_string) == target].copy()
                    col_end = df_f.apply(lambda x: x.astype(str).map(len).max()).idxmax()
                    
                    # Cria planilha de saída
                    df_f['Parada'] = df_f[col_end].apply(extrair_base_endereco)
                    mapa = {end: i + 1 for i, end in enumerate(df_f['Parada'].unique())}
                    
                    saida = pd.DataFrame()
                    saida['Parada'] = df_f['Parada'].map(mapa).astype(str)
                    saida['Endereco'] = df_f[col_end].astype(str)
                    
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w: saida.to_excel(w, index=False)
                    
                    st.session_state.binario_excel = buf.getvalue()
                    st.session_state.df_individual = saida
                    st.session_state.df_resumo = None # Limpa o outro modo

    except Exception as e:
        st.error(f"Erro ao processar: {e}")

# --- EXIBIÇÃO DE RESULTADOS ---
if st.session_state.df_resumo is not None:
    st.markdown("---")
    st.subheader("📋 Resumo da Lista (Foto)")
    st.dataframe(st.session_state.df_resumo, use_container_width=True, hide_index=True)

if st.session_state.df_individual is not None:
    st.markdown("---")
    st.subheader(f"📊 Rota Gerada: {gaiola_manual}")
    st.dataframe(st.session_state.df_individual, use_container_width=True, hide_index=True)
    st.download_button("📥 BAIXAR PLANILHA", st.session_state.binario_excel, f"Rota_{gaiola_manual}.xlsx", use_container_width=True)