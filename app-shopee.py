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
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- NÚCLEO LOGÍSTICO (SUAS DIRETRIZES DO CÓDIGO ALFA) ---
def limpar_gaiola(texto):
    """Trata erros de digitação: transforma C42 ou C 42 em C-42"""
    if pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    match = re.search(r'C[- ]?(\d+)', texto)
    return f"C-{match.group(1)}" if match else texto

def preparar_para_circuit(df_filtrado):
    """Prepara a planilha exatamente como o app Circuit exige"""
    colunas_circuit = {
        'Endereço': 'Address',
        'Número': 'House Number',
        'Bairro': 'City', # Ou agrupamento logístico
        'Cidade': 'Region',
        'CEP': 'Postcode'
    }
    # Tenta mapear o que encontrar no romaneio
    df_c = df_filtrado.copy()
    return df_c

# --- MOTOR DE INTELIGÊNCIA ARTIFICIAL ---
def inicializar_ia():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Configure a GEMINI_API_KEY nos Secrets do Streamlit!")
        return None
    return genai.Client(api_key=api_key, http_options=HttpOptions(api_version='v1'))

def agente_logistico_turbo(client, df, comando):
    # TREINAMENTO COMPLETO DA IA COM AS DIRETRIZES DO CÓDIGO ALFA
    contexto_treinamento = f"""
    Você é o cérebro do app 'Waze Humano'. Sua missão é executar comandos logísticos sobre o Romaneio Shopee.
    
    SUAS REGRAS DE EXECUÇÃO (PONTO ALFA):
    1. BUSCA DE GAIOLA: Identificar gaiolas como 'C-42'. Se o usuário digitar 'C42', você deve entender como 'C-42'.
    2. MULTI-GAIOLAS: Se pedirem várias (ex: C-01 e C-02), você deve filtrar ambas.
    3. CIRCUIT: Se o comando for preparar para o 'Circuit', você deve listar os endereços prontos para exportação.
    4. PRÉ-VISUALIZAÇÃO: Para gaiola única, mostre primeiro o resumo (Total de pacotes, Bairros afetados).
    5. ERROS: Identifique se há gaiolas com nomes estranhos e sugira a correção.

    DADOS ATUAIS (Amostra):
    {df.head(50).to_string()}
    
    COMANDO DO ESTRATEGISTA: {comando}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contexto_treinamento
        )
        return response.text
    except Exception as e:
        return f"Erro no motor: {e}"

# --- INTERFACE ---
st.title("🚚 Waze Humano: Shopee Turbo v3.0")
st.write(f"Estrategista de Rotas | Fortaleza, CE")

with st.sidebar:
    st.header("📦 Carga")
    uploaded_file = st.file_uploader("Arraste o Romaneio (Excel)", type=['xlsx'])
    if st.button("🔄 Resetar"): st.rerun()

if uploaded_file:
    # Processamento Inicial
    df = pd.read_excel(uploaded_file)
    if 'Gaiola' in df.columns:
        df['Gaiola_Limpa'] = df['Gaiola'].apply(limpar_gaiola)

    # Métricas Rápidas
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='metric-card'><b>Pacotes Totais:</b><br>{len(df)}</div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><b>Gaiolas:</b><br>{df['Gaiola'].nunique() if 'Gaiola' in df.columns else 'N/A'}</div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><b>Bairros:</b><br>{df['Bairro'].nunique() if 'Bairro' in df.columns else 'N/A'}</div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["⚡ Filtro Manual Alfa", "🤖 Agente de IA (Treinado)"])

    with tab1:
        st.subheader("Busca de Gaiolas Únicas ou Múltiplas")
        busca = st.text_input("Digite as gaiolas (ex: C-01, C-42):")
        
        if busca:
            lista_busca = [limpar_gaiola(x.strip()) for x in busca.split(',')]
            df_result = df[df['Gaiola_Limpa'].isin(lista_busca)]
            
            st.success(f"Resultados para: {', '.join(lista_busca)}")
            st.dataframe(df_result, use_container_width=True)
            
            # Exportação para o Circuit
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_result.to_excel(writer, index=False)
            st.download_button("📥 Baixar Planilha para o CIRCUIT", data=output.getvalue(), file_name="rota_circuit.xlsx")

    with tab2:
        st.subheader("Controle por Voz ou Texto")
        comando = st.text_input("O que você precisa fazer agora?", placeholder="Ex: 'Filtre a gaiola C42 e me diga quais são os bairros'")
        
        if st.button("Executar Estratégia"):
            client = inicializar_ia()
            if client:
                with st.spinner("IA executando diretrizes Alfa..."):
                    resposta = agente_logistico_turbo(client, df, comando)
                    st.info(f"🤖 **Resposta do Agente:**\n\n{resposta}")

else:
    st.info("Aguardando romaneio para iniciar a estratégia de rotas.")

st.markdown("---")
st.caption("Waze Humano Logística Integrada - Fortaleza/CE")