import sqlite3
import os
from database import DB_NAME # Puxa o nome do DB (financeiro.db) do seu arquivo

def limpar_tabela_vendas():
    """Apaga todos os dados da tabela 'vendas' e reseta o ID."""
    
    if not os.path.exists(DB_NAME):
        print(f"Erro: Banco de dados '{DB_NAME}' não encontrado.")
        print("Execute o 'app.py' pelo menos uma vez para criar o banco.")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        print(f"Conectado ao '{DB_NAME}'. Limpando a tabela 'vendas'...")
        cursor.execute("DELETE FROM vendas")
        
        print("Resetando o contador de ID (autoincrement)...")
        # Reseta o contador para que o próximo ID seja 1
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='vendas'")
        
        conn.commit()
        conn.close()
        
        print("\n-------------------------------------------------")
        print("Banco de dados limpo com sucesso.")
        print("A tabela 'vendas' está vazia e o ID foi resetado.")
        print("-------------------------------------------------")
    
    except Exception as e:
        print(f"Ocorreu um erro ao limpar o banco de dados: {e}")

if __name__ == '__main__':
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!! AVISO !!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("Esta ação é IRREVERSÍVEL e vai apagar TODOS OS REGISTROS de vendas")
    print(f"do arquivo '{DB_NAME}'.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    
    # Pergunta de segurança
    confirm = input(f"Tem CERTEZA que deseja limpar a tabela 'vendas'? (s/n): ").lower()
    
    if confirm == 's' or confirm == 'sim':
        limpar_tabela_vendas()
    else:
        print("Operação cancelada.")