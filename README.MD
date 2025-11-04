# Bot de Aluguel de Brinquedos (BI & NU Kids)

Este é um bot completo para WhatsApp (via Twilio) e Telegram, projetado para gerenciar o aluguel de brinquedos e equipamentos para festas infantis. O projeto integra Google Calendar, Google Maps e Mercado Pago para um fluxo de reserva totalmente automatizado.

## 🚀 Funcionalidades Principais

* **Catálogo Completo:** Navegação por categorias, combos e itens avulsos.
* **Agendamento Inteligente:** Integração em tempo real com **Google Calendar** para verificar disponibilidade de dias e horários.
* **Cálculo de Frete:** Integração com a API do **Google Maps** para calcular a distância e o valor do frete.
* **Pagamento de Sinal:** Geração de link de pagamento (50% do valor) via **Mercado Pago**.
* **Confirmação Automática:** O bot usa Webhooks para ouvir a confirmação do Mercado Pago. Ao receber, ele atualiza o evento no Google Calendar e salva a venda no banco de dados.
* **Sincronização Financeira:** Gera uma planilha **Excel (`.xlsx`)** com todos os dados da venda (custos, faturamento, lucro) e a envia por **e-mail**.
* **Gestão de Estado:** Salva o progresso da conversa de cada usuário em um banco de dados SQLite.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python
* **Servidor Web/Webhooks:** Flask, Gunicorn
* **Mensageria:** Twilio (WhatsApp), Python-Telegram-Bot (Telegram)
* **Banco de Dados:** SQLite
* **APIs Externas:**
    * Google Calendar API
    * Google Maps Geocoding & Distance Matrix API
    * Mercado Pago SDK
* **Manipulação de Dados:** OpenPyXL (Excel), SMTPLib (E-mail)

## 📦 Instalação e Configuração

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git](https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git)
    cd NOME_DO_REPOSITORIO
    ```

2.  **Crie um ambiente virtual e instale as dependências:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # (No Windows: venv\Scripts\activate)
    pip install -r requirements.txt
    ```

3.  **Configure as Credenciais:**
    * **Google:** Crie um projeto no Google Cloud, ative as APIs (Calendar, Maps) e gere um arquivo `credentials.json` de conta de serviço. Coloque-o na raiz do projeto.
    * **Outras Chaves:** Renomeie `config.py.example` para `config.py` e preencha todas as chaves (Telegram, Twilio, Mercado Pago, E-mail, etc.).

4.  **Inicialize o Banco de Dados:**
    ```bash
    python -c "import database; database.inicializar_banco()"
    ```

## 🏃 Como Rodar (Localmente)

Este projeto requer múltiplos serviços rodando simultaneamente. Você precisará de 3 terminais.

1.  **Terminal 1: Servidor de Webhooks (Flask/Gunicorn):**
    Este servidor recebe as respostas do WhatsApp, do Mercado Pago e serve as imagens do catálogo.
    ```bash
    gunicorn image_server:app
    ```

2.  **Terminal 2: Bot do Telegram:**
    Este script inicia o "polling" que fica ouvindo o Telegram.
    ```bash
    python bot_telegram.py
    ```

3.  **Terminal 3: Ngrok:**
    O Ngrok cria um túnel público para o seu servidor local (Gunicorn), permitindo que Twilio e Mercado Pago enviem os webhooks.
    ```bash
    # (Supondo que o Gunicorn esteja na porta 8000)
    ngrok http 8000
    ```
    *Obs: Pegue a URL `https...` gerada pelo Ngrok e cole-a na variável `BASE_URL` dentro do `config.py` e `catalogo.py`.*