#!/usr/bin/env python3
"""
send_ai_news.py – Resumo mundial de IA (últimos 7 dias)
=======================================================

• Busca **10** manchetes publicadas na última **semana** sobre Inteligência
  Artificial em qualquer idioma, usando a NewsAPI.
• Envia um e‑mail com versões texto e HTML.
• Projetado para rodar em GitHub Actions duas vezes por dia: 08h00 e 17h40
  (horário de Brasília). A agenda deve ser definida no arquivo
  `.github/workflows/daily_news.yml` com duas expressões *cron*:

```yaml
schedule:
  - cron: "0 11 * * *"   # 08:00 BRT (11:00 UTC)
  - cron: "40 20 * * *"  # 17:40 BRT (20:40 UTC)
```

Segredos obrigatórios:
  NEWS_API_KEY   – chave da NewsAPI.org
  EMAIL_FROM     – Gmail remetente
  EMAIL_PASSWORD – senha de aplicativo
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

# ─────────── Variáveis de ambiente ───────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_FROM or "")
MAX_ARTIGOS = 10  # fixo, conforme solicitação

QUERY = '"inteligência artificial" OR "IA" OR "AI"'
UA = "AI-News-Agent/2.0 (+https://github.com/jesuegraciliano)"
HEADERS = {"User-Agent": UA}

required = {"NEWS_API_KEY": NEWS_API_KEY, "EMAIL_FROM": EMAIL_FROM, "EMAIL_PASSWORD": EMAIL_PASSWORD}
missing = [k for k, v in required.items() if not v]
if missing:
    sys.stderr.write("Variáveis ausentes: " + ", ".join(missing) + "\n")
    sys.exit(1)

# ─────────── Funções ───────────

def buscar_noticias() -> List[str]:
    """Busca notícias da última semana, retorna lista formatada."""
    hoje = datetime.now(timezone.utc).date()
    semana_passada = hoje - timedelta(days=7)

    url = (
        "https://newsapi.org/v2/everything?"
        f"q={QUERY}&"
        "sortBy=publishedAt&"
        f"from={semana_passada.isoformat()}&"
        "pageSize=100&"  # pegar bastante resultados para filtrar
        f"apiKey={NEWS_API_KEY}"
    )

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "NewsAPI resposta inesperada"))

    artigos = []
    for art in data.get("articles", []):
        titulo, fonte, link = art.get("title"), art.get("source", {}).get("name", ""), art.get("url")
        if titulo and link:
            artigos.append(f"{titulo} — {fonte}\nLink: {link}")
        if len(artigos) == MAX_ARTIGOS:
            break
    return artigos or ["Nenhuma notícia de IA encontrada na última semana."]


def montar_email(noticias: List[str]) -> MIMEMultipart:
    assunto = f"Resumo Semanal de IA — {datetime.now().strftime('%d/%m/%Y')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    # Texto simples
    msg.attach(MIMEText("\n\n".join(noticias), "plain", "utf-8"))

    # HTML
    html_parts = ["<h1>📰 Manchetes Globais de IA (7 dias)</h1><ul>"]
    for item in noticias:
        partes = item.split("Link:")
        if len(partes) == 2:
            titulo, url = partes[0].strip(), partes[1].strip()
            html_parts.append(f"<li>{titulo}<br><a href='{url}'>{url}</a></li>")
        else:
            html_parts.append(f"<li>{item}</li>")
    html_parts.append("</ul><p style='font-size:0.8em;color:#666'>Enviado automaticamente via GitHub Actions.</p>")
    msg.attach(MIMEText("".join(html_parts), "html", "utf-8"))
    return msg


def enviar(msg: MIMEMultipart) -> None:
    """Envia o e‑mail via SMTP‑SSL do Gmail."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

# ─────────── Main ───────────

def main() -> None:
    try:
        noticias = buscar_noticias()
        email_msg = montar_email(noticias)
        enviar(email_msg)
        print("E‑mail enviado com sucesso.")
    except Exception as exc:
        sys.stderr.write(f"Erro: {exc}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
