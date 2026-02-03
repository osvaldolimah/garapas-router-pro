import streamlit as st
import pandas as pd
from google import genai
from google.genai.types import HttpOptions
import re
import io

# --- CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Waze Humano - Shopee Turbo", layout="wide", page_icon="🚚")

st.markdown("""
    <style>
    .stButton>button { background-color: #ff4b4b; color: white; font-weight: bold; border-radius: 8px; }
    .main { background-color: #f0f2f6; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES TÉCNICAS ---
def limpar_gaiola(texto):
    if pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    match = re.search(r'C[- ]?(\d+)', texto)
    return f"C-{match.group(1)}" if match else texto

def encontrar_coluna_gaiola(df):
    """Encontra a coluna da gaiola mesmo que o nome mude no Excel"""
    for col in df.columns:
        if 'gaiola' in col.lower():
            return col
    return None

def inicializar_ia():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Configure a GEMINI_API_KEY nos Secrets do Streamlit!")
        return None
    return genai.Client(api_key=api_key, http_options=HttpOptions(api_version='v1'))

# --- INTERFACE ---
st.title("🚚 Waze Humano: Shopee Turbo v3.1")
st.write(f"Estrategista de Rotas | Fortaleza, CE")

with st.sidebar:
    st.header("📦 Carga")
    uploaded_file = st.file_uploader("Arraste o Romaneio (Excel)", type=['xlsx'])
    if st.button("🔄 Resetar Sistema"): st.rerun()

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    col_gaiola = encontrar_coluna_gaiola(df)
    
    if col_gaiola:
        df['Gaiola_Limpa'] = df[col_gaiola].apply(limpar_gaiola)
    else:
        st.error("⚠️ Não encontrei uma coluna de 'Gaiola' no seu Excel. Verifique o arquivo.")

    # Métricas
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='metric-card'><b>Pacotes:</b> {len(df)}</div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><b>Gaiolas:</b> {df[col_gaiola].nunique() if col_gaiola else 0}</div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><b>Bairros:</b> {df['Bairro'].nunique() if 'Bairro' in df.columns else 'N/A'}</div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🎯 Filtro de Gaiolas", "🤖 Agente de IA"])

    with tab1:
        st.subheader("Busca de Gaiolas")
        busca = st.text_input("Digite a(s) gaiola(s) separadas por vírgula (ex: C42, C01):")
        botao_busca = st.button("🔍 PROCURAR GAIOLA") # SEU NOVO BOTÃO

        if botao_busca and busca:
            if 'Gaiola_Limpa' in df.columns:
                lista_busca = [limpar_gaiola(x.strip()) for x in busca.split(',')]
                df_result = df[df['Gaiola_Limpa'].isin(lista_busca)]
                
                if not df_result.empty:
                    st.success(f"Encontrados {len(df_result)} pacotes para: {', '.join(lista_busca)}")
                    st.dataframe(df_result, use_container_width=True)
                    
                    # Preparação para o Circuit
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_result.to_excel(writer, index=False)
                    st.download_button("📥 Baixar para o CIRCUIT", data=output.getvalue(), file_name="rota_circuit.xlsx")
                else:
                    st.warning("Nenhum pacote encontrado para essa(s) gaiola(s).")
            else:
                st.error("Erro interno: Coluna de processamento não gerada.")

    with tab2:
        st.subheader("Assistente de IA Treinado")
        comando = st.text_input("Comando logístico:", placeholder="Ex: 'Liste as gaiolas e seus bairros'")
        
        if st.button("Executar com IA"):
            client = inicializar_ia()
            if client:
                with st.spinner("IA analisando romaneio..."):
                    contexto = f"Você é o Waze Humano. Dados: {df.head(50).to_string()}. Comando: {comando}"
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=contexto)
                    st.info(f"🤖 **Resposta:**\n\n{response.text}")

else:
    st.info("Aguardando romaneio para iniciar a estratégia.")

st.markdown("---")
st.caption("Waze Humano Logística Integrada - Fortaleza/CE")