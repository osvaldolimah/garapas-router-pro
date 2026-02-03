"""
Script para testar se a API Key do Gemini está funcionando
"""
import streamlit as st
from google import genai

print("=" * 60)
print("🔍 TESTE DA API KEY DO GEMINI")
print("=" * 60)

try:
    # Tentar ler a chave
    api_key = st.secrets["GEMINI_API_KEY"]
    print(f"\n✅ API Key encontrada")
    print(f"   Primeiros caracteres: {api_key[:15]}...")
    print(f"   Tamanho: {len(api_key)} caracteres")
    
    # Tentar inicializar cliente
    print("\n🔄 Inicializando cliente Gemini...")
    client = genai.Client(api_key=api_key)
    print("✅ Cliente inicializado com sucesso")
    
    # Tentar fazer uma chamada simples
    print("\n🔄 Testando chamada à API (prompt simples)...")
    
    modelos = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    
    for modelo in modelos:
        print(f"\n   Testando modelo: {modelo}")
        try:
            response = client.models.generate_content(
                model=modelo,
                contents="Responda apenas: OK"
            )
            print(f"   ✅ FUNCIONOU! Resposta: {response.text[:50]}")
            break
        except Exception as e:
            erro = str(e)
            if 'API_KEY_INVALID' in erro or 'API key not valid' in erro:
                print(f"   ❌ ERRO: API Key inválida")
                print(f"      Detalhes: {erro[:200]}")
                break
            elif '404' in erro:
                print(f"   ⚠️  Modelo não encontrado, tentando próximo...")
            else:
                print(f"   ❌ ERRO: {erro[:150]}")
                
except KeyError:
    print("\n❌ ERRO: API Key não encontrada em secrets.toml")
    print("\nVerifique:")
    print("1. Arquivo existe: .streamlit/secrets.toml")
    print("2. Contém: GEMINI_API_KEY = \"sua-chave\"")
    
except Exception as e:
    print(f"\n❌ ERRO INESPERADO: {type(e).__name__}")
    print(f"   {str(e)[:300]}")

print("\n" + "=" * 60)
