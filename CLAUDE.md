# CLAUDE.md — GameDash

## Visão Geral do Projeto

GameDash é um dashboard Streamlit que consome a Steam Web API, armazena dados em SQLite e exibe estatísticas, conquistas e recomendações de jogos com design inspirado na Steam.

- **Live:** https://gamedash7.streamlit.app/
- **Repositório:** https://github.com/guiharaujo/GameDash

---

## Arquitetura

```
GameDash/
├── app.py                    # Página Home (perfil + sync + top jogos)
├── pages/
│   ├── 1_biblioteca.py       # Grade de jogos com filtros e progresso
│   ├── 2_conquistas.py       # Lista de conquistas por jogo
│   ├── 3_estatisticas.py     # Gráficos Plotly (horas, gêneros, timeline)
│   └── 4_recomendacoes.py    # Sugestões por gênero + quase 100%
├── src/
│   ├── database.py           # SQLAlchemy models (Player, Game, Achievement)
│   ├── steam_api.py          # Wrapper dos 5 endpoints Steam + sync_all_data()
│   └── recommendations.py    # Lógica de recomendações por gênero
├── .streamlit/
│   ├── config.toml           # Tema escuro Steam (#1b2838 / #66c0f4)
│   └── secrets.toml          # Credenciais locais (NÃO commitar)
├── data/
│   └── gamedash.db           # Gerado em runtime pelo SQLAlchemy
├── .env.example              # Template de variáveis de ambiente
└── requirements.txt
```

---

## Stack Técnica

| Camada | Tecnologia |
|---|---|
| UI | Streamlit 1.32+ (multi-page) |
| API | requests + Steam Web API |
| Banco | SQLAlchemy 2.0 + SQLite |
| Gráficos | Plotly Express / Graph Objects |
| Segredos | `st.secrets` (cloud) / `python-dotenv` (local) |
| Design | CSS customizado, tema Steam (#1b2838, #66c0f4) |

---

## Endpoints Steam Utilizados

| Função em `steam_api.py` | Endpoint |
|---|---|
| `get_player_summary()` | `ISteamUser/GetPlayerSummaries/v0002` |
| `get_owned_games()` | `IPlayerService/GetOwnedGames/v0001` |
| `get_player_achievements(app_id)` | `ISteamUserStats/GetPlayerAchievements/v0001` |
| `get_game_schema(app_id)` | `ISteamUserStats/GetSchemaForGame/v2` |
| `get_game_details(app_id)` | `store.steampowered.com/api/appdetails` |

---

## Schema do Banco de Dados

### Player
| Campo | Tipo |
|---|---|
| steam_id | String (PK) |
| name | String |
| avatar_url / avatar_full_url | String |
| profile_url | String |
| country | String |
| updated_at | DateTime |

### Game
| Campo | Tipo |
|---|---|
| app_id | Integer (PK) |
| name | String |
| img_icon_url / img_logo_url | String |
| playtime_forever | Integer (minutos) |
| playtime_2weeks | Integer (minutos) |
| genres | Text (CSV: "Ação,RPG") |
| last_synced | DateTime |

### Achievement
| Campo | Tipo |
|---|---|
| id | Integer (PK auto) |
| app_id | Integer (FK → Game) |
| api_name | String |
| name / description | String / Text |
| icon_url / icon_gray_url | String |
| unlocked | Boolean |
| unlock_time | Integer (Unix timestamp) |

---

## Segredos e Variáveis de Ambiente

**Desenvolvimento local** — criar `.streamlit/secrets.toml`:
```toml
STEAM_API_KEY = "sua_chave_aqui"
STEAM_ID = "seu_steam_id_aqui"
```

**Alternativa local** — criar `.env`:
```
STEAM_API_KEY=sua_chave_aqui
STEAM_ID=seu_steam_id_aqui
```

O código em `steam_api.py` tenta `st.secrets` primeiro, depois `os.environ`.

**NUNCA commitar** `.streamlit/secrets.toml` ou `.env`. Ambos estão no `.gitignore`.

---

## Comandos Comuns

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar localmente
streamlit run app.py

# Sincronizar dados via UI
# Abrir o app e clicar em "Sincronizar dados" na barra lateral
```

---

## Convenções de Código

- Todas as funções de banco de dados ficam em `src/database.py`
- Todo acesso à API Steam passa por `src/steam_api.py`
- Páginas Streamlit importam apenas de `src/` — não fazem chamadas diretas à API
- Horas sempre armazenadas em **minutos** no banco; converter para exibição com `format_hours()`
- CSS customizado via `st.markdown(..., unsafe_allow_html=True)` no topo de cada página

---

## Rate Limits Steam

- API Web Steam: ~100k requests/dia por chave
- Store API (`appdetails`): mais restrita; usar `time.sleep(0.5)` entre chamadas
- `sync_all_data()` faz sleep de 0.3s entre conquistas e 0.5s entre gêneros
- Conquistas buscadas apenas para jogos com `playtime_forever > 0`
- Gêneros buscados apenas para top 50 jogos por horas

---

## Deploy no Streamlit Cloud

1. Fazer push do repo para GitHub (sem `.env` e `secrets.toml`)
2. Acessar [share.streamlit.io](https://share.streamlit.io)
3. Conectar repositório GitHub
4. Em **Advanced settings → Secrets**, colar:
   ```toml
   STEAM_API_KEY = "sua_chave"
   STEAM_ID = "seu_steam_id"
   ```
5. Deploy — o app estará disponível em `https://share.streamlit.io/seu-usuario/gamedash`
