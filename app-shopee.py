import streamlit as st
import pandas as pd
import io
import unicodedata
import re
from typing import List, Dict, Optional

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Waze Humano - Rotas Shopee", 
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
    'CARNES', 'PEIXARIA', 'FRUTARIA', 'HORTIFRUTI', 'FLORICULTURA', 'SABOR LEVINHO'
]
TERMOS_ANULADORES = ['FRENTE', 'LADO', 'PROXIMO', 'VIZINHO', 'DEFRONTE', 'ATRAS', 'DEPOIS', 'PERTO', 'VIZINHA']

# --- SISTEMA DE DESIGN (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    :root { --shopee-orange: #EE4D2D; --shopee-bg: #F6F6F6; }
    .stApp { background-color: var(--shopee-bg); font-family: 'Inter', sans-serif; }
    
    /* Header Estilizado */
    .header-container { 
        text-align: center; padding: 25px 10px; background-color: white; 
        border-bottom: 5px solid var(--shopee-orange); margin-bottom: 25px; 
        border-radius: 0 0 25px 25px; box-shadow: 0 4px 15px rgba(238, 77, 45, 0.15); 
    }
    .main-title { 
        color: var(--shopee-orange) !important; font-size: clamp(1.5rem, 5vw, 2.2rem) !important; 
        font-weight: 900 !important; margin: 0 !important; letter-spacing: -1px;
    }
    .sub-title { color: #555; font-size: 0.9rem; margin-top: 5px; font-weight: 500; }

    /* Botões */
    div.stButton > button { 
        background: linear-gradient(135deg, #EE4D2D 0%, #ff6b4f 100%) !important; 
        color: white !important; font-size: 18px !important; font-weight: 700 !important; 
        border-radius: 12px !important; border: none !important; height: 55px !important;
        box-shadow: 0 4px 6px rgba(238, 77, 45, 0.2); transition: all 0.3s ease;
    }
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(238, 77, 45, 0.3); }

    /* Cards de Info */
    .metric-card { background: white; padding: 15px; border-radius: 12px; border-left: 5px solid var(--shopee-orange); box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-container"><h1 class="main-title">Waze Humano 🚚</h1><div class="sub-title">Estrategista das Rotas Shopee</div></div>', unsafe_allow_html=True)

# --- INICIALIZAÇÃO DA SESSÃO ---
if 'dados_prontos' not in st.session_state: st.session_state.dados_prontos = None
if 'df_visual_tab1' not in st.session_state: st.session_state.df_visual_tab1 = None
if 'df_mapa_tab1' not in st.session_state: st.session_state.df_mapa_tab1 = None # NOVO: Para o mapa
if 'modo_atual' not in st.session_state: st.session_state.modo_atual = 'unica'
if 'resultado_multiplas' not in st.session_state: st.session_state.resultado_multiplas = None
if 'df_cache' not in st.session_state: st.session_state.df_cache = None
if 'planilhas_sessao' not in st.session_state: st.session_state.planilhas_sessao = {}

# --- FUNÇÕES AUXILIARES ---
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
        
        # Filtra pela gaiola (usando conversão string segura)
        df_filt = df_raw[df_raw[col_gaiola_idx].astype(str).apply(limpar_string) == target_limpo].copy()
        if df_filt.empty: return None

        # Identifica colunas chaves dinamicamente
        col_end_idx = None
        col_lat_idx = None
        col_lon_idx = None
        
        # Varredura para encontrar colunas
        for r in range(min(5, len(df_raw))): # Olha as primeiras linhas
            linha = [str(x).upper() for x in df_raw.iloc[r].values]
            for i, val in enumerate(linha):
                if not col_end_idx and any(t in val for t in ['ENDERE', 'LOGRA', 'RUA', 'ADDRESS', 'DIRECCION']):
                    col_end_idx = i
                if not col_lat_idx and any(t in val for t in ['LATIT', 'LAT']):
                    col_lat_idx = i
                if not col_lon_idx and any(t in val for t in ['LONGIT', 'LON', 'LNG']):
                    col_lon_idx = i
        
        # Fallback se não achar cabeçalho
        if col_end_idx is None:
            # Pega a coluna com maior comprimento médio de string
            col_end_idx = df_filt.apply(lambda x: x.astype(str).map(len).max()).idxmax()

        # Processamento
        df_filt['CHAVE_STOP'] = df_filt[col_end_idx].apply(extrair_base_endereco)
        
        # Mapa de paradas
        mapa_stops = {end: i + 1 for i, end in enumerate(df_filt['CHAVE_STOP'].unique())}
        
        saida = pd.DataFrame()
        saida['Parada'] = df_filt['CHAVE_STOP'].map(mapa_stops) # Mantém como int para ordenar
        saida['Gaiola'] = df_filt[col_gaiola_idx]
        saida['Tipo'] = df_filt[col_end_idx].apply(identificar_comercio)
        saida['Endereco_Completo'] = df_filt[col_end_idx].astype(str)
        
        # Tenta extrair Lat/Lon para o mapa
        df_geo = None
        if col_lat_idx is not None and col_lon_idx is not None:
            try:
                df_filt['lat'] = pd.to_numeric(df_filt[col_lat_idx], errors='coerce')
                df_filt['lon'] = pd.to_numeric(df_filt[col_lon_idx], errors='coerce')
                df_geo = df_filt[['lat', 'lon']].dropna()
            except:
                pass

        # Ordenar e formatar saída
        saida = saida.sort_values('Parada')
        
        return {
            'dataframe': saida, 
            'df_geo': df_geo,
            'pacotes': len(saida), 
            'paradas': len(mapa_stops), 
            'comercios': len(saida[saida['Tipo'] == "🏪 Comércio"])
        }
    except Exception as e:
        st.error(f"⚠️ Erro ao processar gaiola {gaiola_alvo}: {str(e)}")
        return None

def processar_multiplas_gaiolas(arquivo_excel, codigos_gaiola: List[str]) -> Dict[str, Dict]:
    resultados = {}
    try:
        xl = pd.ExcelFile(arquivo_excel)
        for gaiola in codigos_gaiola:
            target_limpo = limpar_string(gaiola); encontrado = False
            for aba in xl.sheet_names:
                df_raw = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                col_gaiola_idx = next((col for col in df_raw.columns if df_raw[col].astype(str).apply(limpar_string).eq(target_limpo).any()), None)
                if col_gaiola_idx is not None:
                    res = processar_gaiola_unica(df_raw, gaiola, col_gaiola_idx)
                    if res: resultados[gaiola] = {'pacotes': res['pacotes'], 'paradas': res['paradas'], 'comercios': res['comercios'], 'encontrado': True}; encontrado = True; break
            if not encontrado: resultados[gaiola] = {'pacotes': 0, 'paradas': 0, 'comercios': 0, 'encontrado': False}
        return resultados
    except Exception as e:
        st.error(f"⚠️ Erro ao processar múltiplas gaiolas: {str(e)}")
        return {}

# --- LÓGICA CIRCUIT PRO (MANTIDA) ---
def limpar_e_normalizar_endereco(endereco):
    if not isinstance(endereco, str): return str(endereco)
    texto = remover_acentos(endereco)
    texto = re.sub(r'[^\w\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def extrair_numero_endereco(endereco):
    if not isinstance(endereco, str): return "SN"
    partes = endereco.split(',')
    if len(partes) > 1:
        match = re.search(r'(\d+)', partes[-1])
        if match: return match.group(1)
        match = re.search(r'(\d+)', partes[-2])
        if match: return match.group(1)
    todos_numeros = re.findall(r'(\d+)', endereco)
    if todos_numeros: return todos_numeros[-1]
    return "SN"

def escolher_melhor_endereco(serie_enderecos):
    candidatos = [str(x).strip() for x in serie_enderecos if pd.notna(x) and str(x).strip() != '']
    if not candidatos: return ""
    return max(candidatos, key=len)

def gerar_planilha_otimizada_circuit_pro(df):
    col_end = next((c for c in df.columns if any(t in str(c).upper() for t in ['ADDRESS', 'ENDERE', 'DESTINATION'])), None)
    col_seq = next((c for c in df.columns if 'SEQUENCE' in str(c).upper()), None)
    col_lat = next((c for c in df.columns if any(t in str(c).upper() for t in ['LATITUDE', 'LAT'])), None)
    col_lon = next((c for c in df.columns if any(t in str(c).upper() for t in ['LONGITUDE', 'LON', 'LNG'])), None)

    if not col_end or not col_seq: return None
    
    df_temp = df.copy()

    def criar_chave_unica(row):
        num = extrair_numero_endereco(row[col_end])
        geo_key = ""
        if col_lat and col_lon:
            try:
                lat, lon = float(row[col_lat]), float(row[col_lon])
                if pd.notna(lat) and pd.notna(lon) and abs(lat) > 0.00001:
                    geo_key = f"GEO_{round(lat, 5)}_{round(lon, 5)}"
            except: pass 

        if geo_key: return f"{geo_key}_NUM_{num}"
        else:
            txt_key = limpar_e_normalizar_endereco(row[col_end])
            return f"TXT_{txt_key}_NUM_{num}"

    df_temp['UID_AGRUPAMENTO'] = df_temp.apply(criar_chave_unica, axis=1)
    agg_dict = {col: 'first' for col in df_temp.columns if col not in ['UID_AGRUPAMENTO', col_seq, col_end]}
    agg_dict[col_end] = escolher_melhor_endereco 
    
    def unir_seqs(x): 
        vals = sorted(list(set(x.astype(str))))
        try: vals.sort(key=int)
        except: pass
        return ', '.join(vals)
    
    df_final = df_temp.groupby('UID_AGRUPAMENTO').agg({**agg_dict, col_seq: unir_seqs}).reset_index()
    
    try:
        df_final['SortKey'] = df_final[col_seq].apply(lambda x: int(str(x).split(',')[0]))
        return df_final.sort_values('SortKey').drop(columns=['UID_AGRUPAMENTO', 'SortKey'])
    except:
        return df_final.drop(columns=['UID_AGRUPAMENTO'])

# --- INTERFACE TABS ---
tab1, tab2, tab3 = st.tabs(["🎯 Gaiola Única", "📊 Processar Lote", "⚡ Otimizar Circuit"])

with tab1:
    st.markdown("##### 📥 Análise Detalhada de Rota")
    up_padrao = st.file_uploader("Upload Romaneio (Excel)", type=["xlsx"], key="up_padrao", label_visibility="collapsed")
    
    if up_padrao:
        if st.session_state.df_cache is None:
            with st.spinner("📦 Lendo arquivo..."):
                st.session_state.df_cache = pd.read_excel(up_padrao)
        
        xl = pd.ExcelFile(up_padrao)
        
        col_in, col_btn = st.columns([3, 1])
        with col_in:
            g_unica = st.text_input("Digite o Código da Gaiola", placeholder="Ex: B-50", key="gui_tab1").strip().upper()
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True) # Espaçamento
            btn_processar = st.button("🔍 RASTREAR", key="btn_u_tab1", use_container_width=True)

        if btn_processar:
            if not g_unica:
                st.warning("⚠️ Digite o código da gaiola.")
            else:
                st.session_state.modo_atual = 'unica'
                target = limpar_string(g_unica); enc = False
                
                with st.spinner(f"⚙️ Mapeando gaiola {g_unica}..."):
                    for aba in xl.sheet_names:
                        df_r = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                        # Busca inteligente da coluna da gaiola
                        idx = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target).any()), None)
                        
                        if idx is not None:
                            res = processar_gaiola_unica(df_r, g_unica, idx)
                            if res:
                                enc = True
                                buf = io.BytesIO()
                                with pd.ExcelWriter(buf, engine='openpyxl') as w: res['dataframe'].to_excel(w, index=False)
                                st.session_state.dados_prontos = buf.getvalue()
                                st.session_state.df_visual_tab1 = res['dataframe']
                                st.session_state.df_mapa_tab1 = res['df_geo']
                                st.session_state.metricas_tab1 = res
                                break
                
                if not enc: st.error(f"❌ Gaiola '{g_unica}' não encontrada no arquivo.")
        
        # --- EXIBIÇÃO DE RESULTADOS DA ABA 1 ---
        if st.session_state.modo_atual == 'unica' and st.session_state.dados_prontos:
            m = st.session_state.metricas_tab1
            
            # 1. Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("📦 Pacotes", m["pacotes"])
            c2.metric("📍 Paradas Reais", m["paradas"])
            c3.metric("🏪 Comércios Identificados", m["comercios"], delta_color="inverse")
            
            st.markdown("---")

            # 2. Mapa (Se houver coordenadas)
            if st.session_state.df_mapa_tab1 is not None and not st.session_state.df_mapa_tab1.empty:
                st.markdown("##### 🗺️ Mapa de Calor da Rota")
                st.map(st.session_state.df_mapa_tab1, size=20, color='#EE4D2D')
            else:
                st.info("ℹ️ Coordenadas GPS não encontradas no arquivo para plotar o mapa.")

            # 3. Lista Rápida (Expander)
            with st.expander("📱 Lista Rápida (Copiar para WhatsApp)"):
                df_txt = st.session_state.df_visual_tab1
                texto_zap = f"*ROTA {g_unica} - {m['pacotes']} Pcts / {m['paradas']} Stops*\n\n"
                for idx, row in df_txt.iterrows():
                    icone = "🏪" if row['Tipo'] == "🏪 Comércio" else "🏠"
                    texto_zap += f"{int(row['Parada'])}. {icone} {row['Endereco_Completo']}\n"
                st.text_area("Copie abaixo:", value=texto_zap, height=200)

            # 4. Tabela Visual
            st.markdown("##### 📋 Detalhes da Carga")
            st.dataframe(
                st.session_state.df_visual_tab1,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Parada": st.column_config.NumberColumn("Seq", format="%d"),
                    "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                    "Endereco_Completo": st.column_config.TextColumn("Endereço", width="large"),
                    "Gaiola": st.column_config.TextColumn("Gaiola", width="small"),
                }
            )
            
            # 5. Download
            st.download_button(
                label="📥 BAIXAR PLANILHA FORMATADA",
                data=st.session_state.dados_prontos,
                file_name=f"Rota_{g_unica}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

with tab2:
    st.markdown("##### 🏭 Processamento em Lote")
    if st.session_state.df_cache is not None and 'up_padrao' in locals() and up_padrao:
        xl = pd.ExcelFile(up_padrao)
        cod_m = st.text_area("Cole as gaiolas aqui (uma por linha):", placeholder="A-36\nB-50\nC-12", key="cm_tab2", height=150)
        
        if st.button("🚀 PROCESSAR LISTA", key="btn_m_tab2", use_container_width=True):
            lista = [c.strip().upper() for c in cod_m.split('\n') if c.strip()]
            if not lista:
                st.warning("⚠️ Lista vazia.")
            else:
                st.session_state.modo_atual = 'multiplas'
                with st.spinner(f"⚙️ Processando {len(lista)} gaiolas..."):
                    st.session_state.resultado_multiplas = processar_multiplas_gaiolas(up_padrao, lista)
        
        if st.session_state.modo_atual == 'multiplas' and st.session_state.resultado_multiplas:
            res = st.session_state.resultado_multiplas
            
            # Tabela de Resumo Bonita
            res_data = [{'Gaiola': k, 'Status': '✅ Achou' if v['encontrado'] else '❌ Não', 'Pacotes': v['pacotes'], 'Paradas': v['paradas'], 'Comércios': v['comercios']} for k, v in res.items()]
            st.dataframe(pd.DataFrame(res_data), use_container_width=True, hide_index=True)
            
            g_enc = [k for k, v in res.items() if v['encontrado']]
            
            if g_enc:
                st.markdown("##### 📥 Download Seletivo")
                selecionadas = []
                cols = st.columns(4)
                for i, g in enumerate(g_enc):
                    with cols[i % 4]:
                        if st.checkbox(f"{g}", key=f"chk_m_{g}", value=True): selecionadas.append(g)
                
                if selecionadas and st.button("GERAR ARQUIVOS INDIVIDUAIS"):
                    st.session_state.planilhas_sessao = {}
                    bar = st.progress(0)
                    for i, s in enumerate(selecionadas):
                        target_l = limpar_string(s)
                        for aba in xl.sheet_names:
                            df_r = pd.read_excel(xl, sheet_name=aba, header=None, engine='openpyxl')
                            idx_g = next((c for c in df_r.columns if df_r[c].astype(str).apply(limpar_string).eq(target_l).any()), None)
                            if idx_g is not None:
                                r_ind = processar_gaiola_unica(df_r, s, idx_g)
                                if r_ind:
                                    b_ind = io.BytesIO()
                                    with pd.ExcelWriter(b_ind, engine='openpyxl') as w: r_ind['dataframe'].to_excel(w, index=False)
                                    st.session_state.planilhas_sessao[s] = b_ind.getvalue(); break
                        bar.progress((i + 1) / len(selecionadas))
                
                if st.session_state.planilhas_sessao:
                    st.success("✅ Arquivos prontos!")
                    cols_dl = st.columns(3)
                    for idx, (nome, data) in enumerate(st.session_state.planilhas_sessao.items()):
                        with cols_dl[idx % 3]:
                            st.download_button(label=f"📄 {nome}", data=data, file_name=f"Rota_{nome}.xlsx", key=f"dl_sessao_{nome}", use_container_width=True)
    else:
        st.info("ℹ️ Faça o upload do arquivo na aba 'Gaiola Única' primeiro.")

with tab3:
    st.markdown("##### ⚡ Otimizador Circuit Pro")
    st.markdown("""
    <div style="background-color: #e0f2fe; padding: 15px; border-radius: 10px; border-left: 5px solid #0284c7; color: #0c4a6e; font-size: 0.9rem;">
        <strong>Função Casadinha Inteligente:</strong><br>
        Agrupa pacotes entregues no mesmo local para economizar paradas no App Circuit.<br>
        Critério: <em>(Mesmo GPS + Mesmo Número)</em> OU <em>(Mesmo Endereço + Mesmo Número)</em>.
    </div>
    """, unsafe_allow_html=True)
    
    up_circuit = st.file_uploader("Upload Planilha Circuit", type=["xlsx"], key="up_circuit")
    
    if up_circuit:
        df_c = pd.read_excel(up_circuit)
        if st.button("🚀 OTIMIZAR AGORA", use_container_width=True):
            res_c = gerar_planilha_otimizada_circuit_pro(df_c)
            if res_c is not None:
                stops_antes = len(df_c)
                stops_depois = len(res_c)
                economia = stops_antes - stops_depois
                pct = int((economia / stops_antes) * 100)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Paradas Originais", stops_antes)
                c2.metric("Paradas Otimizadas", stops_depois)
                c3.metric("Economia", f"{economia} stops", f"-{pct}%", delta_color="normal")
                
                st.success(f"✅ Rota otimizada! Você economizou **{economia}** paradas virtuais.")
                
                buf_c = io.BytesIO()
                with pd.ExcelWriter(buf_c, engine='openpyxl') as w: res_c.to_excel(w, index=False)
                st.download_button("📥 BAIXAR ARQUIVO OTIMIZADO", buf_c.getvalue(), "Circuit_Otimizado.xlsx", use_container_width=True)
                
                with st.expander("Ver dados otimizados"):
                    st.dataframe(res_c, use_container_width=True)
            else:
                st.error("⚠️ Não encontrei as colunas necessárias (Address/Endereço e Sequence). Verifique o arquivo.")