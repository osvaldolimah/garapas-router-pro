import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional
from google import genai
from google.genai.types import HttpOptions

# --- CONFIGURAÇÃO DA PÁGINA (MARCO ZERO) ---
st.set_page_config(
    page_title="Filtro de Rotas e Paradas", 
    page_icon="🚚", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CONSTANTES (MARCO ZERO) ---
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

# --- SISTEMA DE DESIGN (MARCO ZERO + MOBILE FORCE v3.15) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 20px 10px; background-color: white; border-bottom: 4px solid var(--shopee-orange); margin-bottom: 20px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .main-title { 
        color: var(--shopee-orange) !important; 
        font-size: clamp(1.0rem, 4vw, 1.4rem) !important; 
        font-weight: 800 !important; 
        margin: 0 !important;
        line-height: 1.2 !important;
        display: block !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: white; padding: 10px; border-radius: 15px; }
    div.stButton > button { background-color: var(--shopee-orange) !important; color: white !important; font-size: 18px !important; font-weight: 700 !important; border-radius: 12px !important; width: 100% !important; height: 60px !important; border: none !important; }
    .success-box { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0; color: #065F46; }
    .info-box { background: #EFF6FF; border-left: 4px solid #2563EB; padding: 12px 16px; border-radius: 8px; margin: 10px 0; font-size: 0.9rem; color: #1E40AF; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Filtro de Rotas e Paradas</h1></div>', unsafe_allow_html=True)

# --- SESSÃO ---
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'resumo_ia' not in st.session_state: st.session_state.resumo_ia = None
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visual_tab1' not in st.session_state: st.session_state.df_visual_tab1 = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None

# --- FUNÇÕES ---
@st.cache_data
def remover_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').upper()

@st.cache_data
def limpar_string(s: str) -> str:
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo: str) -> str:
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def identificar_comercio(endereco: str) -> str:
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
    try:
        target_limpo = limpar_string(gaiola_alvo)
        df_filt = df_raw[df_raw[col_gaiola_idx].astype(str).apply(limpar_string) == target_limpo].copy()
        if df_filt.empty: return None
        col_end_idx = None
        for r in range(min(15, len(df_raw))):
            linha = [str(x).upper() for x in df_raw.iloc[r].values]
            for i, val in enumerate(linha):
                if any(t in val for t in ['ENDERE', 'LOGRA', 'RUA', 'ADDRESS']):
                    col_end_idx = i; break
        if col_end_idx is None: col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops).astype(str)
        saida['Gaiola'] = df_filt[col_gaiola_idx]
        saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str) + ", Fortaleza - CE"
        return {'dataframe': saida, 'pacotes': len(saida), 'paradas': len(mapa_stops), 'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])}
    except: return None

# --- IA (v3.24 - CORRIGIDO) ---
def inicializar_ia():
    """
    CORREÇÃO v3.24: Especifica api_version='v1alpha' para usar gemini-1.5-flash
    Alternativa: usar gemini-2.0-flash-exp que funciona em v1beta
    """
    try:
        return genai.Client(
            api_key=st.secrets["GEMINI_API_KEY"],
            http_options=HttpOptions(api_version='v1alpha')  # CORREÇÃO: v1alpha suporta gemini-1.5-flash
        )
    except KeyError:
        st.error("❌ Configure GEMINI_API_KEY em .streamlit/secrets.toml")
        return None
    except Exception as e:
        st.error(f"❌ Erro ao inicializar IA: {e}")
        return None

def gerar_resumo_estatico_ia(df):
    try:
        col_g = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA', 'CANISTER'])), 0)
        col_e = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['ADDRESS', 'ENDERE', 'RUA'])), 0)
        temp = df.copy()
        temp['B_STOP'] = temp.iloc[:, col_e].apply(extrair_base_endereco)
        resumo = temp.groupby(temp.columns[col_g]).agg(Pacotes=('B_STOP', 'count'), Paradas=('B_STOP', 'nunique')).reset_index()
        texto = "TABELA GERAL:\n"
        for _, row in resumo.iterrows():
            texto += f"- Gaiola {row[0]}: {row['Pacotes']} pacotes, {row['Paradas']} paradas.\n"
        return texto
    except: return "Erro no resumo."

def agente_ia_treinado(client, df, pergunta):
    """
    CORREÇÃO v3.24: Mantém gemini-1.5-flash com v1alpha configurado
    """
    try:
        if st.session_state.resumo_ia is None: 
            st.session_state.resumo_ia = gerar_resumo_estatico_ia(df)
        
        contexto_b = ""
        match = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())
        
        if match:
            g_alvo = limpar_string(match.group(1))
            col_g = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['GAIOLA', 'LETRA'])), 0)
            col_b = next((i for i, c in enumerate(df.columns) if any(t in str(c).upper() for t in ['BAIRRO', 'NEIGHBORHOOD'])), None)
            df_target = df[df.iloc[:, col_g].astype(str).apply(limpar_string) == g_alvo]
            
            if not df_target.empty and col_b is not None:
                bairros = df_target.iloc[:, col_b].dropna().astype(str).apply(remover_acentos).unique().tolist()
                contexto_b = f"BAIRROS DA {g_alvo}: {', '.join(bairros)}."

        prompt = f"Você é o Waze Humano. Dados:\n{st.session_state.resumo_ia}\n{contexto_b}\nResponda logisticamente: {pergunta}"
        
        # CORREÇÃO: gemini-1.5-flash funciona com v1alpha
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt
        )
        
        return response.text
    
    except Exception as e:
        # Tratamento de erro melhorado
        erro_msg = str(e)
        if "404" in erro_msg or "NOT_FOUND" in erro_msg:
            return "⚠️ Erro de conexão com a IA. Verifique se a API key está configurada corretamente."
        else:
            return f"⚠️ Erro: {erro_msg}"

# --- INTERFACE ---
arquivo = st.file_uploader("Upload", type=["xlsx"], label_visibility="collapsed")

if arquivo:
    if st.session_state.df_cache is None:
        with st.spinner("📊 Carregando romaneio..."):
            st.session_state.df_cache = pd.read_excel(arquivo)
            st.session_state.resumo_ia = gerar_resumo_estatico_ia(st.session_state.df_cache)
    
    df_completo = st.session_state.df_cache
    xl = pd.ExcelFile(arquivo)
    t1, t2, t3 = st.tabs(["🎯 Única", "📊 Lote", "🤖 IA"])

    with t1:
        g = st.text_input("Gaiola", key="g_u").strip().upper()
        if st.button("🚀 GERAR", key="b_u", use_container_width=True):
            if not g:
                st.warning("⚠️ Digite um código de gaiola.")
            else:
                st.session_state.modo_atual = 'unica'
                encontrado = False
                
                with st.spinner(f"⚙️ Processando gaiola {g}..."):
                    for aba in xl.sheet_names:
                        df_r = pd.read_excel(xl, sheet_name=aba, header=None)
                        idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(limpar_string(g)).any()), None)
                        
                        if idx is not None:
                            res = processar_gaiola_unica(df_r, g, idx)
                            if res:
                                buf = io.BytesIO()
                                with pd.ExcelWriter(buf, engine='openpyxl') as w: 
                                    res['dataframe'].to_excel(w, index=False)
                                
                                st.session_state.dados_prontos = buf.getvalue()
                                st.session_state.df_visual_tab1 = res['dataframe']
                                st.session_state.metricas_tab1 = res
                                encontrado = True
                                break
                
                if not encontrado:
                    st.error(f"❌ Gaiola '{g}' não encontrada.")
        
        if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
            st.markdown("---")
            m = st.session_state.metricas_tab1
            c = st.columns(3)
            c[0].metric("📦 Pacotes", m["pacotes"])
            c[1].metric("📍 Paradas", m["paradas"])
            c[2].metric("🏪 Comércios", m["comercios"])
            st.dataframe(st.session_state.df_visual_tab1, use_container_width=True, hide_index=True, height=400)
            st.download_button("📥 BAIXAR PLANILHA", st.session_state.dados_prontos, f"Rota_{g}.xlsx", use_container_width=True)

    with t2:
        lista = st.text_area("Gaiolas (uma por linha)", key="l_m", height=150, placeholder="A-36\nA-37\nA-38")
        
        if st.button("📊 PROCESSAR", key="b_m", use_container_width=True):
            gaiolas = [c.strip().upper() for c in lista.split('\n') if c.strip()]
            
            if not gaiolas:
                st.warning("⚠️ Digite pelo menos uma gaiola.")
            else:
                st.session_state.modo_atual = 'multiplas'
                
                with st.spinner(f"⚙️ Processando {len(gaiolas)} gaiola(s)..."):
                    res_l = {}
                    
                    for gn in gaiolas:
                        target = limpar_string(gn)
                        enc = False
                        
                        for aba in xl.sheet_names:
                            df_r = pd.read_excel(xl, sheet_name=aba, header=None)
                            idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target).any()), None)
                            
                            if idx is not None:
                                r = processar_gaiola_unica(df_r, gn, idx)
                                if r:
                                    res_l[gn] = {
                                        'pacotes': r['pacotes'], 
                                        'paradas': r['paradas'], 
                                        'encontrado': True
                                    }
                                    enc = True
                                    break
                        
                        if not enc:
                            res_l[gn] = {'pacotes': 0, 'paradas': 0, 'encontrado': False}
                    
                    st.session_state.resultado_multiplas = res_l

        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            st.markdown("---")
            res = st.session_state.resultado_multiplas
            
            # Contagem
            encontradas = sum(1 for v in res.values() if v['encontrado'])
            st.metric("🎯 Gaiolas Encontradas", f"{encontradas}/{len(res)}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### 📋 Resumo")
            
            df_resumo = pd.DataFrame([
                {
                    'Gaiola': k, 
                    'Status': '✅' if v['encontrado'] else '❌', 
                    'Pacotes': v['pacotes'], 
                    'Paradas': v['paradas']
                } 
                for k, v in res.items()
            ])
            
            st.dataframe(df_resumo, use_container_width=True, hide_index=True, height=400)
            
            # Download resumo
            buffer_resumo = io.BytesIO()
            with pd.ExcelWriter(buffer_resumo, engine='openpyxl') as writer:
                df_resumo.to_excel(writer, index=False, sheet_name='Resumo')
            
            st.download_button(
                "📥 BAIXAR RESUMO", 
                buffer_resumo.getvalue(), 
                "Resumo_Multiplas.xlsx",
                use_container_width=True
            )
            
            # Planilhas individuais
            g_enc = [k for k, v in res.items() if v['encontrado']]
            
            if g_enc:
                st.markdown("---")
                st.markdown("##### 📥 Baixar Planilhas Individuais")
                st.markdown('<div class="info-box">Selecione as gaiolas para gerar planilhas completas.</div>', unsafe_allow_html=True)
                
                sel = []
                cols = st.columns(3)
                
                for i, gn in enumerate(g_enc):
                    with cols[i % 3]:
                        paks = res[gn]['pacotes']
                        stops = res[gn]['paradas']
                        if st.checkbox(f"**{gn}** ({paks}p, {stops}s)", key=f"c_{gn}"): 
                            sel.append(gn)
                
                if sel and st.button("📥 PREPARAR SELECIONADAS", key="b_p", use_container_width=True):
                    with st.spinner(f"⚙️ Gerando {len(sel)} planilha(s)..."):
                        st.session_state.planilhas_sessao = {}
                        
                        for s in sel:
                            for aba in xl.sheet_names:
                                df_r = pd.read_excel(xl, sheet_name=aba, header=None)
                                idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(limpar_string(s)).any()), None)
                                
                                if idx is not None:
                                    r = processar_gaiola_unica(df_r, s, idx)
                                    if r:
                                        b = io.BytesIO()
                                        with pd.ExcelWriter(b, engine='openpyxl') as w: 
                                            r['dataframe'].to_excel(w, index=False)
                                        st.session_state.planilhas_sessao[s] = b.getvalue()
                                        break
                        
                        st.success(f"✅ {len(st.session_state.planilhas_sessao)} planilha(s) gerada(s)!")
                
                if st.session_state.planilhas_sessao:
                    st.markdown("##### 📄 Downloads:")
                    cols_d = st.columns(3)
                    
                    for i, (n, d) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_d[i % 3]: 
                            st.download_button(
                                f"📄 {n}", 
                                d, 
                                f"Rota_{n}.xlsx", 
                                key=f"d_{n}", 
                                use_container_width=True
                            )

    with t3:
        st.markdown('<div class="info-box"><strong>🤖 Agente IA:</strong> Faça perguntas sobre o romaneio.</div>', unsafe_allow_html=True)
        
        p = st.text_input(
            "Sua dúvida:", 
            key="i_p",
            placeholder="Ex: Quantas paradas tem a gaiola A-36?"
        )
        
        if st.button("🧠 CONSULTAR AGENTE", use_container_width=True):
            if not p:
                st.warning("⚠️ Digite uma pergunta.")
            else:
                cli = inicializar_ia()
                
                if cli:
                    with st.spinner("🔍 Analisando romaneio..."):
                        resposta = agente_ia_treinado(cli, df_completo, p)
                        st.markdown(f'<div class="success-box"><strong>✅ Resposta:</strong><br>{resposta}</div>', unsafe_allow_html=True)
else:
    st.info("📁 Aguardando upload do romaneio...")