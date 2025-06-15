#!/usr/bin/env python3
"""
Agente de manchetes globais de IA, com tradução automática
=========================================================

• Busca 10 manchetes sobre IA publicadas nos últimos 7 dias (NewsAPI).
• Traduz o título de cada notícia para **português** usando *googletrans*.
• Envia um e-mail (texto e HTML) contendo o título original e a tradução.
• Projetado para rodar em GitHub Actions duas vezes por dia (08:00 e 17:40 BRT).

Dependências instaladas no workflow:
  pip install requests googletrans==4.0.0-rc1

Segredos obrigatórios:
  NEWS_API_KEY   – chave da NewsAPI.org
  EMAIL_FROM     – Gmail remetente
  EMAIL_PASSWORD – senha de app Gmail
Opcional:
  EMAIL_TO       – destinatário (default = EMAIL_FROM)
"""
from __future__ import annotations

import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import requests
from googletrans import Translator

# ───────────────── Variáveis de ambiente ─────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS = 10

if not all([NEWS_API_KEY, EMAIL_FROM, EMAIL_PASSWORD]):
    sys.stderr.write("Faltam variáveis obrigatórias.\n")
    sys.exit(1)

QUERY = '"inteligência artificial" OR "IA" OR "AI"'
UA = "AI-News-Agent/2.1 (+https://github.com/jesuegraciliano)"
HEADERS = {"User-Agent": UA}
translator = Translator()

# ───────────────── Funções ─────────────────

def buscar_noticias() -> List[dict]:
    hoje = datetime.now(timezone.utc).date()
    semana_passada = hoje - timedelta(days=7)
    url = (
        "https://newsapi.org/v2/everything?"
        f"q={QUERY}&sortBy=publishedAt&from={semana_passada.isoformat()}&"
        "pageSize=100&apiKey=" + NEWS_API_KEY
    )
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "Erro desconhecido da NewsAPI"))

    artigos = []
    for art in data.get("articles", []):
        titulo, fonte, link = art.get("title"), art.get("source", {}).get("name", ""), art.get("url")
        if titulo and link:
            artigos.append({"titulo": titulo, "fonte": fonte, "link": link})
        if len(artigos) == MAX_ARTIGOS:
            break
    return artigos


def traduzir(texto: str) -> str:
    try:
        return translator.translate(texto, dest="pt").text
    except Exception:
        return "[Falha na tradução] " + texto


def montar_email(artigos: List[dict]) -> MIMEMultipart:
    assunto = f"Manchetes Globais de IA — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    linhas_txt = []
    linhas_html = ["<h1>📰 Manchetes Globais de IA (7 dias)</h1><ul>"]
    for art in artigos or [{"titulo": "Nenhuma notícia encontrada", "link": "", "fonte": ""}]:
        titulo, fonte, link = art["titulo"], art["fonte"], art["link"]
        trad = traduzir(titulo)
        linhas_txt.append(f"{titulo} — {fonte}\n{trad}\nLink: {link}\n")
        linhas_html.append(
            f"<li><strong>{titulo}</strong><br>" +
            f"<em>{trad}</em><br>" +
            (f"<a href='{link}'>{link}</a>" if link else "") +
            "</li>"
        )
    linhas_html.append("</ul><p style='font-size:0.8em;color:#666'>Enviado automaticamente via GitHub Actions.</p>")

    msg.attach(MIMEText("\n".join(linhas_txt), "plain", "utf-8"))
    msg.attach(MIMEText("".join(linhas_html), "html", "utf-8"))
    return msg


def enviar(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

# ───────────────── Main ─────────────────

def main():
    try:
        artigos = buscar_noticias()
        email_msg = montar_email(artigos)
        enviar(email_msg)
        print("E-mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Erro: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
