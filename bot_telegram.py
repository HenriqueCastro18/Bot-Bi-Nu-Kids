# bot_telegram.py (Versão ATUALIZADA para v20+, COM DEBUG, BOTÕES e DB)
import logging
import time
import asyncio # Necessário para a v20+

# --- MUDANÇAS DE IMPORTAÇÃO (v20+) ---
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler 
)

# --- Nossas Importações (do seu projeto) ---
from config import TELEGRAM_TOKEN
from logic import processar_mensagem

# --- (NOVO) Import das funções de estado do DB ---
from database import (
    db_carregar_estado_usuario,
    db_salvar_estado_usuario,
    db_deletar_estado_usuario
)
# ------------------------------------------

# Configura o logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Função de envio (Inalterada da última vez) ---
async def enviar_resposta_telegram(context: ContextTypes.DEFAULT_TYPE, chat_id: int, resposta_dict: dict):
    """
    Interpreta o dicionário de resposta do logic.py e envia para o Telegram.
    (ATUALIZADO) Agora desenha botões.
    """
    media_urls = resposta_dict.get('media', [])
    body_text = resposta_dict.get('body', '')
    usar_legenda = resposta_dict.get('usar_legenda', False)

    # --- (LÓGICA DE BOTÕES) ---
    keyboard = None
    botoes_menu = resposta_dict.get('menu_opcoes')
    botoes_rapidos = resposta_dict.get('quick_replies')
    
    if botoes_menu:
        botoes_telegram = [
            [InlineKeyboardButton(opt['titulo'], callback_data=opt['id'])] for opt in botoes_menu
        ]
        keyboard = InlineKeyboardMarkup(botoes_telegram)
        
    elif botoes_rapidos:
        botoes_telegram = [
            InlineKeyboardButton(opt.capitalize(), callback_data=opt) for opt in botoes_rapidos
        ]
        keyboard = InlineKeyboardMarkup([botoes_telegram])
    # --- FIM DA LÓGICA DE BOTÕES ---

    if media_urls:
        print(f"\n[DEBUG] URL da imagem que estou tentando enviar: {media_urls[0]}\n")

    try:
        if media_urls:
            # Cenário 1: Mídia com legenda (caption)
            if usar_legenda and body_text:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=media_urls[0],
                    caption=body_text,
                    reply_markup=keyboard 
                )
                for url in media_urls[1:]:
                    await context.bot.send_photo(chat_id=chat_id, photo=url)
            
            # Cenário 2: Mídia e texto separados
            else:
                for url in media_urls:
                    await context.bot.send_photo(chat_id=chat_id, photo=url)
                
                await asyncio.sleep(1) 

                if body_text:
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text=body_text,
                        reply_markup=keyboard 
                    )
        
        # Cenário 3: Só texto (com os botões)
        elif body_text:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=body_text,
                reply_markup=keyboard 
            )

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem Telegram para {chat_id}: {e}")
        try:
            await context.bot.send_message(chat_id=chat_id, text="Ocorreu um erro ao processar sua solicitação de mídia.")
        except Exception:
            pass

# --- Handler de mensagem (ATUALIZADO com lógica de DB) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processa todas as mensagens de TEXTO recebidas.
    """
    mensagem_recebida = update.message.text.lower().strip()
    chat_id = update.message.chat_id
    numero_cliente_telegram = str(chat_id)
    
    print(f"Mensagem [Texto] de '{numero_cliente_telegram}': '{mensagem_recebida}'") # Log

    # --- (NOVA LÓGICA DE ESTADO) ---
    # 1. Carrega o estado atual do usuário do DB
    estado_info = db_carregar_estado_usuario(numero_cliente_telegram)

    # 2. Chama o logic.py (agora passando o estado)
    resposta_dict, estado_info_atualizado = processar_mensagem(
        mensagem_recebida, 
        numero_cliente_telegram,
        estado_info # Passa o estado carregado
    )
    
    # 3. Salva o novo estado de volta no DB
    if estado_info_atualizado.get('estado') is None:
        # Se o logic zerou o estado (ex: voltou ao menu), deletamos do DB
        db_deletar_estado_usuario(numero_cliente_telegram)
    else:
        # Senão, salvamos a atualização
        db_salvar_estado_usuario(numero_cliente_telegram, estado_info_atualizado)
    # --- (FIM DA NOVA LÓGICA DE ESTADO) ---

    # 4. Envia a resposta (agora com botões)
    await enviar_resposta_telegram(context, chat_id, resposta_dict)

# --- Handler de cliques (ATUALIZADO com lógica de DB) ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa todos os cliques em botões (CallbackQuery)."""
    query = update.callback_query
    await query.answer() 
    
    mensagem_recebida = query.data.lower().strip() 
    chat_id = query.message.chat_id
    numero_cliente_telegram = str(chat_id)
    
    print(f"Clique [Botão] de '{numero_cliente_telegram}': '{mensagem_recebida}'") # Log

    # --- (NOVA LÓGICA DE ESTADO) ---
    # 1. Carrega o estado atual do usuário do DB
    estado_info = db_carregar_estado_usuario(numero_cliente_telegram)

    # 2. Envia o clique para o logic.py (como se fosse texto)
    resposta_dict, estado_info_atualizado = processar_mensagem(
        mensagem_recebida, 
        numero_cliente_telegram,
        estado_info # Passa o estado carregado
    )
    
    # 3. Salva o novo estado de volta no DB
    if estado_info_atualizado.get('estado') is None:
        db_deletar_estado_usuario(numero_cliente_telegram)
    else:
        db_salvar_estado_usuario(numero_cliente_telegram, estado_info_atualizado)
    # --- (FIM DA NOVA LÓGICA DE ESTADO) ---
    
    # 4. Envia a nova resposta
    await enviar_resposta_telegram(context, chat_id, resposta_dict)

# --- Handler /start (ATUALIZADO com lógica de DB) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia a mensagem de /start e simula a primeira mensagem 'oi'."""
    chat_id = update.message.chat_id
    numero_cliente_telegram = str(chat_id)

    await update.message.reply_text(
        "Olá! ✨ Bem-vindo(a) ao mundo mágico da BI & NU Kids! ✨\n"
        "Enviando o menu principal..."
    )
    
    # --- (NOVA LÓGICA DE ESTADO) ---
    # 1. Carrega o estado (que provavelmente estará vazio/novo)
    estado_info = db_carregar_estado_usuario(numero_cliente_telegram)

    # 2. Simula o início da conversa chamando o processar_mensagem com "oi"
    resposta_dict, estado_info_atualizado = processar_mensagem(
        "oi", 
        numero_cliente_telegram,
        estado_info
    )
    
    # 3. Salva o estado inicial (que agora é 'aguardando_tipo_reserva')
    db_salvar_estado_usuario(numero_cliente_telegram, estado_info_atualizado)
    # --- (FIM DA NOVA LÓGICA DE ESTADO) ---

    await enviar_resposta_telegram(context, chat_id, resposta_dict)

# --- Função Principal (Inalterada da última vez) ---
def main():
    """Inicia o bot do Telegram."""
    
    print("Iniciando o bot (v20+)...")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registra os Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot do Telegram iniciado. Pressione Ctrl+C para parar.")
    application.run_polling()


if __name__ == '__main__':
    main()