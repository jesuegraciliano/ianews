#!/usr/bin/env python3
"""
AI News Agent — OpenAI Summaries & Translation
=============================================

* Busca 10 artigos sobre IA publicados nos últimos 7 dias via NewsAPI.
* Usa a OpenAI API (gpt-3.5‑turbo) para gerar, em português:
  - Um título de até 120 caracteres.
  - Um resumo descritivo de **10 linhas** (aprox. 120–150 palavras).
* Entrega e‑mail em texto simples e HTML.
* Projetado para rodar duas vezes ao dia (08 h00 & 17 h40 BRT) no GitHub Actions.

Variáveis/Segredos necessários (definidos em *Settings ▸ Secrets and variables ▸ Actions*):
  NEWS_API_KEY     Chave pessoal da NewsAPI.org.
  OPENAI_API_KEY   Chave da conta OpenAI.
  EMAIL_FROM       Gmail remetente.
  EMAIL_PASSWORD   Senha de app do Gmail.
Opcional:
  EMAIL_TO         Destinatário; se ausente, usa EMAIL_FROM.
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
import openai

# ───────── Configuração de ambiente ─────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS = 10

missing = [k for k, v in {
    "NEWS_API_KEY": NEWS_API_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "EMAIL_FROM": EMAIL_FROM,
    "EMAIL_PASSWORD": EMAIL_PASSWORD,
}.items() if not v]
if missing:
    sys.stderr.write("Variáveis obrigatórias faltando: " + ", ".join(missing) + "\n")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY
MODEL = "gpt-3.5-turbo-0125"

HEADERS = {"User-Agent": "AI-News-Agent/3.0 (+https://github.com/jesuegraciliano)"}
QUERY = '"inteligência artificial" OR "IA" OR "AI"'

# ───────── Funções utilitárias ─────────

def fetch_articles() -> List[dict]:
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)
    url = (
        "https://newsapi.org/v2/everything?"
        f"q={QUERY}&from={week_ago.isoformat()}&sortBy=publishedAt&"
        f"pageSize=100&apiKey={NEWS_API_KEY}"
    )
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "Erro NewsAPI"))

    arts: List[dict] = []
    for art in data.get("articles", []):
        if len(arts) == MAX_ARTIGOS:
            break
        if art.get("title") and art.get("url"):
            arts.append({
                "title": art["title"],
                "description": art.get("description", ""),
                "url": art["url"],
                "source": art.get("source", {}).get("name", "")
            })
    return arts


def ai_summarize(title: str, desc: str) -> dict:
    """Use ChatGPT to translate title & craft 10‑line summary in Portuguese."""
    prompt = (
        "Você é um jornalista brasileiro. Resuma a notícia a seguir em português.\n"
        "Título original: " + title + "\n"
        "Descrição original: " + desc + "\n\n"
        "Responda no formato:\n"
        "TÍTULO: <título em até 120 caracteres>\n"
        "RESUMO (10 linhas):\n<li>linha 1</li> ... <li>linha 10</li>"
    )
    chat = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    content = chat.choices[0].message.content.strip()
    titulo_pt, *resumo_html = content.split("\n", 1)
    titulo_pt = titulo_pt.replace("TÍTULO:", "").strip()
    resumo_html = resumo_html[0] if resumo_html else ""
    resumo_plain = "\n".join([re.sub(r"<[^>]+>", "", ln) for ln in resumo_html.split("\n")])
    return {"titulo": titulo_pt, "resumo_html": resumo_html, "resumo_txt": resumo_plain}


def build_email(items: List[dict]) -> MIMEMultipart:
    subject = f"IA Global — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    txt_parts: List[str] = []
    html_parts: List[str] = ["<h1>📰 Manchetes Globais de IA</h1><ol>"]

    for it in items:
        txt_parts.append(f"{it['titulo']}\n{it['resumo_txt']}\nLink: {it['url']}\n")
        html_parts.append(
            f"<li><strong>{it['titulo']}</strong><br>{it['resumo_html']}<br>"
            f"<a href='{it['url']}'>{it['url']}</a></li>"
        )

    html_parts.append("</ol><p style='font-size:0.8em;color:#666'>Enviado via GitHub Actions + OpenAI API.</p>")

    msg.attach(MIMEText("\n".join(txt_parts), "plain", "utf-8"))
    msg.attach(MIMEText("".join(html_parts), "html", "utf-8"))
    return msg


def send(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

# ───────── Main ─────────

def main() -> None:
    try:
        arts = fetch_articles()
        summaries = []
        for art in arts:
            ai = ai_summarize(art["title"], art["description"])
            summaries.append({**art, **ai})
        email_msg = build_email(summaries)
        send(email_msg)
        print("E‑mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Erro: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
