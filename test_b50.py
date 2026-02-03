import pandas as pd
import unicodedata

def limpar_string(s: str) -> str:
    return "".join(filter(str.isalnum, str(s))).upper()

def extrair_base_endereco(endereco_completo: str) -> str:
    partes = str(endereco_completo).split(',')
    base = partes[0].strip() + " " + partes[1].strip() if len(partes) >= 2 else partes[0].strip()
    return limpar_string(base)

# Carregar planilha
df = pd.read_excel('PM 31_01 ROMANEIO.xlsx', header=None)

# Filtrar B-50
df_b50 = df[df[0].astype(str).apply(limpar_string) == limpar_string('B-50')].copy()

print(f"📦 Total de PACOTES na B-50: {len(df_b50)}")

# Coluna de endereço (coluna 3 baseado na análise anterior)
col_end = 3

# Aplicar extração de base
df_b50['CHAVE_STOP'] = df_b50[col_end].apply(extrair_base_endereco)

# Contar paradas únicas
paradas_unicas = df_b50['CHAVE_STOP'].unique()
print(f"📍 Total de PARADAS na B-50: {len(paradas_unicas)}")

print("\n🔍 Primeiras 15 paradas únicas:")
for i, parada in enumerate(paradas_unicas[:15], 1):
    # Encontrar endereço original
    endereco_original = df_b50[df_b50['CHAVE_STOP'] == parada].iloc[0][col_end]
    qtd = len(df_b50[df_b50['CHAVE_STOP'] == parada])
    print(f"{i}. {endereco_original} ({qtd} pacotes)")

print("\n📊 Distribuição de pacotes por parada:")
contagem = df_b50['CHAVE_STOP'].value_counts()
print(f"- Média de pacotes por parada: {contagem.mean():.1f}")
print(f"- Parada com mais pacotes: {contagem.max()} pacotes")
print(f"- Paradas com 1 pacote: {(contagem == 1).sum()}")
