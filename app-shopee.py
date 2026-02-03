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

# --- FUNÇÕES DE IA ---
def inicializar_ia():
    # Busca a chave nos Secrets do Streamlit
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Chave de API não encontrada! Configure 'GEMINI_API_KEY' nos Secrets do Streamlit.")
        return None
    
    # Configuramos para usar a versão 'v1' estável da API
    return genai.Client(
        api_key=api_key,
        http_options=HttpOptions(api_version='v1')
    )

def analisar_com_ia(client, dados_romaneio, pergunta):
    # Usamos o Gemini 2.5 Flash, que é o seu novo motor de alto desempenho
    modelo_estavel = 'gemini-2.5-flash'
    
    prompt = f"""
    Você é o assistente logístico do 'Waze Humano' em Fortaleza.
    Analise os seguintes dados do Romaneio da Shopee:
    
    {dados_romaneio.to_string()}
    
    Pergunta do Usuário: {pergunta}
    
    Responda de forma curta e prática, focando na eficiência das entregas.
    """
    
    try:
        response = client.models.generate_content(
            model=modelo_estavel,
            contents=prompt
        )
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⚠️ Cota esgotada. Aguarde um minuto para tentar novamente."
        return f"Erro na conexão com a IA: {e}"

# --- INTERFACE PRINCIPAL ---
st.title("🚚 Waze Humano - Filtro de Romaneios")
st.subheader("Otimização de Rotas Shopee - Fortaleza/CE")

# Sidebar para Upload
with st.sidebar:
    st.image("https://logodownload.org/wp-content/uploads/2021/03/shopee-logo-0.png", width=100)
    uploaded_file = st.file_uploader("Carregue o Excel do Romaneio", type=['xlsx'])
    
    if st.button("Limpar Sessão"):
        st.rerun()

# Tabs: Filtro Tradicional e Agente de IA
tab1, tab2 = st.tabs(["🎯 Filtro Rápido", "🤖 Agente de IA"])

if uploaded_file:
    try:
        # Lemos o Excel (ajuste o cabeçalho se necessário)
        df = pd.read_excel(uploaded_file)
        
        with tab1:
            st.write("### Lista de Pacotes")
            st.dataframe(df, use_container_width=True)
            
            # Filtro básico por bairro se a coluna existir
            if 'Bairro' in df.columns:
                bairros = st.multiselect("Selecionar Bairros", options=sorted(df['Bairro'].unique()))
                if bairros:
                    df_filtrado = df[df['Bairro'].isin(bairros)]
                    st.success(f"Exibindo {len(df_filtrado)} pacotes.")
                    st.dataframe(df_filtrado)

        with tab2:
            st.write("### Consultar Assistente Logístico")
            pergunta = st.text_input("Ex: Quais entregas são em prédios comerciais no bairro Edson Queiroz?")
            
            if st.button("Analisar Rota"):
                if not pergunta:
                    st.warning("Por favor, digite uma pergunta.")
                else:
                    client = inicializar_ia()
                    if client:
                        with st.spinner("IA processando seu romaneio..."):
                            # Enviamos uma amostra dos dados para não travar por tamanho
                            resumo_dados = df.head(100) 
                            resultado = analisar_com_ia(client, resumo_dados, pergunta)
                            st.markdown("#### 🤖 Sugestão da IA:")
                            st.info(resultado)
                            
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")

else:
    st.info("Aguardando upload do romaneio para começar as rotas do dia.")

# --- RODAPÉ ---
st.markdown("---")
st.caption("Desenvolvido para o estrategista de rotas 'Waze Humano' - Fortaleza/CE.")