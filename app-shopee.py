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

# --- CONFIGURAÇÃO TESSERACT ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Estrategista de Rotas PRO", page_icon="🚚", layout="wide")

# --- DESIGN MODERNO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px; background-color: white; border-bottom: 4px solid var(--shopee-orange); border-radius: 0 0 20px 20px; margin-bottom: 20px; }
    .main-title { color: var(--shopee-orange); font-weight: 800; }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-weight: 700; border-radius: 12px; height: 60px; width: 100%; border: none; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE ENGENHARIA ---
def limpar_string(s):
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo):
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def processar_imagem_raio_x(imagem_upload):
    try:
        # 1. Carregar imagem
        file_bytes = np.asarray(bytearray(imagem_upload.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # 2. REDIMENSIONAR (Aumenta 2x para melhorar leitura de letras pequenas)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 3. ISOLAR CANAL VERMELHO (O fundo vermelho vira branco, o texto continua preto)
        # Em OpenCV a ordem é BGR, então o Vermelho é o índice 2
        b, g, r = cv2.split(img)
        
        # 4. APLICAR CONTRASTE (Deixa o texto "gritante")
        _, final_img = cv2.threshold(r, 120, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 5. OCR (PSM 6 para tabelas)
        texto_extraido = pytesseract.image_to_string(final_img, lang='por', config='--psm 6')
        
        # 6. REGEX (Padrão C-17, A-44, C42)
        padrao = re.compile(r'([A-Z]\s*[-]?\s*\d+)')
        matches = padrao.findall(texto_extraido.upper())
        
        return [limpar_string(m) for m in matches], texto_extraido
    except Exception as e:
        return [], f"Erro: {e}"

# --- INTERFACE ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

if 'df_resumo' not in st.session_state: st.session_state.df_resumo = None

col1, col2 = st.columns(2)
with col1:
    st.markdown("##### 📥 Passo 1: Romaneio")
    arquivo_excel = st.file_uploader("Subir arquivo da Shopee", type=["xlsx"], label_visibility="collapsed")
with col2:
    st.markdown("##### 📸 Passo 2: Foto da Lista")
    foto_lista = st.file_uploader("Tire foto da planilha", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

btn = st.button("🚀 PROCESSAR LISTA AGORA")

if arquivo_excel and foto_lista and btn:
    try:
        xl = pd.ExcelFile(arquivo_excel)
        # Lê a primeira aba do romaneio que você usa em Fortaleza
        df_raw = pd.read_excel(xl, sheet_name=xl.sheet_names[0], header=None)
        
        with st.spinner('✨ Aplicando filtro Raio-X nas gaiolas...'):
            gaiolas, texto_bruto = processar_imagem_raio_x(foto_lista)
            
            if not gaiolas:
                st.warning("⚠️ O computador ainda não conseguiu ler os códigos.")
                with st.expander("Ver 'visão' do computador:"): st.text(texto_bruto)
            else:
                # Localizar coluna de gaiolas
                col_g_idx = next((c for c in df_raw.columns if df_raw[c].astype(str).apply(limpar_string).isin(gaiolas).any()), None)
                
                if col_g_idx is not None:
                    resumo = []
                    for g in gaiolas:
                        df_g = df_raw[df_raw[col_g_idx].astype(str).apply(limpar_string) == g]
                        if not df_g.empty:
                            col_end = df_g.apply(lambda x: x.astype(str).map(len).max()).idxmax()
                            paradas = len(df_g[col_end].apply(extrair_base_endereco).unique())
                            resumo.append({"Gaiola": g, "📦 Pacotes": len(df_g), "📍 Paradas Reais": paradas})
                    
                    st.session_state.df_resumo = pd.DataFrame(resumo)
                else:
                    st.error("❌ Li as gaiolas, mas elas não batem com o Excel aberto.")
                    st.write("Gaiolas lidas:", gaiolas)

    except Exception as e:
        st.error(f"Erro: {e}")

if st.session_state.df_resumo is not None:
    st.markdown("---")
    st.subheader("📋 Resumo da Carga")
    st.dataframe(st.session_state.df_resumo, use_container_width=True, hide_index=True)