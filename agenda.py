# agenda.py
from datetime import date, datetime, time, timedelta, timezone
from dateutil.relativedelta import relativedelta
import calendar
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

# --- (NOVO) Import para limpar o DB ---
from database import deletar_venda_por_id_google, cancelar_venda_por_id

# --- CONFIGURAÇÃO ---
project_path = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(project_path, 'credentials.json')

CALENDAR_ID = '174ad250bdc61e357abcffacb105c9d125a74ef5caad21f5a920609c40bb25e9@group.calendar.google.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']
HORARIOS_PADRAO_FESTA = ["10:00", "14:00", "18:00"]

# --- Conexão com a API ---
try:
    creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
except Exception as e:
    print(f"Erro ao conectar com a API do Google: {e}")
    service = None

# --- FUNÇÕES ---

def obter_eventos_do_mes(ano, mes):
    """Função auxiliar para buscar todos os eventos de um mês de uma só vez."""
    if not service:
        return []
    try:
        start_of_month = datetime(ano, mes, 1)
        end_of_month = start_of_month + relativedelta(months=1)

        time_min = start_of_month.isoformat() + 'Z'
        time_max = end_of_month.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        print(f"Erro ao obter eventos do mês {mes}/{ano}: {e}")
        return []

# --- (NOVA FUNÇÃO HELPER) ---
def _is_evento_pendente_expirado(evento) -> bool:
    """Verifica se um evento é PENDENTE e tem mais de 24h."""
    summary = evento.get('summary', '')
    description = evento.get('description', '')
    
    # Verifica o título ou a descrição pela chave de status
    is_pending = "[PENDENTE]" in summary or "STATUS_KEY::PENDENTE" in description
    
    if not is_pending:
        return False # É um evento confirmado, não está expirado.

    try:
        # 'created' é fornecido pela API do Google em formato UTC (com 'Z')
        created_str = evento['created'] # Ex: '2025-10-30T18:16:23.000Z'
        created_time_utc = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
        
        # Pega o tempo atual em UTC
        agora_utc = datetime.now(timezone.utc)
        
        # Verifica se já passaram 24 horas
        is_expired = (agora_utc - created_time_utc) > timedelta(hours=24)
        
        if is_expired:
            print(f"Info: Evento {evento['id']} é PENDENTE e EXPIRADO.")
            
        return is_expired
    except Exception as e:
        print(f"Erro ao verificar tempo de evento pendente {evento['id']}: {e}")
        return False # Em caso de dúvida, não expira

# --- FUNÇÃO ATUALIZADA (LÓGICA PRINCIPAL) ---
def verificar_dias_disponiveis(ano: int, mes: int):
    """
    Verifica todos os dias em um mês que estão COMPLETAMENTE livres.
    (NOVO) Ignora eventos PENDENTES com mais de 24h.
    """
    hoje = date.today()
    dias_disponiveis = []
    
    # 1. Busca todos os eventos do mês de uma só vez
    eventos_do_mes = obter_eventos_do_mes(ano, mes)
    
    # 2. Cria um conjunto com os dias que já estão ocupados
    dias_ocupados = set()
    for evento in eventos_do_mes:
        
        # (NOVO) Verifica se o evento está pendente e expirado
        if _is_evento_pendente_expirado(evento):
            print(f"Info: Ignorando evento pendente expirado {evento['id']} ao listar dias.")
            # NÃO adiciona a dias_ocupados. O dia é considerado "disponível".
            continue 
            
        # Lógica antiga (agora só roda para eventos confirmados ou pendentes válidos)
        start_str = evento['start'].get('dateTime', evento['start'].get('date'))
        dia_evento = date.fromisoformat(start_str.split('T')[0])
        
        if dia_evento.month == mes and dia_evento.year == ano:
            dias_ocupados.add(dia_evento.day)
        
    num_dias_mes = calendar.monthrange(ano, mes)[1]
    
    # 3. Itera pelos dias do mês, verificando se estão na lista de ocupados
    for dia_num in range(1, num_dias_mes + 1):
        dia_atual = date(ano, mes, dia_num)
        
        if dia_atual < hoje:
            continue
            
        if dia_num not in dias_ocupados:
            dias_disponiveis.append(dia_num)
            
    return dias_disponiveis

# --- FUNÇÃO ATUALIZADA (SIMPLIFICADA) ---
def verificar_horarios_disponiveis(dia: date):
    """
    Retorna a lista de horários padrão, pois o dia já foi verificado como livre.
    Filtra horários que já passaram se o dia for hoje.
    """
    hoje = date.today()
    agora = datetime.now()

    if dia == hoje:
        return ["08:00", "17:00"] 
    else:
        return ["08:00", "17:00"]


# --- (FUNÇÃO ATUALIZADA) VERIFICAR SE O DIA ESTÁ 100% LIVRE ---
def _is_dia_completamente_livre(dia: date):
    """
    Função auxiliar interna.
    Retorna True se o dia estiver livre.
    Retorna False se tiver eventos (CONFIRMADOS ou PENDENTES VÁLIDOS).
    (NOVO) Deleta eventos PENDENTES EXPIRADOS que encontrar.
    """
    if not service:
        # Se o serviço falhar, assume que não está livre para segurança
        return False
    try:
        start_time_check = datetime.combine(dia, time.min).isoformat() + 'Z'
        end_time_check = datetime.combine(dia, time.max).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_time_check,
            timeMax=end_time_check,
            singleEvents=True
        ).execute()
        
        eventos_do_dia = events_result.get('items', [])
        
        if not eventos_do_dia:
            return True # Dia 100% livre, sem eventos.

        eventos_validos_encontrados = 0
        ids_para_deletar = []

        for evento in eventos_do_dia:
            if _is_evento_pendente_expirado(evento):
                # Este evento não conta como "ocupado" e deve ser deletado
                ids_para_deletar.append(evento['id'])
            else:
                # Este é um evento VÁLIDO (Confirmado ou Pendente dentro das 24h)
                eventos_validos_encontrados += 1
        
        # (NOVO) Rotina de limpeza
        if ids_para_deletar:
            print(f"Limpando {len(ids_para_deletar)} reservas pendentes expiradas do dia {dia}...")
            for event_id in ids_para_deletar:
                # Deleta da Agenda E do DB
                cancelar_evento_expirado(event_id) 

        # O dia está livre SOMENTE se não houver eventos válidos
        return eventos_validos_encontrados == 0
        
    except Exception as e:
        print(f"Erro ao verificar dia livre ({dia}): {e}")
        return False # Segurança: assume que está ocupado


# --- FUNÇÃO ATUALIZADA (Recebe CPF e NOVO status_pagamento) ---
def marcar_horario(dia: date, horario_str: str, nome_cliente: str, cpf_cliente: str, itens_pedido_formatado: str, endereco_evento: str, valor_total: float, status_pagamento: str = 'CONFIRMADO'):
    """Cria um novo evento (PENDENTE ou CONFIRMADO), fazendo verificação final."""
    if not service:
        return False, None # Retorna (Falha, None)

    try:
        # --- VERIFICAÇÃO FINAL (agora limpa pendentes expirados) ---
        # Antes de marcar, verifica se o dia AINDA está 100% livre
        if not _is_dia_completamente_livre(dia):
            print(f"RACE CONDITION: Tentativa de marcar no dia {dia}, que está ocupado por evento válido.")
            return False, None # Retorna (Falha, None)
        # --- FIM DA VERIFICAÇÃO ---

        hora, minuto = map(int, horario_str.split(':'))
        start_time = datetime.combine(dia, time(hora, minuto))
        end_time = start_time + timedelta(hours=4) # Duração de 4 horas
        
        # (NOVO) Define o título e a chave de status
        status_key = ""
        summary = ""
        if status_pagamento == 'PENDENTE':
            summary = f"[PENDENTE] 🎉 Aluguel para {nome_cliente} - R$ {valor_total:,.2f}"
            status_key = "STATUS_KEY::PENDENTE::END_STATUS"
        else:
            summary = f"🎉 Aluguel para {nome_cliente} - R$ {valor_total:,.2f}"
            status_key = "STATUS_KEY::CONFIRMADO::END_STATUS"
        
        description = (
            f"<b>Cliente:</b> {nome_cliente}\n"
            f"<b>CPF do Responsável:</b> {cpf_cliente}\n"
            f"<b>Endereço do Evento:</b>\n{endereco_evento}\n\n"
            f"<b>Itens Reservados:</b>\n{itens_pedido_formatado}\n\n" 
            f"<b>Valor Total do Pedido:</b> R$ {valor_total:,.2f}\n\n"
            f"<i>Agendamento realizado via Chatbot.</i>\n\n"
            f"\n"
            f"CPF_KEY::{cpf_cliente}::END_CPF\n"
            f"{status_key}" # <-- (NOVO) Adiciona a chave de status
        )

        evento = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Sao_Paulo'},
        }

        evento_criado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
        
        # Retorna Sucesso E o ID do evento
        return True, evento_criado.get('id') 
        
    except Exception as e:
        print(f"Erro ao marcar horário na agenda: {e}")
        return False, None # Retorna (Falha, None)

# --- (FUNÇÃO ATUALIZADA) BUSCAR RESERVA(S) POR CPF ---
def buscar_eventos_por_cpf(cpf: str):
    """Busca *todos* os eventos FUTUROS (pendentes ou confirmados) que contenham a chave de CPF."""
    if not service:
        return [] 
    try:
        chave_busca = f"CPF_KEY::{cpf}::END_CPF"
        time_min = datetime.now().isoformat() + 'Z' 

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            q=chave_busca, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        items = events_result.get('items', [])
        eventos_encontrados = [] 
        
        if not items:
            return [] 
            
        for item in items:
            # (NOVO) Ignora eventos expirados que ainda não foram limpos
            if _is_evento_pendente_expirado(item):
                continue
                
            if chave_busca in item.get('description', ''):
                eventos_encontrados.append(item) 
        
        return eventos_encontrados 
        
    except Exception as e:
        print(f"Erro ao buscar eventos por CPF ({cpf}): {e}")
        return [] 

# --- (FUNÇÃO DE CANCELAMENTO DO USUÁRIO) ---
def cancelar_evento(event_id: str):
    """Cancela (deleta) um evento da agenda e atualiza o DB para 'CANCELADO'."""
    if not service:
        return False
    try:
        # 1. Deleta da Agenda
        service.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        
        # 2. Atualiza o DB (marca como cancelado e zera valores)
        cancelar_venda_por_id(event_id)
        
        return True
    except Exception as e:
        print(f"Erro ao cancelar evento ({event_id}): {e}")
        return False

# --- (NOVA FUNÇÃO) PARA LIMPEZA AUTOMÁTICA ---
def cancelar_evento_expirado(event_id: str):
    """(AUTO) Deleta evento da Agenda e DELETA do DB."""
    if not service:
        return False
    try:
        # 1. Deleta da Agenda Google
        service.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        print(f"SUCESSO: Evento expirado {event_id} deletado da Agenda.")
        
        # 2. Deleta do Banco de Dados
        deletar_venda_por_id_google(event_id)
        
        return True
    except Exception as e:
        # Se falhar (ex: já foi deletado), apenas loga
        print(f"Info: Erro ao deletar evento expirado {event_id} (pode já ter sido limpo): {e}")
        return False

# --- (NOVA FUNÇÃO) PARA CONFIRMAR PAGAMENTO ---
def confirmar_pagamento_evento(event_id: str):
    """Atualiza um evento de PENDENTE para CONFIRMADO no Google Calendar."""
    if not service:
        return False
    try:
        # 1. Busca o evento pendente
        evento = service.events().get(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        
        # 2. Atualiza o Título e a Descrição
        evento['summary'] = evento.get('summary', '').replace("[PENDENTE] ", "")
        
        desc = evento.get('description', '')
        desc = desc.replace("STATUS_KEY::PENDENTE::END_STATUS", "STATUS_KEY::CONFIRMADO::END_STATUS")
        evento['description'] = desc
        
        # 3. Envia a atualização
        service.events().update(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            body=evento
        ).execute()
        
        print(f"SUCESSO: Evento {event_id} confirmado na Agenda.")
        return True
        
    except Exception as e:
        print(f"ERRO ao confirmar pagamento do evento {event_id} na Agenda: {e}")
        return False

# --- (FUNÇÃO EXISTENTE) REMARCAR EVENTO ---
def remarcar_evento(event_id: str, novo_dia: date, novo_horario_str: str):
    """
    Atualiza a data e hora de um evento existente.
    Primeiro, verifica se o NOVO dia está livre (e limpa expirados).
    """
    if not service:
        return False
    try:
        # 1. Verifica se o NOVO dia está 100% livre (agora limpa expirados)
        if not _is_dia_completamente_livre(novo_dia):
            print(f"REMARCAÇÃO FALHOU: O novo dia {novo_dia} não está livre.")
            return False
            
        # 2. Se estiver livre, busca o evento original para pegar os detalhes
        evento_original = service.events().get(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        
        # 3. Calcula os novos horários
        hora, minuto = map(int, novo_horario_str.split(':'))
        new_start_time = datetime.combine(novo_dia, time(hora, minuto))
        new_end_time = new_start_time + timedelta(hours=4) # Mantém 4h de duração
        
        # 4. Atualiza o corpo do evento com as novas datas
        evento_original['start'] = {'dateTime': new_start_time.isoformat(), 'timeZone': 'America/Sao_Paulo'}
        evento_original['end'] = {'dateTime': new_end_time.isoformat(), 'timeZone': 'America/Sao_Paulo'}
        
        # 5. Envia a atualização
        service.events().update(
            calendarId=CALENDAR_ID,
            eventId=event_id,
            body=evento_original
        ).execute()
        
        return True
        
    except Exception as e:
        print(f"Erro ao remarcar evento ({event_id}): {e}")
        return False

# --- (FUNÇÃO EXISTENTE) PARA SINCRONIZAÇÃO ---
def verificar_evento_existe(event_id: str):
    """Verifica se um evento com um ID específico ainda existe no calendário."""
    if not service:
        print(f"AVISO: Serviço do Google não iniciado. Assumindo que evento {event_id} existe.")
        return True 
    try:
        service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"Info: Evento {event_id} não encontrado no Google Calendar (provavelmente deletado): {e}")
        return False