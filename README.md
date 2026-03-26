# 🎮 GameDash

Dashboard pessoal da Steam com estatísticas, conquistas e recomendações de jogos — construído com Python + Streamlit.

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-gamedash7.streamlit.app-66c0f4?style=for-the-badge)](https://gamedash7.streamlit.app/)

![Tema Steam](https://img.shields.io/badge/tema-Steam%20Dark-1b2838?style=flat&logo=steam)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.32%2B-FF4B4B)

---

## Funcionalidades

| Página | Descrição |
|---|---|
| 🏠 **Home** | Perfil Steam, métricas gerais, top 5 jogos |
| 📚 **Biblioteca** | Todos os jogos com horas, filtros e capas |
| 🏆 **Conquistas** | Progresso por jogo com ícones e datas |
| 📊 **Estatísticas** | Gráficos interativos de horas, gêneros e linha do tempo |
| 💡 **Recomendações** | Sugestões por gênero + jogos quase 100% |

---

## Pré-requisitos

- Python 3.9+
- Conta Steam com perfil **público**
- [Steam API Key](https://steamcommunity.com/dev/apikey) (gratuita)
- Seu [Steam ID 64](https://www.steamidfinder.com/)

---

## Instalação Local

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/gamedash.git
cd gamedash
```

### 2. Crie e ative um ambiente virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as credenciais

Crie o arquivo `.streamlit/secrets.toml`:

```toml
STEAM_API_KEY = "sua_api_key_aqui"
STEAM_ID = "seu_steam_id_aqui"
```

> Ou copie `.env.example` para `.env` e preencha os valores.

### 5. Execute o app

```bash
streamlit run app.py
```

O app abrirá em `http://localhost:8501`.

### 6. Sincronize os dados

Clique em **"🔄 Sincronizar dados"** na barra lateral. A sincronização busca:
- Perfil do jogador
- Biblioteca completa de jogos
- Conquistas de todos os jogos jogados
- Gêneros dos top 50 jogos

> A sincronização pode levar alguns minutos dependendo do tamanho da biblioteca.

---

## Deploy

> **App em produção:** [https://gamedash7.streamlit.app/](https://gamedash7.streamlit.app/)
> **Repositório:** [https://github.com/guiharaujo/GameDash](https://github.com/guiharaujo/GameDash)

## Deploy no Streamlit Cloud (gratuito)

### 1. Crie um repositório no GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/seu-usuario/gamedash.git
git push -u origin main
```

> O `.gitignore` já está configurado para **não subir** `.env` e `secrets.toml`.

### 2. Acesse o Streamlit Cloud

1. Vá para [share.streamlit.io](https://share.streamlit.io)
2. Faça login com GitHub
3. Clique em **"New app"**
4. Selecione o repositório `gamedash`
5. Main file: `app.py`

### 3. Configure os Secrets

Antes de fazer deploy:
1. Clique em **"Advanced settings"**
2. Na aba **"Secrets"**, cole:

```toml
STEAM_API_KEY = "sua_api_key_aqui"
STEAM_ID = "seu_steam_id_aqui"
```

3. Clique em **"Deploy!"**

Seu app estará disponível em:
```
https://seu-usuario-gamedash-app-HASH.streamlit.app
```

---

## Estrutura do Projeto

```
GameDash/
├── app.py                    # Página inicial
├── pages/
│   ├── 1_biblioteca.py
│   ├── 2_conquistas.py
│   ├── 3_estatisticas.py
│   └── 4_recomendacoes.py
├── src/
│   ├── database.py           # SQLAlchemy + SQLite
│   ├── steam_api.py          # Cliente Steam API
│   └── recommendations.py    # Motor de recomendações
├── .streamlit/
│   └── config.toml           # Tema escuro Steam
├── data/                     # gamedash.db (gerado automaticamente)
├── .env.example
├── requirements.txt
└── .gitignore
```

---

## Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `STEAM_API_KEY` | Chave da Steam Web API |
| `STEAM_ID` | Seu Steam ID 64 |

---

## Tecnologias

- **[Streamlit](https://streamlit.io/)** — Interface web
- **[SQLAlchemy](https://www.sqlalchemy.org/)** — ORM + SQLite
- **[Plotly](https://plotly.com/python/)** — Gráficos interativos
- **[requests](https://docs.python-requests.org/)** — Chamadas HTTP para Steam API
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** — Variáveis de ambiente locais

---

## Segurança

- API Key nunca exposta no código — sempre via `st.secrets` ou `.env`
- `.env` e `secrets.toml` no `.gitignore`
- `.env.example` como template sem dados sensíveis

---

## Licença

MIT
