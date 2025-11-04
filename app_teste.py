import requests
from flask import Flask, request, send_from_directory
import os
import time

# Funções da agenda e do ficheiro de configuração
from agenda import verificar_horarios_disponiveis, marcar_horario
# ATUALIZADO: Importando as credenciais da Z-API (assumindo que estão em config.py)
from config import ZAPI_INSTANCE_ID, ZAPI_TOKEN 
from logic import processar_mensagem, menu_principal as logic_menu_principal

app = Flask(__name__)

# Monta a URL da Z-API no formato padrão que a API espera para endpoints.
# Exemplo: https://api.z-api.io/instances/{ID}/token/{TOKEN}
ZAPI_URL_BASE_ENDPOINT = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}"


# --- ROTA DE IMAGEM ATUALIZADA ---
@app.route('/images/<path:filename>')
def serve_image(filename):
    # ATENÇÃO: Verifique se sua pasta de imagens está no mesmo nível de 'app.py'
    return send_from_directory('image', filename)

# --- (FUNÇÃO ATUALIZADA PARA Z-API) ---
def enviar_mensagem_whatsapp(para, resposta_dict):
    """
    Envia a resposta (texto e/ou média) para o cliente usando a Z-API.
    """
    try:
        media_urls = resposta_dict.get('media', [])
        body_text = resposta_dict.get('body', '')
        # Pega a flag, o padrão é False se não existir
        usar_legenda = resposta_dict.get('usar_legenda', False) 
        
        # LIMPE O NÚMERO: A Z-API espera DDI DDD NÚMERO (ex: 551199999999)
        numero_limpo = para.replace('whatsapp:', '').replace('+', '').strip()

        headers = {'Content-Type': 'application/json'}
        
        # --- CENÁRIO 1 & 2: MÍDIA (Imagem) ---
        if media_urls:
            
             # --- CENÁRIO 1: USAR LEGENDA (Imagem com legenda) ---
             if usar_legenda:
                # 1. Envia a PRIMEIRA imagem com legenda
                url_send_image = f"{ZAPI_URL_BASE_ENDPOINT}/send-image" 
                payload = {
                     "phone": numero_limpo,
                     "image": media_urls[0],
                     "caption": body_text
                }
                response = requests.post(url_send_image, headers=headers, json=payload)
                print(f"DEBUG ZAPI ENVIO IMAGEM (CENÁRIO 1): Status {response.status_code}, Resposta: {response.text}")
                
                # 2. Envia as imagens restantes SEM legenda
                for url_media in media_urls[1:]:
                    url_send_image = f"{ZAPI_URL_BASE_ENDPOINT}/send-image" 
                    payload = {
                         "phone": numero_limpo,
                         "image": url_media
                    }
                    response = requests.post(url_send_image, headers=headers, json=payload)
                    print(f"DEBUG ZAPI ENVIO IMAGEM RESTANTE (CENÁRIO 1): Status {response.status_code}, Resposta: {response.text}")
        
            # --- CENÁRIO 2: NÃO USAR LEGENDA (Imagens primeiro, texto separado depois) ---
             else:
                # 1. Envia TODAS as imagens, UMA POR UMA, sem legenda
                for url_media in media_urls:
                    url_send_image = f"{ZAPI_URL_BASE_ENDPOINT}/send-image" 
                    payload = {
                         "phone": numero_limpo,
                         "image": url_media
                    }
                    response = requests.post(url_send_image, headers=headers, json=payload)
                    print(f"DEBUG ZAPI ENVIO IMAGEM (CENÁRIO 2): Status {response.status_code}, Resposta: {response.text}")

                    # 2. Adiciona um pequeno delay (ex: 5.5 segundos)
                    time.sleep(5.5) 

                # 3. Se houver texto, envia como uma mensagem SEPARADA
                if body_text:
                    url_send_text = f"{ZAPI_URL_BASE_ENDPOINT}/send-text"
                    payload_text = {
                        "phone": numero_limpo,
                        "message": body_text
                    }
                    response = requests.post(url_send_text, headers=headers, json=payload_text)
                    print(f"DEBUG ZAPI ENVIO TEXTO (CENÁRIO 2): Status {response.status_code}, Resposta: {response.text}")

        # --- CENÁRIO 3: SÓ TEXTO (Se não tem mídia, mas tem texto) ---
        elif body_text:
             url_send_text = f"{ZAPI_URL_BASE_ENDPOINT}/send-text"
             payload_text = {
                "phone": numero_limpo,
                "message": body_text
             }
             response = requests.post(url_send_text, headers=headers, json=payload_text)
             print(f"DEBUG ZAPI ENVIO SÓ TEXTO: Status {response.status_code}, Resposta: {response.text}")


    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")


# --- ROTA DE RECEBIMENTO (WEBHOOK) ATUALIZADA PARA Z-API ---
@app.route('/whatsapp', methods=['POST'])
def webhook_whatsapp():
    # A Z-API envia dados como JSON
    dados_recebidos = request.get_json() 
    mensagem_recebida = ""
    numero_cliente = ""

    # LÓGICA DE EXTRAÇÃO DE MENSAGEM (CORRIGIDA E ROBUSTA)
    try:
        # Tenta extrair o número do remetente
        numero_cliente = dados_recebidos.get('phone', '') # Primeira tentativa
        
        # 1. Tenta extrair de uma estrutura de array de mensagens (estrutura comum)
        if dados_recebidos and dados_recebidos.get('messages'):
             primeira_mensagem = dados_recebidos['messages'][0]
             
             # Se o número não foi pego no root, tenta pegar da mensagem
             if not numero_cliente:
                 numero_cliente = primeira_mensagem.get('phone', '')

             # Garante que estamos pegando a string de texto
             if primeira_mensagem.get('text'):
                  mensagem_conteudo = primeira_mensagem.get('text', {}).get('message', '') 
                  if isinstance(mensagem_conteudo, str):
                       mensagem_recebida = mensagem_conteudo
        
        # 2. Tenta extrair de uma estrutura de webhook mais simples/direta
        elif dados_recebidos and dados_recebidos.get('text'):
             mensagem_conteudo = dados_recebidos.get('text', '')
             if isinstance(mensagem_conteudo, str):
                 mensagem_recebida = mensagem_conteudo
             elif isinstance(mensagem_conteudo, dict) and mensagem_conteudo.get('message'): 
                 mensagem_recebida = mensagem_conteudo.get('message', '')
             
             if not numero_cliente:
                 numero_cliente = dados_recebidos.get('phone', '')
             
        # 3. Se for evento de status/outro, ignora
        else:
             return ('', 200)

        # 4. GARANTE QUE A MENSAGEM É UMA STRING E NÃO É VAZIA antes de processar
        if isinstance(mensagem_recebida, str) and mensagem_recebida.strip():
             mensagem_recebida = mensagem_recebida.lower().strip()
        else:
             return ('', 200)
             
    except Exception as e:
        # Se ocorrer qualquer outro erro inesperado na extração
        print(f"ERRO CRÍTICO ao processar JSON do Webhook da Z-API: {e}")
        return ('', 200)

    # O código continua aqui SOMENTE se tivermos uma mensagem válida
    print(f"Mensagem de '{numero_cliente}': '{mensagem_recebida}'")

    resposta_dict = processar_mensagem(mensagem_recebida, numero_cliente)
    
    # Envio da Resposta (usando a função Z-API atualizada)
    enviar_mensagem_whatsapp(numero_cliente, resposta_dict)

    return ('', 200)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
