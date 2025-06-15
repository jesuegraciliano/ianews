#!/usr/bin/env python3
"""
Agente diário de manchetes sobre Inteligência Artificial
=======================================================

Busca artigos nas últimas 48 h que contenham termos relacionados a IA
(“inteligência artificial”, “IA”, “AI”), em português ou inglês, usando a
NewsAPI. Envia um resumo por e‑mail (texto + HTML) via Gmail.

Segredos obrigatórios (definidos no repositório GitHub):
  NEWS_API_KEY   – chave da NewsAPI.org
  EMAIL_FROM     – Gmail que enviará o e‑mail
  EMAIL_PASSWORD – senha de aplicativo (Google, com 2FA)
Opcional:
  EMAIL_TO       – destinatário; se omitido, usa EMAIL_FROM
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

# ─────────────── Configurações (via variáveis de ambiente) ────────────────
NEWS_API_KEY: str | None = os.getenv("NEWS_API_KEY")
EMAIL_FROM: str | None = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
EMAIL_TO: str = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS: int = int(os.getenv("MAX_ARTIGOS", "10"))

QUERY = (
    '"inteligência artificial" OR "IA" OR "AI"'
)  # NewsAPI usa OR maiúsculo

UA = "AI-News-Agent/1.3 (+https://github.com/jesuegraciliano)"
HDRS = {"User-Agent": UA}

missing = [k for k, v in {
    "NEWS_API_KEY": NEWS_API_KEY,
    "EMAIL_FROM": EMAIL_FROM,
    "EMAIL_PASSWORD": EMAIL_PASSWORD,
}.items() if not v]
if missing:
    sys.stderr.write(f"Variáveis ausentes: {', '.join(missing)}\n")
    sys.exit(1)

# ───────────────────────── Funções utilitárias ────────────────────────────

def buscar_noticias() -> List[str]:
    """Retorna até MAX_ARTIGOS strings formatadas."""
    hoje = datetime.now(timezone.utc).date()
    anteontem = hoje - timedelta(days=4)
    url = (
        "https://newsapi.org/v2/everything?"
        f"q={QUERY}&"
        "language=pt,en&"
        "sortBy=publishedAt&"
        f"from={anteontem.isoformat()}&"
        f"apiKey={NEWS_API_KEY}"
    )

    r = requests.get(url, headers=HDRS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "Resposta inesperada da NewsAPI"))

    artigos = []
    for art in data.get("articles", []):
        titulo = art.get("title")
        fonte = art.get("source", {}).get("name", "")
        link = art.get("url")
        if titulo and link:
            artigos.append(f"{titulo} — {fonte}\nLink: {link}")
        if len(artigos) >= MAX_ARTIGOS:
            break
    return artigos or ["Nenhuma notícia encontrada nos últimos dois dias."]


def montar_email(noticias: List[str]) -> MIMEMultipart:
    assunto = f"Resumo Diário de IA — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Parte texto
    msg.attach(MIMEText("\n\n".join(noticias), "plain", "utf-8"))

    # Parte HTML
    html = ["<h1>📰 Últimas Notícias de IA (48 h)</h1><ul>"]
    for item in noticias:
        partes = item.split("Link:")
        if len(partes) == 2:
            titulo, url = partes[0].strip(), partes[1].strip()
            html.append(f"<li>{titulo}<br><a href='{url}'>{url}</a></li>")
        else:
            html.append(f"<li>{item}</li>")
    html.append("</ul><p style='font-size:0.8em;color:#666'>Enviado automaticamente via GitHub Actions.</p>")
    msg.attach(MIMEText("".join(html), "html", "utf-8"))
    return msg


def enviar_email(msg: MIMEMultipart) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASSWORD)
        s.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

# ─────────────────────────────── main ─────────────────────────────────────

def main() -> None:
    try:
        noticias = buscar_noticias()
        email = montar_email(noticias)
        enviar_email(email)
        print("E‑mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Falha: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
