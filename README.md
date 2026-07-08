# Magic Maths

**Analisador estatístico de decks de Magic: The Gathering.**

Classifica cada card do seu deck por tipo (ramp, draw, interação, etc.) e executa simulações Monte Carlo e cálculos de distribuição hipergeométrica para responder perguntas como:

- Quanto de mana terei disponível em cada turno?
- Com que velocidade fico sem cartas na mão jogando no máximo?
- Quantas remoções, counterspells e graveyard hate meu deck tem?
- Quantos terrenos devo usar para este perfil de deck?

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.14+, Flask, SQLAlchemy, NumPy, SciPy |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| API externa | Scryfall (cards database) |
| Auth | JWT (flask-jwt-extended) |
| DB | SQLite (desenvolvimento) |

---

## Arquitetura

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  React App  │────▶│              Flask API (port 5555)           │
│  (Vite dev) │     │                                              │
│  :5173      │     │  /api/auth     → registro, login, JWT        │
│             │     │  /api/decks    → CRUD decks + import         │
│             │     │  /api/collection → CRUD coleção pessoal      │
│             │     │  /api/analysis → 4 motores de análise        │
└─────────────┘     │  /api/health   → health check               │
                    └──────────┬───────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐     ┌───────────────┐
                    │   SQLite / PostgreSQL│────▶│  Scryfall API │
                    │   (cards, users,    │     │  (cache local) │
                    │    decks, collection)│     └───────────────┘
                    └─────────────────────┘
```

### Fluxo de Análise Completa

```
POST /api/analysis/full  { deck_id: "..." }
         │
         ├─▶ mana_ramp.analyze_mana_ramp()      ─▶ distribuição hipergeométrica + Monte Carlo
         ├─▶ goldfish.simulate_goldfish()        ─▶ simulação de goldfish (2000 runs)
         ├─▶ interactions.analyze_interactions() ─▶ regex scan do oracle_text
         └─▶ land_rec.recommend_lands()          ─▶ fórmula Frank Karsten escalonada
         │
         └─▶ ThreadPoolExecutor (4 workers paralelos)
```

---

## Modelos de Dados

### User (`users`)
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID | PK |
| username | str(80) | Único, indexado |
| email | str(120) | Único, indexado |
| password_hash | str(256) | Werkzeug hash |
| created_at | datetime | Auto |

### Card (`cards`)
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | int | PK auto |
| oracle_id | str(64) | Scryfall oracle ID (único) |
| scryfall_id | str(64) | Scryfall card ID |
| name | str(256) | Nome do card |
| cmc | float | Converted mana cost |
| mana_cost | str | Ex: "{2}{U}{U}" |
| colors | JSON | ["U", "B"] |
| color_identity | JSON | ["U", "B"] |
| type_line | str | "Creature — Human Wizard" |
| oracle_text | text | Regras textuais |
| prices | JSON | {usd, usd_foil, eur} |
| image_uris | JSON | {small, normal, large} |

### Deck + DeckCard
- **Deck**: id (UUID), user_id (FK), name, format (commander/standard/etc), is_public, timestamps
- **DeckCard**: deck_id (FK), card_id (FK), quantity, is_commander, is_sideboard

### Collection
- **Collection**: user_id (FK), card_id (FK), quantity, is_foil, condition (NM/SP/MP/HP/DMG)
- Unique constraint: (user_id, card_id, is_foil)

---

## API Endpoints

### Auth
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/register` | Criar conta. Body: `{username, email, password}` |
| POST | `/api/auth/login` | Login. Body: `{email, password}` |
| GET | `/api/auth/me` | Dados do usuário logado (Bearer token) |

### Decks
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/decks` | Listar decks do usuário |
| GET | `/api/decks/:id` | Deck + cards |
| POST | `/api/decks` | Criar deck manual. Body: `{name, format, cards: [{name, quantity}]}` |
| POST | `/api/decks/import` | Importar decklist texto. Body: `{decklist, name?, format?}` |
| PUT | `/api/decks/:id` | Atualizar deck |
| DELETE | `/api/decks/:id` | Deletar deck |

### Collection
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/collection` | Listar coleção |
| POST | `/api/collection` | Adicionar card. Body: `{card_name, quantity, is_foil?, condition?}` |
| PUT | `/api/collection/:id` | Atualizar quantidade/condição |
| DELETE | `/api/collection/:id` | Remover da coleção |

### Analysis
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/analysis/mana-ramp` | Predição de mana por turno |
| POST | `/api/analysis/goldfish` | Velocidade de esvaziamento da mão |
| POST | `/api/analysis/interactions` | Contagem de remoções/contadores |
| POST | `/api/analysis/land-recommendation` | Terrenos recomendados |
| POST | `/api/analysis/full` | **Todas as 4 análises em paralelo** |
| POST | `/api/analysis/classify-card` | Classificar card individual |

Todas as rotas de análise aceitam `{deck_id}` ou `{cards: [{name, quantity}]}`.

---

## Motores de Análise

### 1. Mana Ramp (`services/mana_ramp.py`)

**Card Classification** — cada card não-terreno é analisado por regex no `oracle_text`:

| Categoria | Subtipos | Exemplo |
|-----------|----------|---------|
| Ramp | dork, rock_fixed, rock_any, land_ramp_basic, land_ramp_any, extra_land, extra_mana, cost_reducer, ritual | Llanowar Elves, Arcane Signet, Rampant Growth, Dark Ritual |
| Draw | cantrip, draw_spell, draw_x, wheel, looting | Consider, Ancestral Recall, Timetwister |
| Manipulation | scry, surveil, topdeck_look, topdeck_put | Serum Visions, Thought Scour, Brainstorm |

**Two-Phase Prediction:**

1. **Analytical (Hypergeometric):**
   ```
   Para cada turno T (1-10):
     cards_drawn = 7 + (T-1)
     P(k lands in hand) = PMF(deck_size, land_count, cards_drawn, k)
     expected_lands = Σ k · P(k)
     mana = lands_in_play + dorks(T≥2) + rocks(T≥2) + land_ramp(T≥3) + rituals
   ```

2. **Simulation (Monte Carlo, N=5000):**
   ```
   Para cada simulação:
     deck = [L]×lands + [R]×ramps + [O]×other
     shuffle
     para turno 1..T: jogar land → jogar ramp → contar mana
   Retorna percentis P10, P50, P90 por turno
   ```

### 2. Goldfish Speed (`services/goldfish.py`)

```
Para cada simulação (N=2000):
  shuffle deck
  draw 7
  para turno 1..15:
    jogar land da mão (se houver)
    enquanto mana disponível > 0:
      jogar spell de maior CMC que cabe na mana
  registrar turno em que mão = ∅
```

Estratégia: **greedy CMC-max** — sempre joga o spell mais caro possível, simulando "descer tudo que pode".

Outputs:
- Turno médio/mediano/P10/P90 de mão vazia
- Probabilidade de mão vazia nos turnos 5 e 7
- Gráfico cards-na-mão por turno (média, P10, P90)

### 3. Interaction Analyzer (`services/interactions.py`)

Escaneia `oracle_text` de cada card não-terreno com 42 regex patterns organizados em 7 categorias:

| Categoria | Ação | Exemplo de trigger |
|-----------|------|--------------------|
| destroy | Destruir permanente | "destroy target creature" |
| exile | Exilar permanente | "exile target artifact" |
| bounce | Devolver à mão | "return target permanent to hand" |
| counter | Anular mágica | "counter target spell" |
| damage | Dano a criatura | "deals 3 damage to target creature" |
| graveyard | Exilar do cemitério | "exile target card from a graveyard" |
| tuck | Colocar no fundo do library | "put target creature on the bottom" |

Cada interação é **de-duplicada** por (ação + tipo de alvo) por card — um Counterspell conta como 1, não como todas as variações de regex que match.

### 4. Land Recommendation (`services/land_rec.py`)

**Fórmula base (Frank Karsten, 2019-2020):**
```
Lands = 31.42 - 1.04 × Ramp + 0.52 × AvgCMC + 0.84 × Draw
```

**Scaling** para formatos não-60:
```
Commander (99): Lands_base × (99/60)
Outros:         Lands_base × (deck_size/60)
```

**Profile Detection:**
| Perfil | Critério | Ajuste |
|--------|----------|--------|
| aggro | >50% CMC≤2, >40% criaturas | -1 land |
| midrange | >30% criaturas, >30% CMC≤2 | 0 |
| control | >15% CMC≥6 ou <20% criaturas+>10% CMC≥6 | +1 land |

**Color Sources:** recomenda número de fontes de mana colorida baseado na contagem de pips de cada cor no deck.

---

## Instalação e Uso

### Requisitos
- Python 3.14+
- Node.js 18+ (para o frontend)

### Backend
```bash
cd backend
pip install -r requirements.txt
python run.py
# → http://localhost:5555
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173 (com proxy para :5555)
```

### Produção
```bash
cd backend
gunicorn -w 4 -b 0.0.0.0:5555 run:app
```
Configure `DATABASE_URL` no `.env` para PostgreSQL em produção.

---

## Estrutura de Arquivos

```
magic-maths/
├── backend/
│   ├── app/
│   │   ├── __init__.py           # Factory: create_app()
│   │   ├── config.py             # Config via .env
│   │   ├── extensions.py         # db, migrate, jwt
│   │   ├── models/
│   │   │   ├── user.py           # User com password hash
│   │   │   ├── card.py           # Card com dados Scryfall
│   │   │   ├── collection.py     # Collection (user ↔ card)
│   │   │   └── deck.py           # Deck + DeckCard
│   │   ├── routes/
│   │   │   ├── auth.py           # Register, login, me
│   │   │   ├── decks.py          # CRUD + importação
│   │   │   ├── collection.py     # CRUD coleção
│   │   │   └── analysis.py       # 6 endpoints de análise
│   │   ├── services/
│   │   │   ├── scryfall.py       # Cache Scryfall API
│   │   │   ├── mana_ramp.py      # Feature 1
│   │   │   ├── goldfish.py       # Feature 2
│   │   │   ├── interactions.py   # Feature 3
│   │   │   └── land_rec.py       # Feature 4
│   │   └── utils/
│   │       └── card_parser.py    # Parser de decklist texto
│   ├── requirements.txt
│   ├── run.py                    # Entrypoint
│   └── .env                      # Config local
├── frontend/
│   ├── src/
│   │   ├── main.tsx              # Entrypoint React
│   │   ├── App.tsx               # Router + AuthProvider
│   │   ├── index.css             # Tailwind + classes utilitárias
│   │   ├── services/api.ts       # Axios client
│   │   ├── hooks/useAuth.ts      # Contexto de autenticação
│   │   ├── pages/
│   │   │   ├── Login.tsx         # Tela de login
│   │   │   ├── Register.tsx      # Tela de cadastro
│   │   │   ├── Dashboard.tsx     # Home com lista de decks
│   │   │   ├── DeckBuilder.tsx   # Importar/montar deck
│   │   │   ├── DeckAnalysis.tsx  # 4 abas de análise
│   │   │   └── Collection.tsx    # Gerenciar coleção
│   │   └── components/
│   │       ├── Layout.tsx        # Navbar + sidebar
│   │       ├── ProtectedRoute.tsx # Guard de autenticação
│   │       ├── ManaCurveChart.tsx    # Gráfico mana ramp
│   │       ├── GoldfishSim.tsx       # Gráfico goldfish
│   │       ├── InteractionBreakdown.tsx  # Tabela interações
│   │       └── LandRecommender.tsx   # Recomendação terrenos
│   ├── package.json
│   ├── vite.config.ts            # Proxy /api → :5555
│   └── tailwind.config.js        # Tema customizado
└── README.md
```

---
