import pandas as pd
import unicodedata
import re

def limpar_string(s: str) -> str:
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo: str) -> str:
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

def identificar_comercio(endereco: str) -> str:
    TERMOS_COMERCIAIS = ['LOJA', 'MERCADO', 'MERCEARIA', 'FARMACIA']
    def remover_acentos(texto):
        return "".join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').upper()
    
    end_limpo = remover_acentos(endereco)
    for termo in TERMOS_COMERCIAIS:
        if termo in end_limpo:
            return "🏪 Comércio"
    return "🏠 Residencial"

# Simular o que a IA recebe
df = pd.read_excel('PM 31_01 ROMANEIO.xlsx', header=None)

pergunta = "Quantas paradas tem a gaiola b50?"
match_gaiola = re.search(r'([A-Z][- ]?\d+)', pergunta.upper())

if match_gaiola:
    g_alvo = limpar_string(match_gaiola.group(1))
    print(f"🔍 Detectado: {g_alvo}")
    
    for col in df.columns:
        df_target = df[df[col].astype(str).apply(limpar_string) == g_alvo]
        if not df_target.empty:
            print(f"\n✅ Encontrado na coluna {col}")
            print(f"📦 Pacotes: {len(df_target)}")
            
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
            
            print(f"🏠 Coluna de endereço: {col_end_idx}")
            
            if col_end_idx is None:
                col_end_idx = df_target.apply(lambda x: x.astype(str).map(len).max()).idxmax()
                print(f"🔄 Coluna detectada automaticamente: {col_end_idx}")
            
            # Calcular paradas
            df_target_copy = df_target.copy()
            df_target_copy['CHAVE_STOP'] = df_target_copy[col_end_idx].apply(extrair_base_endereco)
            
            paradas_unicas = df_target_copy['CHAVE_STOP'].unique()
            num_paradas = len(paradas_unicas)
            
            print(f"📍 PARADAS: {num_paradas}")
            
            # Tamanho do prompt
            amostra = df_target.head(50).to_string(max_rows=50)
            print(f"\n📏 Tamanho da amostra: {len(amostra)} caracteres")
            
            if len(amostra) > 10000:
                print("⚠️ ALERTA: Amostra muito grande! Pode causar erro na IA.")
            
            break
