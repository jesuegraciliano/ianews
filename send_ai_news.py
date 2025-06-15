#!/usr/bin/env python3
"""
send_ai_news.py – Agente diário de manchetes sobre Inteligência Artificial

Funciona dentro de GitHub Actions. O runner injeta, como variáveis de ambiente,
quatro segredos configurados no repositório:

  NEWS_API_KEY   – chave obtida em https://newsapi.org
  EMAIL_FROM     – endereço Gmail que enviará o e‑mail
  EMAIL_PASSWORD – senha de aplicativo gerada no Google (2FA habilitado)
  EMAIL_TO       – destinatário (opcional; assume EMAIL_FROM se ausente)

O script executa quatro etapas:
  1. Consulta a NewsAPI por artigos (máx. 10) que contenham a expressão
     “inteligência artificial”, publicados hoje, em português.
  2. Monta um resumo em texto simples e em HTML.
  3. Envia o e‑mail via SMTP‑SSL do Gmail.
  4. Exibe "E-mail enviado com sucesso" ou lança erro; o GitHub Actions
     registra o resultado na interface.
"""
from __future__ import annotations

import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import requests

# ─────────────────────────────────── Configs ──────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_FROM)
MAX_ARTIGOS = int(os.getenv("MAX_ARTIGOS", "10"))
QUERY = os.getenv("QUERY", "inteligência artificial")

_USER_AGENT = "AI-News-Agent/1.2 (+https://github.com/jesuegraciliano)"
_HEADERS = {"User-Agent": _USER_AGENT}

missing = [k for k, v in {
    "NEWS_API_KEY": NEWS_API_KEY,
    "EMAIL_FROM": EMAIL_FROM,
    "EMAIL_PASSWORD": EMAIL_PASSWORD,
}.items() if not v]
if missing:
    sys.stderr.write(f"Variáveis ausentes: {', '.join(missing)}\n")
    sys.exit(1)

# ────────────────────────────────── Funções ───────────────────────────────────

def _buscar_noticias() -> List[str]:
    """Obtém até MAX_ARTIGOS artigos pertinentes na NewsAPI."""
    hoje = datetime.now(timezone.utc).date().isoformat()
    url = (
        "https://newsapi.org/v2/everything?"
        f"q={QUERY}&language=pt&sortBy=publishedAt&from={hoje}&apiKey={NEWS_API_KEY}"
    )
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"NewsAPI status: {data.get('status')} – {data.get('message')}")

    artigos = []
    for art in data.get("articles", []):
        titulo = art.get("title")
        fonte = art.get("source", {}).get("name", "")
        url_ = art.get("url")
        if titulo and url_:
            artigos.append(f"{titulo} — {fonte}\nLink: {url_}")
        if len(artigos) >= MAX_ARTIGOS:
            break

    return artigos or ["Nenhuma notícia encontrada hoje."]


def _montar_email(noticias: List[str]) -> MIMEMultipart:
    """Cria objeto MIMEMultipart contendo versões texto e HTML."""
    assunto = f"Resumo Diário de IA — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Corpo texto
    msg.attach(MIMEText("\n\n".join(noticias), "plain", "utf-8"))

    # Corpo HTML
    html_parts = ["<h1>📰 Últimas Notícias de IA</h1>", "<ul>"]
    for item in noticias:
        partes = item.split("Link:")
        if len(partes) == 2:
            titulo, url_ = partes[0].strip(), partes[1].strip()
            html_parts.append(
                f"<li>{titulo}<br><a href='{url_}'>{url_}</a></li>"
            )
        else:
            html_parts.append(f"<li>{item}</li>")
    html_parts.append(
        "</ul><p style='font-size:0.8em;color:#666'>Enviado automaticamente via "
        "GitHub Actions.</p>"
    )
    msg.attach(MIMEText("".join(html_parts), "html", "utf-8"))
    return msg


def _enviar_email(msg: MIMEMultipart) -> None:
    """Envia a mensagem usando SMTP‑SSL no Gmail."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

# ─────────────────────────────────── Main ─────────────────────────────────────

def main() -> None:
    try:
        noticias = _buscar_noticias()
        email_msg = _montar_email(noticias)
        _enviar_email(email_msg)
        print("E-mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Falha: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
