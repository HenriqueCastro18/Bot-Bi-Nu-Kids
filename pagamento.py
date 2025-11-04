# pagamento.py
import mercadopago
import config
import uuid
import json # <-- 1. IMPORTAR JSON
from catalogo import BASE_URL 

# Configura o SDK do Mercado Pago com seu token
sdk = mercadopago.SDK(config.MP_ACCESS_TOKEN)

# --- 2. MODIFICAR A FUNÇÃO para aceitar 'chat_id' e 'event_id' ---
def criar_link_pagamento_sinal(titulo_reserva: str, valor_total_carrinho: float, chat_id: str, event_id: str):
    """
    Cria um link de pagamento no Mercado Pago para 50% (sinal) do valor total.
    (NOVO) Salva um JSON com chat_id E event_id na referência externa.
    """
    try:
        valor_sinal = round(valor_total_carrinho / 2.0, 2)
        
        # 3. CONSTRUIR O NOSSO URL DE WEBHOOK
        url_de_notificacao = f"{BASE_URL}/webhook/mercadopago"
        
        # --- (NOVO) Cria o JSON para a referência ---
        external_reference_data = json.dumps({
            "chat_id": chat_id,
            "event_id": event_id
        })
        print(f"Gerando link para: {external_reference_data}")
        # --- Fim da Atualização ---

        preference_data = {
            "items": [
                {
                    "title": titulo_reserva,
                    "quantity": 1,
                    "unit_price": valor_sinal,
                    "currency_id": "BRL"
                }
            ],
            "notification_url": url_de_notificacao,
            # --- (ATUALIZADO) Passa o JSON como referência ---
            "external_reference": external_reference_data, 
            "purpose": "wallet_purchase",
            "back_urls": {
                "success": "https://www.google.com", 
                "failure": "https://www.google.com",
                "pending": "https://www.google.com"
            },
            "auto_return": "approved"
        }

        preference_response = sdk.preference().create(preference_data)
        
        if preference_response and "response" in preference_response and "init_point" in preference_response["response"]:
            link_pagamento = preference_response["response"]["init_point"]
            print(f"Link de pagamento gerado ({external_reference_data}): {link_pagamento}")
            return link_pagamento
        else:
            print(f"Erro na resposta da API do Mercado Pago: {preference_response}")
            return None

    except Exception as e:
        print(f"ERRO ao criar link de pagamento: {e}")
        return None