# catalogo.py

# ==============================================================================
# --- CONFIGURAÇÃO DE URL BASE (MOVIDO DE LOGIC.PY) ---
# ==============================================================================
# ATENÇÃO: Se você mudar o BASE_URL em logic.py, mude aqui também.
# (Uma solução melhor no futuro seria carregar isso de um config.py)
BASE_URL = "https://unreliant-rayford-unresumptive.ngrok-free.dev"
# ==============================================================================


# ==============================================================================
# --- LISTAS DE ITENS PARA COMBOS ---
# ==============================================================================
ITENS_BRINQUEDOS_G = [
    "Pula Pula P", "Arara de Fantasia", "Balanço", "Pesca", "Sorveteria",
    "Playground Urso", "Feirinha e Carrinho", "Penteadeira", "Cozinha",
    "Casa da Barbie", "Kart Elétrico", "Lambreta Elétrica", "Circuito Espumado",
    "Piscina de Bolinhas", "Escorregador", "Mesa Lego", "Game Airhockey", "Pebolim",
    "Andador Unicórnio", "Cabana Creme", "Tenda Creme", "Cabana Rosa"
]
ITENS_KIT_BABY = [
    "Cadeira 3 em 1 (Moisés/Berço)", "Cadeira Moises Musical", "Cadeira de Balanço Automática",
    "Cadeira de Descanso Mamaroo", "Berço Chiqueirinho", "Cadeirinha Pula-Pula",
    "Tapete de Atividades", "Cadeira de Balanço Fisher Price", "Cercado para Bebês",
    "Mesa de Atividades Baby", "Centro de Atividades Baby", "Assento Dino"
]
ITENS_BRINQUEDOS_M = [
    "Balanço Montessori", "Carrinho de Boneca", "Biblioteca", "Balanço Elefante",
    "Balanço Cavalinho", "Piano e Violão", "Triciclo Patinete Zoo", "Andador Dino",
    "Pista de Carrinho", "Amarelinha", "Motoneta", "Bicicleta sem Pedal",
    "Avião Velocipede", "Mesa Multi Games"
]
ITENS_BRINQUEDOS_P = [
    "Arco Íris de Madeira", "Bonecos Super Heróis", "Castelo Batman", 
    "Jogo de Argola Girafa", "Andador Zebrinha", "Instrumentos Musicais",
    "Pista Hot Wheels Dino", "Pista Hot Wheels Dragão", "Centro de Atividades",
    "Bloco Cidade", "Jogos Diversos", "Brinquedo Playhouse Fisher Price"
]
# ==============================================================================

# ==============================================================================
# --- NOTA IMPORTANTE: ATUALIZE OS CUSTOS ---
# Você PRECISA atualizar o valor "R$ 0,00" para o custo real de cada item.
# ==============================================================================
CATALOGO_COMBOS = {
    "geral": { "imagem_url": [f"{BASE_URL}/image/Combos.png"] }, 
    "tipos": [
        { "id": 1, "nome": "Brinquedos G", "imagens_urls": [f"{BASE_URL}/image/Brinquedos_G.png", f"{BASE_URL}/image/Brinquedos_G2.png"]},
        { "id": 2, "nome": "Brinquedos M", "imagens_urls": [f"{BASE_URL}/image/Brinquedos_M.png", f"{BASE_URL}/image/Brinquedos_M2.png"]},
        { "id": 3, "nome": "Brinquedos P", "imagens_urls": [f"{BASE_URL}/image/Brinquedos_P.png", f"{BASE_URL}/image/Brinquedos_P2.png"]},
        { "id": 4, "nome": "Kit Baby", "imagens_urls": [f"{BASE_URL}/image/Kit_Baby.png"]}
    ]
}

DEFINICOES_COMBOS = {
    "1": {
        "id": 101, "nome": "Combo 1 (Customizado)", "preco": "R$ 1.400,00", "custo": "R$ 0,00", # <-- ATUALIZE
        "etapas": [
            {"id_cat": [1, 4], "limite": 4, "nome_etapa": "Brinquedos G / Kit Baby"},
            {"id_cat": [2], "limite": 3, "nome_etapa": "Brinquedos M"},
            {"id_cat": [3], "limite": 4, "nome_etapa": "Brinquedos P"}
        ]
    },
    "2": {
        "id": 102, "nome": "Combo 2 (Customizado)", "preco": "R$ 1.740,00", "custo": "R$ 0,00", # <-- ATUALIZE
        "etapas": [
            {"id_cat": [1, 4], "limite": 6, "nome_etapa": "Brinquedos G / Kit Baby"},
            {"id_cat": [2], "limite": 4, "nome_etapa": "Brinquedos M"},
            {"id_cat": [3], "limite": 4, "nome_etapa": "Brinquedos P"}
        ]
    },
    "3": {
        "id": 103, "nome": "Combo 3 (Customizado)", "preco": "R$ 2.250,00", "custo": "R$ 0,00", # <-- ATUALIZE
        "etapas": [
            {"id_cat": [1, 4], "limite": 9, "nome_etapa": "Brinquedos G / Kit Baby"},
            {"id_cat": [2], "limite": 4, "nome_etapa": "Brinquedos M"},
            {"id_cat": [3], "limite": 4, "nome_etapa": "Brinquedos P"}
        ]
    }
}

CATALOGO_AVULSOS_CATEGORIZADO = {
    "Infláveis": [
        { "id": 24, "nome": "Castelinho 3 em 1", "preco": "R$ 1.000,00", "custo": "R$ 0,00", "descricao": "Um playground completo com pula pula, piscina de bolinha e escorregador, tudo em um só brinquedo. Ideal para quem busca diversão e aventura!", "imagens_urls": [f"{BASE_URL}/image/Avulsos/Castelinho3em1.png"]},
        { "id": 25, "nome": "Castelinho 2 em 1", "preco": "R$ 600,00", "custo": "R$ 0,00", "descricao": "Diversão em dobro! Este brinquedo conta com pula pula e escorregador, garantindo a alegria da criançada.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/Castelinho2em1.png"]},
        { "id": 26, "nome": "Castelo Inflável Princess", "preco": "R$ 500,00", "custo": "R$ 0,00", "descricao": "Um castelo dos sonhos para as princesas. Com pula pula, escoregador e um design encantador, é o cenário perfeito para fotos e brincadeiras.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CasteloInflavelPrincess.png"]},
        { "id": 27, "nome": "Bubble House", "preco": "R$ 1.100,00", "custo": "R$ 0,00", "descricao": "Uma experiência única! Uma bolha transparente que pode ser personalizada com balões, criando um ambiente mágico para fotos e diversão.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/BubbleHouse.png"]}
    ],
    "Pula-Pula e Piscinas": [
        { "id": 6, "nome": "Cama Elástica", "preco": "R$ 450,00", "custo": "R$ 0,00", "descricao": "Pura diversão e energia! Nossa cama elástica é segura, resistente e garante saltos de alegria para todas as idades.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CamaElastica.png"] },
        { "id": 37, "nome": "Piscina de Bolinhas Coração", "preco": "R$ 400,00", "custo": "R$ 0,00", "descricao": "Uma piscina de bolinhas charmosa e divertida em formato de coração. Perfeita para os pequenos mergulharem na brincadeira.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/PiscinaBolinhaCoracao.png"]}
    ],
    "Casinhas e Tendas": [
        { "id": 8, "nome": "Casinha Encantada", "preco": "R$ 390,00", "custo": "R$ 0,00", "descricao": "Um refúgio mágico para as crianças soltarem a imaginação. Com design delicado, é ideal para criar histórias e brincadeiras.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CasinhaEncantada.png"] },
        { "id": 19, "nome": "Tenda Arco-Íris", "preco": "R$ 450,00", "custo": "R$ 0,00", "descricao": "Uma tenda colorida e aconchegante que transforma qualquer cantinho em um mundo de sonhos e aventuras.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/TendaArcoIris.png"] },
        { "id": 20, "nome": "Tenda Encantada", "preco": "R$ 950,00", "custo": "R$ 0,00", "descricao": "Crie uma festa do pijama inesquecível! Nossas tendas são confortáveis e criam um ambiente mágico para celebrar com os amigos.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/TendaEncantada.png"] },
        { "id": 21, "nome": "Tenda Foguete", "preco": "R$ 380,00", "custo": "R$ 0,00", "descricao": "Prepare-se para uma viagem espacial! Esta tenda em formato de foguete inspira grandes aventuras intergalácticas.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/TendaFoguete.png"] }
    ],
    "Eletrônicos e Motorizados": [
        { "id": 10, "nome": "Fliperama Portátil", "preco": "R$ 350,00", "custo": "R$ 0,00", "descricao": "Leve os jogos clássicos para sua festa! Com milhares de jogos retrô, diversão garantida para adultos e crianças.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/FliperamaPortatil.png"] },
        { "id": 13, "nome": "Máquina De Ursos", "preco": "A partir de R$ 800,00", "custo": "R$ 0,00", "descricao": "Desafie seus convidados! Nossa máquina de pelúcias é um clássico que diverte e premia. (Valor sob consulta, inclui pelúcias).", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MaquinaDeUrsos.png"] },
        { "id": 16, "nome": "Mesa Interativa", "preco": "R$ 650,00", "custo": "R$ 0,00", "descricao": "Mesa com diversos jogos educativos e divertidos que estimulam o aprendizado e a coordenação motora.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MesaInterativa.png"] },
        { "id": 28, "nome": "Pelúcia Motorizada", "preco": "R$ 500,00 (cada)", "custo": "R$ 0,00", "descricao": "Ande pela festa com estilo! Nossas pelúcias motorizadas são fáceis de pilotar e amadas pelas crianças.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/PeluciaMotorizada.png"]},
        { "id": 29, "nome": "Triciclo Elétrico Drift LED", "preco": "R$ 250,00", "custo": "R$ 0,00", "descricao": "Para os amantes de velocidade! Nosso triciclo elétrico faz manobras de drift e possui luzes LED para uma experiência radical.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/Triciclo.png"]},
        { "id": 30, "nome": "Kart Elétrico", "preco": "R$ 250,00", "custo": "R$ 0,00", "descricao": "Os pequenos podem pilotar de verdade! Um kart seguro e divertido para eles se sentirem verdadeiros pilotos.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/KartEletrico.png"]},
        { "id": 31, "nome": "Pista Carrinho Bate Bate", "preco": "R$ 1.100,00", "custo": "R$ 0,00", "descricao": "A diversão clássica do parque de diversões na sua festa! Nossos carrinhos de bate-bate são garantia de risadas.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/PistaCarrinhoBateBate.png"]},
        { "id": 32, "nome": "Fliperama Kids", "preco": "R$ 300,00", "custo": "R$ 0,00", "descricao": "Milhares de jogos clássicos em um fliperama adaptado para os pequenos, com design colorido e controles fáceis.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/FliperamaKids.png"]}
    ],
    "Gourmet e Efeitos de Festa": [
        { "id": 5, "nome": "Caixa De Som Amplificada", "preco": "R$ 350,00", "custo": "R$ 0,00", "descricao": "Aumente o som da festa! Caixa de som profissional com microfone para animar qualquer ambiente.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CaixaDeSomAmplificada.png"] },
        { "id": 7, "nome": "Candy Wall", "preco": "R$ 1.100,00", "custo": "R$ 0,00", "descricao": "Uma parede de doces que é o ponto alto da decoração! Um painel interativo para os convidados se servirem de guloseimas.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CandyWall.png"] },
        { "id": 12, "nome": "Máquina De Fumaça", "preco": "R$ 250,00", "custo": "R$ 0,00", "descricao": "Crie um ambiente de balada! Nossa máquina de fumaça é potente e ideal para pistas de dança e momentos especiais.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MaquinaDeFumaca.png"] },
        { "id": 14, "nome": "Máquina Para Bolhas", "preco": "R$ 130,00", "custo": "R$ 0,00", "descricao": "Encante a todos com uma chuva de bolhas de sabão! Perfeito para criar um clima lúdico e mágico.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MaquinaParaBolhas.png"] },
        { "id": 18, "nome": "Moving Head Spot LED", "preco": "R$ 150,00", "custo": "R$ 0,00", "descricao": "Iluminação profissional para sua festa! Crie efeitos de luz coloridos e dinâmicos na pista de dança.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MovingHeadSpotLED.png"] },
        { "id": 39, "nome": "Carrinho de Algodão Doce e Pipoca", "preco": "R$ 500,00", "custo": "R$ 0,00", "descricao": "O cheirinho de festa no ar! Nosso carrinho retrô serve algodão doce e pipoca à vontade para os convidados.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CarrinhoAlgodaoDoce.png"]}
    ],
    "Mobiliário e Atividades": [
        { "id": 9, "nome": "Cubo De Cristal", "preco": "R$ 250,00", "custo": "R$ 0,00", "descricao": "Um toque de elegância e modernidade para sua decoração. Perfeito como mesa de bolo ou para destacar objetos.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CuboDeCristal.png"] },
        { "id": 15, "nome": "Mesa Criativa", "preco": "R$ 450,00", "custo": "R$ 0,00", "descricao": "Um espaço perfeito para oficinas de arte, pintura e massinha. Estimula a criatividade das crianças.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MesaCriativa.png"] },
        { "id": 17, "nome": "Mesa Piquenique", "preco": "A partir de R$ 300,00", "custo": "R$ 0,00", "descricao": "Crie um cantinho charmoso e aconchegante para um lanche. Ideal para festas ao ar livre ou com tema de jardim.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MesaPpiiccnnicc.png"] },
        { "id": 33, "nome": "Painel Interativo", "preco": "R$ 490,00", "custo": "R$ 0,00", "descricao": "Um grande painel sensorial com diversas atividades que estimulam o tato, a visão e a coordenação dos bebês.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/PainelInterativo.png"]},
        { "id": 38, "nome": "Circuito Ursinho", "preco": "R$ 650,00", "custo": "R$ 0,00", "descricao": "Um desafio divertido! O circuito com tema de ursinho inclui túneis, rampas e obstáculos para os pequenos gastarem energia.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/CirculoUrsinho.png"]}
    ],
    "Cenários Móbile": [
        { "id": 34, "nome": "Mobile Pet Shop", "preco": "R$ 300,00", "custo": "R$ 0,00", "descricao": "Um cenário temático completo para os pequenos cuidarem dos seus bichinhos de pelúcia, com banheira, acessórios e caixa registradora.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MobilePetShoop.png"]},
        { "id": 35, "nome": "Mobile Oficina", "preco": "R$ 300,00", "custo": "R$ 0,00", "descricao": "Para os pequenos construtores! Um cenário de oficina com ferramentas de brinquedo, bancada e tudo para 'consertar' e criar.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MobileOficina.png"]},
        { "id": 36, "nome": "Mobile Camarim", "preco": "R$ 300,00", "custo": "R$ 0,00", "descricao": "Um camarim de estrelas com penteadeira, espelho, fantasias e acessórios para as crianças se transformarem e brincarem.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/MobileCamarim.png"]}
    ],
    "Brinquedos Lúdicos": [
        { "id": 4, "nome": "Barco Candy", "preco": "R$ 300,00", "custo": "R$ 0,00", "descricao": "Navegue em um mar de doçura! Um barquinho em tons pastéis que serve como balanço e cenário para fotos incríveis.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/BarcoCandy.png"] },
        { "id": 11, "nome": "Gangorra Candy", "preco": "R$ 250,00", "custo": "R$ 0,00", "descricao": "Balanço e diversão em tons suaves. Uma gangorra segura e charmosa para os pequenos.", "imagens_urls": [f"{BASE_URL}/image/Avulsos/GangorraCandy.png"] }
    ]
}

# Cria a lista única de avulsos (usada em logic.py)
CATALOGO_AVULSOS = [item for sublist in CATALOGO_AVULSOS_CATEGORIZADO.values() for item in sublist]