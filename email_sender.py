# email_sender.py
from datetime import datetime # <--- CERTIFIQUE-SE QUE ESTA LINHA ESTÁ AQUI E NO TOPO
import smtplib
import os.path
from email.message import EmailMessage
from email.mime.application import MIMEApplication


# Importa as configurações
from config import EMAIL_REMETENTE, EMAIL_SENHA_APP, EMAIL_DESTINATARIO
from excel_sync import ARQUIVO_EXCEL # Puxa o nome ("Gestão de Custo.xlsx")

def enviar_planilha_por_email():
    """
    Monta e envia um e-mail com a planilha de custos em anexo.
    """

    # Verifica se a planilha existe antes de tentar enviar
    if not os.path.exists(ARQUIVO_EXCEL):
        print(f"ERRO DE E-MAIL: Planilha '{ARQUIVO_EXCEL}' não encontrada.")
        return False, f"Arquivo '{ARQUIVO_EXCEL}' não encontrado."

    print(f"Iniciando envio de e-mail para {EMAIL_DESTINATARIO}...")

    try:
        # --- 1. Criando a mensagem ---
        msg = EmailMessage()
        msg['Subject'] = f"Relatório Financeiro: Gestão de Custo ({datetime.now().strftime('%d/%m/%Y %H:%M')})" # Usa datetime aqui
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg.set_content(f"Olá,\n\nSegue em anexo o relatório '{ARQUIVO_EXCEL}' atualizado.\n\nEnviado via Bot WhatsApp.")

        # --- 2. Lendo e anexando o arquivo Excel ---
        with open(ARQUIVO_EXCEL, 'rb') as f:
            arquivo_excel_data = f.read()

        # Adiciona o anexo
        msg.add_attachment(arquivo_excel_data,
                           maintype='application',
                           subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           filename=ARQUIVO_EXCEL)

        # --- 3. Enviando o e-mail ---
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
            smtp.send_message(msg)

        print("E-mail enviado com sucesso.")
        return True, None

    except Exception as e:
        print(f"ERRO AO ENVIAR E-MAIL: {e}")
        return False, str(e)

# (Adicionado para permitir testes manuais)
if __name__ == '__main__':
    #from datetime import datetime # Não precisa mais aqui se já importou no topo
    print("Testando envio de e-mail...")
    # (Requer que a planilha 'Gestão de Custo.xlsx' exista)
    sucesso, erro = enviar_planilha_por_email()
    if sucesso:
        print("Teste de e-mail concluído com sucesso.")
    else:
        print(f"Falha no teste de e-mail: {erro}")