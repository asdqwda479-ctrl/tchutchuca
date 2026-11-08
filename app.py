"""Painel de busca de @usuario — Streamlit + X, Instagram e TikTok."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from checkers import ENCONTRADO, buscar, normalizar, usuario_valido

st.set_page_config(page_title="Busca de @usuario", page_icon="🔎", layout="centered")


@st.cache_data(ttl=300, show_spinner=False)
def buscar_com_cache(usuario: str) -> list[dict]:
    """Evita repetir requisições para o mesmo handle por 5 minutos."""
    return buscar(usuario)


st.title("🔎 Painel de busca de @usuario")
st.caption("Consulta o mesmo handle em X, Instagram e TikTok.")

with st.form("form_busca"):
    entrada = st.text_input(
        "Usuário",
        placeholder="@usuario",
        help="Aceita @usuario, usuario ou a URL completa do perfil.",
    )
    enviado = st.form_submit_button("Pesquisar", type="primary")

if enviado:
    alvo = normalizar(entrada)
    if not alvo:
        st.session_state.pop("usuario", None)
        st.warning("Digite um @usuario para pesquisar.")
    elif not usuario_valido(alvo):
        st.session_state.pop("usuario", None)
        st.error("Handle inválido. Use de 1 a 30 caracteres: letras, números, ponto ou sublinhado.")
    else:
        st.session_state["usuario"] = alvo

usuario = st.session_state.get("usuario")

if usuario:
    st.markdown(f"Handle pesquisado: `@{usuario}`")

    with st.spinner("Consultando as plataformas..."):
        linhas = buscar_com_cache(usuario)

    df = pd.DataFrame(linhas)
    df = df.rename(
        columns={
            "plataforma": "Plataforma",
            "status": "Status",
            "confianca": "Confiança",
            "link": "Link",
            "detalhe": "Detalhe",
        }
    )

    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "Plataforma": st.column_config.TextColumn(width="small"),
            "Status": st.column_config.TextColumn(width="small"),
            "Confiança": st.column_config.TextColumn(width="small"),
            "Link": st.column_config.LinkColumn(
                "Link",
                display_text=r"^https?://[^/]+/(?:@)?([^/?#]+)/?$",
            ),
            "Detalhe": st.column_config.TextColumn(width="large"),
        },
    )

    encontrados = int((df["Status"] == ENCONTRADO).sum())
    confirmados = int((df["Confiança"] == "confirmado").sum())
    st.success(
        f"{encontrados} de {len(df)} plataformas com perfil detectado "
        f"({confirmados} com confirmação oficial)."
    )

    st.download_button(
        "Baixar resultado em CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"busca_{usuario}.csv",
        mime="text/csv",
    )

with st.expander("Como interpretar o resultado"):
    st.markdown(
        """
- **encontrado + confirmado** — a plataforma respondeu de forma inequívoca (ou a API oficial confirmou).
- **encontrado + provável** — a página respondeu como perfil existente, mas pode ser desafio anti-bot. Vale abrir o link.
- **indeterminado** — a plataforma respondeu 200 para qualquer handle ou exigiu login. Não é possível afirmar nada sem autenticação.
- **não encontrado** — retorno 404, ou página de "conta não encontrada".

X e Instagram só entregam resposta conclusiva via API oficial. Sem token,
o painel mostra `indeterminado` de propósito, em vez de inventar um link.
"""
    )

st.divider()
st.caption("Resultados são indicativos: confirme no navegador antes de usar a informação.")
