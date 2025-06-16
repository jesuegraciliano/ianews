#!/usr/bin/env python3
"""
Versão leve do pipeline IA para teste de performance
"""

import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

import requests
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

ENV = {
    "NEWS_API_KEY": os.getenv("NEWS_API_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "EMAIL_FROM": os.getenv("EMAIL_FROM"),
    "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
}
missing = [k for k, v in ENV.items() if not v]
if missing:
    sys.stderr.write("Variáveis ausentes: " + ", ".join(missing) + "\n")
    sys.exit(1)

EMAIL_TO = os.getenv("EMAIL_TO", ENV["EMAIL_FROM"])

# Coleta simplificada de manchetes
HEADERS = {"User-Agent": "IA-Agents-Light/1.0"}
QUERY = '"Artificial Intelligence"'
MAX_ARTIGOS = 3

def fetch_ai_headlines() -> List[Dict]:
    print("🌐 Buscando manchetes da NewsAPI (versão leve)...")
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
    headlines = [
        {"title": art["title"], "url": art["url"]}
        for art in data.get("articles", [])
        if art.get("title") and art.get("url")
    ][:MAX_ARTIGOS]
    print(f"✅ Manchetes coletadas: {len(headlines)}")
    return headlines

# Agentes e tarefas com LLM
llm = ChatOpenAI(model="gpt-4o-mini", api_key=ENV["OPENAI_API_KEY"])

planejador = Agent(
    role="Planejador de Conteúdo",
    goal="Criar um esboço com base nas manchetes fornecidas",
    backstory="Você é responsável por organizar a estrutura do artigo semanal.",
    verbose=False,
    tools=[],  # ferramentas removidas
    llm=llm,
)

redator = Agent(
    role="Redator de Conteúdo",
    goal="Escrever um artigo informativo em português a partir do esboço",
    backstory="Você transforma o esboço em um artigo completo em markdown.",
    verbose=False,
    tools=[],  # ferramentas removidas
    llm=llm,
)

editor = Agent(
    role="Editor",
    goal="Revisar o conteúdo final para clareza e foco",
    backstory="Você faz a revisão final do texto.",
    verbose=False,
    tools=[],  # ferramentas removidas
    llm=llm,
)

# Tarefas
planejamento_task = Task(
    description="Crie um esboço em markdown com base nas manchetes.",
    expected_output="Esboço estruturado",
    agent=planejador,
)

escrita_task = Task(
    description="Escreva o artigo final em português com introdução, seções e conclusão.",
    expected_output="Artigo markdown finalizado",
    agent=redator,
)

edicao_task = Task(
    description="Revise o artigo garantindo clareza, gramática e foco em IA.",
    expected_output="Versão final do artigo em markdown",
    agent=editor,
)

def generate_article(headlines: List[Dict]) -> str:
    context = "\n".join([f"- {h['title']} ({h['url']})" for h in headlines]) or "Nenhuma manchete"
    print("🧠 Iniciando geração do artigo (sem scraping)...")
    crew = Crew(
        agents=[planejador, redator, editor],
        tasks=[planejamento_task, escrita_task, edicao_task],
        verbose=2,
    )
    result = crew.kickoff(inputs={"tópico": "Artificial Intelligence", "manchetes": context})
    print("📄 Artigo gerado com sucesso!")
    return result

def send_email(markdown_body: str) -> None:
    print(f"📬 Enviando e-mail para {EMAIL_TO}...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Artigo IA (teste leve) — {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"] = ENV["EMAIL_FROM"]
    msg["To"] = EMAIL_TO

    msg.attach(MIMEText(markdown_body, "plain", "utf-8"))
    msg.attach(MIMEText(markdown_body.replace("\n", "<br>"), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(ENV["EMAIL_FROM"], ENV["EMAIL_PASSWORD"])
        smtp.sendmail(ENV["EMAIL_FROM"], [EMAIL_TO], msg.as_string())
    print("✅ E-mail enviado com sucesso!")

# Execução principal
if __name__ == "__main__":
    try:
        print("🚀 Iniciando pipeline leve de teste...")
        manchetes = fetch_ai_headlines()
        artigo = generate_article(manchetes)
        send_email(artigo)
        print("🏁 Pipeline leve concluído com sucesso.")
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
