import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os # Importado para acessar variáveis de ambiente
from datetime import datetime

# 🔹 CONFIGURAÇÃO (EDITE AQUI OU USE VARIÁVEIS DE AMBIENTE) 🔹
# É ALTAMENTE RECOMENDADO USAR VARIÁVEIS DE AMBIENTE PARA SEGURANÇA.
# As variáveis de ambiente serão lidas automaticamente pelo script.
# Ex: export NEWS_API_KEY="sua_chave_aqui"
# Ex: export GMAIL_APP_PASSWORD="sua_senha_de_app_aqui"
# Ex: export GMAIL_SENDER_EMAIL="seu_email@gmail.com"
# Ex: export RECIPIENT_EMAIL="email_destino@dominio.com"

NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
EMAIL_REMETENTE = os.environ.get('GMAIL_SENDER_EMAIL', 'jesuegraci@gmail.com') # Usa default se não estiver em ambiente
EMAIL_DESTINATARIO = os.environ.get('RECIPIENT_EMAIL', 'jesue@ifsc.edu.br') # Usa default se não estiver em ambiente

# Verifica se as variáveis de ambiente essenciais estão configuradas
if not NEWS_API_KEY:
    print("ERRO: A variável de ambiente 'NEWS_API_KEY' não está configurada. Por favor, defina-a.")
    exit(1) # Sai com código de erro
if not GMAIL_APP_PASSWORD:
    print("ERRO: A variável de ambiente 'GMAIL_APP_PASSWORD' não está configurada. Por favor, defina-a.")
    exit(1) # Sai com código de erro

def pesquisar_noticias_ia():
    """Pesquisa notícias de IA usando a NewsAPI.org"""
    try:
        # Obtém a data de hoje no formato YYYY-MM-DD para buscar notícias recentes
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Constrói a URL da API NewsAPI.org usando o endpoint /everything
        # q: palavra-chave para a busca
        # language: 'pt' para notícias em português
        # sortBy: 'relevancy' para as notícias mais relevantes, ou 'publishedAt' para as mais recentes
        # from: data a partir da qual buscar notícias (hoje, para notícias diárias)
        # apiKey: sua chave de API
        url = (f"https://newsapi.org/v2/everything?"
               f"q=inteligencia artificial&"
               f"language=pt&"
               f"sortBy=relevancy&" # Ou 'publishedAt' para as mais recentes
               f"from={today}&"
               f"apiKey={NEWS_API_KEY}")

        # Define um User-Agent para a requisição, boa prática para identificar sua aplicação
        headers = {'User-Agent': 'AI-News-Bot/1.0 (jesuegraci@gmail.com)'}
        
        # Faz a requisição HTTP GET para a API
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx)

        # Converte a resposta JSON para um dicionário Python
        data = response.json()
        noticias =

        # Verifica se o status da API é 'ok' e se há artigos
        if data['status'] == 'ok' and data['articles']:
            # Limita a 5 notícias, como especificado no código original do usuário
            for article in data['articles'][:5]:
                titulo = article.get('title')
                link = article.get('url')
                # Adiciona a notícia formatada se título e link existirem
                if titulo and link:
                    noticias.append(f"{titulo} - {link}")
        else:
            print("Nenhum artigo encontrado ou status não 'ok' da API. Verifique a chave da API ou os parâmetros.")
            return ["Nenhuma notícia de IA encontrada hoje."]

        return noticias
    except requests.exceptions.RequestException as req_err:
        # Captura erros relacionados à requisição HTTP (rede, timeout, status 4xx/5xx)
        print(f"Erro de requisição à NewsAPI: {req_err}")
        return
    except Exception as e:
        # Captura quaisquer outros erros inesperados durante a pesquisa
        print(f"Erro inesperado na pesquisa de notícias: {e}")
        return

def enviar_email(noticias):
    """Envia o resumo das notícias para o e-mail do destinatário"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_REMETENTE
    msg = EMAIL_DESTINATARIO
    msg = f"📰 Notícias de IA - {datetime.now().strftime('%d/%m/%Y')}"

    # Constrói o corpo do e-mail em HTML
    corpo_email = "<h1>📰 Últimas Notícias de IA</h1><ul>"
    if not noticias:
        corpo_email += "<li>Nenhuma notícia disponível hoje.</li>"
    else:
        for noticia in noticias:
            corpo_email += f"<li>{noticia}</li>"
    corpo_email += "</ul><br><p style='font-size: 0.8em; color: #666;'>Este é um serviço automatizado. Para cancelar, por favor, desative o bot.</p>"

    msg.attach(MIMEText(corpo_email, 'html'))

    try:
        # Conecta ao servidor SMTP do Gmail usando TLS explícito na porta 587
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls() # Inicia a criptografia TLS para a comunicação
            server.login(EMAIL_REMETENTE, GMAIL_APP_PASSWORD) # Autentica com o e-mail e a senha de app
            server.send_message(msg) # Envia o e-mail
        print("📤 E-mail de notícias de IA enviado com sucesso!")
    except smtplib.SMTPAuthenticationError:
        # Erro específico para problemas de autenticação (usuário/senha incorretos)
        print("❌ Erro de autenticação SMTP. Verifique seu EMAIL_REMETENTE e GMAIL_APP_PASSWORD.")
        print("Certifique-se de que a Senha de App do Gmail está correta e que a Verificação em Duas Etapas (2FA) está ativada.")
    except Exception as e:
        # Captura quaisquer outros erros inesperados durante o envio do e-mail
        print(f"❌ Erro ao enviar e-mail: {e}")

def tarefa_diaria():
    """Função principal que orquestra a busca e o envio de notícias."""
    print(f" 🔎 Buscando notícias de IA...")
    noticias = pesquisar_noticias_ia()
    enviar_email(noticias)
    print(f" ✅ Tarefa diária concluída.")

# A lógica de agendamento (schedule.every().day.at()...) e o loop 'while True'
# são removidos, pois o agendamento será feito pela plataforma de hospedagem (PythonAnywhere).
# Este script será executado uma vez por dia pelo agendador externo.
if __name__ == "__main__":
    tarefa_diaria()
