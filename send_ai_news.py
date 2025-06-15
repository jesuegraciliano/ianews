#!/usr/bin/env python3
"""
Pipeline semanal de geração de artigo sobre IA com agentes CrewAI
"""

from __future__ import annotations
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

import requests
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

# ──────────── Validação de variáveis de ambiente ────────────
ENV = {
    "NEWS_API_KEY": os.getenv("NEWS_API_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "SERPER_API_KEY": os.getenv("SERPER_API_KEY"),
    "EMAIL_FROM": os.getenv("EMAIL_FROM"),
    "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
}
missing = [k for k, v in ENV.items() if not v]
if missing:
    sys.stderr.write("Variáveis ausentes: " + ", ".join(missing) + "\n")
    sys.exit(1)

EMAIL_TO = os.getenv("EMAIL_TO", ENV["EMAIL_FROM"])

# ──────────── 1. Coleta de manchetes ────────────
HEADERS = {"User-Agent": "IA-Agents-Pipeline/1.0"}
QUERY = '"Artificial Intelligence"'
MAX_ARTIGOS = 3  # reduzido para acelerar a execução

def fetch_ai_headlines() -> List[Dict]:
    print("🌐 Buscando manchetes de IA na NewsAPI...")
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)
    url = (
        "https://newsapi.org/v2/everything?q=" + QUERY +
        f"&from={week_ago.isoformat()}&sortBy=publishedAt&language=en&"
        f"pageSize=100&apiKey={ENV['NEWS_API_KEY']}"
    )
    data = requests.get(url, headers=HEADERS, timeout=30).json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "Erro na NewsAPI"))
    headlines = []
    for art in data.get("articles", []):
        if len(headlines) == MAX_ARTIGOS:
            break
        if art.get("title") and art.get("url"):
            headlines.append({"title": art["title"], "url": art["url"]})
    print(f"✅ Manchetes coletadas: {len(headlines)}")
    return headlines

# ──────────── 2. Agentes e tarefas CrewAI ────────────
llm = ChatOpenAI(model="gpt-4o-mini", api_key=ENV["OPENAI_API_KEY"])
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()

planejador = Agent(
    role="Planejador de Conteúdo",
    goal="Criar um esboço conciso sobre Inteligência Artificial baseado nas manchetes",
    backstory="Você prepara a pauta para um artigo semanal sobre IA.",
    verbose=False,
    tools=[search_tool, scrape_tool],
    llm=llm,
)

redator = Agent(
    role="Redator de Conteúdo",
    goal="Escrever artigo em português, objetivo e interessante",
    backstory="Você transforma o esboço em um artigo markdown.",
    verbose=False,
    tools=[search_tool, scrape_tool],
    llm=llm,
)

editor = Agent(
    role="Editor",
    goal="Garantir clareza, correção gramatical e foco em IA",
    backstory="Você revisa e finaliza o texto.",
    verbose=False,
    tools=[],
    llm=llm,
)

planejamento_task = Task(
    description="Crie um esboço detalhado (markdown) para um artigo sobre IA.",
    expected_output="Esboço markdown com seções.",
    agent=planejador,
)

escrita_task = Task(
    description="Escreva o artigo (markdown) com introdução, 3 seções e conclusão.",
    expected_output="Artigo completo markdown.",
    agent=redator,
)

edicao_task = Task(
    description="Revise o artigo garantindo foco em IA e clareza.",
    expected_output="Artigo final markdown revisado.",
    agent=editor,
)

def generate_article(headlines: List[Dict]) -> str:
    context = "\n".join([f"- {h['title']} ({h['url']})" for h in headlines]) or "Nenhuma manchete"
    print("🧠 Iniciando geração do artigo com agentes da CrewAI...")
    crew = Crew(
        agents=[planejador, redator, editor],
        tasks=[planejamento_task, escrita_task, edicao_task],
        verbose=2,
    )
    result = crew.kickoff(inputs={"tópico": "Artificial Intelligence", "manchetes": context})
    print("📄 Artigo gerado com sucesso!")
    return result

# ──────────── 3. Envio de e-mail ────────────
def send_email(markdown_body: str) -> None:
    print(f"📬 Enviando e-mail para {EMAIL_TO}...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Artigo Semanal sobre IA — {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"] = ENV["EMAIL_FROM"]
    msg["To"] = EMAIL_TO

    msg.attach(MIMEText(markdown_body, "plain", "utf-8"))
    msg.attach(MIMEText(markdown_body.replace("\n", "<br>"), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(ENV["EMAIL_FROM"], ENV["EMAIL_PASSWORD"])
        smtp.sendmail(ENV["EMAIL_FROM"], [EMAIL_TO], msg.as_string())
    print("✅ E-mail enviado com sucesso!")

# ──────────── Execução principal ────────────
if __name__ == "__main__":
    try:
        print("🚀 Iniciando pipeline de geração de artigo sobre IA...")
        manchetes = fetch_ai_headlines()
        article_md = generate_article(manchetes)
        send_email(article_md)
        print("🏁 Pipeline concluído com sucesso!")
    except Exception as err:
        print(f"❌ Erro durante o pipeline: {err}")
        sys.exit(1)
