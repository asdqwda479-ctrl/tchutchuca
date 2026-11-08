"""Verificação de existência de @usuario em X, Instagram e TikTok.

Uso rápido pela linha de comando:

    python checkers.py fulano

A função pública é `buscar(usuario)`, que devolve uma lista de dicionários
pronta para virar DataFrame.

Nota de projeto: para um visitante anônimo, X e Instagram devolvem HTTP 200
para praticamente qualquer handle (SPA / muro de login). Portanto uma resposta
200 NÃO é prova de que o perfil existe. Nesses casos o status é
"indeterminado" — melhor um resultado honesto do que um falso positivo.
"""

from __future__ import annotations

import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

import requests

TIMEOUT = 8

ENCONTRADO = "encontrado"
NAO_ENCONTRADO = "não encontrado"
INDETERMINADO = "indeterminado"
ERRO = "erro"

CONFIRMADO = "confirmado"
PROVAVEL = "provável"
SEM_CONFIANCA = "—"

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")

# Identificamos o cliente abertamente. Não nos passamos por um navegador:
# mascarar o User-Agent para driblar proteções viola os termos das plataformas
# e, na prática, só aumenta o bloqueio por rate limit.
HEADERS = {
    "User-Agent": "usercheck/1.0 (verificacao de handle)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


@dataclass(frozen=True)
class Resultado:
    plataforma: str
    status: str
    confianca: str
    link: str
    detalhe: str

    def como_dict(self) -> dict:
        return asdict(self)


def normalizar(entrada: str) -> str:
    """Aceita '@fulano', 'fulano' ou a URL completa do perfil."""
    valor = (entrada or "").strip()
    valor = re.sub(r"^https?://", "", valor, flags=re.IGNORECASE)
    valor = valor.split("?")[0].split("#")[0].strip("/")
    if "/" in valor:
        valor = valor.rsplit("/", 1)[-1]
    return valor.lstrip("@").strip()


def usuario_valido(usuario: str) -> bool:
    return bool(USERNAME_RE.match(usuario))


def _get(url: str) -> requests.Response:
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)


def _falha_de_rede(plataforma: str, link: str, exc: Exception) -> Resultado:
    return Resultado(
        plataforma,
        ERRO,
        SEM_CONFIANCA,
        "",
        f"falha de rede: {exc.__class__.__name__}",
    )


# --------------------------------------------------------------------------- #
# X (Twitter)
# --------------------------------------------------------------------------- #
def _checar_x_api(usuario: str) -> Resultado | None:
    """Confirmação real, se houver um token oficial em X_BEARER_TOKEN."""
    token = os.getenv("X_BEARER_TOKEN", "").strip()
    if not token:
        return None

    link = f"https://x.com/{usuario}"
    try:
        resposta = requests.get(
            f"https://api.x.com/2/users/by/username/{usuario}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        return _falha_de_rede("X", link, exc)

    if resposta.status_code == 200:
        return Resultado("X", ENCONTRADO, CONFIRMADO, link, "confirmado pela API oficial")
    if resposta.status_code == 404:
        return Resultado("X", NAO_ENCONTRADO, CONFIRMADO, "", "API oficial: usuário inexistente")
    if resposta.status_code in (401, 403):
        return Resultado("X", ERRO, SEM_CONFIANCA, "", "token da API inválido, expirado ou sem permissão")
    if resposta.status_code == 429:
        return Resultado("X", INDETERMINADO, SEM_CONFIANCA, "", "limite de requisições da API oficial atingido")
    return Resultado("X", INDETERMINADO, SEM_CONFIANCA, "", f"API oficial respondeu HTTP {resposta.status_code}")


def checar_x(usuario: str) -> Resultado:
    via_api = _checar_x_api(usuario)
    if via_api is not None:
        return via_api

    link = f"https://x.com/{usuario}"
    try:
        resposta = _get(link)
    except requests.RequestException as exc:
        return _falha_de_rede("X", link, exc)

    if resposta.status_code == 404:
        return Resultado("X", NAO_ENCONTRADO, CONFIRMADO, "", "HTTP 404 — perfil não existe")
    if resposta.status_code in (403, 429):
        return Resultado("X", INDETERMINADO, SEM_CONFIANCA, "", f"HTTP {resposta.status_code} — bloqueio ou limite de taxa")
    if resposta.status_code == 200:
        return Resultado(
            "X",
            INDETERMINADO,
            SEM_CONFIANCA,
            link,
            "HTTP 200 — o X devolve 200 para qualquer handle; confirmação exige a API oficial (X_BEARER_TOKEN)",
        )
    return Resultado("X", INDETERMINADO, SEM_CONFIANCA, "", f"HTTP {resposta.status_code} — resposta não conclusiva")


# --------------------------------------------------------------------------- #
# Instagram
# --------------------------------------------------------------------------- #
def checar_instagram(usuario: str) -> Resultado:
    link = f"https://www.instagram.com/{usuario}/"
    try:
        resposta = _get(link)
    except requests.RequestException as exc:
        return _falha_de_rede("Instagram", link, exc)

    if resposta.status_code == 404:
        return Resultado("Instagram", NAO_ENCONTRADO, CONFIRMADO, "", "HTTP 404 — perfil não existe")
    if resposta.status_code in (301, 302, 303, 307, 308):
        destino = resposta.headers.get("Location", "")
        if "login" in destino.lower():
            return Resultado("Instagram", INDETERMINADO, SEM_CONFIANCA, "", "redirecionado para o login")
        return Resultado("Instagram", INDETERMINADO, SEM_CONFIANCA, "", f"redirecionado para {destino[:60]}")
    if resposta.status_code in (401, 403, 429):
        return Resultado("Instagram", INDETERMINADO, SEM_CONFIANCA, "", f"HTTP {resposta.status_code} — acesso restringido")
    if resposta.status_code == 200:
        return Resultado(
            "Instagram",
            INDETERMINADO,
            SEM_CONFIANCA,
            link,
            "HTTP 200 — o Instagram serve a mesma página para perfis inexistentes; confirmação exige login ou API",
        )
    return Resultado("Instagram", INDETERMINADO, SEM_CONFIANCA, "", f"HTTP {resposta.status_code} — resposta não conclusiva")


# --------------------------------------------------------------------------- #
# TikTok
# --------------------------------------------------------------------------- #
def checar_tiktok(usuario: str) -> Resultado:
    link = f"https://www.tiktok.com/@{usuario}"
    try:
        resposta = _get(link)
    except requests.RequestException as exc:
        return _falha_de_rede("TikTok", link, exc)

    if resposta.status_code == 404:
        return Resultado("TikTok", NAO_ENCONTRADO, CONFIRMADO, "", "HTTP 404 — perfil não existe")
    if resposta.status_code in (403, 429):
        return Resultado("TikTok", INDETERMINADO, SEM_CONFIANCA, "", f"HTTP {resposta.status_code} — bloqueio ou limite de taxa")
    if resposta.status_code == 200:
        corpo = (resposta.text or "")[:200_000]
        minusculo = corpo.lower()
        if "couldn't find this account" in minusculo or "nao foi possivel encontrar" in minusculo:
            return Resultado("TikTok", NAO_ENCONTRADO, PROVAVEL, "", "página de 'conta não encontrada'")
        # O TikTok devolve uma página-stub (~1,5 KB) igual para perfil real e
        # para handle inventado quando detecta bot. Só aceitamos 200 como
        # "provável" se houver dados de perfil embutidos no HTML.
        tem_dados = bool(re.search(rf'"uniqueid"\s*:\s*"{re.escape(usuario.lower())}"', minusculo))
        if tem_dados:
            return Resultado(
                "TikTok",
                ENCONTRADO,
                PROVAVEL,
                link,
                "HTTP 200 com dados de perfil no HTML — confira no navegador",
            )
        return Resultado(
            "TikTok",
            INDETERMINADO,
            SEM_CONFIANCA,
            link,
            f"HTTP 200 sem dados de perfil ({len(corpo)} bytes) — página anti-bot; abra e confira",
        )
    return Resultado("TikTok", INDETERMINADO, SEM_CONFIANCA, "", f"HTTP {resposta.status_code} — resposta não conclusiva")


# --------------------------------------------------------------------------- #
# Agregador
# --------------------------------------------------------------------------- #
SONDAS = {
    "X": checar_x,
    "Instagram": checar_instagram,
    "TikTok": checar_tiktok,
}


def buscar(usuario: str) -> list[dict]:
    """Consulta as três plataformas em paralelo. Nunca levanta exceção."""
    with ThreadPoolExecutor(max_workers=len(SONDAS)) as pool:
        futuros = [(nome, pool.submit(sonda, usuario)) for nome, sonda in SONDAS.items()]
        saida: list[dict] = []
        for nome, futuro in futuros:
            try:
                saida.append(futuro.result().como_dict())
            except Exception as exc:  # DNS, TLS, resposta inesperada...
                saida.append(
                    Resultado(nome, ERRO, SEM_CONFIANCA, "", f"falha inesperada: {exc.__class__.__name__}").como_dict()
                )
    return saida


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python checkers.py <usuario>")
    alvo = normalizar(sys.argv[1])
    if not usuario_valido(alvo):
        sys.exit(f"handle inválido: {alvo!r}")
    for linha in buscar(alvo):
        print(f"{linha['plataforma']:<10} {linha['status']:<15} {linha['confianca']:<12} {linha['link']}")
        print(f"{'':<10} {linha['detalhe']}")
