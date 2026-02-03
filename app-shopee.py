import streamlit as st
import pandas as pd
from google import genai
import os

# Configuração da Página
st.set_page_config(page_title="Waze Humano - Shopee Turbo", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; }
    .stDataFrame { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE IA ---
def inicializar_ia():
    # Busca a chave nos Secrets do Streamlit ou variáveis de ambiente
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Chave de API não encontrada! Configure 'GEMINI_API_KEY' nos Secrets.")
        return None
    return genai.Client(api_key=api_key)

def analisar_com_ia(client, dados_romaneio, pergunta):
    prompt = f"""
    Você é o assistente logístico do 'Waze Humano' em Fortaleza.
    Dados do Romaneio:
    {dados_romaneio.to_string()}
    
    Pergunta do Usuário: {pergunta}
    
    Responda de forma clara, focando em otimizar a rota de entrega.
    """
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Erro na IA: {e}"

# --- INTERFACE PRINCIPAL ---
st.title("🚚 Waze Humano - Filtro de Romaneios")
st.subheader("Otimização de Rotas Shopee - Fortaleza/CE")

# Sidebar para Upload
with st.sidebar:
    st.image("https://logodownload.org/wp-content/uploads/2021/03/shopee-logo-0.png", width=100)
    uploaded_file = st.file_uploader("Carregue o Excel do Romaneio", type=['xlsx'])
    
    if st.button("Limpar Dados"):
        st.rerun()

# Tabs: Filtro Tradicional e Agente de IA
tab1, tab2 = st.tabs(["🎯 Filtro Rápido", "🤖 Agente de IA"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    with tab1:
        st.write("### Dados Brutos")
        st.dataframe(df.head(10))
        
        # Lógica de Filtro (Sua lógica turbo atual)
        bairro_filtro = st.multiselect("Filtrar por Bairro", options=df['Bairro'].unique() if 'Bairro' in df.columns else [])
        if bairro_filtro:
            df_filtrado = df[df['Bairro'].isin(bairro_filtro)]
            st.success(f"Encontrados {len(df_filtrado)} pacotes.")
            st.dataframe(df_filtrado)

    with tab2:
        st.write("### Pergunte ao Agente Logístico")
        pergunta = st.text_input("Ex: Quais desses endereços são comerciais no Edson Queiroz?")
        
        if st.button("Consultar IA"):
            client = inicializar_ia()
            if client:
                with st.spinner("IA analisando a rota..."):
                    # Enviamos apenas uma amostra ou dados filtrados para economizar cota
                    resultado = analisar_com_ia(client, df.head(50), pergunta)
                    st.markdown("#### 🤖 Sugestão da IA:")
                    st.info(resultado)

else:
    st.info("Aguardando upload do romaneio para começar o dia.")

# --- RODAPÉ ---
st.markdown("---")
st.caption("Desenvolvido para uso exclusivo em rotas de entrega Shopee - Fortaleza.")