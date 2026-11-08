import streamlit as st
import pandas as pd
from checkers import buscar, normalizar

# Configuração da página
st.set_page_config(page_title="Painel OSINT - Busca Avançada", page_icon="🔍", layout="wide")

# Estilização customizada para parecer ferramenta de inteligência
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #262730; color: white; border: 1px solid #464b5d; }
    .stButton>button:hover { border-color: #ff4b4b; color: #ff4b4b; }
    .reportview-container { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

st.title("🔍 Orquestrador OSINT")
st.subheader("Busca de Identidade e Reconhecimento Digital")

# Criação de abas para separar as funções
tab1, tab2 = st.tabs(["👤 Busca por Username", "🖼️ Busca por Imagem"])

with tab1:
    st.markdown("### Localizador de Perfis")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        alvo = st.text_input("Digite o @usuario ou handle:", placeholder="ex: nsnns8943")
    
    with col2:
        st.write(" ") # Espaçador
        btn_buscar = st.button("Rastrear")

    if btn_buscar and alvo:
        with st.spinner(f"Varrendo redes sociais para {alvo}..."):
            alvo_norm = normalizar(alvo)
            resultados = buscar(alvo_norm)
            df = pd.DataFrame(resultados)
            
            # Organiza as colunas para ficar limpo
            df = df[["plataforma", "status", "confianca", "link"]]
            df.columns = ["Plataforma", "Status", "Confiança", "Link"]
            
            st.dataframe(df, use_container_width=True)
    elif btn_buscar and not alvo:
        st.warning("Por favor, insira um username.")

with tab2:
    st.markdown("### Reconhecimento Facial e Busca Reversa")
    st.info("Envie a foto do alvo para gerar gatilhos de busca nos motores de reconhecimento facial do mundo.")
    
    foto = st.file_uploader("Upload da foto do alvo", type=["jpg", "jpeg", "png", "webp"])
    
    if foto:
        st.image(foto, caption="Foto carregada para análise", width=300)
        
        # Como não temos servidor de storage próprio, vamos simular a ponte de URL
        # Em um cenário real, subiríamos para um S3 ou Imgur API
        st.markdown("---")
        st.markdown("#### 🚀 Gatilhos de Busca Profunda")
        st.write("Clique nos botões abaixo para disparar a busca da imagem nos motores de IA:")
        
        # Aqui está o "pulo do gato": 
        # Como o navegador não deixa enviar o arquivo direto via URL, 
        # orientamos o usuário a usar a URL da imagem ou usamos a técnica de upload via link.
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown("**Google Lens**")
            st.markdown("[🔍 Iniciar Busca](https://lens.google.com/upload)")
            st.caption("Melhor para objetos e locais.")
            
        with col_b:
            st.markdown("**Yandex Visual**")
            st.markdown("[🔍 Iniciar Busca](https://yandex.com/images/search?rpt=imageview)")
            st.caption("O mais forte para rostos (Rússia).")
            
        with col_c:
            st.markdown("**Bing Visual**")
            st.markdown("[🔍 Iniciar Busca](https://www.bing.com/visualsearch)")
            st.caption("Excelente para perfis sociais.")

        st.warning("⚠️ Nota: Devido a restrições de segurança dos navegadores, você deve arrastar a foto carregada acima para dentro da página de busca aberta.")
