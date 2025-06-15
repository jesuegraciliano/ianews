#!/usr/bin/env python3
"""
ai_news_agent_openai.py

Agente de notícias globais sobre Inteligência Artificial que usa a NewsAPI para
coletar artigos e a OpenAI API (gpt‑3.5‑turbo) para gerar, em português:
  • Título curto (≤120 caracteres)
  • Resumo de 10 linhas

O e‑mail inclui título, resumo e link de cada notícia. O script foi pensado
para rodar duas vezes ao dia via GitHub Actions.

Segredos obrigatórios no repositório:
  NEWS_API_KEY   – chave pessoal da NewsAPI.org
  OPENAI_API_KEY – chave da conta OpenAI
  EMAIL_FROM     – Gmail remetente (mesmo usado para login)
  EMAIL_PASSWORD – senha de aplicativo do Gmail
Opcional:
  EMAIL_TO       – destinatário; se ausente, usa EMAIL_FROM
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

# ───────── Variáveis de ambiente ─────────
NEWS_API_KEY   = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM     = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO       = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS    = 10

required = {
    "NEWS_API_KEY": NEWS_API_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "EMAIL_FROM": EMAIL_FROM,
    "EMAIL_PASSWORD": EMAIL_PASSWORD,
}
missing = [k for k, v in required.items() if not v]
if missing:
    sys.stderr.write("Faltam variáveis: " + ", ".join(missing) + "\n")
    sys.exit(1)

openai.api_key = OPENAI_API_KEY
MODEL = "gpt-3.5-turbo-0125"
HEADERS = {"User-Agent": "AI-News-Agent/3.0 (+https://github.com/jesuegraciliano)"}
QUERY = '"inteligência artificial" OR "IA" OR "AI"'

# ───────── Funções ─────────

def buscar_artigos() -> List[dict]:
    hoje = datetime.now(timezone.utc).date()
    semana = hoje - timedelta(days=7)
    url = (
        "https://newsapi.org/v2/everything?q=" + QUERY +
        f"&from={semana.isoformat()}&sortBy=publishedAt&pageSize=100&apiKey={NEWS_API_KEY}"
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


def resumo_ai(title: str, desc: str) -> dict:
    prompt = (
        "Você é jornalista de tecnologia. Traduza o título abaixo para o português (até 120 caracteres) "
        "e escreva um resumo detalhado em exatamente 10 linhas, cada linha iniciada com '•'.\n\n"
        f"TÍTULO ORIGINAL: {title}\n"
        f"DESCRIÇÃO ORIGINAL: {desc}\n"
    )
    chat = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    content = chat.choices[0].message.content.strip()
    partes = content.split("\n", 1)
    titulo_pt = partes[0].replace("TÍTULO:", "").strip(" •-")
    resumo = partes[1] if len(partes) == 2 else ""
    resumo_html = "<br>".join([ln.strip(" •") for ln in resumo.split("\n") if ln.strip()])
    resumo_txt = "\n".join([ln.strip(" •") for ln in resumo.split("\n") if ln.strip()])
    return {"titulo": titulo_pt, "resumo_html": resumo_html, "resumo_txt": resumo_txt}


def montar_email(items: List[dict]) -> MIMEMultipart:
    assunto = f"Resumo de IA — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    txt: List[str] = []
    html: List[str] = ["<h1>📰 IA: Manchetes & Resumos</h1><ol>"]

    for it in items:
        txt.append(f"{it['titulo']}\n{it['resumo_txt']}\nLink: {it['url']}\n")
        html.append(
            f"<li><strong>{it['titulo']}</strong><br>{it['resumo_html']}<br>"
            f"<a href='{it['url']}'>{it['url']}</a></li>"
        )

    html.append("</ol><p style='font-size:0.8em;color:#666'>Enviado via GitHub Actions + OpenAI API.</p>")

    msg.attach(MIMEText("\n".join(txt), "plain", "utf-8"))
    msg.attach(MIMEText("".join(html), "html", "utf-8"))
    return msg


def enviar(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

# ───────── Main ─────────

def main() -> None:
    try:
        arts = buscar_artigos()
        enriched = [{**a, **resumo_ai(a['title'], a['description'])} for a in arts]
        email_msg = montar_email(enriched)
        enviar(email_msg)
        print("E-mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Falha: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
