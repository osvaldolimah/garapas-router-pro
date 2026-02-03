import streamlit as st
import pandas as pd
import re
import io

# --- CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Waze Humano - Shopee Turbo", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    .stButton>button { background-color: #ff4b4b; color: white; font-weight: bold; border-radius: 8px; height: 3em; }
    .main { background-color: #f0f2f6; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- NÚCLEO LOGÍSTICO (SUA LÓGICA DE CONFIANÇA) ---

def limpar_gaiola(valor):
    """Transforma c42, C 42, c-42 no padrão oficial C-42"""
    if pd.isna(valor): return ""
    texto = str(valor).upper().strip()
    match = re.search(r'C[- ]?(\d+)', texto)
    if match:
        return f"C-{match.group(1)}"
    return texto

def detectar_coluna_gaiolas(df):
    """Varre as colunas para achar o padrão C-XX (Independente do nome da coluna)"""
    for col in df.columns:
        amostra = df[col].astype(str).str.contains(r'[Cc][- ]?\d+', na=False)
        if amostra.mean() > 0.3:
            return col
    return None

# --- INTERFACE PRINCIPAL ---
st.title("🚚 Waze Humano: Shopee Turbo")
st.write(f"Estrategista de Rotas | Fortaleza, CE")

with st.sidebar:
    st.header("📦 Importação")
    uploaded_file = st.file_uploader("Subir Romaneio Shopee (Excel)", type=['xlsx'])
    if st.button("🔄 Reiniciar App"): st.rerun()

if uploaded_file:
    # Lemos os dados e já aplicamos a inteligência de colunas do Ponto Alfa
    df = pd.read_excel(uploaded_file)
    nome_coluna_gaiola = detectar_coluna_gaiolas(df)
    
    if nome_coluna_gaiola:
        df['Gaiola_Limpa'] = df[nome_coluna_gaiola].apply(limpar_gaiola)
        
        # Painel de Métricas (Visibilidade Total)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='metric-card'><b>Total de Pacotes:</b><br>{len(df)}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><b>Gaiolas no Arquivo:</b><br>{df['Gaiola_Limpa'].nunique()}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><b>Bairros Detectados:</b><br>{df['Bairro'].nunique() if 'Bairro' in df.columns else 'N/A'}</div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # --- BUSCA E FILTRAGEM ---
        st.subheader("🎯 Filtrar para o Circuit")
        busca = st.text_input("Quais gaiolas você vai carregar? (Ex: c42, C01, C 15)", placeholder="Digite e clique no botão abaixo...")
        
        if st.button("🔍 PROCURAR GAIOLA"):
            if busca:
                # Normaliza o que o usuário digitou para bater com o Excel
                termos_busca = [limpar_gaiola(t.strip()) for t in busca.split(',')]
                df_filtrado = df[df['Gaiola_Limpa'].isin(termos_busca)]
                
                if not df_filtrado.empty:
                    st.success(f"✅ Sucesso! {len(df_filtrado)} pacotes prontos para a rota.")
                    
                    # Pre-visualização rápida antes de baixar
                    st.dataframe(df_filtrado, use_container_width=True)
                    
                    # Gerador do Excel para o Circuit
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_filtrado.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 BAIXAR PLANILHA PARA O CIRCUIT",
                        data=output.getvalue(),
                        file_name=f"ROTA_WAZE_HUMANO.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("Nenhuma gaiola encontrada com esses códigos. Verifique o arquivo.")
            else:
                st.info("Digite o código de uma gaiola para filtrar.")
    else:
        st.error("❌ Não foi possível identificar as Gaiolas. Verifique se o arquivo segue o padrão da Shopee.")

else:
    st.info("Aguardando upload do romaneio para iniciar a estratégia de rotas.")

st.markdown("---")
st.caption("Waze Humano v3.2 (Versão Estável) - Foco em Agilidade Logística")