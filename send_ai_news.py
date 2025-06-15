#!/usr/bin/env python3
"""
send_ai_news.py – Script principal do agente de notícias de IA

Coloque‑o na raiz do seu repositório GitHub. O GitHub Actions irá executá‑lo
todos os dias (conforme definido no arquivo .github/workflows/daily_news.yml),
pegar as manchetes da NewsAPI e enviar para o e‑mail configurado via segredos.
"""

import os
import sys
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

import requests

# ───────────────── Configurações por variáveis de ambiente ──────────────────
NEWS_API_KEY   = os.getenv("NEWS_API_KEY")           # chave da NewsAPI.org
EMAIL_FROM     = os.getenv("EMAIL_FROM")             # Gmail que envia
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")         # Senha de app do Gmail
EMAIL_TO       = os.getenv("EMAIL_TO", EMAIL_FROM)   # Destinatário
MAX_ARTIGOS    = int(os.getenv("MAX_ARTIGOS", "10"))
QUERY          = os.getenv("QUERY", "inteligência artificial")

# Validação rápida
missing = [k for k, v in {
    "NEWS_API_KEY": NEWS_API_KEY,
    "EMAIL_FROM": EMAIL_FROM,
    "EMAIL_PASSWORD": EMAIL_PASSWORD,
}.items() if not v]
if missing:
    sys.stderr.write(f"Variáveis ausentes: {', '.join(missing)}\n")
    sys.exit(1)

# ─────────────────── Funções auxiliares ─────────────────────────────────────

def buscar_noticias() -> List[str]:
    hoje = datetime.now(timezone.utc).date().isoformat()
    url = (
        "https://newsapi.org/v2/everything?"
        f"q={QUERY}&language=pt&sortBy=publishedAt&from={hoje}&apiKey={NEWS_API_KEY}"
    )
    headers = {"User-Agent": "AI-News-Agent/1.0 (+github.com/jesuegraciliano)"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(data)
    artigos = data.get("articles", [])[:MAX_ARTIGOS]
    if not artigos:
        return ["Nenhuma notícia encontrada hoje."]
    return [f"{i+1}. {a['title']} — {a['source']['name']}\nLink: {a['url']}" for i, a in enumerate(artigos)]


def montar_email(noticias: List[str]) -> MIMEMultipart:
    assunto = f"Resumo Diário de IA — {datetime.now().strftime('%d/%m/%Y')}"
    corpo_html = "<h1>📰 Últimas Notícias de IA</h1><ul>" + "".join(
        f"<li>{n.split('Link:')[0]}<br><a href='{n.split('Link:')[1].strip()}'>{n.split('Link:')[1].strip()}</a></li>" for n in noticias
    ) + "</ul><p style='font-size:0.8em;color:#666'>Enviado automaticamente via GitHub Actions.</p>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText("\n\n".join(noticias), "plain", "utf-8"))
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))
    return msg


def enviar(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
    print("E‑mail enviado com sucesso.")

# ─────────────────── Execução ───────────────────────────────────────────────

def main():
    try:
        noticias = buscar_noticias()
        email_msg = montar_email(noticias)
        enviar(email_msg)
    except Exception as e:
        sys.stderr.write(f"Erro: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
