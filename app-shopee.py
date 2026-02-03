import streamlit as st
import pandas as pd
import re
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Waze Humano - Shopee Turbo", layout="wide", page_icon="🚚")

# --- ESTILO ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; font-weight: bold; }
    .main { background-color: #f5f5f5; }
    .css-1r6slb0 { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE LIMPEZA E TRATAMENTO ---
def limpar_gaiola(texto):
    """Corrige erros de digitação: c42, C 42 -> C-42"""
    if pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    match = re.search(r'C[- ]?(\d+)', texto)
    if match:
        return f"C-{match.group(1)}"
    return texto

def baixar_excel(df, nome_arquivo):
    """Gera o arquivo pronto para o Circuit"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- LÓGICA DE PROCESSAMENTO ---
def processar_gaiola_unica(df, gaiola_alvo):
    g_limpa = limpar_gaiola(gaiola_alvo)
    df_filtrado = df[df['Gaiola_Limpa'] == g_limpa]
    
    if not df_filtrado.empty:
        st.success(f"✅ Gaiola {g_limpa}: {len(df_filtrado)} pacotes encontrados.")
        
        # Métricas Rápidas
        c1, c2 = st.columns(2)
        with c1: st.metric("Total de Pacotes", len(df_filtrado))
        with c2: st.metric("Bairros Diferentes", df_filtrado['Bairro'].nunique() if 'Bairro' in df_filtrado.columns else "N/A")
        
        # Pré-visualização
        st.write("### Pré-visualização da Rota")
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Botão de Download para o Circuit
        excel_data = baixar_excel(df_filtrado, f"ROTA_{g_limpa}.xlsx")
        st.download_button(
            label=f"📥 BAIXAR PLANILHA {g_limpa} PARA O CIRCUIT",
            data=excel_data,
            file_name=f"ROTA_{g_limpa}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning(f"⚠️ Nenhuma gaiola encontrada como '{gaiola_alvo}'.")

def processar_multiplas_gaiolas(df, lista_gaiolas):
    gaiolas_limpas = [limpar_gaiola(g.strip()) for g in lista_gaiolas.split(',')]
    df_filtrado = df[df['Gaiola_Limpa'].isin(gaiolas_limpas)]
    
    if not df_filtrado.empty:
        st.success(f"✅ Total: {len(df_filtrado)} pacotes em {len(gaiolas_limpas)} gaiolas.")
        st.dataframe(df_filtrado, use_container_width=True)
        
        excel_data = baixar_excel(df_filtrado, "ROTA_MULTI_GAIOLAS.xlsx")
        st.download_button(
            label="📥 BAIXAR TODAS AS GAIOLAS (CIRCUIT)",
            data=excel_data,
            file_name="ROTA_MULTI_GAIOLAS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("❌ Nenhuma das gaiolas digitadas foi encontrada.")

# --- INTERFACE PRINCIPAL ---
st.title("🚚 Waze Humano - Shopee Turbo (Ponto Alfa)")

with st.sidebar:
    st.header("📂 Arquivos")
    arquivo = st.file_uploader("Carregue o Romaneio Excel", type=['xlsx'])
    if st.button("🔄 Reiniciar Sistema"): st.rerun()

if arquivo:
    df = pd.read_excel(arquivo)
    
    # Busca automática da coluna de Gaiola (por conteúdo)
    col_gaiola = None
    for col in df.columns:
        if df[col].astype(str).str.contains(r'[Cc][- ]?\d+', na=False).any():
            col_gaiola = col
            break
            
    if col_gaiola:
        df['Gaiola_Limpa'] = df[col_gaiola].apply(limpar_gaiola)
        
        aba1, aba2 = st.tabs(["📍 Gaiola Única", "📦 Múltiplas Gaiolas"])
        
        with aba1:
            gaiola_input = st.text_input("Digite o código da gaiola (Ex: c42):")
            if st.button("Procurar Gaiola Única"):
                processar_gaiola_unica(df, gaiola_input)
                
        with aba2:
            multi_input = st.text_area("Digite os códigos separados por vírgula (Ex: c42, c01, C 15):")
            if st.button("Processar Múltiplas"):
                processar_multiplas_gaiolas(df, multi_input)
    else:
        st.error("Não identifiquei o padrão de gaiolas 'C-XX' neste arquivo.")
else:
    st.info("Aguardando romaneio para iniciar a estratégia de rotas.")

st.markdown("---")
st.caption("Estrategista de Rotas - Fortaleza/CE")