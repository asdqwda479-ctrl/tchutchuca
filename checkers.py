"""Motor de busca OSINT expandido.
Foco em evasão de bloqueio e validação multi-plataforma.
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

# Headers simulando navegador real para evitar detecção imediata de bot
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
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
    return Resultado(plataforma, ERRO, SEM_CONFIANCA, "", f"falha: {exc.__class__.__name__}")

# --- PLATAFORMAS ---

def checar_instagram(usuario: str) -> Resultado:
    link = f"https://www.instagram.com/{usuario}/"
    try:
        res = _get(link)
        if res.status_code == 404:
            return Resultado("Instagram", NAO_ENCONTRADO, CONFIRMADO, "", "HTTP 404")
        if res.status_code in (301, 302):
            # Se redireciona para login, o perfil provavelmente existe mas está protegido
            return Resultado("Instagram", ENCONTRADO, PROVAVEL, link, "Redirecionou para Login (Perfil Provável)")
        if res.status_code == 200:
            return Resultado("Instagram", ENCONTRADO, PROVAVEL, link, "HTTP 200 (Acesso permitido)")
    except Exception as e:
        return _falha_de_rede("Instagram", link, e)
    return Resultado("Instagram", INDETERMINADO, SEM_CONFIANCA, "", "Resposta inconclusiva")

def checar_x(usuario: str) -> Resultado:
    link = f"https://x.com/{usuario}"
    try:
        res = _get(link)
        if res.status_code == 404:
            return Resultado("X", NAO_ENCONTRADO, CONFIRMADO, "", "HTTP 404")
        if res.status_code == 200:
            return Resultado("X", ENCONTRADO, PROVAVEL, link, "HTTP 200")
    except Exception as e:
        return _falha_de_rede("X", link, e)
    return Resultado("X", INDETERMINADO, SEM_CONFIANCA, "", "Resposta inconclusiva")

def checar_tiktok(usuario: str) -> Resultado:
    link = f"https://www.tiktok.com/@{usuario}"
    try:
        res = _get(link)
        if res.status_code == 404:
            return Resultado("TikTok", NAO_ENCONTRADO, CONFIRMADO, "", "HTTP 404")
        if res.status_code == 200:
            if "uniqueid" in res.text and usuario.lower() in res.text.lower():
                return Resultado("TikTok", ENCONTRADO, CONFIRMADO, link, "Confirmado via HTML")
            return Resultado("TikTok", ENCONTRADO, PROVAVEL, link, "HTTP 200")
    except Exception as e:
        return _falha_de_rede("TikTok", link, e)
    return Resultado("TikTok", INDETERMINADO, SEM_CONFIANCA, "", "Resposta inconclusiva")

def checar_github(usuario: str) -> Resultado:
    link = f"https://github.com/{usuario}"
    try:
        res = _get(link)
        if res.status_code == 200:
            return Resultado("GitHub", ENCONTRADO, CONFIRMADO, link, "Perfil Ativo")
        if res.status_code == 404:
            return Resultado("GitHub", NAO_ENCONTRADO, CONFIRMADO, "", "Não existe")
    except Exception as e:
        return _falha_de_rede("GitHub", link, e)
    return Resultado("GitHub", INDETERMINADO, SEM_CONFIANCA, "", "Erro")

def checar_pinterest(usuario: str) -> Resultado:
    link = f"https://www.pinterest.com/{usuario}/"
    try:
        res = _get(link)
        if res.status_code == 200:
            return Resultado("Pinterest", ENCONTRADO, CONFIRMADO, link, "Perfil Ativo")
        if res.status_code == 404:
            return Resultado("Pinterest", NAO_ENCONTRADO, CONFIRMADO, "", "Não existe")
    except Exception as e:
        return _falha_de_rede("Pinterest", link, e)
    return Resultado("Pinterest", INDETERMINADO, SEM_CONFIANCA, "", "Erro")

def checar_spotify(usuario: str) -> Resultado:
    link = f"https://open.spotify.com/user/{usuario}"
    try:
        res = _get(link)
        if res.status_code == 200:
            return Resultado("Spotify", ENCONTRADO, CONFIRMADO, link, "Perfil Ativo")
        if res.status_code == 404:
            return Resultado("Spotify", NAO_ENCONTRADO, CONFIRMADO, "", "Não existe")
    except Exception as e:
        return _falha_de_rede("Spotify", link, e)
    return Resultado("Spotify", INDETERMINADO, SEM_CONFIANCA, "", "Erro")

def checar_twitch(usuario: str) -> Resultado:
    link = f"https://www.twitch.tv/{usuario}"
    try:
        res = _get(link)
        if res.status_code == 200:
            return Resultado("Twitch", ENCONTRADO, CONFIRMADO, link, "Perfil Ativo")
        if res.status_code == 404:
            return Resultado("Twitch", NAO_ENCONTRADO, CONFIRMADO, "", "Não existe")
    except Exception as e:
        return _falha_de_rede("Twitch", link, e)
    return Resultado("Twitch", INDETERMINADO, SEM_CONFIANCA, "", "Erro")

# --- AGREGADOR ---

SONDAS = {
    "Instagram": checar_instagram,
    "X": checar_x,
    "TikTok": checar_tiktok,
    "GitHub": checar_github,
    "Pinterest": checar_pinterest,
    "Spotify": checar_spotify,
    "Twitch": checar_twitch,
}

def buscar(usuario: str) -> list[dict]:
    with ThreadPoolExecutor(max_workers=len(SONDAS)) as pool:
        futuros = [(nome, pool.submit(sonda, usuario)) for nome, sonda in SONDAS.items()]
        saida = []
        for nome, futuro in futuros:
            try:
                saida.append(futuro.result().como_dict())
            except Exception as e:
                saida.append(Resultado(nome, ERRO, SEM_CONFIANCA, "", f"Erro: {e}").como_dict())
    return saida

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python checkers.py <usuario>")
    alvo = normalizar(sys.argv[1])
    for linha in buscar(alvo):
        print(f"{linha['plataforma']:<12} {linha['status']:<15} {linha['confianca']:<12} {linha['link']}")
