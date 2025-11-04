# logic.py
import locale
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
import googlemaps
import math 
import re 
import json 
import threading 

from agenda import (
    verificar_horarios_disponiveis,
    marcar_horario,
    verificar_dias_disponiveis,
    buscar_eventos_por_cpf, 
    cancelar_evento,       
    remarcar_evento,
    confirmar_pagamento_evento 
)

from database import (
    inicializar_banco,
    registrar_venda,
    cancelar_venda_por_id,
    atualizar_data_horario_venda,
    atualizar_status_pagamento,
)

from pagamento import criar_link_pagamento_sinal

# --- (NOVOS IMPORTS) ---
import excel_sync       # Importa o módulo de sync
import email_sender     # Importa o novo módulo de email

# --- (NOVO) IMPORTAÇÃO DO CATÁLOGO ---
from catalogo import (
    BASE_URL,  # URL base para imagens
    ITENS_BRINQUEDOS_G,
    ITENS_KIT_BABY,
    ITENS_BRINQUEDOS_M,
    ITENS_BRINQUEDOS_P,
    CATALOGO_COMBOS,
    DEFINICOES_COMBOS,
    CATALOGO_AVULSOS_CATEGORIZADO,
    CATALOGO_AVULSOS  # Lista única de avulsos
)
# ------------------------------------

# --- (NOVO) IMPORT DA CHAVE DE API ---
from config import GOOGLE_MAPS_API_KEY
# ------------------------------------


try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    print("Locale pt_BR.UTF-8 não encontrado, usando locale padrão.")

nomes_meses = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# ==============================================================================
# --- (NOVO) CONFIGURAÇÕES DE CUSTO DE COMBUSTÍVEL ---
# ==============================================================================
PRECO_GASOLINA_LITRO = 5.60 # R$ 5,60
CONSUMO_CARRO_KM_L = 3.5  # 3.5 km/L
# ==============================================================================

# ==============================================================================
# --- CONFIGURAÇÃO DO FRETE (GOOGLE MAPS) ---
# ==============================================================================
ENDERECO_ORIGEM = "Praça Francisca de Campo Melo Freire, 1 - Parque Monte Libano, Mogi das Cruzes - SP, 08780-310"
# ==============================================================================

# Inicializa o cliente do Google Maps
try:
    if GOOGLE_MAPS_API_KEY != "COLE_SUA_CHAVE_DE_API_AQUI" and GOOGLE_MAPS_API_KEY != "":
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    else:
        gmaps = None
        print("AVISO: Chave da API do Google Maps não configurada. Cálculo de frete desativado.")
except Exception as e:
    print(f"Erro ao inicializar o Google Maps. Verifique sua chave de API: {e}")
    gmaps = None

# --- INICIALIZA O BANCO DE DADOS ---
inicializar_banco() 
# -----------------------------------

# --- (NOVA FUNÇÃO HELPER) ---
def disparar_envio_planilha():
    """
    Função para rodar em segundo plano (thread).
    (ATUALIZADO) Só envia email se a sincronização funcionar.
    """
    try:
        print("THREAD: Iniciando envio de planilha por email...")
        
        sucesso_sync = excel_sync.sincronizar_db_para_excel() 
        
        if not sucesso_sync:
            print("THREAD: Sincronização do Excel falhou (provavelmente arquivo aberto). Email NÃO será enviado.")
            return # Aborta a thread
            
        sucesso_email, erro = email_sender.enviar_planilha_por_email()
        if sucesso_email:
            print("THREAD: Planilha enviada por email com sucesso.")
        else:
            print(f"THREAD: Falha ao enviar email: {erro}")
            
    except Exception as e:
        print(f"THREAD: Erro na thread de envio de email: {e}")
# ----------------------------


# --- FUNÇÃO AUXILIAR PARA SINCRONIZAR EM SEGUNDO PLANO ---
def iniciar_sincronizacao_excel():
    """Inicia a sincronização do DB para o Excel em uma thread separada."""
    print("Disparando thread de sincronização (Calendar -> DB -> Excel)...")
    sync_thread = threading.Thread(target=excel_sync.sincronizar_db_para_excel, daemon=True)
    sync_thread.start()
# -----------------------------------------------------------

def formatar_reais(valor: float) -> str:
    """Formata um valor float para o padrão R$ X.XXX,XX"""
    try:
        formatado_en = f"{valor:,.2f}"
        temp_swap = formatado_en.replace(',', '_')
        com_virgula = temp_swap.replace('.', ',')
        formatado_br = com_virgula.replace('_', '.')
        return formatado_br
    except Exception:
        return f"{valor:.2f}"

def formatar_cpf(cpf_numeros: str) -> str:
    """Formata uma string de 11 dígitos de CPF para XXX.XXX.XXX-XX."""
    if not cpf_numeros or len(cpf_numeros) != 11 or not cpf_numeros.isdigit():
        return cpf_numeros
    return f"{cpf_numeros[0:3]}.{cpf_numeros[3:6]}.{cpf_numeros[6:9]}-{cpf_numeros[9:11]}"

# ==============================================================================
# --- FUNÇÕES DE FRETE (GOOGLE MAPS) ---
# ==============================================================================

def calcular_distancia_google(origem, destino):
    """Calcula a distância de condução usando a API do Google Maps."""
    if gmaps is None:
        print("Cliente Google Maps não inicializado. Verifique a API Key.")
        return None
    try:
        directions_result = gmaps.directions(origem,
                                             destino,
                                             mode="driving",
                                             departure_time=datetime.now())
        if directions_result and 'legs' in directions_result[0] and directions_result[0]['legs']:
            leg = directions_result[0]['legs'][0]
            distancia_texto = leg['distance']['text']
            distancia_metros = leg['distance']['value']
            distancia_km = distancia_metros / 1000.0
            return {'texto': distancia_texto, 'km': distancia_km}
        else:
            print("Não foi possível extrair a distância da resposta do Google Maps.")
            return None
    except Exception as e:
        print(f"Erro ao calcular distância: {e}")
        return None

def calcular_preco_frete(distancia_km, carrinho):
    """Calcula o preço do frete com base na distância e nos itens do carrinho."""
    tem_combo = any(item.get('id') in [101, 102, 103] for item in carrinho)

    if tem_combo:
        if distancia_km <= 60:
            return 0.0
        else:
            km_excedente = distancia_km - 60
            PRECO_POR_KM_EXCEDENTE = 3.50
            preco_final = km_excedente * PRECO_POR_KM_EXCEDENTE
            return preco_final
    else:
        if distancia_km < 20:
            return 0.0 

        TAXA_BASE = 15.00
        PRECO_POR_KM = 3.50
        km_arredondado = math.ceil(distancia_km)
        preco_um_trecho = TAXA_BASE + (km_arredondado * PRECO_POR_KM)

        if preco_um_trecho < 25.00:
            preco_um_trecho = 25.00

        preco_final_ida_e_volta = preco_um_trecho * 2
        return preco_final_ida_e_volta

# ==============================================================================
# --- FUNÇÕES DO CARRINHO DE COMPRAS ---
# ==============================================================================

def calcular_total(carrinho):
    """Calcula o total (PREÇO) dos itens no carrinho (sem frete)."""
    total = 0.0
    for item in carrinho:
        try:
            preco_str = item['preco'].replace('R$', '').replace('.', '').replace(',', '.').strip()
            if 'partir' in preco_str:
                preco_str = preco_str.split()[-1]
            total += float(preco_str)
        except (ValueError, IndexError, KeyError):
            continue
    return total

def calcular_custo_total(carrinho):
    """Calcula o CUSTO total dos itens no carrinho."""
    total = 0.0
    for item in carrinho:
        try:
            custo_str = item['custo'].replace('R$', '').replace('.', '').replace(',', '.').strip()
            if 'partir' in custo_str:
                custo_str = custo_str.split()[-1]
            total += float(custo_str)
        except (ValueError, IndexError, KeyError):
            print(f"Aviso: Item {item.get('nome')} sem chave 'custo' definida.")
            continue
    return total

def adicionar_ao_carrinho(mensagem, numero_cliente, resposta, estado_info):
    """Adiciona itens AVULSOS por ID ao carrinho."""
    partes = mensagem.lower().split()
    if len(partes) < 2 or partes[0] != 'carrinho':
        resposta['body'] = "Comando inválido. Para adicionar, use `carrinho <ID1> <ID2>...`."
        return resposta, estado_info
    
    carrinho_atual = estado_info.get('carrinho', [])
    itens_adicionados_nomes = []
    erros_adicionar = []

    ids_para_adicionar_str = partes[1:]
    for id_str in ids_para_adicionar_str:
        try:
            item_id = int(id_str)
            item_para_add = next((item for item in CATALOGO_AVULSOS if item['id'] == item_id), None)

            if item_para_add:
                if any(item['id'] == item_para_add['id'] for item in carrinho_atual):
                    erros_adicionar.append(f"*{item_para_add['nome']}* (ID: {item_id}) já está no carrinho.")
                else:
                    carrinho_atual.append(item_para_add)
                    itens_adicionados_nomes.append(f"*{item_para_add['nome']}* (ID: {item_id})")
            else:
                erros_adicionar.append(f"Item com ID *{item_id}* não encontrado.")
        except ValueError:
            erros_adicionar.append(f"'{id_str}' não é um ID válido.")
            
    texto_resposta = ""
    if itens_adicionados_nomes:
        texto_resposta += "✅ Itens adicionados:\n" + "\n".join(itens_adicionados_nomes) + "\n"
    if erros_adicionar:
        texto_resposta += "\n⚠️ Atenção:\n" + "\n".join(erros_adicionar) + "\n"
    
    estado_info['carrinho'] = carrinho_atual
    resposta['body'] = texto_resposta.strip()
    return mostrar_carrinho(numero_cliente, resposta, estado_info)

def remover_do_carrinho(mensagem, numero_cliente, resposta, estado_info):
    try:
        item_id = int(mensagem.split(" ")[1])
        carrinho_atual = estado_info.get('carrinho', [])
        item_para_remover = next((item for item in carrinho_atual if item['id'] == item_id), None)
        if item_para_remover:
            carrinho_atual = [item for item in carrinho_atual if item['id'] != item_id]
            estado_info['carrinho'] = carrinho_atual
            resposta['body'] = f"*{item_para_remover['nome']}* foi removido do seu carrinho."
            return mostrar_carrinho(numero_cliente, resposta, estado_info)
        else:
            resposta['body'] = "Este item não está no seu carrinho. 🤔"
            return mostrar_carrinho(numero_cliente, resposta, estado_info)
    except (ValueError, IndexError):
        resposta['body'] = "Comando inválido. Para remover, use `remover <ID>` (ex: `remover 25`)."
        return resposta, estado_info

def mostrar_carrinho(numero_cliente, resposta, estado_info):
    """Mostra o carrinho de compras."""
    carrinho = estado_info.get('carrinho', [])
    texto_carrinho = "🛒 *Seu Carrinho de Compras*\n\n"
    if not carrinho:
        texto_carrinho += "Seu carrinho está vazio.\n\n"
    else:
        for item in carrinho:
            if 'descricao_custom' in item:
                texto_carrinho += f"*{item['id']}* - {item['nome']} ({item['preco']})\n"
                for etapa_nome, itens_escolhidos in item['descricao_custom'].items():
                    if itens_escolhidos:
                        itens_formatados = ", ".join(itens_escolhidos)
                        texto_carrinho += f"   └ _{etapa_nome}:_ {itens_formatados}\n"
            else:
                texto_carrinho += f"*{item['id']}* - {item['nome']} ({item['preco']})\n"
                
        total_itens = calcular_total(carrinho)
        texto_carrinho += f"\n*Total dos Itens:* R$ {formatar_reais(total_itens)}\n"
        frete_valor = estado_info.get('frete_valor', -1.0)
        
        if frete_valor >= 0:
            total_geral = total_itens + frete_valor
            if frete_valor == 0.0 and total_itens > 0:
                 texto_carrinho += f"🚚 *Frete:* Grátis\n"
            else:
                 texto_carrinho += f"🚚 *Frete:* R$ {formatar_reais(frete_valor)}\n"
            texto_carrinho += f"--------------------\n"
            texto_carrinho += f"TOTAL: *R$ {formatar_reais(total_geral)}*\n"
            
        texto_carrinho += "\n---\n"
        texto_carrinho += "Para remover um item, digite `remover <ID>`.\n"
        
    corpo_atual = resposta.get('body', '')
    if "🛒 *Seu Carrinho de Compras*" not in corpo_atual:
        if corpo_atual:
            resposta['body'] += "\n\n" + texto_carrinho
        else:
            resposta['body'] = texto_carrinho
            
    if not carrinho:
        resposta['quick_replies'] = ['voltar']
    else:
        resposta['quick_replies'] = ['finalizar pedido', 'voltar']
        
    return resposta, estado_info


# ==============================================================================
# --- FUNÇÕES DE CONSTRUÇÃO DE COMBO ---
# ==============================================================================

def iniciar_etapa_combo(numero_cliente: str, resposta: dict, estado_info: dict):
    """Envia as imagens e instruções para a etapa atual de construção do combo."""
    try:
        combo_info = estado_info['combo_em_construcao']
        etapa_atual_idx = combo_info['etapa_idx']
        
        etapa_definicao = DEFINICOES_COMBOS[combo_info['tipo_combo_id']]['etapas'][etapa_atual_idx]

        limite_itens = etapa_definicao['limite']
        ids_categorias = etapa_definicao['id_cat']
        
        combo_info['etapa_atual'] = etapa_definicao
        
        imagens_para_enviar = []
        nomes_categorias = []
        combo_types_cache = CATALOGO_COMBOS.get('tipos', [])
        
        for cat_id in ids_categorias:
            tipo_encontrado = next((tipo for tipo in combo_types_cache if tipo['id'] == cat_id), None)
            if tipo_encontrado:
                imagens_para_enviar.extend(tipo_encontrado.get('imagens_urls', []))
                nomes_categorias.append(tipo_encontrado['nome'])

        texto_listas_opcoes = ""
        current_index = 1

        if 1 in ids_categorias:
            lista_formatada = "*LISTA DE OPÇÕES (Brinquedos G):*\n"
            lista_formatada += "\n".join([f"*{current_index + i}* - {item}" for i, item in enumerate(ITENS_BRINQUEDOS_G)])
            texto_listas_opcoes += lista_formatada + "\n\n"
            current_index += len(ITENS_BRINQUEDOS_G)
        
        if 4 in ids_categorias:
            lista_formatada = "*LISTA DE OPÇÕES (Kit Baby):*\n"
            lista_formatada += "\n".join([f"*{current_index + i}* - {item}" for i, item in enumerate(ITENS_KIT_BABY)])
            texto_listas_opcoes += lista_formatada + "\n\n"
            current_index += len(ITENS_KIT_BABY)
        
        if 2 in ids_categorias:
            lista_formatada = "*LISTA DE OPÇÕES (Brinquedos M):*\n"
            lista_formatada += "\n".join([f"*{current_index + i}* - {item}" for i, item in enumerate(ITENS_BRINQUEDOS_M)])
            texto_listas_opcoes += lista_formatada + "\n\n"
            current_index += len(ITENS_BRINQUEDOS_M)
            
        if 3 in ids_categorias:
            lista_formatada = "*LISTA DE OPÇÕES (Brinquedos P):*\n"
            lista_formatada += "\n".join([f"*{current_index + i}* - {item}" for i, item in enumerate(ITENS_BRINQUEDOS_P)])
            texto_listas_opcoes += lista_formatada + "\n\n"
            current_index += len(ITENS_BRINQUEDOS_P)
        
        nomes_formatados = " / ".join(nomes_categorias)
        texto_etapa = (
            f"Vamos montar seu *{combo_info['nome']}*!\n\n"
            f"--- ETAPA {etapa_atual_idx + 1} de {len(DEFINICOES_COMBOS[combo_info['tipo_combo_id']]['etapas'])} ---\n"
            f"*{nomes_formatados}*\n\n"
            f"Você precisa escolher *{limite_itens} itens* desta(s) categoria(s).\n\n"
            f"{texto_listas_opcoes.strip()}"
            "\n\nDigite *apenas os números* dos itens que você quer (ex: `1 5 10`)."
        )
        
        resposta['media'] = imagens_para_enviar
        resposta['body'] = texto_etapa
        return resposta, estado_info

    except Exception as e:
        print(f"Erro em iniciar_etapa_combo: {e}")
        resposta['body'] = "Ocorreu um erro ao iniciar a montagem do combo. 😕 Tente novamente ou digite *voltar*."
        return resposta, estado_info

def avancar_etapa_combo(numero_cliente: str, resposta: dict, estado_info: dict):
    """Move para a próxima etapa ou finaliza a construção do combo."""
    combo_info = estado_info['combo_em_construcao']
    
    combo_info['etapa_idx'] += 1
    
    total_etapas = len(DEFINICOES_COMBOS[combo_info['tipo_combo_id']]['etapas'])
    
    if combo_info['etapa_idx'] < total_etapas:
        estado_info['estado'] = 'construindo_combo'
        return iniciar_etapa_combo(numero_cliente, resposta, estado_info)
    else:
        carrinho_atual = estado_info.get('carrinho', [])
        
        item_combo_final = {
            'id': combo_info['id'],
            'nome': combo_info['nome'],
            'preco': combo_info['preco'],
            'custo': combo_info['custo'], 
            'descricao_custom': combo_info['itens_escolhidos']
        }
        
        carrinho_filtrado = [item for item in carrinho_atual if item['id'] != item_combo_final['id']]
        carrinho_filtrado.append(item_combo_final) 
        
        estado_info['carrinho'] = carrinho_filtrado
        resposta['body'] = f"🎉 Woohoo! *{item_combo_final['nome']}* foi montado e adicionado ao seu carrinho!"

        del estado_info['combo_em_construcao']
        estado_info['estado'] = 'aguardando_tipo_reserva'
        return mostrar_carrinho(numero_cliente, resposta, estado_info)

def obter_opcoes_etapa_atual(combo_info):
    """
    Retorna uma lista com todos os nomes de itens disponíveis para a etapa atual.
    """
    etapa_definicao = DEFINICOES_COMBOS[combo_info['tipo_combo_id']]['etapas'][combo_info['etapa_idx']]
    ids_categorias = etapa_definicao['id_cat']
    
    opcoes = []
    
    if 1 in ids_categorias:
        opcoes.extend(ITENS_BRINQUEDOS_G)
    if 4 in ids_categorias:
        opcoes.extend(ITENS_KIT_BABY)
    if 2 in ids_categorias:
        opcoes.extend(ITENS_BRINQUEDOS_M)
    if 3 in ids_categorias:
        opcoes.extend(ITENS_BRINQUEDOS_P)
    
    return opcoes

# ==============================================================================
# --- LÓGICA PRINCIPAL (PROCESSAR MENSAGEM) ---
# ==============================================================================

def processar_mensagem(mensagem, numero_cliente, estado_info: dict):
    
    mensagem_lower = mensagem.lower().strip()
    resposta = {'body': '', 'media': []}

    estado_atual = estado_info.get('estado')
    saudacoes = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "começar", "opa"]
    
    if estado_atual is None or mensagem_lower in saudacoes:
        if 'combo_em_construcao' in estado_info:
              del estado_info['combo_em_construcao']
        if 'evento_para_gerenciar' in estado_info:
             del estado_info['evento_para_gerenciar']
        if 'lista_eventos_gerenciar' in estado_info:
             del estado_info['lista_eventos_gerenciar']
        if 'pending_event_id' in estado_info:
             del estado_info['pending_event_id']
             
        estado_info.update({'estado': 'aguardando_tipo_reserva', 'carrinho': [], 'frete_valor': -1.0})
        
        resposta_final = menu_principal(resposta)
        return resposta_final, estado_info
    
    if mensagem_lower == "mandar custo":
        resposta['body'] = "Ok! 👍\n\nEstou gerando o relatório financeiro atualizado e enviando para o seu email. Pode levar alguns segundos..."
        envio_thread = threading.Thread(target=disparar_envio_planilha, daemon=True)
        envio_thread.start()
        return resposta, estado_info 
    
    # --- Comandos Globais ---
    if mensagem_lower.startswith("carrinho "):
        return adicionar_ao_carrinho(mensagem, numero_cliente, resposta, estado_info)
        
    elif mensagem_lower.startswith("remover "):
        return remover_do_carrinho(mensagem, numero_cliente, resposta, estado_info)
        
    elif mensagem_lower in ["ver carrinho", "meu carrinho", "carrinho"]:
        return mostrar_carrinho(numero_cliente, resposta, estado_info)
        
    elif mensagem_lower in ["finalizar", "finalizar pedido", "agendar"]:
        if not estado_info.get('carrinho'):
            resposta['body'] = "Seu carrinho está vazio! Adicione pelo menos um item antes de finalizar o pedido."
            resposta['quick_replies'] = ['voltar'] 
            return resposta, estado_info
            
        estado_info['frete_valor'] = -1.0
        estado_info['distancia_km'] = 0.0 
        estado_info['estado'] = 'coletando_cep'
        resposta['body'] = "Vamos finalizar seu pedido! 🎉\n\nPara maior precisão no cálculo do frete, por favor, me informe o *CEP* do local da festa."
        return resposta, estado_info
    
    # --- Fluxo: Menu Principal ---
    elif estado_atual == 'aguardando_tipo_reserva':
        if "voltar" in mensagem_lower:
            return menu_principal(resposta), estado_info
        
        if mensagem_lower == '1':
            estado_info['estado'] = 'aguardando_categoria_avulsos'
            categorias = list(CATALOGO_AVULSOS_CATEGORIZADO.keys())
            estado_info['categorias_cache'] = categorias
            
            texto_menu = (
                "Você escolheu *Brinquedos Avulsos*! 🧸\n\n"
                "Para adicionar um item direto pelo ID, digite `carrinho <número>` (ex: `carrinho 24`).\n\n"
                "Ou, escolha uma categoria abaixo para explorar:"
            )
            resposta['body'] = texto_menu
            
            menu_opcoes = [{"id": "1", "titulo": "1️⃣ Ver Catálogo Completo"}]
            for i, categoria in enumerate(categorias):
                menu_opcoes.append({"id": str(i + 2), "titulo": f"{(i + 2)}️⃣ {categoria}"})
            menu_opcoes.append({"id": "voltar", "titulo": "🔙 Voltar"})
            resposta['menu_opcoes'] = menu_opcoes
            
            return resposta, estado_info
            
        elif mensagem_lower == '2':
            estado_info['estado'] = 'aguardando_escolha_combo_tipo'
            resposta['media'] = CATALOGO_COMBOS['geral']['imagem_url']
            resposta['usar_legenda'] = True 
            
            texto_menu_combo = (
                "Você escolheu os *Combos Mágicos*! 🎁\n\n"
                "Baseado na imagem, qual combo você gostaria de *montar*?"
            )
            resposta['body'] = texto_menu_combo
            
            resposta['menu_opcoes'] = [
                {"id": "1", "titulo": f"1️⃣ Combo 1 ({DEFINICOES_COMBOS['1']['preco']})"},
                {"id": "2", "titulo": f"2️⃣ Combo 2 ({DEFINICOES_COMBOS['2']['preco']})"},
                {"id": "3", "titulo": f"3️⃣ Combo 3 ({DEFINICOES_COMBOS['3']['preco']})"},
                {"id": "voltar", "titulo": "🔙 Voltar"}
            ]
            
            return resposta, estado_info
            
        elif mensagem_lower == '3':
            estado_info['estado'] = 'pedindo_cpf_para_gerenciar'
            resposta['body'] = ("Ok, vamos gerenciar sua reserva. ✏️\n\n"
                              "Por favor, digite o *CPF* (apenas números) que foi usado para fazer o agendamento.")
            return resposta, estado_info
        else:
            resposta['body'] = "Opção inválida 😕. Por favor, escolha uma das opções."
            retorno = menu_principal(resposta)
            return retorno, estado_info

    # --- Fluxo: Montagem de Combo ---
    elif estado_atual == 'aguardando_escolha_combo_tipo':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'aguardando_tipo_reserva'
            return menu_principal(resposta), estado_info

        if mensagem_lower in DEFINICOES_COMBOS:
            escolha_id = mensagem_lower
            combo_def = DEFINICOES_COMBOS[escolha_id]
            
            estado_info['estado'] = 'construindo_combo'
            estado_info['combo_em_construcao'] = {
                'tipo_combo_id': escolha_id,
                'id': combo_def['id'],
                'nome': combo_def['nome'],
                'preco': combo_def['preco'],
                'custo': combo_def['custo'], 
                'etapa_idx': 0,
                'itens_escolhidos': {}
            }
            return iniciar_etapa_combo(numero_cliente, resposta, estado_info)
        else:
            texto_menu_combo = (
                "Opção inválida 😕. Por favor, escolha um número da lista:"
            )
            resposta['body'] = texto_menu_combo
            resposta['menu_opcoes'] = [
                {"id": "1", "titulo": f"1️⃣ Combo 1 ({DEFINICOES_COMBOS['1']['preco']})"},
                {"id": "2", "titulo": f"2️⃣ Combo 2 ({DEFINICOES_COMBOS['2']['preco']})"},
                {"id": "3", "titulo": f"3️⃣ Combo 3 ({DEFINICOES_COMBOS['3']['preco']})"},
                {"id": "voltar", "titulo": "🔙 Voltar"}
            ]
            return resposta, estado_info
    
    elif estado_atual == 'construindo_combo':
        if "voltar" in mensagem_lower:
            del estado_info['combo_em_construcao']
            estado_info['estado'] = 'aguardando_tipo_reserva'
            resposta['body'] = "Construção do combo cancelada."
            return menu_principal(resposta), estado_info
            
        try:
            combo_info = estado_info['combo_em_construcao']
            etapa_def = combo_info['etapa_atual']
            etapa_nome_chave = etapa_def['nome_etapa']
            limite_itens = etapa_def['limite']
            
            if etapa_nome_chave not in combo_info['itens_escolhidos']:
                combo_info['itens_escolhidos'][etapa_nome_chave] = []
                
            lista_escolhidos_etapa = combo_info['itens_escolhidos'][etapa_nome_chave]
            opcoes_da_etapa = obter_opcoes_etapa_atual(combo_info)
            
            itens_adicionados_sucesso = []
            itens_falhados = []
            
            partes = mensagem.split() 
            
            for numero_str in partes:
                nome_para_add = None
                
                if len(lista_escolhidos_etapa) >= limite_itens:
                    itens_falhados.append(numero_str) 
                    continue

                try:
                    item_idx = int(numero_str) - 1 
                    if 0 <= item_idx < len(opcoes_da_etapa):
                        nome_para_add = opcoes_da_etapa[item_idx]
                    else:
                        itens_falhados.append(f"Nº {numero_str} (inválido)")
                except ValueError:
                    itens_falhados.append(f"'{numero_str}' (não é um número)")
                    continue 
                        
                if nome_para_add:
                    if nome_para_add in lista_escolhidos_etapa:
                        itens_falhados.append(f"{nome_para_add} (já escolhido)")
                    else:
                        lista_escolhidos_etapa.append(nome_para_add)
                        itens_adicionados_sucesso.append(nome_para_add)
                
            itens_escolhidos_qtd = len(lista_escolhidos_etapa)
            
            texto_feedback = ""
            if itens_adicionados_sucesso:
                 nomes_formatados = ", ".join([f"'{n}'" for n in itens_adicionados_sucesso])
                 texto_feedback += f"Legal! Itens adicionados: {nomes_formatados}.\n"
            
            if itens_falhados:
                nomes_falhados = ", ".join(itens_falhados)
                texto_feedback += f"Atenção: Não foi possível adicionar '{nomes_falhados}'.\n"
            
            if itens_escolhidos_qtd < limite_itens:
                texto_feedback += (
                    f"\nVocê já escolheu {itens_escolhidos_qtd} de {limite_itens} para ({etapa_nome_chave}).\n"
                    "Por favor, digite o número do próximo item."
                )
                resposta['body'] = texto_feedback.strip()
                return resposta, estado_info
            else:
                texto_feedback += (
                    f"\nVocê completou a etapa *{etapa_nome_chave}*!"
                )
                resposta['body'] = texto_feedback.strip()
                return avancar_etapa_combo(numero_cliente, resposta, estado_info)
                
        except Exception as e:
            print(f"Erro em construindo_combo: {e}")
            resposta['body'] = "Ocorreu um erro 😕. Por favor, digite os números novamente ou *voltar*."
            return resposta, estado_info

    # --- Fluxo: Catálogo Avulso (ATUALIZADO) ---
    elif estado_atual == 'aguardando_categoria_avulsos':
        if "voltar" in mensagem_lower:
             estado_info['estado'] = 'aguardando_tipo_reserva'
             return menu_principal(resposta), estado_info
        try:
            escolha_num = int(mensagem_lower)
            categorias_cache = estado_info.get('categorias_cache', [])
            
            if escolha_num == 1:
                # Caso 1: Catálogo Completo (Envia texto, espera número)
                estado_info['estado'] = 'visualizando_lista_avulsos'
                titulo = "Aqui está nosso catálogo completo, organizado por categoria! ✨\n\nEscolha um número para ver os detalhes:\n"
                message_parts = [titulo]
                for category, items in CATALOGO_AVULSOS_CATEGORIZADO.items():
                    message_parts.append(f"*{category}*")
                    items_sorted = sorted(items, key=lambda x: x['id']) 
                    for item in items_sorted:
                        message_parts.append(f"*{item['id']}* - {item['nome']}")
                    message_parts.append("") 
                message_parts.append("Digite o *número* do brinquedo ou *voltar*.")
                resposta['body'] = "\n".join(message_parts)
                return resposta, estado_info

            elif 2 <= escolha_num <= len(categorias_cache) + 1:
                # Caso 2: Categoria Específica (Envia BOTÕES, espera clique)
                estado_info['estado'] = 'visualizando_lista_avulsos' 
                
                categoria_escolhida = categorias_cache[escolha_num - 2]
                lista_de_itens = sorted(CATALOGO_AVULSOS_CATEGORIZADO[categoria_escolhida], key=lambda x: x['id'])
                
                texto_lista = f"Estes são os nossos itens de *{categoria_escolhida}*! ✨\n\nEscolha um item para ver os detalhes:"
                
                menu_opcoes_itens = []
                for item in lista_de_itens:
                    menu_opcoes_itens.append({"id": str(item['id']), "titulo": f"{item['nome']} (ID: {item['id']})"})
                
                menu_opcoes_itens.append({"id": "voltar", "titulo": "🔙 Voltar (Ver categorias)"})
                
                resposta['body'] = texto_lista
                resposta['menu_opcoes'] = menu_opcoes_itens 
                
                return resposta, estado_info
            else:
                estado_info['estado'] = 'aguardando_categoria_avulsos' 
                raise ValueError("Número fora do intervalo")
                
        except (ValueError, IndexError):
            estado_info['estado'] = 'aguardando_categoria_avulsos'
            resposta['body'] = "Opção inválida 😕. Por favor, escolha uma opção da lista."
            categorias = list(CATALOGO_AVULSOS_CATEGORIZADO.keys())
            estado_info['categorias_cache'] = categorias
            menu_opcoes = [{"id": "1", "titulo": "1️⃣ Ver Catálogo Completo"}]
            for i, categoria in enumerate(categorias):
                menu_opcoes.append({"id": str(i + 2), "titulo": f"{(i + 2)}️⃣ {categoria}"})
            menu_opcoes.append({"id": "voltar", "titulo": "🔙 Voltar"})
            resposta['menu_opcoes'] = menu_opcoes
            
            return resposta, estado_info

    elif estado_atual == 'visualizando_lista_avulsos':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'aguardando_categoria_avulsos'
            categorias = list(CATALOGO_AVULSOS_CATEGORIZADO.keys())
            estado_info['categorias_cache'] = categorias
            
            texto_menu = (
                "Voltando para as categorias... 🧸\n\n"
                "Para adicionar um item direto pelo ID, digite `carrinho <número>` (ex: `carrinho 24`).\n\n"
                "Ou, escolha uma categoria abaixo para explorar:"
            )
            resposta['body'] = texto_menu
            
            menu_opcoes = [{"id": "1", "titulo": "1️⃣ Ver Catálogo Completo"}]
            for i, categoria in enumerate(categorias):
                menu_opcoes.append({"id": str(i + 2), "titulo": f"{(i + 2)}️⃣ {categoria}"})
            menu_opcoes.append({"id": "voltar", "titulo": "🔙 Voltar"})
            resposta['menu_opcoes'] = menu_opcoes
            
            return resposta, estado_info
        try:
            escolha_num = int(mensagem_lower) 
            brinquedo_escolhido = next((item for item in CATALOGO_AVULSOS if item['id'] == escolha_num), None)
            
            if brinquedo_escolhido:
                descricao_limpa = brinquedo_escolhido.get('descricao', '')
                
                resposta['media'] = brinquedo_escolhido['imagens_urls']
                texto_brinquedo = (
                    f"✨ *{brinquedo_escolhido['nome']}* (ID: {brinquedo_escolhido['id']}) ✨\n\n"
                    f"Valor: *{brinquedo_escolhido['preco']}*\n\n"
                    f"{descricao_limpa}\n\n"
                    "O que você gostaria de fazer?" 
                )
                resposta['body'] = texto_brinquedo
                resposta['usar_legenda'] = True
                
                resposta['menu_opcoes'] = [
                    {"id": f"carrinho {brinquedo_escolhido['id']}", "titulo": "🛒 Adicionar ao Carrinho"},
                    {"id": "voltar", "titulo": "🔙 Voltar (Ver outros)"}
                ]
                
                return resposta, estado_info
            else:
                raise ValueError("ID do item não encontrado")
        except (ValueError, IndexError):
            resposta['body'] = "Opção inválida 😕. Digite um *número* da lista ou *voltar*."
            return resposta, estado_info
            
    # --- Fluxo: Gerenciamento de Reserva ---
    elif estado_atual == 'pedindo_cpf_para_gerenciar':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'aguardando_tipo_reserva'
            return menu_principal(resposta), estado_info
        
        cpf_cliente = re.sub(r'\D', '', mensagem)
        if len(cpf_cliente) != 11:
            resposta['body'] = "CPF inválido. 😕 Por favor, digite um CPF com 11 dígitos (apenas números) ou *voltar*."
            return resposta, estado_info

        eventos_encontrados = buscar_eventos_por_cpf(cpf_cliente) 
        
        if not eventos_encontrados: 
            estado_info['estado'] = 'aguardando_tipo_reserva'
            resposta['body'] = "Não encontrei nenhuma reserva *futura* para este CPF. 😕"
            resposta['quick_replies'] = ['oi'] 
            return resposta, estado_info
        
        elif len(eventos_encontrados) == 1: 
            evento_encontrado = eventos_encontrados[0]
            estado_info['evento_para_gerenciar'] = evento_encontrado
            estado_info['estado'] = 'mostrando_reserva_e_opcoes'
            
            start_time_str = evento_encontrado['start'].get('dateTime')
            start_obj = datetime.fromisoformat(start_time_str)
            dia_formatado = start_obj.strftime("%d/%m/%Y")
            hora_formatada = start_obj.strftime("%H:%M")

            resposta['body'] = (
                f"Encontrei sua reserva! 🎉\n\n"
                f"Resumo: *{evento_encontrado.get('summary', 'Reserva')}*\n"
                f"Data: *{dia_formatado} às {hora_formatada}*\n\n"
                "O que você gostaria de fazer?"
            )
            resposta['menu_opcoes'] = [
                {"id": "1", "titulo": "✏️ Remarcar esta reserva"},
                {"id": "2", "titulo": "❌ Cancelar esta reserva"},
                {"id": "voltar", "titulo": "🔙 Voltar"}
            ]
            return resposta, estado_info

        else: 
            estado_info['lista_eventos_gerenciar'] = eventos_encontrados
            estado_info['estado'] = 'selecionando_reserva_para_gerenciar'
            
            MAX_EVENTOS_EXIBIDOS = 10 
            eventos_para_exibir = eventos_encontrados[:MAX_EVENTOS_EXIBIDOS]
            eventos_nao_exibidos = len(eventos_encontrados) - len(eventos_para_exibir)
            
            texto_resposta = f"Encontrei *{len(eventos_encontrados)} reservas* futuras neste CPF:\n\n"
            menu_opcoes_eventos = [] 
            
            for i, evento in enumerate(eventos_para_exibir):
                start_time_str = evento['start'].get('dateTime')
                start_obj = datetime.fromisoformat(start_time_str)
                dia_formatado = start_obj.strftime("%d/%m/%Y")
                hora_formatada = start_obj.strftime("%H:%M")
                
                titulo_evento = f"{evento.get('summary', 'Reserva')} ({dia_formatado} às {hora_formatada})"
                menu_opcoes_eventos.append({"id": str(i + 1), "titulo": f"*{i + 1}* - {titulo_evento}"})
            
            if eventos_nao_exibidos > 0:
                texto_resposta += f"\n... e mais *{eventos_nao_exibidos}* reservas futuras (exibindo apenas as {MAX_EVENTOS_EXIBIDOS} primeiras). Por favor, escolha entre as opções acima."
            
            texto_resposta += "\nQual reserva você gostaria de gerenciar?"
            resposta['body'] = texto_resposta
            
            menu_opcoes_eventos.append({"id": "voltar", "titulo": "🔙 Voltar"})
            resposta['menu_opcoes'] = menu_opcoes_eventos
            
            return resposta, estado_info

    elif estado_atual == 'selecionando_reserva_para_gerenciar':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'aguardando_tipo_reserva'
            if 'lista_eventos_gerenciar' in estado_info:
                del estado_info['lista_eventos_gerenciar']
            return menu_principal(resposta), estado_info
        
        try:
            lista_eventos = estado_info.get('lista_eventos_gerenciar', [])
            if not lista_eventos:
                 estado_info['estado'] = 'aguardando_tipo_reserva'
                 if 'lista_eventos_gerenciar' in estado_info:
                     del estado_info['lista_eventos_gerenciar']
                 resposta['body'] = "Ocorreu um erro, vamos recomeçar. Digite 'oi'."
                 return resposta, estado_info
                 
            escolha_num = int(mensagem_lower)
            if 1 <= escolha_num <= len(lista_eventos):
                evento_escolhido = lista_eventos[escolha_num - 1]
                estado_info['evento_para_gerenciar'] = evento_escolhido
                del estado_info['lista_eventos_gerenciar']
                estado_info['estado'] = 'mostrando_reserva_e_opcoes'
                
                start_time_str = evento_escolhido['start'].get('dateTime')
                start_obj = datetime.fromisoformat(start_time_str)
                dia_formatado = start_obj.strftime("%d/%m/%Y")
                hora_formatada = start_obj.strftime("%H:%M")

                resposta['body'] = (
                    f"Você selecionou:\n"
                    f"Resumo: *{evento_escolhido.get('summary', 'Reserva')}*\n"
                    f"Data: *{dia_formatado} às {hora_formatada}*\n\n"
                    "O que você gostaria de fazer?"
                )
                resposta['menu_opcoes'] = [
                    {"id": "1", "titulo": "✏️ Remarcar esta reserva"},
                    {"id": "2", "titulo": "❌ Cancelar esta reserva"},
                    {"id": "voltar", "titulo": "🔙 Voltar"}
                ]
                return resposta, estado_info
            else:
                raise ValueError("Número fora do range")
                
        except (ValueError, IndexError):
            texto_erro = "Opção inválida. 😕 Por favor, escolha uma das reservas da lista."
            resposta['body'] = texto_erro
            
            eventos = estado_info.get('lista_eventos_gerenciar', [])
            MAX_EVENTOS_EXIBIDOS = 10 
            eventos_para_exibir = eventos[:MAX_EVENTOS_EXIBIDOS]
            menu_opcoes_eventos = []

            for i, evento in enumerate(eventos_para_exibir):
                start_time_str = evento['start'].get('dateTime')
                start_obj = datetime.fromisoformat(start_time_str)
                dia_formatado = start_obj.strftime("%d/%m/%Y")
                hora_formatada = start_obj.strftime("%H:%M")
                titulo_evento = f"{evento.get('summary', 'Reserva')} ({dia_formatado} às {hora_formatada})"
                menu_opcoes_eventos.append({"id": str(i + 1), "titulo": f"*{i + 1}* - {titulo_evento}"})
            
            menu_opcoes_eventos.append({"id": "voltar", "titulo": "🔙 Voltar"})
            resposta['menu_opcoes'] = menu_opcoes_eventos

            return resposta, estado_info

    elif estado_atual == 'mostrando_reserva_e_opcoes':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'aguardando_tipo_reserva'
            if 'evento_para_gerenciar' in estado_info:
                del estado_info['evento_para_gerenciar']
            return menu_principal(resposta), estado_info
        
        if mensagem_lower == '1': # REMARCAR
            estado_info['estado'] = 'remarcando_pedindo_mes'
            return mostrar_meses_disponiveis(resposta, numero_cliente, estado_info) 
        
        elif mensagem_lower == '2': # CANCELAR
            estado_info['estado'] = 'confirmando_cancelamento'
            resposta['body'] = "Tem *certeza* que deseja cancelar esta reserva? Esta ação não pode ser desfeita."
            resposta['quick_replies'] = ['sim', 'voltar'] 
            return resposta, estado_info
        else:
            resposta['body'] = "Opção inválida. Por favor, escolha uma das opções."
            resposta['menu_opcoes'] = [
                {"id": "1", "titulo": "✏️ Remarcar esta reserva"},
                {"id": "2", "titulo": "❌ Cancelar esta reserva"},
                {"id": "voltar", "titulo": "🔙 Voltar"}
            ]
            return resposta, estado_info

    elif estado_atual == 'confirmando_cancelamento':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'mostrando_reserva_e_opcoes'
            evento_encontrado = estado_info['evento_para_gerenciar']
            start_time_str = evento_encontrado['start'].get('dateTime')
            start_obj = datetime.fromisoformat(start_time_str)
            dia_formatado = start_obj.strftime("%d/%m/%Y")
            hora_formatada = start_obj.strftime("%H:%M")
            resposta['body'] = (
                f"Cancelamento não confirmado. Voltando...\n\n"
                f"Reserva: *{evento_encontrado.get('summary', 'Reserva')}* em *{dia_formatado} às {hora_formatada}*\n\n"
                "O que você gostaria de fazer?"
            )
            resposta['menu_opcoes'] = [
                {"id": "1", "titulo": "✏️ Remarcar esta reserva"},
                {"id": "2", "titulo": "❌ Cancelar esta reserva"},
                {"id": "voltar", "titulo": "🔙 Voltar"}
            ]
            return resposta, estado_info

        if mensagem_lower == 'sim':
            try:
                event_id = estado_info['evento_para_gerenciar']['id']
                sucesso_agenda = cancelar_evento(event_id) 
                
                if sucesso_agenda:
                    try:
                        iniciar_sincronizacao_excel() 
                    except Exception as e_db:
                        print(f"ERRO CRÍTICO: Evento {event_id} CANCELADO na agenda, MAS FALHOU ao atualizar DB: {e_db}")
                        
                    resposta['body'] = "Sua reserva foi cancelada com sucesso. ✅\n\nEsperamos te ver em uma próxima oportunidade!"
                    resposta['quick_replies'] = ['oi'] 
                else:
                    raise Exception("Falha no cancelamento da agenda (API Google)")
            
            except Exception as e:
                print(f"Erro ao cancelar evento: {e}")
                resposta['body'] = "Ocorreu um erro ao tentar cancelar sua reserva. 😕 Por favor, entre em contato com nosso suporte."
            
            estado_info = {'estado': None, 'carrinho': [], 'frete_valor': -1.0}
            return resposta, estado_info
        else:
            resposta['body'] = "Comando não reconhecido. Por favor, confirme a ação."
            resposta['quick_replies'] = ['sim', 'voltar'] 
            return resposta, estado_info

    # --- Fluxo: Remarcação ---
    elif estado_atual == 'remarcando_pedindo_mes':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'mostrando_reserva_e_opcoes'
            evento_encontrado = estado_info['evento_para_gerenciar']
            start_time_str = evento_encontrado['start'].get('dateTime')
            start_obj = datetime.fromisoformat(start_time_str)
            dia_formatado = start_obj.strftime("%d/%m/%Y")
            hora_formatada = start_obj.strftime("%H:%M")
            resposta['body'] = (
                f"Voltando... Sua reserva atual é:\n"
                f"*{evento_encontrado.get('summary', 'Reserva')}* em *{dia_formatado} às {hora_formatada}*\n\n"
                "O que você gostaria de fazer?"
            )
            resposta['menu_opcoes'] = [
                {"id": "1", "titulo": "✏️ Remarcar esta reserva"},
                {"id": "2", "titulo": "❌ Cancelar esta reserva"},
                {"id": "voltar", "titulo": "🔙 Voltar"}
            ]
            return resposta, estado_info
        try:
            meses_disponiveis = estado_info.get('meses_cache', [])
            escolha = int(mensagem_lower)
            if 1 <= escolha <= len(meses_disponiveis):
                mes_escolhido = meses_disponiveis[escolha - 1]
                estado_info.update({'estado': 'remarcando_pedindo_dia', 'ano_novo': mes_escolhido['ano'], 'mes_novo': mes_escolhido['mes']})
                return mostrar_dias_disponiveis(resposta, mes_escolhido['ano'], mes_escolhido['mes'], numero_cliente, estado_info)
            else: raise ValueError()
        except (ValueError, IndexError):
            resposta['body'] = "Opção inválida 😕. Por favor, escolha um dos meses da lista."
            return mostrar_meses_disponiveis(resposta, numero_cliente, estado_info) 

    elif estado_atual == 'remarcando_pedindo_dia':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'remarcando_pedindo_mes'
            return mostrar_meses_disponiveis(resposta, numero_cliente, estado_info)
        try:
            dia_escolhido = int(mensagem_lower)
            ano, mes = estado_info.get('ano_novo'), estado_info.get('mes_novo')
            dias_disponiveis_cache = estado_info.get('dias_cache', [])
            
            if dia_escolhido in dias_disponiveis_cache:
                dia_obj = date(ano, mes, dia_escolhido)
                
                evento_original = estado_info['evento_para_gerenciar']
                start_original_obj = datetime.fromisoformat(evento_original['start'].get('dateTime'))
                if dia_obj == start_original_obj.date():
                     resposta['body'] = "Este já é o dia da sua reserva atual. 😕 Por favor, escolha um *novo dia* da lista ou digite *voltar*."
                     return mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info) 
                
                estado_info.update({'estado': 'remarcando_pedindo_hora', 'dia_obj_novo': dia_obj})
                return mostrar_horarios_disponiveis(resposta, dia_obj, estado_info)
            else:
                 raise ValueError("Dia inválido ou não disponível")
        except (ValueError, IndexError):
            resposta['body'] = "Dia inválido ou não disponível 😕. Por favor, digite um *dia* da lista acima ou *voltar*."
            ano, mes = estado_info.get('ano_novo'), estado_info.get('mes_novo')
            return mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info) 

    elif estado_atual == 'remarcando_pedindo_hora':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'remarcando_pedindo_dia'
            ano, mes = estado_info.get('ano_novo'), estado_info.get('mes_novo')
            return mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info)
        
        horario_escolhido = mensagem.lower().strip()
        if horario_escolhido.startswith("marcar "):
            horario_escolhido = horario_escolhido.replace("marcar ", "").strip()
        
        try:
            horario_obj = datetime.strptime(horario_escolhido, '%H:%M').time()
            if not (datetime.strptime('08:00', '%H:%M').time() <= horario_obj <= datetime.strptime('17:00', '%H:%M').time()):
                raise ValueError("Horário fora do intervalo permitido (08:00-17:00)")

            estado_info['horario_escolhido_novo'] = horario_escolhido
            estado_info['estado'] = 'confirmando_remarcacao'
            
            evento_original = estado_info.get('evento_para_gerenciar')
            start_original_obj = datetime.fromisoformat(evento_original['start'].get('dateTime'))
            dia_original_formatado = start_original_obj.strftime("%d/%m/%Y às %H:%M")
            
            # --- (CORREÇÃO AQUI) ---
            # Converte 'dia_obj_novo' de string (do DB) para objeto date
            dia_novo_obj = date.fromisoformat(estado_info.get('dia_obj_novo'))
            dia_novo_formatado = dia_novo_obj.strftime("%d/%m/%Y")

            texto_resumo = (
                f"OK! Vamos confirmar a remarcação.\n\n"
                f"Sua reserva *anterior* era:\n"
                f"🗓️ {dia_original_formatado}\n\n"
                f"Sua *NOVA* reserva será:\n"
                f"🗓️ *{dia_novo_formatado} às {horario_escolhido}*\n\n"
                f"Resumo: {evento_original.get('summary', 'Reserva')}\n\n"
                "Podemos confirmar a mudança?"
            )
            resposta['body'] = texto_resumo
            resposta['quick_replies'] = ['sim', 'não'] 
            
            return resposta, estado_info
        except (ValueError, IndexError):
            resposta['body'] = ("Horário inválido 😕.\n\n"
                                "Por favor, digite um horário entre as *08:00 e 17:00* no formato HH:MM (ex: `14:30`), ou digite *voltar*.")
            return resposta, estado_info

    elif estado_atual == 'confirmando_remarcacao':
        if mensagem_lower == 'sim':
            try:
                event_id = estado_info['evento_para_gerenciar']['id']
                # --- (CORREÇÃO AQUI) ---
                novo_dia = date.fromisoformat(estado_info['dia_obj_novo'])
                novo_horario = estado_info['horario_escolhido_novo'] 

                sucesso_agenda = remarcar_evento(event_id, novo_dia, novo_horario) 
                
                if sucesso_agenda:
                    try:
                        atualizar_data_horario_venda(event_id, novo_dia.isoformat(), novo_horario) 
                        iniciar_sincronizacao_excel()
                    except Exception as e_db:
                         print(f"ERRO: Evento {event_id} REMARCADO na agenda, MAS FALHOU ao atualizar data no DB: {e_db}")

                    dia_formatado = novo_dia.strftime("%d/%m/%Y")
                    resposta['body'] = (
                        f"Confirmado! 🎊✨\n\n"
                        f"Sua reserva foi remarcada com sucesso para o dia *{dia_formatado}* às *{novo_horario}*!\n\n"
                        "Obrigado!"
                    )
                    resposta['quick_replies'] = ['oi'] 
                    estado_info = {'estado': None, 'carrinho': [], 'frete_valor': -1.0}
                else:
                    resposta['body'] = (
                        f"Oh, que pena! 😕 O dia *{novo_dia.strftime('%d/%m')}* foi reservado por outra pessoa enquanto você decidia.\n\n"
                        "Vamos tentar de novo:"
                    )
                    estado_info['estado'] = 'remarcando_pedindo_dia'
                    ano, mes = estado_info.get('ano_novo'), estado_info.get('mes_novo')
                    return mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info)
            
            except Exception as e:
                print(f"Erro ao remarcar: {e}")
                resposta['body'] = "Ocorreu um erro ao tentar remarcar sua reserva. 😕 Por favor, entre em contato com nosso suporte."
                estado_info = {'estado': None, 'carrinho': [], 'frete_valor': -1.0}
            
            return resposta, estado_info
        
        elif mensagem_lower == 'não' or "voltar" in mensagem_lower :
            estado_info['estado'] = 'remarcando_pedindo_hora'
            resposta['body'] = "Ok, remarcação não confirmada. Voltando para a escolha do horário."
            # --- (CORREÇÃO AQUI) ---
            dia_obj_novo = date.fromisoformat(estado_info.get('dia_obj_novo'))
            return mostrar_horarios_disponiveis(resposta, dia_obj_novo, estado_info)
        else:
            resposta['body'] = "Opção inválida. Por favor, confirme a ação."
            resposta['quick_replies'] = ['sim', 'não'] 
            return resposta, estado_info

    # --- Fluxo: Checkout (Coleta de Dados) ---
    elif estado_atual == 'coletando_cep':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'aguardando_tipo_reserva'
            return mostrar_carrinho(numero_cliente, resposta, estado_info)
        
        cep_cliente = mensagem
        if not any(char.isdigit() for char in cep_cliente):
            resposta['body'] = "CEP inválido 😕. Por favor, digite um CEP válido ou *voltar* para cancelar."
            return resposta, estado_info

        estado_info['cep'] = cep_cliente
        estado_info['estado'] = 'coletando_endereco'
        resposta['body'] = f"CEP `{cep_cliente}` recebido! 👍\n\nAgora, por favor, me informe o restante do endereço (*Rua, Número, Bairro e Cidade*)."
        return resposta, estado_info

    elif estado_atual == 'coletando_endereco':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'coletando_cep'
            resposta['body'] = "Ok, voltando. Por favor, informe o *CEP* do local da festa novamente."
            return resposta, estado_info
            
        resto_do_endereco = mensagem
        cep = estado_info.get('cep', '')
        endereco_completo_base = f"{resto_do_endereco}, {cep}"
        
        estado_info['endereco_completo'] = endereco_completo_base

        if gmaps is None:
            resposta['body'] = "Desculpe, o serviço de cálculo de frete não está configurado. 😕"
            estado_info['estado'] = None
            return resposta, estado_info
        
        distancia_info = calcular_distancia_google(ENDERECO_ORIGEM, endereco_completo_base)
        if distancia_info is None:
            resposta['body'] = "Desculpe, não consegui calcular o frete para este endereço. 😕\n\nPor favor verifique se o endereço está completo (Rua, Número, Bairro, Cidade, CEP).\n\nDigite o endereço novamente ou *voltar* para cancelar."
            return resposta, estado_info
        
        carrinho_atual = estado_info.get('carrinho', [])
        preco_frete = calcular_preco_frete(distancia_info['km'], carrinho_atual)
        
        estado_info['frete_valor'] = preco_frete
        estado_info['distancia_km'] = distancia_info['km']
        estado_info['distancia_texto'] = distancia_info['texto'] 
        
        estado_info['estado'] = 'coletando_complemento'
        resposta['body'] = "Endereço principal recebido! 👍\n\nAgora, por favor, informe o *complemento* (ex: Apto 101, Bloco B, Salão de Festas, Ponto de Referência).\n\nSe não houver complemento, digite `não tenho`."
        return resposta, estado_info

    elif estado_atual == 'coletando_complemento':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'coletando_endereco'
            estado_info['frete_valor'] = -1.0 
            estado_info['distancia_km'] = 0.0 
            if 'distancia_texto' in estado_info:
                del estado_info['distancia_texto']
            resposta['body'] = "Ok, voltando. Por favor, me informe o *endereço completo* (Rua, Número, Bairro e Cidade) novamente."
            return resposta, estado_info

        complemento = mensagem
        base_address = estado_info.get('endereco_completo', '')
        
        if mensagem_lower not in ['nao tenho', 'não tenho', 'sem complemento', 'nao', 'não', 'n/a', 'nao tenhu']:
            endereco_final = f"{base_address} - {complemento}"
            estado_info['endereco_completo'] = endereco_final
        
        preco_frete = estado_info.get('frete_valor', 0.0)
        distancia_texto = estado_info.get('distancia_texto', 'Distância calculada') 
        carrinho_atual = estado_info.get('carrinho', [])
        tem_combo = any(item.get('id') in [101, 102, 103] for item in carrinho_atual)

        texto_frete = f"Ótimo! Complemento anotado.\n\nA distância da nossa base até o local é de *{distancia_texto}*.\n\n"
        quick_replies_frete = [] 

        if preco_frete == 0.0:
            if tem_combo:
                texto_frete += "Para pedidos com combo, nosso frete é grátis para até 60km (ida). *O frete é por nossa conta*! 🎉\n\n"
            else:
                texto_frete += "Como a distância é menor que 20 km, o *frete é GRÁTIS*! 🎉\n\n"
            texto_frete += "Podemos continuar com o pedido?"
            quick_replies_frete = ['sim', 'voltar']
        else:
            if tem_combo:
                texto_frete += (
                    "Para pedidos com combo, nosso frete é grátis para até 60km (ida). Como sua distância excedeu este limite, o frete será calculado apenas sobre os quilômetros adicionais.\n\n"
                    f"O valor do frete adicional fica em *R$ {formatar_reais(preco_frete)}*.\n\n"
                )
            else:
                texto_frete += f"O valor do frete fica em *R$ {formatar_reais(preco_frete)}*.\n\n"
            
            texto_frete += "Podemos adicionar este valor ao pedido?"
            quick_replies_frete = ['sim', 'não', 'voltar']

        estado_info['estado'] = 'confirmando_frete'
        resposta['body'] = texto_frete
        resposta['quick_replies'] = quick_replies_frete 
        return resposta, estado_info

    elif estado_atual == 'confirmando_frete':
        if "voltar" in mensagem_lower:
              estado_info['estado'] = 'coletando_complemento'
              resposta['body'] = "Ok, voltando. Por favor, informe o *complemento* novamente (ex: Apto 101, Salão de Festas).\n\nSe não houver complemento, digite `não tenho`."
              return resposta, estado_info
        if mensagem_lower == 'sim':
            estado_info['estado'] = 'coletando_nome'
            if estado_info.get('frete_valor', -1) == 0.0:
                 resposta['body'] = "Perfeito! Frete grátis confirmado. 👍\n\nAgora, qual o *nome completo* (nome e sobrenome) do responsável pela reserva?"
            else:
                 resposta['body'] = "Perfeito! Frete adicionado. 👍\n\nAgora, qual o *nome completo* (nome e sobrenome) do responsável pela reserva?"
            return resposta, estado_info
        elif estado_info.get('frete_valor', -1) > 0.0 and mensagem_lower == 'não':
            estado_info = {'estado': None, 'carrinho': [], 'frete_valor': -1.0} 
            resposta['body'] = "Entendido. O frete é necessário para a entrega.\n\nSeu pedido foi cancelado. Se quiser tentar novamente, basta mandar um 'oi'. 👋"
            return resposta, estado_info
        else:
              resposta['body'] = "Opção inválida. Por favor, confirme a ação."
              if estado_info.get('frete_valor', -1) == 0.0:
                  resposta['quick_replies'] = ['sim', 'voltar']
              else:
                  resposta['quick_replies'] = ['sim', 'não', 'voltar']
              return resposta, estado_info

    elif estado_atual == 'coletando_nome':
        if "voltar" in mensagem_lower:
              estado_info['estado'] = 'confirmando_frete'
              preco_frete = estado_info.get('frete_valor', 0.0)
              distancia_texto = estado_info.get('distancia_texto', 'Distância calculada')
              
              if preco_frete == 0.0:
                   texto_frete = (f"Voltando... A distância é *{distancia_texto}* e o frete é GRÁTIS.\n\nPodemos continuar?")
                   resposta['quick_replies'] = ['sim', 'voltar']
              else:
                   texto_frete = (f"Voltando... A distância é *{distancia_texto}* e o frete é *R$ {formatar_reais(preco_frete)}*.\n\nPodemos adicionar este valor?")
                   resposta['quick_replies'] = ['sim', 'não', 'voltar']
              resposta['body'] = texto_frete
              return resposta, estado_info
              
        estado_info['nome_cliente'] = mensagem
        estado_info['estado'] = 'coletando_cpf'
        resposta['body'] = "Obrigado! 🙏\n\nAgora, por favor, digite o *CPF* do responsável (apenas números)."
        return resposta, estado_info

    elif estado_atual == 'coletando_cpf':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'coletando_nome'
            resposta['body'] = "Voltando... Qual o *nome completo* (nome e sobrenome) do responsável pela reserva?"
            return resposta, estado_info
            
        cpf_cliente = re.sub(r'\D', '', mensagem)
        if len(cpf_cliente) != 11:
            resposta['body'] = "CPF inválido. 😕 Por favor, digite um CPF com 11 dígitos (apenas números) ou *voltar*."
            return resposta, estado_info
            
        cpf_formatado = formatar_cpf(cpf_cliente) 
        estado_info['cpf_para_confirmar'] = cpf_cliente 
        estado_info['estado'] = 'confirmando_cpf' 
        
        resposta['body'] = (f"Você digitou: *{cpf_formatado}*\n\n"
                          "Este CPF está correto?")
        resposta['quick_replies'] = ['sim', 'não'] 
        return resposta, estado_info

    elif estado_atual == 'confirmando_cpf':
        if "voltar" in mensagem_lower or mensagem_lower == 'não':
            estado_info['estado'] = 'coletando_cpf'
            if 'cpf_para_confirmar' in estado_info:
                 del estado_info['cpf_para_confirmar']
            resposta['body'] = "Entendido. Por favor, digite o CPF correto novamente (apenas números)."
            return resposta, estado_info
        
        if mensagem_lower == 'sim':
            cpf_confirmado = estado_info.get('cpf_para_confirmar')
            if not cpf_confirmado: 
                estado_info['estado'] = 'coletando_cpf'
                resposta['body'] = "Ocorreu um erro. Por favor, digite seu CPF novamente."
                return resposta, estado_info

            estado_info['cpf_cliente'] = cpf_confirmado
            if 'cpf_para_confirmar' in estado_info:
                del estado_info['cpf_para_confirmar']
            
            estado_info['estado'] = 'agendando_pedindo_mes'
            return mostrar_meses_disponiveis(resposta, numero_cliente, estado_info)
        else:
            resposta['body'] = "Opção inválida. 😕 Por favor, confirme."
            resposta['quick_replies'] = ['sim', 'não'] 
            return resposta, estado_info

    # --- Fluxo: Agendamento ---
    elif estado_atual == 'agendando_pedindo_mes':
        if "voltar" in mensagem_lower:
              estado_info['estado'] = 'confirmando_cpf' 
              cpf_cliente = estado_info.get('cpf_cliente', estado_info.get('cpf_para_confirmar', ''))
              cpf_formatado = formatar_cpf(cpf_cliente)
              
              if 'cpf_cliente' in estado_info:
                  estado_info['cpf_para_confirmar'] = estado_info['cpf_cliente']
                  del estado_info['cpf_cliente']

              resposta['body'] = (f"Voltando... O CPF *{cpf_formatado}* está correto?")
              resposta['quick_replies'] = ['sim', 'não'] 
              return resposta, estado_info
        try:
            meses_disponiveis = estado_info.get('meses_cache', [])
            escolha = int(mensagem_lower)
            if 1 <= escolha <= len(meses_disponiveis):
                mes_escolhido = meses_disponiveis[escolha - 1]
                estado_info.update({'estado': 'agendando_pedindo_dia', 'ano': mes_escolhido['ano'], 'mes': mes_escolhido['mes']})
                return mostrar_dias_disponiveis(resposta, mes_escolhido['ano'], mes_escolhido['mes'], numero_cliente, estado_info)
            else: raise ValueError()
        except (ValueError, IndexError):
            resposta['body'] = "Opção inválida 😕. Por favor, escolha um dos meses da lista."
            return mostrar_meses_disponiveis(resposta, numero_cliente, estado_info)

    elif estado_atual == 'agendando_pedindo_dia':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'agendando_pedindo_mes'
            return mostrar_meses_disponiveis(resposta, numero_cliente, estado_info)
        try:
            dia_escolhido = int(mensagem_lower)
            ano, mes = estado_info.get('ano'), estado_info.get('mes')
            dias_disponiveis_cache = estado_info.get('dias_cache', [])
            if dia_escolhido in dias_disponiveis_cache:
                dia_obj = date(ano, mes, dia_escolhido)
                estado_info.update({'estado': 'agendando_pedindo_hora', 'dia_obj': dia_obj})
                return mostrar_horarios_disponiveis(resposta, dia_obj, estado_info)
            else:
                 raise ValueError("Dia inválido ou não disponível")
        except (ValueError, IndexError):
            resposta['body'] = "Dia inválido ou não disponível 😕. Por favor, digite um *dia* da lista acima ou *voltar*."
            ano, mes = estado_info.get('ano'), estado_info.get('mes')
            return mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info)

    elif estado_atual == 'agendando_pedindo_hora':
        if "voltar" in mensagem_lower:
            estado_info['estado'] = 'agendando_pedindo_dia'
            ano, mes = estado_info.get('ano'), estado_info.get('mes')
            return mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info)
        
        horario_escolhido = mensagem.lower().strip()
        if horario_escolhido.startswith("marcar "):
            horario_escolhido = horario_escolhido.replace("marcar ", "").strip()

        try:
            horario_obj = datetime.strptime(horario_escolhido, '%H:%M').time()
            if not (datetime.strptime('08:00', '%H:%M').time() <= horario_obj <= datetime.strptime('17:00', '%H:%M').time()):
                raise ValueError("Horário fora do intervalo permitido (08:00-17:00)")

            estado_info['horario_escolhido'] = horario_escolhido
            estado_info['estado'] = 'confirmando_pedido'
            carrinho = estado_info.get('carrinho', [])
            
            itens_formatado_lista = []
            for item in carrinho:
                if 'descricao_custom' in item:
                    itens_formatado_lista.append(f"- *{item['nome']}*")
                    for etapa_nome, itens_escolhidos in item['descricao_custom'].items():
                         if itens_escolhidos:
                             itens_formatados = ", ".join(itens_escolhidos)
                             itens_formatado_lista.append(f"   └ _{etapa_nome}:_ {itens_formatados}")
                else:
                    itens_formatado_lista.append(f"- {item['nome']}")
            itens_formatado = "\n".join(itens_formatado_lista)

            endereco = estado_info.get('endereco_completo', 'Não especificado')
            nome_cliente = estado_info.get('nome_cliente', 'Não especificado')
            cpf_cliente = estado_info.get('cpf_cliente', 'Não informado') 
            cpf_formatado = formatar_cpf(cpf_cliente) 
            
            # --- (CORREÇÃO AQUI) ---
            dia_obj_str = estado_info.get('dia_obj')
            dia_obj = date.fromisoformat(dia_obj_str) # Converte string para objeto date
            dia_formatado = dia_obj.strftime("%d/%m/%Y") # Agora funciona
            # --- (FIM DA CORREÇÃO) ---
            
            frete_valor = estado_info.get('frete_valor', 0.0)
            total_itens = calcular_total(carrinho)
            total_geral = total_itens + frete_valor

            tem_combo = any(item.get('id') in [101, 102, 103] for item in carrinho)
            
            if frete_valor == 0.0:
                texto_frete_resumo = "🚚 *Frete:* Grátis\n"
            elif tem_combo: 
                texto_frete_resumo = f"🚚 *Frete Adicional (>60km):* R$ {formatar_reais(frete_valor)}\n"
            else:
                texto_frete_resumo = f"🚚 *Frete:* R$ {formatar_reais(frete_valor)}\n"
            
            texto_resumo = (f"🎉 *Tudo pronto para confirmar?*\n\n"
                            f"Por favor, revise os detalhes do seu pedido:\n\n"
                            f"✨ *Itens:*\n{itens_formatado}\n"
                            f"--------------------\n"
                            f"💰 *Valor dos Itens:* R$ {formatar_reais(total_itens)}\n"
                            f"{texto_frete_resumo}"
                            f"--------------------\n"
                            f"TOTAL: *R$ {formatar_reais(total_geral)}*\n\n"
                            f"👤 *Responsável:* {nome_cliente}\n"
                            f"📄 *CPF:* {cpf_formatado}\n" 
                            f"📍 *Endereço:* {endereco}\n"
                            f"🗓️ *Data:* {dia_formatado}\n"
                            f"⏰ *Horário:* {horario_escolhido}\n\n"
                            "Se estiver tudo certo, podemos confirmar?")
            resposta['body'] = texto_resumo
            resposta['quick_replies'] = ['sim', 'não'] 
            
            return resposta, estado_info
        except (ValueError, IndexError):
            resposta['body'] = ("Horário inválido 😕.\n\n"
                                "Por favor, digite um horário entre as *08:00 e 17:00* no formato HH:MM (ex: `14:30`), ou digite *voltar*.")
            return resposta, estado_info

    # --- Fluxo: Confirmação Final (ATUALIZADO) ---
    elif estado_atual == 'confirmando_pedido':
        if mensagem_lower == 'sim':
            return iniciar_reserva_pendente(resposta, numero_cliente, estado_info) 
        
        elif mensagem_lower == 'não' or "voltar" in mensagem_lower :
            estado_info['estado'] = 'agendando_pedindo_hora'
            resposta['body'] = "Ok, pedido não confirmado. Voltando para a escolha do horário."
            # --- (CORREÇÃO AQUI) ---
            dia_obj = date.fromisoformat(estado_info.get('dia_obj'))
            return mostrar_horarios_disponiveis(resposta, dia_obj, estado_info)
        else:
            resposta['body'] = "Opção inválida. Por favor, confirme o pedido."
            resposta['quick_replies'] = ['sim', 'não'] 
            return resposta, estado_info

    # --- (BLOCO ATUALIZADO PARA O FLUXO DE PAGAMENTO) ---
    elif estado_atual == 'aguardando_confirmacao_pagamento':
        if mensagem_lower == 'voltar' or mensagem_lower == 'cancelar':
            estado_info['estado'] = 'aguardando_tipo_reserva'
            if 'pending_event_id' in estado_info:
                 del estado_info['pending_event_id']
            resposta = menu_principal(resposta)
            resposta['body'] = "Reserva cancelada. Voltando ao menu principal.\n\n(Sua pré-reserva anterior será invalidada)."
            return resposta, estado_info
        else:
            resposta['body'] = (
                "Estou apenas aguardando a confirmação do pagamento pelo Mercado Pago... ⏳\n\n"
                "Seu horário está *pré-reservado* por 24 horas.\n\n"
                "Assim que for aprovado, eu te envio a confirmação final automaticamente por aqui."
            )
            resposta['quick_replies'] = ['cancelar'] 
            
            return resposta, estado_info
    # --- (FIM DO BLOCO NOVO) ---

    # --- Fallback (Mensagem não entendida) ---
    else:
        texto_fallback = "Não entendi o que você quis dizer. 😕\n\n"
        if estado_atual and ('agendando' in estado_atual or 'coletando' in estado_atual or 'confirmando' in estado_atual or 'construindo' in estado_atual or 'remarcando' in estado_atual):
             texto_fallback += "Se estiver no meio de um pedido, você também pode usar o botão 'voltar' (se disponível) ou 'cancelar'."
        
        resposta['body'] = texto_fallback
        resposta['quick_replies'] = ['oi'] 
        
        return resposta, estado_info

# ==============================================================================
# --- FUNÇÕES AUXILIARES DE AGENDAMENTO E MENU ---
# ==============================================================================

def gerar_lista_meses():
    meses = []
    mes_atual = date.today().replace(day=1)
    data_limite = mes_atual + relativedelta(months=12)
    while mes_atual < data_limite:
        meses.append({'ano': mes_atual.year, 'mes': mes_atual.month})
        mes_atual += relativedelta(months=1)
    return meses

def mostrar_meses_disponiveis(resposta, numero_cliente, estado_info):
    meses_info = gerar_lista_meses()
    estado_info['meses_cache'] = meses_info
    texto_meses = "🗓️ *Escolha o Mês*\n\nPara qual mês você gostaria de reservar?\n"
    
    menu_opcoes_meses = []
    for i, info in enumerate(meses_info):
        nome_mes_manual = nomes_meses.get(info['mes'], f"Mês {info['mes']}")
        nome_formatado = f"{nome_mes_manual} de {info['ano']}"
        menu_opcoes_meses.append({"id": str(i + 1), "titulo": nome_formatado})

    menu_opcoes_meses.append({"id": "voltar", "titulo": "🔙 Voltar"})
    
    resposta['body'] = texto_meses
    resposta['menu_opcoes'] = menu_opcoes_meses
    
    return resposta, estado_info

def mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info):
    try:
        dias_livres = verificar_dias_disponiveis(ano, mes) 
        estado_info['dias_cache'] = dias_livres
        nome_mes_manual = nomes_meses.get(mes, f"Mês {mes}")
        nome_formatado = f"{nome_mes_manual} de {ano}"

        if not dias_livres:
            resposta['body'] = f"Poxa, não temos mais dias disponíveis em *{nome_formatado}*. 😕\n\nPor favor, escolha outro mês."
            resposta['quick_replies'] = ['voltar'] 
        else:
            texto_dias = f"🗓️ *Escolha o Dia em {nome_formatado}*\n\n"
            texto_dias += "Estes são os dias disponíveis:\n\n"
            dias_formatados = [f"`{str(dia).zfill(2)}`" for dia in sorted(dias_livres)]
            linhas_dias = []
            for i in range(0, len(dias_formatados), 5):
                 linhas_dias.append("   ".join(dias_formatados[i:i+5]))
            texto_dias += "\n".join(linhas_dias)
            texto_dias += f"\n\nPor favor, digite o *dia* que você prefere ou *voltar*."
            resposta['body'] = texto_dias
    except Exception as e:
        print(f"Erro em mostrar_dias_disponiveis: {e}")
        resposta['body'] = "Ocorreu um erro ao buscar os dias disponíveis. Tente novamente ou digite *voltar*."
    return resposta, estado_info

def mostrar_horarios_disponiveis(resposta, dia_obj: date, estado_info):
    try:
        dia_formatado = dia_obj.strftime("%d/%m/%Y")
        texto_horarios = (
            f"⏰ *Escolha o Horário para {dia_formatado}*\n\n"
            "Nossos valores incluem a locação por até *4 horas de festa*.\n\n"
            "Você pode agendar a *chegada* dos brinquedos a qualquer hora entre as *08:00 e as 17:00*.\n\n"
            "Por favor, digite o horário desejado no formato HH:MM (ex: `14:00`), ou digite *voltar*."
        )
        resposta['body'] = texto_horarios
    except Exception as e:
        print(f"Erro em mostrar_horarios_disponiveis: {e}")
        resposta['body'] = "Ocorreu um erro ao preparar a escolha de horários. Tente novamente ou digite *voltar*."
    return resposta, estado_info

def iniciar_reserva_pendente(resposta, numero_cliente, estado_info):
    """
    PASSO 1 DO AGENDAMENTO:
    Calcula tudo, marca a reserva como PENDENTE na Agenda e no DB,
    e gera o link de pagamento.
    """
    try:
        # --- (CORREÇÃO AQUI) ---
        dia_obj = date.fromisoformat(estado_info.get('dia_obj'))
        horario_escolhido = estado_info.get('horario_escolhido')
        carrinho = estado_info.get('carrinho', [])
        
        endereco_evento = estado_info.get('endereco_completo', 'Endereço não informado') 
        nome_cliente = estado_info.get('nome_cliente', f"Cliente {numero_cliente[-4:]}")
        cpf_cliente = estado_info.get('cpf_cliente', 'Não informado') 
        frete_valor = estado_info.get('frete_valor', 0.0)
        
        # 2. Calcula todos os financeiros
        total_itens = calcular_total(carrinho)
        valor_total_geral = total_itens + frete_valor
        custo_dos_itens = calcular_custo_total(carrinho)

        distancia_km_ida = estado_info.get('distancia_km', 0.0)
        distancia_km_total_ida_volta = distancia_km_ida * 2
        litros_gastos = distancia_km_total_ida_volta / CONSUMO_CARRO_KM_L
        custo_combustivel = litros_gastos * PRECO_GASOLINA_LITRO
        lucro_liquido = valor_total_geral - custo_dos_itens - custo_combustivel

        # 3. Formata os dados para a Agenda e DB
        itens_formatado_lista = []
        for item in carrinho:
            if 'descricao_custom' in item:
                itens_formatado_lista.append(f"- {item['nome']}")
                for etapa_nome, itens_escolhidos in item['descricao_custom'].items():
                       if itens_escolhidos:
                           itens_formatados = ", ".join(itens_escolhidos)
                           itens_formatado_lista.append(f"   └ {etapa_nome}: {itens_formatados}")
            else:
                itens_formatado_lista.append(f"- {item['nome']}")
        itens_formatado_agenda = "\n".join(itens_formatado_lista)
        
        itens_para_db = json.dumps(carrinho, ensure_ascii=False)

        # 4. Tenta marcar na Agenda como PENDENTE
        print(f"Tentando marcar PENDENTE na Agenda para {numero_cliente}...")
        sucesso_agenda, evento_id = marcar_horario( 
            dia_obj, # Passa o objeto date
            horario_escolhido, 
            nome_cliente, 
            cpf_cliente, 
            itens_formatado_agenda, 
            endereco_evento, 
            valor_total_geral,
            status_pagamento='PENDENTE' 
        )
        
        if not sucesso_agenda:
            resposta['body'] = f"Oh, que pena! 😕 O dia *{dia_obj.strftime('%d/%m')}* foi reservado por outra pessoa no último segundo.\n\nVamos tentar de novo:"
            estado_info['estado'] = 'agendando_pedindo_dia'
            ano, mes = estado_info.get('ano'), estado_info.get('mes')
            return mostrar_dias_disponiveis(resposta, ano, mes, numero_cliente, estado_info)

        # 5. Registra no DB como PENDENTE
        print(f"Agenda PENDENTE OK (ID: {evento_id}). Salvando no DB...")
        registrar_venda( 
            id_google=evento_id,
            data_evento=dia_obj.isoformat(), # Passa o ISO string
            horario_evento=horario_escolhido,
            nome=nome_cliente,
            cpf=cpf_cliente,
            endereco=endereco_evento,
            itens_json=itens_para_db,
            faturamento=valor_total_geral,
            custo_op=custo_dos_itens,
            lucro=lucro_liquido,
            distancia_km=distancia_km_ida,
            custo_combustivel=custo_combustivel,
            frete_valor_pago=frete_valor,
            status_pagamento='PENDENTE' 
        )
        
        # 6. Dispara a sincronização (para o Excel mostrar 'PENDENTE')
        iniciar_sincronizacao_excel()

        # 7. Salva o ID do evento pendente no estado do usuário
        estado_info['pending_event_id'] = evento_id
        
        # 8. Gera o link de pagamento
        valor_sinal = round(valor_total_geral / 2.0, 2)
        titulo_pagamento = f"Sinal 50% - Reserva {dia_obj.strftime('%d/%m/%Y')}"
        
        link_pagamento = criar_link_pagamento_sinal(
            titulo_pagamento, 
            valor_total_geral, 
            numero_cliente, 
            evento_id       
        )
        
        if link_pagamento:
            # 9. SUCESSO: Envia o link e muda o estado
            resposta['body'] = (
                f"Perfeito! Sua pré-reserva para *{dia_obj.strftime('%d/%m/%Y')} às {horario_escolhido}* está feita.\n\n"
                f"Valor Total: *R$ {formatar_reais(valor_total_geral)}*\n"
                f"Valor do Sinal (50%): *R$ {formatar_reais(valor_sinal)}*\n\n"
                "Para confirmar, por favor, realize o pagamento do sinal através deste link:\n"
                f"{link_pagamento}\n\n"
                "⚠️ *Atenção: A sua reserva expira em 24 horas se o pagamento não for confirmado.* ⚠️\n\n"
                "Eu te avisarei *automaticamente* assim que o pagamento for aprovado."
            )
            estado_info['estado'] = 'aguardando_confirmacao_pagamento'
        else:
            # 10. FALHA MP: (Raro)
            resposta['body'] = "Tive um problema ao gerar seu link de pagamento. 😕\n\nPor favor, tente confirmar novamente."
            estado_info['estado'] = 'confirmando_pedido'
            resposta['quick_replies'] = ['sim', 'não'] 
            
    except Exception as e:
        print(f"Erro em iniciar_reserva_pendente: {e}")
        resposta['body'] = "Ocorreu um erro ao pré-agendar. Tente novamente ou digite *voltar*."
        
    return resposta, estado_info


def finalizar_reserva_pos_pagamento(resposta, numero_cliente, event_id, estado_info):
    """
    PASSO 2 DO AGENDAMENTO:
    Chamado pelo Webhook DEPOIS que o pagamento é APROVADO.
    Confirma a reserva na Agenda e no DB.
    """
    try:
        # 1. Confirma na Agenda Google
        sucesso_agenda = confirmar_pagamento_evento(event_id)
        
        if not sucesso_agenda:
            raise Exception(f"Webhook não conseguiu confirmar o evento {event_id} na agenda.")

        # 2. Confirma no Banco de Dados
        atualizar_status_pagamento(event_id, 'CONFIRMADO')
        
        # 3. Dispara a sincronização
        iniciar_sincronizacao_excel()
            
        # 4. Responde ao cliente e limpa o estado
        dia_obj_str = estado_info.get('dia_obj')
        horario_escolhido = estado_info.get('horario_escolhido')
        endereco_evento = estado_info.get('endereco_completo', 'Não informado') 
        
        # --- (CORREÇÃO AQUI) ---
        if isinstance(dia_obj_str, str):
            dia_obj = date.fromisoformat(dia_obj_str)
        else:
            dia_obj = dia_obj_str # Já é um objeto (caso raro)

        dia_formatado = dia_obj.strftime("%d/%m/%Y")
        nome_dia_semana = dia_obj.strftime('%A').capitalize() 
        
        resposta['body'] = (
            "Pagamento confirmado! 🎉\n\n"
            "Sua reserva está *100% CONFIRMADA*.\n\n"
            f"🗓️ *Quando:* {dia_formatado} ({nome_dia_semana}) às {horario_escolhido}\n"
            f"📍 *Onde:* {endereco_evento}\n\n"
            "Muito obrigado pela confiança! Entraremos em contato em breve para acertar os detalhes restantes."
        )
        estado_info = {'estado': None, 'carrinho': [], 'frete_valor': -1.0}
            
    except Exception as e:
        print(f"Erro em finalizar_reserva_pos_pagamento: {e}")
        resposta['body'] = "Ocorreu um erro crítico ao finalizar sua reserva após o pagamento. Por favor, entre em contato conosco e informe este erro."
    return resposta, estado_info


def menu_principal(resposta):
    resposta['media'] = [f"{BASE_URL}/image/Principal.png"]
    resposta['body'] = (
        "Olá! ✨ Bem-vindo(a) ao mundo mágico da *BI & NU Kids*!\n\n"
        "Como podemos começar a nossa jornada hoje?\n\n"
        "A qualquer momento, você pode digitar *ver carrinho* para ver seu pedido."
    )
    resposta['menu_opcoes'] = [
        {"id": "1", "titulo": "1️⃣ Explorar Brinquedos 🧸"},
        {"id": "2", "titulo": "2️⃣ Montar Combos Mágicos 🎁"},
        {"id": "3", "titulo": "3️⃣ Gerenciar minha Reserva ✏️"}
    ]
    resposta['usar_legenda'] = True
    return resposta