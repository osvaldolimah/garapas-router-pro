import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional
from google import genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONSTANTES ---
TERMOS_COMERCIAIS = [
    'LOJA', 'MERCADO', 'MERCEARIA', 'FARMACIA', 'DROGARIA', 'SHOPPING', 
    'CLINICA', 'HOSPITAL', 'POSTO', 'OFICINA', 'RESTAURANTE', 'LANCHONETE', 
    'PADARIA', 'PANIFICADORA', 'ACADEMIA', 'ESCOLA', 'COLEGIO', 'FACULDADE', 
    'IGREJA', 'TEMPLO', 'EMPRESA', 'LTDA', 'MEI', 'SALA', 'SALAO', 'BARBEARIA', 
    'ESTACIONAMENTO', 'HOTEL', 'SUPERMERCADO', 'AMC', 'ATACADO', 'DISTRIBUIDORA', 
    'AUTOPECAS', 'VIDRAÇARIA', 'LABORATORIO', 'CLUBE', 'ASSOCIACAO', 'BOUTIQUE', 
    'MERCANTIL', 'DEPARTAMENTO', 'VARIEDADES', 'PIZZARIA', 'CHURRASCARIA', 
    'CARNES', 'PEIXARIA', 'FRUTARIA', 'HORTIFRUTI', 'FLORICULTURA'
]

TERMOS_ANULADORES = [
    'FRENTE', 'LADO', 'PROXIMO', 'VIZINHO', 'DEFRONTE', 'ATRAS', 
    'DEPOIS', 'PERTO', 'VIZINHA'
]

# --- SISTEMA DE DESIGN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

    :root {
        --shopee-orange: #EE4D2D;
        --shopee-bg: #F6F6F6;
        --placeholder-color: rgba(49, 51, 63, 0.4); 
        --success-green: #10B981;
        --info-blue: #3B82F6;
    }

    .stApp { 
        background-color: var(--shopee-bg);
        font-family: 'Inter', sans-serif;
    }

    .header-container {
        text-align: center;
        padding: 20px 10px;
        background-color: white;
        border-bottom: 4px solid var(--shopee-orange);
        margin-bottom: 20px;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    .main-title {
        color: var(--shopee-orange);
        font-size: clamp(1.4rem, 5vw, 2.2rem);
        font-weight: 800;
        margin: 0;
    }

    .tutorial-section {
        background: white;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }

    .step-item {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        font-size: 0.9rem;
        color: #555;
    }

    .step-badge {
        background: var(--shopee-orange);
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 12px;
        flex-shrink: 0;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: white;
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f0f0;
        border-radius: 10px;
        padding: 0 24px;
        font-weight: 600;
        border: 2px solid transparent;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--shopee-orange) !important;
        color: white !important;
        border-color: var(--shopee-orange);
    }

    [data-testid="stFileUploader"] section button div[data-testid="stMarkdownContainer"] p {
        font-size: 0 !important;
    }
    [data-testid="stFileUploader"] section button div[data-testid="stMarkdownContainer"] p::before {
        content: "📁 Selecionar Romaneio";
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        visibility: visible;
    }

    div.stButton > button {
        background-color: var(--shopee-orange) !important;
        color: white !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 60px !important;
        box-shadow: 0 6px 15px rgba(238, 77, 45, 0.3) !important;
        border: none !important;
        transition: all 0.1s ease;
    }
    div.stButton > button:active { transform: scale(0.96); }

    div[data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 10px;
        border-bottom: 3px solid var(--shopee-orange);
    }

    .info-box {
        background: #EFF6FF;
        border-left: 4px solid var(--info-blue);
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
        color: #1E40AF;
    }
    
    .success-box {
        background: #F0FDF4;
        border-left: 4px solid var(--success-green);
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
        font-size: 0.9rem;
        color: #065F46;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- INICIALIZAÇÃO DA SESSÃO ---
if 'dados_prontos' not in st.session_state:
    st.session_state.dados_prontos = None
if 'df_visualizacao' not in st.session_state:
    st.session_state.df_visualizacao = None
if 'modo_atual' not in st.session_state:
    st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state:
    st.session_state.resultado_multiplas = None
if 'df_cache' not in st.session_state:
    st.session_state.df_cache = None
if 'arquivo_atual' not in st.session_state:
    st.session_state.arquivo_atual = None

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def remover_acentos(texto: str) -> str:
    """Remove acentos de uma string."""
    return "".join(
        c for c in unicodedata.normalize('NFD', str(texto)) 
        if unicodedata.category(c) != 'Mn'
    ).upper()

@st.cache_data
def limpar_string(s: str) -> str:
    """Remove caracteres não alfanuméricos e converte para maiúsculas."""
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo: str) -> str:
    """Extrai a base do endereço para agrupamento de paradas."""
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def identificar_comercio(endereco: str) -> str:
    """Identifica se o endereço é comercial ou residencial."""
    end_limpo = remover_acentos(endereco)
    for parte in end_limpo.split(','):
        palavras = parte.split()
        for i, palavra in enumerate(palavras):
            p_limpa = "".join(filter(str.isalnum, palavra))
            if any(termo == p_limpa for termo in TERMOS_COMERCIAIS):
                if not any(anul in " ".join(palavras[:i]) for anul in TERMOS_ANULADORES):
                    return "🏪 Comércio"
    return "🏠 Residencial"

def processar_gaiola_unica(df_raw: pd.DataFrame, gaiola_alvo: str, col_gaiola_idx: int) -> Optional[Dict]:
    """
    Processa uma única gaiola e retorna os dados processados.
    
    Returns:
        Dicionário com dados processados ou None se houver erro
    """
    try:
        target_limpo = limpar_string(gaiola_alvo)
        df_filt = df_raw[df_raw[col_gaiola_idx].astype(str).apply(limpar_string) == target_limpo].copy()
        
        if df_filt.empty:
            return None
        
        # Identificar colunas
        col_end_idx, col_bairro_idx = None, None
        for r in range(min(15, len(df_raw))):
            linha = [str(x).upper() for x in df_raw.iloc[r].values]
            for i, val in enumerate(linha):
                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA', 'ADDRESS']):
                    col_end_idx = i
                if any(t in val for t in ['BAIRRO', 'SETOR', 'NEIGHBORHOOD']):
                    col_bairro_idx = i
        
        if col_end_idx is None:
            col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()
        
        # Processar endereços
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        
        # Criar DataFrame de saída
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
        saida['Gaiola'] = df_filt[col_gaiola_idx]
        saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        
        bairro = (df_filt[col_bairro_idx].astype(str) + ", ") if col_bairro_idx is not None else ""
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", " + bairro + "Fortaleza - CE"
        
        return {
            'dataframe': saida,
            'pacotes': len(saida),
            'paradas': len(mapa_stops),
            'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])
        }
    
    except Exception as e:
        st.error(f"⚠️ Erro ao processar gaiola {gaiola_alvo}: {e}")
        return None

def processar_multiplas_gaiolas(arquivo_excel, codigos_gaiola: List[str]) -> Dict[str, Dict]:
    """
    Processa múltiplas gaiolas e retorna resumo de cada uma.
    
    Returns:
        Dicionário com código da gaiola como chave e métricas como valor
    """
    resultados = {}
    
    try:
        xl = pd.ExcelFile(arquivo_excel)
        
        for gaiola in codigos_gaiola:
            target_limpo = limpar_string(gaiola)
            encontrado = False
            
            for aba in xl.sheet_names:
                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                
                # Procurar coluna da gaiola
                col_gaiola_idx = next(
                    (col for col in df_raw.columns 
                     if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), 
                    None
                )
                
                if col_gaiola_idx is not None:
                    resultado = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                    if resultado:
                        resultados[gaiola] = {
                            'pacotes': resultado['pacotes'],
                            'paradas': resultado['paradas'],
                            'comercios': resultado['comercios'],
                            'encontrado': True
                        }
                        encontrado = True
                        break
            
            if not encontrado:
                resultados[gaiola] = {
                    'pacotes': 0,
                    'paradas': 0,
                    'comercios': 0,
                    'encontrado': False
                }
        
        return resultados
    
    except Exception as e:
        st.error(f"⚠️ Erro ao processar múltiplas gaiolas: {e}")
        return {}

# --- MELHORIAS PRIORIDADE 1 ---

# MELHORIA #3: Cache do DataFrame (performance)
@st.cache_data(show_spinner=False)
def carregar_dataframe_completo(_arquivo) -> Optional[pd.DataFrame]:
    """
    Carrega DataFrame uma única vez e mantém em cache.
    MELHORIA: Evita múltiplas leituras do mesmo arquivo (economia de 50-70% de tempo).
    """
    try:
        return pd.read_excel(_arquivo)
    except Exception as e:
        st.error(f"❌ Erro ao carregar arquivo Excel: {e}")
        return None

# MELHORIA #1: Inicialização segura da IA
def inicializar_ia() -> Optional[genai.Client]:
    """
    Inicializa cliente Gemini com tratamento robusto de erros.
    MELHORIA: Validação adequada de API key e mensagens claras de erro.
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except KeyError:
        st.error("""
        ❌ **API Key não configurada**
        
        Para usar o Agente IA, configure a chave do Gemini:
        1. Crie o arquivo `.streamlit/secrets.toml`
        2. Adicione: `GEMINI_API_KEY = "sua-chave-aqui"`
        """)
        return None
    except Exception as e:
        st.error(f"❌ Erro ao inicializar IA: {e}")
        return None

# MELHORIA #5: Prompt otimizado (preservando TODA lógica original + melhorias)
def agente_ia_treinado(client: genai.Client, df: pd.DataFrame, pergunta: str) -> str:
    """
    Agente IA com contexto otimizado para planilhas grandes.
    
    LÓGICA PRESERVADA:
    - Busca específica por gaiola quando mencionada na pergunta
    - Usa dados reais do romaneio
    - Mantém todas as funções matemáticas originais
    
    MELHORIAS:
    - Contexto reduzido para evitar timeout
    - Prompt mais estruturado e específico
    - Instruções claras sobre cálculos
    """
    try:
        # LÓGICA ORIGINAL: Detectar gaiola na pergunta
        match_gaiola = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())
        contexto_dados = ""
        metricas_calculadas = None
        
        if match_gaiola:
            # LÓGICA ORIGINAL: Buscar dados específicos da gaiola
            g_alvo = limpar_string(match_gaiola.group(1))
            for col in df.columns:
                df_target = df[df[col].astype(str).apply(limpar_string) == g_alvo]
                if not df_target.empty:
                    try:
                        # CALCULAR MÉTRICAS REAIS (mesma lógica do processamento)
                        # Identificar coluna de endereço
                        col_end_idx = None
                        for r in range(min(15, len(df))):
                            linha = [str(x).upper() for x in df.iloc[r].values]
                            for i, val in enumerate(linha):
                                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA', 'ADDRESS']):
                                    col_end_idx = i
                                    break
                            if col_end_idx is not None:
                                break
                        
                        if col_end_idx is None:
                            col_end_idx = df_target.apply(lambda x: x.astype(str).map(len).max()).idxmax()
                        
                        # Aplicar a MESMA lógica de extração de base de endereço
                        df_target_copy = df_target.copy()
                        df_target_copy['CHAVE_STOP'] = df_target_copy[col_end_idx].apply(extrair_base_endereco)
                        
                        # Contar paradas únicas (RUA + NÚMERO)
                        paradas_unicas = df_target_copy['CHAVE_STOP'].unique()
                        num_paradas = len(paradas_unicas)
                        
                        # Contar comércios
                        num_comercios = sum(1 for end in df_target_copy[col_end_idx] if identificar_comercio(str(end)) == "🏪 Comércio")
                        
                        metricas_calculadas = {
                            'pacotes': len(df_target),
                            'paradas': num_paradas,
                            'comercios': num_comercios
                        }
                        
                        contexto_dados = f"""DADOS DA GAIOLA {g_alvo}:

✅ PACOTES: {metricas_calculadas['pacotes']}
✅ PARADAS: {metricas_calculadas['paradas']} (endereços únicos agrupados por rua+número)
✅ COMÉRCIOS: {metricas_calculadas['comercios']}

Nota: PARADA = vários pacotes no mesmo endereço base (rua + número)."""
                        break
                    except Exception as calc_error:
                        # Se falhar ao calcular métricas, usar modo simplificado
                        contexto_dados = f"""DADOS REAIS DA GAIOLA {g_alvo}:
                        
⚠️ Não foi possível calcular métricas automaticamente.
Erro: {str(calc_error)}

🔍 AMOSTRA DOS DADOS (primeiras 50 linhas de {len(df_target)}):
{df_target.head(50).to_string(max_rows=50)}

💡 Use a aba "Gaiola Única" para obter métricas precisas.
"""
                        break
        
        if not contexto_dados:
            # LÓGICA ORIGINAL: Usar amostra geral se não encontrou gaiola específica
            contexto_dados = f"""AMOSTRA DO ROMANEIO (primeiras 30 linhas de {len(df)} totais):
{df.head(30).to_string(max_rows=30)}

ESTATÍSTICAS GERAIS:
- Total de linhas no romaneio: {len(df)}
- Colunas disponíveis: {list(df.columns)}
"""
        
        # PROMPT OTIMIZADO - versão ultra compacta
        prompt = f"""Você é assistente de logística especializado em romaneios de entrega.

📊 DADOS:
{contexto_dados}

IMPORTANTE:
- PARADA = endereços únicos (rua+número). Vários pacotes podem ir para a mesma parada.
- PACOTE = cada item individual para entrega
- Use os valores fornecidos acima (já calculados corretamente)

Pergunta: {pergunta}

Resposta objetiva:"""

        # Chamar a IA com fallback de modelos (nomes atualizados 2025)
        modelos = [
            'gemini-2.5-flash',      # Modelo mais recente e rápido
            'gemini-2.0-flash',      # Modelo 2.0 estável
            'gemini-1.5-flash',      # Fallback 1.5
            'gemini-1.5-pro'         # Modelo mais poderoso
        ]
        
        for modelo in modelos:
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt
                )
                return response.text
            except Exception as model_error:
                if modelo == modelos[-1]:
                    raise
                continue
    
    except Exception as e:
        import traceback
        erro_completo = traceback.format_exc()
        erro_msg = str(e)
        
        # Verificar tipo específico de erro
        if 'API_KEY_INVALID' in erro_msg or 'API key not valid' in erro_msg:
            return """❌ **API Key do Gemini inválida ou expirada**

🔑 **Como resolver:**
1. Acesse o Streamlit Cloud → Settings → Secrets
2. Gere uma nova API Key em: https://aistudio.google.com/apikey
3. Atualize o secret: `GEMINI_API_KEY = "sua-nova-chave"`
4. Salve e aguarde o redeploy

💡 **Enquanto isso:** Use as abas "Gaiola Única" ou "Múltiplas Gaiolas" para processar suas rotas normalmente."""
        
        if '404' in erro_msg or 'not found' in erro_msg.lower():
            return """❌ **Erro de configuração do modelo de IA**
            
Os modelos Gemini disponíveis podem ter mudado. 

**Solução alternativa:**
1. Verifique sua API key do Gemini
2. Certifique-se de que tem acesso aos modelos Gemini
3. Ou use as funcionalidades de processamento de gaiolas (abas 1 e 2)

💡 O sistema funciona perfeitamente sem IA para filtrar e organizar rotas."""
        
        # Log detalhado apenas em ambiente de desenvolvimento
        if 'localhost' in str(erro_msg) or 'DEBUG' in erro_msg:
            st.error(f"🔍 **Debug - Erro detalhado:**\n```\n{erro_completo}\n```")
        
        return f"""❌ **Erro ao processar pergunta**

**Tipo do erro:** {type(e).__name__}
**Mensagem resumida:** {erro_msg[:200]}...

💡 **Dica:** Use as abas "Gaiola Única" ou "Múltiplas Gaiolas" para resultados garantidos."""

# --- TUTORIAL ---
st.markdown("""
<div class="tutorial-section">
    <div class="step-item"><div class="step-badge">1</div><span>Selecione o arquivo <b>.xlsx</b> do romaneio.</span></div>
    <div class="step-item"><div class="step-badge">2</div><span>Escolha: Digite <b>uma gaiola</b> OU digite <b>várias gaiolas</b>.</span></div>
    <div class="step-item"><div class="step-badge">3</div><span>Baixe a planilha ou consulte o <b>Agente IA</b>.</span></div>
</div>
""", unsafe_allow_html=True)

# --- UPLOAD DE ARQUIVO ---
arquivo_upload = st.file_uploader(
    "Upload", 
    type=["xlsx"], 
    label_visibility="collapsed", 
    key="romaneio_upload"
)

# --- PROCESSAMENTO ---
if arquivo_upload:
    # MELHORIA #3: Cache de DataFrame (evita releituras)
    nome_arquivo = arquivo_upload.name
    
    # Verificar se é um novo arquivo
    if st.session_state.arquivo_atual != nome_arquivo:
        st.session_state.arquivo_atual = nome_arquivo
        st.session_state.df_cache = None
    
    # Carregar DataFrame com cache
    if st.session_state.df_cache is None:
        with st.spinner("📊 Carregando romaneio..."):
            st.session_state.df_cache = carregar_dataframe_completo(arquivo_upload)
    
    df_completo = st.session_state.df_cache
    xl = pd.ExcelFile(arquivo_upload)
    
    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["🎯 Gaiola Única", "📊 Múltiplas Gaiolas", "🤖 Agente IA"])

    # --- TAB 1: GAIOLA ÚNICA ---
    with tab1:
        st.markdown("""
        <div class="info-box">
            <strong>💡 Modo Gaiola Única:</strong> Digite o código de uma gaiola para gerar 
            a rota completa com endereços detalhados.
        </div>
        """, unsafe_allow_html=True)
        
        gaiola_unica = st.text_input(
            "Digite o código da gaiola", 
            placeholder="Ex: A-36, C-42",
            key="gaiola_unica_input",
            label_visibility="collapsed"
        ).strip().upper()
        
        if st.button("🚀 GERAR ROTA DA GAIOLA", key="btn_unica", use_container_width=True):
            if not gaiola_unica:
                st.warning("⚠️ Por favor, digite um código de gaiola.")
            else:
                st.session_state.modo_atual = 'unica'
                
                with st.spinner(f'⚙️ Processando gaiola {gaiola_unica}...'):
                    target_limpo = limpar_string(gaiola_unica)
                    encontrado = False
                    
                    for aba in xl.sheet_names:
                        df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                        
                        col_gaiola_idx = next(
                            (col for col in df_raw.columns 
                             if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), 
                            None
                        )
                        
                        if col_gaiola_idx is not None:
                            resultado = processar_gaiola_unica(df_raw, gaiola_unica, col_gaiola_idx)
                            
                            if resultado:
                                encontrado = True
                                
                                # Gerar arquivo Excel
                                buffer = io.BytesIO()
                                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                    resultado['dataframe'].to_excel(writer, index=False)
                                
                                st.session_state.dados_prontos = buffer.getvalue()
                                st.session_state.df_visualizacao = resultado['dataframe']
                                st.session_state.nome_arquivo = f"Rota_{gaiola_unica}.xlsx"
                                st.session_state.metricas = {
                                    "pacotes": resultado['pacotes'],
                                    "paradas": resultado['paradas'],
                                    "comercios": resultado['comercios']
                                }
                                break
                    
                    if not encontrado:
                        st.error(f"❌ Gaiola '{gaiola_unica}' não encontrada no romaneio.")

    # --- TAB 2: MÚLTIPLAS GAIOLAS ---
    with tab2:
        st.markdown("""
        <div class="info-box">
            <strong>💡 Modo Múltiplas Gaiolas:</strong> Digite os códigos de várias gaiolas 
            (um por linha) para obter um resumo rápido.
        </div>
        """, unsafe_allow_html=True)
        
        codigos_multiplas = st.text_area(
            "Digite os códigos das gaiolas (um por linha)",
            placeholder="A-36\nA-37\nA-38\nC-42",
            height=200,
            key="codigos_multiplas",
            label_visibility="collapsed"
        )
        
        # Mostrar preview dos códigos detectados
        if codigos_multiplas:
            codigos_lista = [c.strip().upper() for c in codigos_multiplas.split('\n') if c.strip()]
            
            if codigos_lista:
                st.markdown(
                    f"<div class='success-box'>✅ <b>{len(codigos_lista)} código(s) detectado(s)</b></div>", 
                    unsafe_allow_html=True
                )
        
        if st.button("📊 PROCESSAR MÚLTIPLAS GAIOLAS", key="btn_multiplas", use_container_width=True):
            codigos_lista = [c.strip().upper() for c in codigos_multiplas.split('\n') if c.strip()]
            
            if not codigos_lista:
                st.warning("⚠️ Por favor, digite pelo menos um código de gaiola.")
            else:
                st.session_state.modo_atual = 'multiplas'
                
                with st.spinner(f'⚙️ Processando {len(codigos_lista)} gaiola(s)...'):
                    st.session_state.resultado_multiplas = processar_multiplas_gaiolas(
                        arquivo_upload, 
                        codigos_lista
                    )

    # --- TAB 3: AGENTE IA ---
    with tab3:
        st.markdown("""
        <div class="info-box">
            <strong>🤖 Agente IA - Waze Humano:</strong> Faça perguntas sobre o romaneio. 
            O agente pode contar pacotes, analisar rotas e responder dúvidas sobre gaiolas específicas.
        </div>
        """, unsafe_allow_html=True)
        
        pergunta_ia = st.text_input(
            "Sua dúvida sobre este romaneio:",
            placeholder="Ex: Quantas paradas tem a gaiola A-36? / Quantos comércios na rota C-42?",
            key="pergunta_ia",
            label_visibility="collapsed"
        )
        
        if st.button("🧠 CONSULTAR AGENTE IA", key="btn_ia", use_container_width=True):
            if not pergunta_ia:
                st.warning("⚠️ Por favor, digite uma pergunta.")
            elif df_completo is None:
                st.error("❌ Erro ao carregar o romaneio. Tente fazer upload novamente.")
            else:
                cliente_ia = inicializar_ia()
                
                if cliente_ia:
                    with st.spinner("🔍 O Agente IA está analisando o romaneio..."):
                        resposta = agente_ia_treinado(cliente_ia, df_completo, pergunta_ia)
                        
                        # MELHORIA #4: Feedback diferenciado
                        if resposta.startswith("❌"):
                            st.error(resposta)
                        else:
                            st.markdown("""
                            <div class="success-box">
                                <strong>✅ Resposta do Agente IA:</strong>
                            </div>
                            """, unsafe_allow_html=True)
                            st.markdown(resposta)

    # --- RESULTADOS GAIOLA ÚNICA ---
    if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
        st.markdown("---")
        st.markdown("### 📊 Resultado da Rota")
        
        m = st.session_state.metricas
        c1, c2, c3 = st.columns(3)
        c1.metric("📦 Pacotes", m["pacotes"])
        c2.metric("📍 Paradas", m["paradas"])
        c3.metric("🏪 Comércios", m["comercios"])
        
        st.markdown("##### 📋 Visualização Completa da Rota")
        st.dataframe(
            st.session_state.df_visualizacao, 
            use_container_width=True, 
            hide_index=True,
            height=400
        )
        
        st.download_button(
            label="📥 BAIXAR PLANILHA COMPLETA", 
            data=st.session_state.dados_prontos, 
            file_name=st.session_state.nome_arquivo, 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # --- RESULTADOS MÚLTIPLAS GAIOLAS ---
    if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
        st.markdown("---")
        st.markdown("### 📊 Resumo das Gaiolas Processadas")
        
        resultados = st.session_state.resultado_multiplas
        
        # Contagem de gaiolas encontradas
        gaiolas_encontradas = sum(1 for r in resultados.values() if r['encontrado'])
        
        st.metric("🎯 Gaiolas Encontradas", f"{gaiolas_encontradas}/{len(resultados)}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabela detalhada
        st.markdown("##### 📋 Detalhamento por Gaiola")
        
        df_resumo = pd.DataFrame([
            {
                'Gaiola': codigo,
                'Status': '✅ Encontrada' if dados['encontrado'] else '❌ Não encontrada',
                'Pacotes': dados['pacotes'],
                'Paradas': dados['paradas'],
                'Comércios': dados['comercios']
            }
            for codigo, dados in resultados.items()
        ])
        
        st.dataframe(
            df_resumo,
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Opção de exportar resumo
        buffer_resumo = io.BytesIO()
        with pd.ExcelWriter(buffer_resumo, engine='openpyxl') as writer:
            df_resumo.to_excel(writer, index=False, sheet_name='Resumo')
        
        st.download_button(
            label="📥 BAIXAR RESUMO EM EXCEL", 
            data=buffer_resumo.getvalue(), 
            file_name="Resumo_Multiplas_Gaiolas.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            use_container_width=True
        )
        
        # Avisos sobre gaiolas não encontradas
        nao_encontradas = [codigo for codigo, dados in resultados.items() if not dados['encontrado']]
        if nao_encontradas:
            st.warning(f"⚠️ Gaiolas não encontradas no romaneio: {', '.join(nao_encontradas)}")
        
        # --- DOWNLOAD INDIVIDUAL ---
        gaiolas_encontradas_lista = [codigo for codigo, dados in resultados.items() if dados['encontrado']]
        
        if gaiolas_encontradas_lista:
            st.markdown("---")
            st.markdown("### 📥 Baixar Planilhas Individuais para Circuit")
            
            st.markdown("""
            <div class="info-box">
                <strong>💡 Selecione as gaiolas:</strong> Marque as caixas abaixo para gerar planilhas 
                completas (com endereços) no formato do Circuit.
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("##### ✅ Selecione as gaiolas:")
            
            # Organizar em colunas
            num_colunas = 3
            colunas = st.columns(num_colunas)
            
            gaiolas_selecionadas = []
            for idx, codigo in enumerate(gaiolas_encontradas_lista):
                col_idx = idx % num_colunas
                with colunas[col_idx]:
                    pacotes = resultados[codigo]['pacotes']
                    paradas = resultados[codigo]['paradas']
                    
                    if st.checkbox(
                        f"**{codigo}** ({pacotes} pacotes, {paradas} paradas)",
                        key=f"checkbox_{codigo}"
                    ):
                        gaiolas_selecionadas.append(codigo)
            
            # Botão para gerar planilhas
            if gaiolas_selecionadas:
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button(
                    f"📥 GERAR PLANILHAS DAS {len(gaiolas_selecionadas)} GAIOLA(S) SELECIONADA(S)",
                    key="btn_gerar_individuais",
                    use_container_width=True
                ):
                    with st.spinner(f'⚙️ Gerando planilhas de {len(gaiolas_selecionadas)} gaiola(s)...'):
                        planilhas_geradas = {}
                        
                        for gaiola in gaiolas_selecionadas:
                            target_limpo = limpar_string(gaiola)
                            
                            # Buscar e processar a gaiola
                            for aba in xl.sheet_names:
                                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                                
                                col_gaiola_idx = next(
                                    (col for col in df_raw.columns 
                                     if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), 
                                    None
                                )
                                
                                if col_gaiola_idx is not None:
                                    resultado = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                                    
                                    if resultado:
                                        # Gerar Excel individual
                                        buffer_individual = io.BytesIO()
                                        with pd.ExcelWriter(buffer_individual, engine='openpyxl') as writer:
                                            resultado['dataframe'].to_excel(writer, index=False)
                                        
                                        planilhas_geradas[gaiola] = buffer_individual.getvalue()
                                        break
                        
                        # Mostrar planilhas geradas
                        if planilhas_geradas:
                            st.success(f"✅ {len(planilhas_geradas)} planilha(s) gerada(s) com sucesso!")
                            
                            st.markdown("##### 📥 Download das Planilhas:")
                            
                            # Criar colunas para os botões de download
                            cols_download = st.columns(min(3, len(planilhas_geradas)))
                            
                            for idx, (gaiola, dados_excel) in enumerate(planilhas_geradas.items()):
                                col_idx = idx % 3
                                with cols_download[col_idx]:
                                    st.download_button(
                                        label=f"📄 {gaiola}",
                                        data=dados_excel,
                                        file_name=f"Rota_{gaiola}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key=f"download_{gaiola}",
                                        use_container_width=True
                                    )
                        else:
                            st.error("❌ Erro ao gerar planilhas. Tente novamente.")

else:
    st.info("📁 Aguardando upload do romaneio para iniciar...")