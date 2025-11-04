# image_server.py (Agora também é o Servidor de Webhooks)
from flask import Flask, send_from_directory, request, abort
import os
import json # <-- Importa JSON
import requests # Para enviar a msg de volta ao Telegram

# Nossas importações de lógica
import config
import mercadopago
import logic # <-- Importa todo o nosso cérebro

# Configura o SDK do MP (necessário para verificar o pagamento)
sdk = mercadopago.SDK(config.MP_ACCESS_TOKEN)

app = Flask(__name__)

# Pega o diretório ATUAL e encontra a pasta 'image' (singular)
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image')

# --- Rota 1: Servir Imagens (A rota antiga) ---
@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve os arquivos de dentro da pasta 'image'."""
    return send_from_directory(IMAGE_DIR, filename)

# --- Rota 2: Ouvir o Webhook do Mercado Pago (ATUALIZADA) ---
@app.route('/webhook/mercadopago', methods=['POST'])
def webhook_mercadopago():
    """
    Recebe a notificação de pagamento do Mercado Pago.
    """
    print("\n[Webhook MP] Notificação recebida!")
    
    try:
        dados = request.json
        print(f"[Webhook MP] Dados recebidos: {dados}")

        # 1. Verifica se é uma notificação de pagamento
        if dados.get("type") == "payment":
            payment_id = dados.get("data", {}).get("id")
            if not payment_id:
                return "ID de pagamento não encontrado", 400

            print(f"[Webhook MP] Obtendo detalhes do Pagamento ID: {payment_id}")
            
            # 2. Busca os detalhes completos do pagamento
            payment_info = sdk.payment().get(payment_id)
            payment_status = payment_info.get("response", {}).get("status")
            
            # --- (ATUALIZADO) Decodifica o JSON da referência ---
            external_ref_str = payment_info.get("response", {}).get("external_reference")

            print(f"[Webhook MP] Status: {payment_status} | Ref Externa (JSON str): {external_ref_str}")

            # 3. É O PAGAMENTO QUE QUEREMOS?
            if payment_status == "approved" and external_ref_str:
                
                try:
                    # Decodifica o JSON
                    ref_data = json.loads(external_ref_str)
                    numero_cliente = ref_data.get("chat_id")
                    event_id = ref_data.get("event_id")
                except Exception as e:
                    print(f"ERRO: Webhook com external_reference malformada: {external_ref_str}. Erro: {e}")
                    return "Ref externa malformada", 200 # 200 OK para o MP parar

                if not numero_cliente or not event_id:
                    print(f"ERRO: Webhook com dados faltando no JSON: {external_ref_str}")
                    return "Ref externa com dados faltando", 200

                print(f"[Webhook MP] PAGAMENTO APROVADO para chat_id: {numero_cliente}, event_id: {event_id}")

                # --- 4. EXECUTAR A LÓGICA DE FINALIZAÇÃO ---
                logic.user_states = logic.carregar_estados()
                
                estado_cliente = logic.user_states.get(numero_cliente, {}).get('estado')
                
                # (ATUALIZADO) Apenas confirma se o evento BATER com o salvo
                pending_event_id = logic.user_states.get(numero_cliente, {}).get('pending_event_id')
                
                if estado_cliente == 'aguardando_confirmacao_pagamento' and pending_event_id == event_id:
                
                    # (ATUALIZADO) Passa o event_id para a lógica final
                    resposta_dict = logic.finalizar_reserva_pos_pagamento({}, numero_cliente, event_id)
                    
                    # Salva o estado (que foi alterado por 'finalizar_reserva...')
                    logic.salvar_estados()
                    
                    # --- 5. ENVIAR A MENSAGEM DE CONFIRMAÇÃO ---
                    texto_confirmacao = resposta_dict.get('body', 'Erro ao gerar texto de confirmação.')
                    enviar_mensagem_telegram_direto(numero_cliente, texto_confirmacao)
                    
                    print(f"[Webhook MP] Reserva finalizada e cliente {numero_cliente} notificado.")
                
                else:
                    print(f"[Webhook MP] Pagamento aprovado, mas estado do cliente é {estado_cliente} ou ID do evento {event_id} não bate com o pendente {pending_event_id}. Ignorando.")

    except Exception as e:
        print(f"ERRO CRÍTICO no Webhook do Mercado Pago: {e}")
        # Retorna 200 OK mesmo em erro, para evitar que o MP fique a tentar de novo.
        return "Erro processando webhook", 200

    # Responde 200 OK para o Mercado Pago saber que recebemos
    return "Notificação recebida.", 200


def enviar_mensagem_telegram_direto(chat_id: str, texto: str):
    """
    Função simples para enviar uma mensagem pelo Telegram
    usando a API HTTP, sem depender do 'bot_telegram.py'.
    """
    try:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": int(chat_id), # API do Telegram espera um INT
            "text": texto,
            "parse_mode": "Markdown" # Para o texto ficar formatado (com *negrito*)
        }
        response = requests.post(url, json=payload)
        print(f"[Envio Direto] Resposta da API Telegram: {response.json()}")
    except Exception as e:
        print(f"ERRO ao enviar mensagem direta para {chat_id}: {e}")


if __name__ == '__main__':
    print(f"Servidor de imagens e Webhooks rodando. Servindo da pasta: {IMAGE_DIR}")
    # Roda na porta 5000, acessível pelo ngrok
    app.run(port=5000)