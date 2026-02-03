"""
Script de teste para verificar a configuração do Gemini
"""
import streamlit as st

try:
    from google import genai
    print("✅ Biblioteca 'google-genai' importada com sucesso")
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        print(f"✅ API Key encontrada: {api_key[:10]}...")
        
        client = genai.Client(api_key=api_key)
        print("✅ Cliente Gemini inicializado")
        
        modelos_para_testar = [
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash', 
            'gemini-1.5-pro',
            'gemini-pro',
            'models/gemini-1.5-flash',
            'models/gemini-pro'
        ]
        
        print("\n🧪 Testando modelos disponíveis:")
        print("-" * 50)
        
        for modelo in modelos_para_testar:
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents="Responda apenas 'OK'"
                )
                print(f"✅ FUNCIONA: {modelo}")
                print(f"   Resposta: {response.text[:50]}")
                break
            except Exception as e:
                erro = str(e)
                if '404' in erro:
                    print(f"❌ NÃO EXISTE: {modelo}")
                else:
                    print(f"⚠️  ERRO: {modelo} - {erro[:100]}")
        
    except KeyError:
        print("❌ API Key não configurada em .streamlit/secrets.toml")
        print("\nCrie o arquivo com:")
        print('GEMINI_API_KEY = "sua-chave-aqui"')
    
except ImportError:
    print("❌ Biblioteca 'google-genai' não instalada")
    print("\nInstale com:")
    print("pip install google-genai")
