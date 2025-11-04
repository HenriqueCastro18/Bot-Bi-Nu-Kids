# database.py
import sqlite3
from datetime import datetime, date # Importa 'date'
import json # Importa 'json'

DB_NAME = 'financeiro.db'

# --- (NOVO) Função movida do logic.py ---
def def_json_serial(obj):
    """Tradutor para o JSON salvar datas e datetimes."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
# --- Fim da nova função ---


def inicializar_banco():
    """Cria as tabelas e adiciona colunas se não existirem."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # --- Tabela de Vendas ---
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_google_calendar TEXT UNIQUE,
        data_confirmacao TEXT,
        data_evento TEXT,
        horario_evento TEXT, 
        nome_cliente TEXT,
        cpf_cliente TEXT,
        endereco TEXT,
        itens_vendidos TEXT,
        faturamento_bruto REAL,
        custo_operacional REAL,
        lucro_liquido REAL,
        status TEXT DEFAULT 'CONFIRMADO',
        distancia_km REAL,
        custo_combustivel REAL,
        frete_valor_pago REAL DEFAULT 0.0,
        status_pagamento TEXT DEFAULT 'CONFIRMADO' 
    )
    ''')
    
    colunas_existentes_vendas = [col[1] for col in cursor.execute(f"PRAGMA table_info(vendas)").fetchall()]
    
    if 'distancia_km' not in colunas_existentes_vendas:
        cursor.execute('ALTER TABLE vendas ADD COLUMN distancia_km REAL')
    if 'custo_combustivel' not in colunas_existentes_vendas: 
        cursor.execute('ALTER TABLE vendas ADD COLUMN custo_combustivel REAL')
    if 'frete_valor_pago' not in colunas_existentes_vendas:
        cursor.execute('ALTER TABLE vendas ADD COLUMN frete_valor_pago REAL DEFAULT 0.0')
    if 'horario_evento' not in colunas_existentes_vendas:
        cursor.execute('ALTER TABLE vendas ADD COLUMN horario_evento TEXT')
    if 'status_pagamento' not in colunas_existentes_vendas:
        cursor.execute("ALTER TABLE vendas ADD COLUMN status_pagamento TEXT DEFAULT 'CONFIRMADO'")

    # --- (NOVA TABELA) Para Estados de Conversa ---
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversa_estados (
        chat_id TEXT PRIMARY KEY,
        estado_json TEXT
    )
    ''')
    # --- Fim da nova tabela ---

    conn.commit()
    conn.close()

# ==============================================================================
# --- FUNÇÕES DE VENDAS (Existentes) ---
# ==============================================================================

def registrar_venda(id_google, data_evento, horario_evento, nome, cpf, endereco, itens_json, faturamento, custo_op, lucro, distancia_km, custo_combustivel, frete_valor_pago, status_pagamento: str = 'CONFIRMADO'):
    """Insere uma nova venda no banco (podendo ser pendente ou confirmada)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO vendas (
            id_google_calendar, data_confirmacao, data_evento, horario_evento, nome_cliente, 
            cpf_cliente, endereco, itens_vendidos, faturamento_bruto, 
            custo_operacional, lucro_liquido, distancia_km, custo_combustivel, 
            frete_valor_pago, status_pagamento 
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_google, datetime.now().isoformat(), data_evento, horario_evento, nome, cpf, 
            endereco, itens_json, faturamento, custo_op, lucro, 
            distancia_km, custo_combustivel, frete_valor_pago, status_pagamento
        ))
        conn.commit()
        conn.close()
        print(f"SUCESSO: Venda registrada no DB para {nome} (Status: {status_pagamento})")
    except Exception as e:
        print(f"ERRO ao registrar venda no DB: {e}")

def atualizar_status_pagamento(id_google, novo_status):
    """Atualiza o status de pagamento de uma venda (ex: PENDENTE -> CONFIRMADO)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE vendas 
        SET status_pagamento = ?
        WHERE id_google_calendar = ?
        ''', (novo_status, id_google))
        conn.commit()
        conn.close()
        print(f"SUCESSO: Status de pagamento do {id_google} atualizado para {novo_status}.")
    except Exception as e:
        print(f"ERRO ao atualizar status de pagamento no DB: {e}")

def deletar_venda_por_id_google(id_google):
    """Remove uma venda do DB (usado para reservas pendentes expiradas)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM vendas WHERE id_google_calendar = ?",
            (id_google,)
        )
        conn.commit()
        conn.close()
        print(f"SUCESSO: Venda pendente/expirada {id_google} deletada do DB.")
    except Exception as e:
        print(f"ERRO ao deletar venda pendente do DB: {e}")

def buscar_todas_vendas():
    """Busca todas as vendas registradas no banco de dados."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, id_google_calendar, data_evento, horario_evento, nome_cliente, cpf_cliente, endereco, 
                itens_vendidos, faturamento_bruto, custo_operacional, lucro_liquido, distancia_km, 
                custo_combustivel, frete_valor_pago, status_pagamento
            FROM vendas 
            ORDER BY data_evento, horario_evento
        """)
        
        vendas = cursor.fetchall()
        return vendas
    except sqlite3.Error as e:
        print(f"Erro ao buscar todas as vendas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def cancelar_venda_por_id(id_google):
    """Atualiza o status para 'CANCELADO' e zera os valores."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE vendas 
        SET status = 'CANCELADO', 
            status_pagamento = 'CANCELADO', 
            faturamento_bruto = 0, 
            custo_operacional = 0, 
            lucro_liquido = 0,
            distancia_km = 0,
            custo_combustivel = 0,
            frete_valor_pago = 0,
            horario_evento = NULL
        WHERE id_google_calendar = ?
        ''', (id_google,))
        conn.commit()
        conn.close()
        print(f"SUCESSO: Venda {id_google} cancelada no DB.")
    except Exception as e:
        print(f"ERRO ao cancelar venda no DB: {e}")

def atualizar_data_horario_venda(id_google, nova_data_evento, novo_horario_evento):
    """Atualiza a data e o horário do evento (remarcação)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE vendas 
        SET data_evento = ?, horario_evento = ? 
        WHERE id_google_calendar = ?
        ''', (nova_data_evento, novo_horario_evento, id_google))
        conn.commit()
        conn.close()
        print(f"SUCESSO: Venda {id_google} remarcada no DB para {nova_data_evento} às {novo_horario_evento}.")
    except Exception as e:
        print(f"ERRO ao remarcar venda no DB: {e}")

def get_active_google_ids():
    """Busca todos os IDs do Google Calendar que estão com status 'CONFIRMADO'."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id_google_calendar FROM vendas WHERE status = 'CONFIRMADO'")
        ids = [row[0] for row in cursor.fetchall() if row[0] is not None]
        conn.close()
        return ids
    except Exception as e:
        print(f"ERRO ao buscar IDs ativos do DB: {e}")
        return []

# ==============================================================================
# --- (NOVAS FUNÇÕES) GERENCIAMENTO DE ESTADO DA CONVERSA ---
# ==============================================================================

def db_carregar_todos_estados():
    """Carrega TODOS os estados de usuários do DB para a memória (usado na inicialização)."""
    # Esta função é opcional, mas boa para se você quiser manter o bot_telegram.py
    # carregando tudo na inicialização. Para o Twilio (app.py),
    # é melhor carregar usuário por usuário.
    print("Carregando todos os estados de conversa do DB...")
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, estado_json FROM conversa_estados")
        rows = cursor.fetchall()
        conn.close()
        
        user_states = {}
        for row in rows:
            chat_id = row[0]
            try:
                user_states[chat_id] = json.loads(row[1])
            except Exception as e:
                print(f"ERRO: Falha ao decodificar JSON para o chat_id {chat_id}: {e}")
        print(f"Carregados {len(user_states)} estados.")
        return user_states
    except Exception as e:
        print(f"ERRO CRÍTICO ao carregar todos os estados: {e}")
        return {}

def db_carregar_estado_usuario(chat_id: str) -> dict:
    """Carrega o estado de um usuário específico do DB."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT estado_json FROM conversa_estados WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Encontrado, decodifica o JSON e retorna
            return json.loads(row[0])
        else:
            # Não encontrado, retorna um estado novo (padrão)
            return {'estado': None, 'carrinho': [], 'frete_valor': -1.0}
    except Exception as e:
        print(f"ERRO ao carregar estado para {chat_id}: {e}")
        return {'estado': None, 'carrinho': [], 'frete_valor': -1.0} # Retorna padrão em caso de erro

def db_salvar_estado_usuario(chat_id: str, estado_dict: dict):
    """Salva (ou atualiza) o estado de um usuário específico no DB."""
    try:
        # Converte o dicionário Python para uma string JSON
        estado_json = json.dumps(estado_dict, default=def_json_serial)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # INSERT OR REPLACE (UPSERT): Insere se for novo, substitui se já existir
        cursor.execute('''
        INSERT OR REPLACE INTO conversa_estados (chat_id, estado_json)
        VALUES (?, ?)
        ''', (chat_id, estado_json))
        conn.commit()
        conn.close()
        # print(f"Estado salvo para {chat_id}") # (Opcional: pode poluir o log)
    except Exception as e:
        print(f"ERRO CRÍTICO ao salvar estado para {chat_id}: {e}")

def db_deletar_estado_usuario(chat_id: str):
    """Remove o estado de um usuário do DB (quando ele volta ao menu principal)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversa_estados WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        print(f"Estado limpo para {chat_id} (sessão finalizada).")
    except Exception as e:
        print(f"ERRO ao deletar estado para {chat_id}: {e}")