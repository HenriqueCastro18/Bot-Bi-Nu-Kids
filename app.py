# app.py
from flask import Flask, request, send_from_directory
from twilio.rest import Client
import os
import time # <--- ADICIONADO DE VOLTA

# Funções da agenda e do ficheiro de configuração
from agenda import verificar_horarios_disponiveis, marcar_horario
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
from logic import processar_mensagem

app = Flask(__name__)
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- ROTA DE IMAGEM ATUALIZADA ---
@app.route('/image/<path:filename>')
def serve_image(filename):
    return send_from_directory('image', filename)

# --- (FUNÇÃO ATUALIZADA - SOLUÇÃO DEFINITIVA) ---
def enviar_mensagem_whatsapp(para, resposta_dict):
    """
    Envia a resposta (texto e/ou média) para o cliente.
    LÓGICA ATUALIZADA (ROBUSTA):
    - Se 'usar_legenda' é True: Envia texto com a PRIMEIRA imagem.
    - Se 'usar_legenda' é False: Envia imagens, espera, e envia texto separado.
    Isso garante a ordem correta de entrega.
    """
    try:
        media_urls = resposta_dict.get('media', [])
        body_text = resposta_dict.get('body', '')
        # Pega a flag, o padrão é False se não existir
        usar_legenda = resposta_dict.get('usar_legenda', False) 

        if usar_legenda and media_urls:
            # --- CENÁRIO 1: USAR LEGENDA (Menu Principal, Seleção de Combo) ---
            
            # Envia a PRIMEIRA imagem (media_urls[0]) COM a legenda
            client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                media_url=[media_urls[0]], # Apenas a primeira URL
                body=body_text,            # Com o texto como legenda
                to=para
            )
            
            # Se houver MAIS imagens (de 1 em diante)
            if len(media_urls) > 1:
                # Envia as imagens restantes, UMA POR UMA, sem legenda
                for url in media_urls[1:]:
                    client.messages.create(
                        from_=TWILIO_WHATSAPP_NUMBER,
                        media_url=[url],
                        to=para
                    )
        
        # --- (LÓGICA ATUALIZADA CONFORME SOLICITADO) ---
        elif (not usar_legenda) and media_urls:
            # --- CENÁRIO 2: NÃO USAR LEGENDA (Montagem de Combo) ---
            
            # 1. Envia TODAS as imagens, UMA POR UMA, sem legenda
            for url in media_urls:
                client.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    media_url=[url],
                    to=para
                )
            
            # 2. Adiciona um pequeno delay (ex: 2 segundos)
            time.sleep(5.5) 

            # 3. Se houver texto, envia como uma mensagem SEPARADA
            if body_text:
                client.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    body=body_text,
                    to=para
                )
            # --- (FIM DA ATUALIZAÇÃO) ---

        elif (not media_urls) and body_text:
             # --- CENÁRIO 3: SÓ TEXTO ---
             client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body=body_text,
                to=para
            )

    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")


@app.route('/whatsapp', methods=['POST'])
def webhook_whatsapp():
    mensagem_recebida = request.values.get('Body', '').lower().strip()
    numero_cliente = request.values.get('From', '')

    print(f"Mensagem de '{numero_cliente}': '{mensagem_recebida}'")

    resposta_dict = processar_mensagem(mensagem_recebida, numero_cliente)
    
    enviar_mensagem_whatsapp(numero_cliente, resposta_dict)

    return ('', 200)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)