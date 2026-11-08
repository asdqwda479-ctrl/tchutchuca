# Painel de busca de @usuario

Interface Streamlit que consulta um handle em **X**, **Instagram** e **TikTok** e
devolve uma tabela com status, nível de confiança, link e o motivo da resposta.

## Arquivos

| Arquivo           | Papel                                                      |
| ----------------- | ---------------------------------------------------------- |
| `app.py`          | Interface Streamlit (campo, botão, tabela, CSV)             |
| `checkers.py`     | Lógica de busca por plataforma + agregador paralelo         |
| `requirements.txt`| Dependências                                               |

## Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Teste a lógica sem interface:

```bash
python checkers.py fulano
```

## Confirmação real no X (opcional)

Sem token, o X responde HTTP 200 para qualquer handle e o painel marca
`indeterminado`. Para confirmação de verdade, crie um app no portal de
desenvolvedor do X e disponibilize o token **fora do código**:

```bash
export X_BEARER_TOKEN="..."
```

No Hugging Face Spaces use *Settings → Variables and secrets → New secret*.
Nunca faça commit de tokens.

## Deploy no Hugging Face Spaces

1. Crie um Space em <https://huggingface.co/new-space>.
2. Escolha **SDK: Streamlit** e o hardware gratuito (CPU básica).
3. Envie `app.py`, `checkers.py` e `requirements.txt` (git ou upload pela web).
4. O Space roda em `https://<usuario>-<nome-do-space>.hf.space`.

O tráfego sai pelos servidores do Hugging Face, então o seu IP doméstico não
aparece para as plataformas consultadas — isso o próprio proxy do Space já faz,
sem precisar de conta descartável.

## Limites que o código assume de propósito

- **Instagram**: para visitante anônimo devolve a mesma página para perfil
  existente e inexistente. Só a API oficial (que cobre contas que você
  administra) confirma.
- **X**: idem; a API v2 é a única resposta confiável e é paga.
- **TikTok**: 404 é confiável. Já o 200 medido neste projeto veio como uma
  página-stub de ~1,5 KB, **idêntica para perfil real e handle inventado** — por
  isso ele é tratado como `indeterminado`, e não como "encontrado".
- **Scraping/User-Agent falsificado**: não implementado. Viola os termos das três
  plataformas, quebra a cada mudança de layout e costuma ser bloqueado por IP de
  datacenter — inclusive do Hugging Face. O painel prefere dizer
  `indeterminado` a mentir.
