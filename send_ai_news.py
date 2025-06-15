#!/usr/bin/env python3
"""
Agente de notícias globais de IA (manchetes + resumo traduzido)
==============================================================

* Busca 10 artigos sobre IA publicados nos últimos 7 dias (NewsAPI).
* Traduz título **e** descrição para português com `googletrans‑fixed`.
* Recorta as 10 primeiras linhas do texto traduzido como resumo.
* Envia e‑mail em texto simples e HTML.
* Pensado para rodar em GitHub Actions duas vezes por dia (08h00 e 17h40 BRT).

Segredos exigidos no repositório
--------------------------------
NEWS_API_KEY   chave da NewsAPI.org 
EMAIL_FROM     Gmail remetente (mesmo usado para login) 
EMAIL_PASSWORD senha de aplicativo do Gmail (2FA) 
EMAIL_TO       (opcional) destinatário; default = EMAIL_FROM
"""
from __future__ import annotations

import os
import re
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import requests
from googletrans_fixed import Translator

# ───── Variáveis de ambiente ─────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS = 10

if not all([NEWS_API_KEY, EMAIL_FROM, EMAIL_PASSWORD]):
    sys.stderr.write("Variáveis obrigatórias ausentes.\n")
    sys.exit(1)

QUERY = '"inteligência artificial" OR "IA" OR "AI"'
HEADERS = {"User-Agent": "AI-News-Agent/2.3 (+https://github.com/jesuegraciliano)"}
translator = Translator()

# ───── Funções auxiliares ─────

def _split_sentences(texto: str) -> List[str]:
    texto = re.sub(r"\s+", " ", texto.strip())
    return re.split(r"(?<=[.!?]) +", texto)


def _translate(texto: str) -> str:
    try:
        return translator.translate(texto, dest="pt").text
    except Exception:
        return texto  # devolve original se falhar


def buscar_artigos() -> List[dict]:
    hoje = datetime.now(timezone.utc).date()
    semana = hoje - timedelta(days=7)
    url = (
        "https://newsapi.org/v2/everything?q=" + QUERY +
        f"&from={semana.isoformat()}&sortBy=publishedAt&pageSize=100&apiKey={NEWS_API_KEY}"
    )
    dados = requests.get(url, headers=HEADERS, timeout=30).json()
    if dados.get("status") != "ok":
        raise RuntimeError(dados.get("message", "Erro NewsAPI"))

    artigos: List[dict] = []
    for art in dados.get("articles", []):
        if len(artigos) == MAX_ARTIGOS:
            break
        titulo = art.get("title")
        desc = art.get("description") or ""
        link = art.get("url")
        fonte = art.get("source", {}).get("name", "")
        if titulo and link:
            artigos.append({"titulo": titulo, "desc": desc, "link": link, "fonte": fonte})
    return artigos


def montar_email(artigos: List[dict]) -> MIMEMultipart:
    assunto = f"IA Global — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Corpo texto
    txt_lines: List[str] = []
    # Corpo HTML
    html_parts: List[str] = ["<h1>📰 Manchetes Globais de IA (7 dias)</h1><ol>"]

    for art in artigos or [{"titulo": "Nenhuma notícia encontrada", "desc": "", "link": "", "fonte": ""}]:
        tit_pt = _translate(art["titulo"])
        desc_pt = _translate(art["desc"])
        resumo = "\n".join(_split_sentences(desc_pt)[:10]) or "[sem descrição]"

        txt_lines.append(f"{tit_pt} — {art['fonte']}\n{resumo}\nLink: {art['link']}\n")

        html_parts.append(
            f"<li><strong>{tit_pt}</strong><br>" +
            "<br>".join(_split_sentences(desc_pt)[:10]) + "<br>" +
            (f"<a href='{art['link']}'>{art['link']}</a>" if art['link'] else "") +
            "</li>"
        )

    html_parts.append(
        "</ol><p style='font-size:0.8em;color:#666'>Enviado automaticamente via GitHub Actions.</p>"
    )

    msg.attach(MIMEText("\n".join(txt_lines), "plain", "utf-8"))
    msg.attach(MIMEText("".join(html_parts), "html", "utf-8"))
    return msg


def enviar_email(m: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, [EMAIL_TO], m.as_string())

# ───── Main ─────

def main() -> None:
    try:
        artigos = buscar_artigos()
        email_msg = montar_email(artigos)
        enviar_email(email_msg)
        print("E-mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Erro: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
