import streamlit as st
import pandas as pd
from google import genai
from google.genai.types import HttpOptions
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

# --- FUNÇÕES DE IA COM DIRETRIZES TÉCNICAS ---
def inicializar_ia():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Chave de API não encontrada nos Secrets!")
        return None
    return genai.Client(api_key=api_key, http_options=HttpOptions(api_version='v1'))

def analisar_com_ia(client, dados_romaneio, pergunta):
    # Aqui injetamos o treinamento e as diretrizes do app original
    prompt_sistema = f"""
    Você é o Agente 'Waze Humano', especialista em logística da Shopee para a região de Fortaleza/CE.
    
    DIRETRIZES DE ANÁLISE:
    1. GAIOLAS: Identifique códigos como 'C-01', 'C-42', etc. Elas representam os agrupamentos de pacotes.
    2. LOCALIDADE: Foco total em bairros de Fortaleza (Edson Queiroz, Meireles, Aldeota, etc).
    3. FILTRAGEM: O usuário precisa separar comércios de residências para otimizar o horário de entrega.
    4. PRIORIDADE: Identifique pacotes que pareçam ser de empresas ou órgãos públicos.

    DADOS DO ROMANEIO ATUAL:
    {dados_romaneio.to_string()}
    
    PERGUNTA DO ESTRATEGISTA: {pergunta}
    
    REPOSTA: Seja extremamente direto. Se ele pediu gaiolas, liste as gaiolas e o porquê.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_sistema
        )
        return response.text
    except Exception as e:
        return f"Erro na análise: {e}"

# --- INTERFACE ---
st.title("🚚 Waze Humano - Shopee Turbo")
st.subheader("Inteligência Logística Aplicada")

with st.sidebar:
    st.image("https://logodownload.org/wp-content/uploads/2021/03/shopee-logo-0.png", width=100)
    uploaded_file = st.file_uploader("Subir Romaneio Excel", type=['xlsx'])
    if st.button("Reiniciar Sistema"):
        st.rerun()

tab1, tab2 = st.tabs(["🎯 Filtro Manual", "🤖 Agente de IA"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    with tab1:
        st.write("### Visão Geral da Carga")
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.write("### Comando Central da IA")
        st.info("A IA agora conhece as regras de Gaiolas e Bairros de Fortaleza.")
        pergunta = st.text_input("Comando (Ex: 'Quais pacotes da gaiola C-42 são comerciais?')")
        
        if st.button("Executar Análise"):
            client = inicializar_ia()
            if client:
                with st.spinner("IA processando diretrizes logísticas..."):
                    # Processamos os dados para a IA focar no que importa
                    resultado = analisar_com_ia(client, df.head(100), pergunta)
                    st.markdown("#### 🤖 Resultado da Inteligência:")
                    st.success(resultado)
else:
    st.info("Aguardando romaneio para iniciar estratégia.")

st.markdown("---")
st.caption("Sistema de Apoio Logístico - Waze Humano v2.5")