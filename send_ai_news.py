#!/usr/bin/env python3
"""
Gera resumo diário sobre IA com base em manchetes da NewsAPI
e envia e‑mail com resumo em português via OpenAI.
"""

import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
import requests
import openai

# Variáveis obrigatórias
NEWS_API_KEY   = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM     = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO       = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS    = 5

# Validação
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
MODEL = "gpt-4o"
HEADERS = {"User-Agent": "IA-Resumo-Agent/1.0"}
QUERY = '"inteligência artificial" OR "IA" OR "AI"'

def buscar_manchetes() -> List[dict]:
    hoje = datetime.now(timezone.utc).date()
    semana = hoje - timedelta(days=7)
    url = (
        f"https://newsapi.org/v2/everything?q={QUERY}&from={semana}&sortBy=publishedAt"
        f"&language=en&pageSize=20&apiKey={NEWS_API_KEY}"
    )
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "Erro na NewsAPI"))
    artigos = [
        {
            "title": art["title"],
            "description": art.get("description", ""),
            "url": art["url"],
        }
        for art in data.get("articles", [])
        if art.get("title") and art.get("url")
    ]
    return artigos[:MAX_ARTIGOS]

def gerar_resumo(titulo: str, descricao: str) -> dict:
    prompt = (
        f"Traduza o título abaixo para o português (máx 120 caracteres). Em seguida, escreva um resumo "
        f"em exatamente 5 frases claras sobre o conteúdo da notícia.\n\n"
        f"TÍTULO ORIGINAL: {titulo}\nDESCRIÇÃO: {descricao}"
    )
    chat = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    resposta = chat.choices[0].message.content.strip()
    partes = resposta.split("\n", 1)
    titulo_pt = partes[0].strip("•- ")
    resumo = partes[1] if len(partes) > 1 else ""
    return {
        "titulo": titulo_pt,
        "resumo": resumo.replace("\n", "<br>"),
        "resumo_txt": resumo.replace("<br>", "\n")
    }

def montar_email(itens: List[dict]) -> MIMEMultipart:
    assunto = f"Resumo de IA — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    txt: List[str] = []
    html: List[str] = ["<h1>📰 Resumo de Notícias sobre IA</h1><ol>"]

    for it in itens:
        txt.append(f"{it['titulo']}\n{it['resumo_txt']}\nLink: {it['url']}\n")
        html.append(
            f"<li><strong>{it['titulo']}</strong><br>{it['resumo']}<br>"
            f"<a href='{it['url']}'>{it['url']}</a></li>"
        )

    html.append("</ol><p style='font-size:0.8em;color:#666'>Enviado via OpenAI + GitHub Actions</p>")
    msg.attach(MIMEText("\n".join(txt), "plain", "utf-8"))
    msg.attach(MIMEText("".join(html), "html", "utf-8"))
    return msg

def enviar_email(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

def main():
    try:
        artigos = buscar_manchetes()
        enriquecido = [{**a, **gerar_resumo(a["title"], a["description"])} for a in artigos]
        email = montar_email(enriquecido)
        enviar_email(email)
        print("✅ E-mail enviado com sucesso.")
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
