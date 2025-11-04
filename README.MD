# Bot de Aluguel de Brinquedos (BI & NU Kids)

Este é um bot completo para WhatsApp (via Twilio) e Telegram, projetado para gerenciar o aluguel de brinquedos e equipamentos para festas infantis. Ele gerencia todo o fluxo: consulta o catálogo, verifica disponibilidade no Google Calendar, calcula frete via Google Maps e processa o pagamento (sinal) com Mercado Pago. Após a confirmação (webhook), atualiza a agenda e envia um relatório financeiro por e-mail.

## 📺 Demonstração em Ação

Assista aos vídeos abaixo para ver as principais funcionalidades do bot em ação.

---

### Vídeo 1: Testando o Fluxo Principal do Bot
*(Demonstração completa do fluxo de reserva no WhatsApp, desde a escolha no catálogo, cálculo de frete, agendamento no Google Calendar e geração do link de pagamento do Mercado Pago.)*

[![Demonstração do Bot no WhatsApp](https://img.youtube.com/vi/UNsJ8uvj7Y8/0.jpg)](https://www.youtube.com/watch?v=UNsJ8uvj7Y8)

[Link Direto para o Vídeo 1](https://www.youtube.com/watch?v=UNsJ8uvj7Y8)

---

### Vídeo 2: Testando o Reagendamento
*(Demonstração da funcionalidade de reagendamento de um evento existente, mostrando a interação do bot com o Google Calendar para alterar a data.)*

[![Demonstração do Bot no Telegram](https://img.youtube.com/vi/6HPeNNPDBmQ/0.jpg)](https://www.youtube.com/watch?v=6HPeNNPDBmQ)

[Link Direto para o Vídeo 2](https://www.youtube.com/watch?v=6HPeNNPDBmQ)

---

## 🚀 Funcionalidades Principais

* **Multi-Plataforma:** Funciona de forma idêntica no **WhatsApp** (via Twilio) e no **Telegram**.
* **Catálogo Completo:** Navegação por categorias, combos e itens avulsos com imagens, descrições e preços.
* **Agendamento Inteligente:** Integração em tempo real com a API do **Google Calendar** para verificar dias e horários disponíveis, evitando conflitos de reserva.
* **Cálculo de Frete:** Integração com a API do **Google Maps** (Distance Matrix) para calcular a distância exata até o endereço do cliente e definir o valor do frete.
* **Pagamento de Sinal:** Geração de link de pagamento (50% do valor) via **Mercado Pago SDK**.
* **Confirmação Automática:** O bot usa Webhooks para "ouvir" a confirmação do Mercado Pago. Ao receber, ele:
    1.  Atualiza o evento no Google Calendar de "Pendente" para "Confirmado".
    2.  Salva a venda no banco de dados SQLite.
    3.  Avisa o cliente da confirmação.
* **Reagendamento:** Permite ao cliente buscar seus eventos futuros (pelo CPF) e solicitar o reagendamento.
* **Sincronização Financeira:** Após uma venda confirmada, o bot automaticamente:
    1.  Atualiza uma planilha **Excel (`.xlsx`)** com todos os dados da venda (custos, faturamento, lucro).
    2.  Envia esta planilha atualizada por **e-mail** (via SMTPLib) para o administrador.
* **Gestão de Estado:** Salva o progresso da conversa de cada usuário (carrinho, etapa atual) em um banco de dados SQLite, permitindo que o usuário continue de onde parou.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python
* **Servidores Web/API:** Flask, Gunicorn
* **Mensageria:** Twilio (WhatsApp), Python-Telegram-Bot (Telegram)
* **Banco de Dados:** SQLite
* **APIs Externas:**
    * Google Calendar API
    * Google Maps Geocoding & Distance Matrix API
    * Mercado Pago SDK
* **Manipulação de Dados:** OpenPyXL (para gerar planilhas Excel)
* **Notificação:** SMTPLib (para envio de e-mail com relatórios)

## 🏗️ Como Funciona (Arquitetura)

Este projeto é modular e requer 3 serviços principais rodando em paralelo:

1.  **Servidor WhatsApp (`app.py`):** Um servidor Flask que recebe os webhooks da Twilio (mensagens do WhatsApp).
2.  **Servidor de Imagens e Pagamentos (`image_server.py`):** Um segundo servidor Flask que:
    * Serve as imagens dos produtos para o bot (`/image/...`).
    * Recebe os webhooks de confirmação do Mercado Pago (`/webhook/mercadopago`).
3.  **Bot do Telegram (`bot_telegram.py`):** Um script que roda em *polling*, conectando-se diretamente à API do Telegram para ler e enviar mensagens.

O "cérebro" do projeto está no `logic.py`, que é chamado tanto pelo `app.py` quanto pelo `bot_telegram.py` para processar as mensagens e manter o estado da conversa.

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

3.  **Configure as Credenciais (Arquivos Ignorados):**
    * **Google:** Crie um projeto no Google Cloud, ative as APIs (Calendar, Maps) e gere um arquivo `credentials.json` de conta de serviço. Coloque-o na raiz do projeto.
    * **Outras Chaves:** Renomeie `config.py.example` para `config.py` e preencha **todas** as chaves (Telegram, Twilio, Mercado Pago, E-mail, etc.).

4.  **Inicialize o Banco de Dados:**
    (Este comando cria o arquivo `financeiro.db` com as tabelas necessárias)
    ```bash
    python -c "import database; database.inicializar_banco()"
    ```

## 🏃 Como Rodar (Localmente)

Você precisará de 3 (ou 4) terminais abertos para rodar o projeto localmente.

1.  **Terminal 1: Servidor de Imagens e Pagamentos**
    (Este servidor serve as imagens e ouve o Mercado Pago)
    ```bash
    # (Por padrão, Gunicorn roda na porta 8000)
    gunicorn image_server:app
    ```

2.  **Terminal 2: Servidor do WhatsApp**
    (Este servidor ouve as mensagens do WhatsApp/Twilio)
    ```bash
    # (Por padrão, Gunicorn roda na porta 5000)
    gunicorn -b 0.0.0.0:5000 app:app
    ```

3.  **Terminal 3: Bot do Telegram**
    (Este script se conecta ao Telegram e busca mensagens)
    ```bash
    python bot_telegram.py
    ```

4.  **Terminal 4: Ngrok (Exposição dos Servidores)**
    Você precisará de **dois** túneis Ngrok, um para cada servidor Flask:
    ```bash
    # Túnel para o Servidor de Imagens/MP (porta 8000)
    ngrok http 8000
    
    # Em outro terminal, o túnel para o Servidor do WhatsApp (porta 5000)
    ngrok http 5000
    ```

### Configuração Final dos Webhooks:

* **URL do Ngrok (porta 8000):** Pegue a URL `https://...` gerada pelo Ngrok (porta 8000) e cole-a na variável `BASE_URL` dentro dos arquivos `config.py` e `catalogo.py`.
* **URL do Ngrok (porta 5000):** Pegue a URL `https://...` gerada pelo Ngrok (porta 5000) e cole-a no painel da **Twilio**, na configuração de webhook do seu número de WhatsApp, adicionando `/whatsapp` no final (ex: `https://abcd-1234.ngrok-free.dev/whatsapp`).