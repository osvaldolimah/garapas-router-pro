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
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Waze Humano - Shopee Pro", page_icon="🚚", layout="wide")

# --- DESIGN (CSS) ---
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

def limpar_string(s):
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo):
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def processar_imagem_raio_x(imagem_upload):
    try:
        # 1. Carregar a imagem
        file_bytes = np.asarray(bytearray(imagem_upload.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        # 2. ZOOM DIGITAL (Melhora a leitura de letras pequenas)
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # 3. O SEGREDO: ISOLAR O CANAL VERMELHO
        # Em BGR, o vermelho é o índice 2. Ao isolar, o fundo vermelho vira branco.
        b, g, r = cv2.split(img)
        
        # 4. APLICAR LIMIAR (Threshold) para deixar o texto preto puro
        _, img_binaria = cv2.threshold(r, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 5. LEITURA OCR (PSM 6: Assume que é uma tabela/coluna)
        texto_extraido = pytesseract.image_to_string(img_binaria, lang='por', config='--psm 6')
        
        # 6. BUSCA FLEXÍVEL (Padrão: Letra, seguido de qualquer coisa, seguido de número)
        # Isso pega: C-17, C17, C 17, C:17
        padrao = re.compile(r'([A-Z]\s*[-]?\s*\d+)')
        matches = padrao.findall(texto_extraido.upper())
        
        gaiolas_encontradas = [limpar_string(m) for m in matches if m]
        return list(dict.fromkeys(gaiolas_encontradas)), texto_extraido
        
    except Exception as e:
        return [], f"Erro técnico: {e}"

# --- INTERFACE ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

if 'df_resumo' not in st.session_state: st.session_state.df_resumo = None

st.info("💡 Como o seu romaneio em Fortaleza tem colunas vermelhas, apliquei um filtro de contraste para o computador não 'se perder'.")

col1, col2 = st.columns(2)
with col1:
    st.markdown("##### 📥 Passo 1: Romaneio")
    arquivo_excel = st.file_uploader("Subir Excel", type=["xlsx"], label_visibility="collapsed")
with col2:
    st.markdown("##### 📸 Passo 2: Foto da Lista")
    foto_lista = st.file_uploader("Tire foto da planilha", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

if arquivo_excel and foto_lista:
    if st.button("🚀 PROCESSAR LISTA AGORA"):
        try:
            xl = pd.ExcelFile(arquivo_excel)
            df_raw = pd.read_excel(xl, sheet_name=xl.sheet_names[0], header=None)
            
            with st.spinner('✨ Removendo fundo vermelho e lendo códigos...'):
                gaiolas, texto_bruto = processar_imagem_raio_x(foto_lista)
                
                if not gaiolas:
                    st.warning("⚠️ Não encontrei os códigos. Verifique se a foto está focada.")
                    with st.expander("Ver o que o app 'leu'"): st.text(texto_bruto)
                else:
                    # Acha a coluna da gaiola no Excel
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
                        st.success(f"✅ Encontrei as gaiolas: {', '.join(gaiolas)}")
                    else:
                        st.error("❌ Os códigos lidos na foto não existem neste Excel.")
                        st.write("Lido na foto:", gaiolas)

        except Exception as e:
            st.error(f"Erro: {e}")

if st.session_state.df_resumo is not None:
    st.markdown("---")
    st.subheader("📋 Resumo da Carga")
    st.dataframe(st.session_state.df_resumo, use_container_width=True, hide_index=True)