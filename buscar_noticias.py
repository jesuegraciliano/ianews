import requests
import smtplib
from email.mime.text import MIMEText

# Configuração da API de notícias (NewsAPI)
API_KEY = "SUA_API_KEY"
URL = f"https://newsapi.org/v2/everything?q=inteligencia-artificial&from=2025-06-06&sortBy=popularity&apiKey={API_KEY}"

# Obtendo as notícias
response = requests.get(URL)
data = response.json()
noticias = "\n".join([f"{i+1}. {article['title']} - {article['source']['name']}\nLink: {article['url']}\n" for i, article in enumerate(data["articles"][:10])])

# Configuração do e-mail
EMAIL_REMETENTE = "seuemail@gmail.com"
EMAIL_SENHA = "sua_senha_de_app"
EMAIL_DESTINATARIO = "destinatario@gmail.com"

# Criando e enviando o e-mail
mensagem = MIMEText(noticias)
mensagem["Subject"] = "Resumo diário de notícias sobre IA"
mensagem["From"] = EMAIL_REMETENTE
mensagem["To"] = EMAIL_DESTINATARIO

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
    servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
    servidor.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIO, mensagem.as_string())

print("E-mail enviado com sucesso!")
