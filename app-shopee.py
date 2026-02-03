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

# --- CONFIGURAÇÃO TESSERACT (PC) ---
if platform.system() == "Windows":
    # Caminho padrão da instalação que você fez
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Estrategista de Rotas PRO", page_icon="🚚", layout="wide")

# --- DESIGN DO APP ---
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

# --- FUNÇÕES DE LIMPEZA ---
def limpar_string(s):
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo):
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def processar_imagem_limpeza_total(imagem_upload):
    try:
        # 1. Converter para OpenCV
        file_bytes = np.asarray(bytearray(imagem_upload.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # 2. ZOOM DIGITAL (Aumenta 3x para o computador ver letras minúsculas)
        img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        
        # 3. FILTRO DE COR (Isolando o Canal Vermelho)
        # Em imagens com fundo vermelho, o canal R (índice 2) torna o fundo BRANCO
        b, g, r = cv2.split(img)
        
        # 4. CONTRASTE EXTREMO (Preto no Branco puro)
        # Tudo que for clarinho vira branco, o que for escuro vira preto
        _, final_img = cv2.threshold(r, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 5. OCR (PSM 6: Tratar como uma tabela/bloco único)
        texto_extraido = pytesseract.image_to_string(final_img, lang='por', config='--psm 6')
        
        # 6. BUSCA INTELIGENTE (Pega A-3, C-42, etc)
        padrao = re.compile(r'([A-Z]\s*[-]\s*\d+)')
        matches = padrao.findall(texto_extraido.upper())
        
        return [limpar_string(m) for m in matches], texto_extraido
    except Exception as e:
        return [], f"Erro: {e}"

# --- INTERFACE ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

if 'df_resumo' not in st.session_state: st.session_state.df_resumo = None

# Passo a passo para o usuário em Fortaleza
st.info("💡 Como você trabalha com entrega de pacotes, use este campo para conferir a carga total antes de sair.")

col1, col2 = st.columns(2)
with col1:
    st.markdown("##### 📥 Passo 1")
    arquivo_excel = st.file_uploader("Subir Romaneio (.xlsx)", type=["xlsx"], label_visibility="collapsed")
with col2:
    st.markdown("##### 📸 Passo 2")
    foto_lista = st.file_uploader("Foto da Tabela Vermelha", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

if arquivo_excel and foto_lista:
    if st.button("🚀 ANALISAR TODAS AS GAIOLAS"):
        try:
            xl = pd.ExcelFile(arquivo_excel)
            df_raw = pd.read_excel(xl, sheet_name=xl.sheet_names[0], header=None)
            
            with st.spinner('✨ Removendo fundo vermelho e lendo lista...'):
                gaiolas, texto_bruto = processar_imagem_limpeza_total(foto_lista)
                
                if not gaiolas:
                    st.warning("⚠️ Não consegui ler nada. Tente uma foto com mais luz.")
                    with st.expander("Ver o que o app 'viu'"): st.text(texto_bruto)
                else:
                    # Tenta achar a coluna de gaiola (Geralmente a última ou penúltima)
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
                        st.success(f"✅ Encontrei {len(resumo)} gaiolas na foto!")
                    else:
                        st.error("❌ Li os códigos, mas eles não existem neste Excel.")
                        st.write("Códigos lidos:", gaiolas)
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

if st.session_state.df_resumo is not None:
    st.markdown("---")
    st.subheader("📋 Resumo Consolidado")
    st.dataframe(st.session_state.df_resumo, use_container_width=True, hide_index=True)