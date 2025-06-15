#!/usr/bin/env python3
"""
ai_news_agent_openai.py (Versão focada)
======================================

Busca *exclusivamente* notícias cujo conteúdo mencione explicitamente
“Artificial Intelligence” (expressão exata, em inglês). As demais
funcionalidades permanecem:
  • Seleção dos 10 artigos mais recentes (últimos 7 dias) via NewsAPI.
  • Uso da OpenAI API para traduzir título e produzir resumo de 10 linhas em
    português.
  • Envio por e-mail com corpo texto e HTML.

Segredos obrigatórios (GitHub ▸ Settings ▸ Secrets):
  NEWS_API_KEY   Chave da NewsAPI.org
  OPENAI_API_KEY Chave da OpenAI
  EMAIL_FROM     Gmail remetente
  EMAIL_PASSWORD Senha de app Gmail
Opcional:
  EMAIL_TO       Destinatário (default = EMAIL_FROM)
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

# ──────────── Variáveis de ambiente ────────────
NEWS_API_KEY   = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM     = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO       = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS    = 10

missing = [k for k, v in {
    "NEWS_API_KEY": NEWS_API_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "EMAIL_FROM": EMAIL_FROM,
    "EMAIL_PASSWORD": EMAIL_PASSWORD,
}.items() if not v]
if missing:
    sys.stderr.write("Faltam variáveis: " + ", ".join(missing) + "\n")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY
MODEL = "gpt-3.5-turbo-0125"
HEADERS = {"User-Agent": "AI-News-Agent/3.1 (+https://github.com/jesuegraciliano)"}
# Query restrita à expressão exata "Artificial Intelligence" em inglês
QUERY = '"Artificial Intelligence"'

# ──────────── Funções ────────────

def fetch_articles() -> List[dict]:
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)
    url = (
        "https://newsapi.org/v2/everything?q=" + QUERY +
        f"&from={week_ago.isoformat()}&sortBy=publishedAt&pageSize=100&language=en&apiKey={NEWS_API_KEY}"
    )
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "Erro NewsAPI"))

    items: List[dict] = []
    for art in data.get("articles", []):
        if len(items) == MAX_ARTIGOS:
            break
        if art.get("title") and art.get("url"):
            items.append({
                "title": art["title"],
                "description": art.get("description", ""),
                "url": art["url"],
                "source": art.get("source", {}).get("name", "")
            })
    return items


def ai_summary(title: str, desc: str) -> dict:
    prompt = (
        "Traduza o título abaixo para o português (≤120 caracteres) e elabore um resumo em 10 linhas, "
        "cada linha iniciada com •, também em português.\n\n"
        f"TÍTULO ORIGINAL: {title}\n"
        f"DESCRIÇÃO ORIGINAL: {desc}\n"
    )
    chat = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    content = chat.choices[0].message.content.strip()
    linhas = [ln.strip(" •-") for ln in content.split("\n") if ln.strip()]
    titulo_pt = linhas[0]
    resumo_list = linhas[1:11]
    resumo_txt = "\n".join(resumo_list)
    resumo_html = "<br>".join(resumo_list)
    return {"titulo": titulo_pt, "resumo_txt": resumo_txt, "resumo_html": resumo_html}


def build_email(items: List[dict]) -> MIMEMultipart:
    subject = f"AI Global (Últimos 7 dias) — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    txt_blocks: List[str] = []
    html_blocks: List[str] = ["<h1>📰 Artificial Intelligence — Destaques</h1><ol>"]

    for it in items:
        txt_blocks.append(f"{it['titulo']}\n{it['resumo_txt']}\nLink: {it['url']}\n")
        html_blocks.append(
            f"<li><strong>{it['titulo']}</strong><br>{it['resumo_html']}<br>"
            f"<a href='{it['url']}'>{it['url']}</a></li>"
        )

    html_blocks.append("</ol><p style='font-size:0.8em;color:#666'>Enviado via GitHub Actions + OpenAI API.</p>")

    msg.attach(MIMEText("\n".join(txt_blocks), "plain", "utf-8"))
    msg.attach(MIMEText("".join(html_blocks), "html", "utf-8"))
    return msg


def send(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

# ──────────── Main ────────────

def main() -> None:
    try:
        arts = fetch_articles()
        enriched = [{**art, **ai_summary(art['title'], art['description'])} for art in arts]
        email_msg = build_email(enriched)
        send(email_msg)
        print("E-mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Erro: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
