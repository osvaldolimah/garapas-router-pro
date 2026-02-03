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
    .stButton>button { background-color: #ff4b4b; color: white; font-weight: bold; border-radius: 8px; height: 3em; }
    .main { background-color: #f0f2f6; }
    .metric-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- NÚCLEO LOGÍSTICO (TRATAMENTO DE DADOS) ---

def normalizar_codigo_gaiola(valor):
    """Transforma c42, C 42, c-42 no padrão oficial C-42"""
    if pd.isna(valor): return ""
    texto = str(valor).upper().strip()
    # Busca o padrão: Letra C + opcional (- ou espaço) + Números
    match = re.search(r'C[- ]?(\d+)', texto)
    if match:
        return f"C-{match.group(1)}"
    return texto

def detectar_coluna_gaiolas(df):
    """Varre as colunas para achar qual delas contém o padrão C-XX"""
    for col in df.columns:
        # Verifica se pelo menos 30% da coluna segue o padrão de gaiola
        amostra = df[col].astype(str).str.contains(r'[Cc][- ]?\d+', na=False)
        if amostra.mean() > 0.3:
            return col
    return None

def preparar_circuit(df_filtrado):
    """Garante as colunas básicas para o app Circuit"""
    # Se o romaneio tiver nomes diferentes, o Circuit precisa de colunas claras
    # Aqui você pode adicionar renomeação de colunas se desejar
    return df_filtrado

# --- MOTOR DE IA TREINADO (DIRETRIZES ALFA) ---

def inicializar_ia():
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("ERRO: Configure a GEMINI_API_KEY nos Secrets do Streamlit!")
        return None
    return genai.Client(api_key=api_key, http_options=HttpOptions(api_version='v1'))

def agente_logistico_alfa(client, df, comando):
    contexto = f"""
    Você é o Waze Humano, assistente de elite da Shopee em Fortaleza.
    Sua base de conhecimento é o código original 'Ponto Alfa'.
    
    REGRAS DE OURO:
    1. GAIOLAS: O padrão oficial é 'C-XX'. Ignore erros como 'c42' ou 'C 42' e trate como 'C-42'.
    2. BUSCA MULTI: Se o usuário pedir mais de uma gaiola, você deve analisar todas as citadas.
    3. CIRCUIT: Se pedirem para preparar o Circuit, foque nos endereços e bairros.
    4. LOGÍSTICA: Separe comércios de residências quando solicitado para evitar entregas fora de hora.

    DADOS DO ROMANEIO (Amostra):
    {df.head(40).to_string()}
    
    COMANDO: {comando}
    """
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=contexto)
        return response.text
    except Exception as e:
        return f"Erro na IA: {e}"

# --- INTERFACE PRINCIPAL ---
st.title("🚚 Waze Humano: Shopee Turbo v3.2")
st.caption("Estrategista de Rotas | Especialista em Fortaleza, CE")

with st.sidebar:
    st.header("📦 Importação")
    uploaded_file = st.file_uploader("Subir Romaneio Shopee (Excel)", type=['xlsx'])
    if st.button("🔄 Reiniciar App"): st.rerun()

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # 1. Detecção Automática da Coluna
    nome_coluna_original = detectar_coluna_gaiolas(df)
    
    if nome_coluna_original:
        # 2. Normalização de todos os códigos (Corrige c42 -> C-42)
        df['Gaiola_Limpa'] = df[nome_coluna_original].apply(normalizar_codigo_gaiola)
        
        # Métricas Dinâmicas
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"<div class='metric-card'><b>Total de Pacotes:</b><br>{len(df)}</div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><b>Gaiolas Detectadas:</b><br>{df['Gaiola_Limpa'].nunique()}</div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><b>Bairros na Rota:</b><br>{df['Bairro'].nunique() if 'Bairro' in df.columns else 'N/A'}</div>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🎯 Filtro de Gaiolas (Alfa)", "🤖 Agente de IA"])

        with tab1:
            st.subheader("Busca Inteligente de Gaiolas")
            busca = st.text_input("Quais gaiolas buscar? (Ex: c42, C01, C 15)", placeholder="Separe por vírgula...")
            
            if st.button("🔍 PROCURAR GAIOLA"):
                if busca:
                    # Normaliza a busca do usuário também para bater com os dados
                    termos_busca = [normalizar_codigo_gaiola(t.strip()) for t in busca.split(',')]
                    df_filtrado = df[df['Gaiola_Limpa'].isin(termos_busca)]
                    
                    if not df_filtrado.empty:
                        st.success(f"✅ Encontrados {len(df_filtrado)} pacotes para: {', '.join(termos_busca)}")
                        
                        # Preview Rápido
                        with st.expander("Ver lista de bairros e endereços"):
                            st.dataframe(df_filtrado, use_container_width=True)
                        
                        # Exportação Circuit
                        df_circuit = preparar_circuit(df_filtrado)
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_circuit.to_excel(writer, index=False)
                        
                        st.download_button(
                            label="📥 BAIXAR PLANILHA PARA O CIRCUIT",
                            data=output.getvalue(),
                            file_name=f"rota_{termos_busca[0]}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("Nenhuma gaiola encontrada com esses códigos. Verifique a digitação.")

        with tab2:
            st.subheader("Assistente Logístico Treinado")
            comando_ia = st.text_input("O que você deseja analisar?", placeholder="Ex: 'Quais gaiolas têm mais entregas comerciais?'")
            
            if st.button("Executar com IA"):
                client = inicializar_ia()
                if client:
                    with st.spinner("IA processando inteligência logístico-espacial..."):
                        resultado = agente_logistico_alfa(client, df, comando_ia)
                        st.markdown("#### 🤖 Resposta Estratégica:")
                        st.info(resultado)
    else:
        st.error("❌ Não consegui identificar a coluna de Gaiolas. O padrão 'C-XX' não foi encontrado no arquivo.")

else:
    st.info("Aguardando upload do romaneio para iniciar a estratégia de rotas.")

st.markdown("---")
st.caption("Waze Humano v3.2 - Logística e Automação para Shopee")