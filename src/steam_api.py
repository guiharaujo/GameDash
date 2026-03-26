import os
import time
import requests
import streamlit as st
from src.database import (
    init_db, upsert_player, upsert_games, upsert_achievements,
    update_game_genres, get_all_games,
)

BASE_URL = "https://api.steampowered.com"
STORE_URL = "https://store.steampowered.com/api/appdetails"
FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/"

# Mapeamento de nomes de gênero → tag IDs Steam
GENRE_TAG_MAP = {
    "Ação": 19, "Action": 19,
    "RPG": 122,
    "Aventura": 21, "Adventure": 21,
    "Estratégia": 9, "Strategy": 9,
    "Indie": 492,
    "Simulação": 599, "Simulation": 599,
    "Esportes": 701, "Sports": 701,
    "Terror": 4026, "Horror": 4026,
    "Mundo Aberto": 1695, "Open World": 1695,
}


def _get_credentials():
    """Lê API key e Steam ID com múltiplos fallbacks."""
    api_key  = ""
    steam_id = ""

    # 1. st.secrets (Streamlit Cloud ou secrets.toml local)
    try:
        api_key  = str(st.secrets.get("STEAM_API_KEY", ""))
        steam_id = str(st.secrets.get("STEAM_ID", ""))
    except Exception:
        pass

    # 2. Variáveis de ambiente / .env
    if not api_key or not steam_id:
        try:
            from dotenv import load_dotenv
            # Caminho absoluto do .env na raiz do projeto
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            load_dotenv(env_path)
        except Exception:
            pass
        api_key  = api_key  or os.environ.get("STEAM_API_KEY", "")
        steam_id = steam_id or os.environ.get("STEAM_ID", "")

    # 3. Leitura direta do secrets.toml como fallback final
    if not api_key or not steam_id:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib  # pip install tomli
            except ImportError:
                tomllib = None

        if tomllib:
            secrets_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                ".streamlit", "secrets.toml"
            )
            try:
                with open(secrets_path, "rb") as f:
                    data = tomllib.load(f)
                api_key  = api_key  or data.get("STEAM_API_KEY", "")
                steam_id = steam_id or data.get("STEAM_ID", "")
            except Exception:
                pass

    if not api_key or not steam_id:
        raise ValueError(
            "Credenciais Steam não encontradas.\n"
            "Configure STEAM_API_KEY e STEAM_ID em:\n"
            "  • .streamlit/secrets.toml  (local)\n"
            "  • .env  (local)\n"
            "  • Streamlit Cloud → App settings → Secrets"
        )

    return api_key, steam_id


def get_player_summary() -> dict:
    api_key, steam_id = _get_credentials()
    resp = requests.get(
        f"{BASE_URL}/ISteamUser/GetPlayerSummaries/v0002/",
        params={"key": api_key, "steamids": steam_id},
        timeout=10,
    )
    resp.raise_for_status()
    players = resp.json().get("response", {}).get("players", [])
    return players[0] if players else {}


def get_owned_games() -> list:
    api_key, steam_id = _get_credentials()
    resp = requests.get(
        f"{BASE_URL}/IPlayerService/GetOwnedGames/v0001/",
        params={
            "key": api_key,
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("response", {}).get("games", [])


def get_most_played_steam_games(count: int = 10) -> list:
    """
    Retorna os jogos mais jogados na Steam agora (ranking global).
    Fonte: ISteamChartsService/GetMostPlayedGames/v1
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/ISteamChartsService/GetMostPlayedGames/v1/",
            timeout=10,
        )
        resp.raise_for_status()
        ranks = resp.json().get("response", {}).get("ranks", [])[:count]
    except Exception:
        return []

    results = []
    for entry in ranks:
        app_id = entry["appid"]
        # Busca nome básico do jogo na Store
        try:
            detail_resp = requests.get(
                STORE_URL,
                params={"appids": app_id, "filters": "basic", "l": "portuguese"},
                timeout=8,
            )
            detail_resp.raise_for_status()
            detail_data = detail_resp.json().get(str(app_id), {})
            name = detail_data.get("data", {}).get("name", f"App {app_id}") if detail_data.get("success") else f"App {app_id}"
        except Exception:
            name = f"App {app_id}"

        results.append({
            "rank": entry["rank"],
            "app_id": app_id,
            "name": name,
            "peak_in_game": entry.get("peak_in_game", 0),
            "last_week_rank": entry.get("last_week_rank", 0),
            "header_image": f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",
        })
        time.sleep(0.2)

    return results


def get_game_price(app_id: int) -> dict:
    """Retorna preço atual de um jogo na Steam Store (BR)."""
    try:
        resp = requests.get(
            STORE_URL,
            params={"appids": app_id, "cc": "br", "l": "portuguese", "filters": "price_overview"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json().get(str(app_id), {})
        if not data.get("success"):
            return {}
        price = data.get("data", {}).get("price_overview", {})
        def esc(s):
            return s.replace("$", "&#36;") if s else s

        return {
            "final": esc(price.get("final_formatted", "")),
            "original": esc(price.get("initial_formatted", "")),
            "discount": price.get("discount_percent", 0),
            "is_free": data.get("data", {}).get("is_free", False),
        }
    except Exception:
        return {}


def get_store_recommendations(genre_names: list, owned_app_ids: set, count: int = 30) -> list:
    """
    Busca jogos populares da Steam Store que o usuário não possui.
    Coleta de múltiplas fontes para maximizar variedade do pool.
    """
    candidates = []

    # Fonte 1: featuredcategories (todas as categorias)
    try:
        resp = requests.get(FEATURED_URL, params={"cc": "br", "l": "portuguese"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for category in ("top_sellers", "new_releases", "specials", "coming_soon"):
            candidates.extend(data.get(category, {}).get("items", []))
    except Exception:
        pass

    # Fonte 2: featured (destaques do dia — jogos diferentes)
    try:
        resp2 = requests.get(
            "https://store.steampowered.com/api/featured/",
            params={"cc": "br", "l": "portuguese"},
            timeout=10,
        )
        resp2.raise_for_status()
        d2 = resp2.json()
        for key in ("featured_win", "large_capsules"):
            for item in d2.get(key, []):
                # Normaliza campos para formato compatível
                item.setdefault("final_price", item.get("final_price", item.get("discounted_price", 0)))
                candidates.append(item)
    except Exception:
        pass

    if not candidates:
        return []

    def fmt_brl(cents):
        if not cents:
            return "Gratuito"
        return f"R&#36; {cents / 100:.2f}".replace(".", ",")

    recommendations = []
    seen = set()
    for item in candidates:
        app_id = item.get("id")
        if not app_id or app_id in owned_app_ids or app_id in seen:
            continue
        seen.add(app_id)

        final_cents = item.get("final_price", 0)
        original_cents = item.get("original_price", 0)
        discount = item.get("discount_percent", 0)
        header = item.get("header_image") or f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"

        recommendations.append({
            "app_id": app_id,
            "name": item.get("name", ""),
            "price": fmt_brl(final_cents),
            "original_price": fmt_brl(original_cents) if discount > 0 else "",
            "discount": discount,
            "header_image": header,
        })

        if len(recommendations) >= count:
            break

    return recommendations


def get_player_achievements(app_id: int) -> list:
    api_key, steam_id = _get_credentials()
    try:
        resp = requests.get(
            f"{BASE_URL}/ISteamUserStats/GetPlayerAchievements/v0001/",
            params={"key": api_key, "steamid": steam_id, "appid": app_id, "l": "portuguese"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("playerstats", {})
        if not data.get("success", False):
            return []
        return data.get("achievements", [])
    except Exception:
        return []


def get_game_schema(app_id: int) -> dict:
    api_key, _ = _get_credentials()
    try:
        resp = requests.get(
            f"{BASE_URL}/ISteamUserStats/GetSchemaForGame/v2/",
            params={"key": api_key, "appid": app_id, "l": "portuguese"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("game", {}).get("availableGameStats", {})
    except Exception:
        return {}


def get_game_details(app_id: int) -> dict:
    try:
        resp = requests.get(
            STORE_URL,
            params={"appids": app_id, "l": "portuguese", "cc": "br"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get(str(app_id), {})
        if not data.get("success"):
            return {}
        return data.get("data", {})
    except Exception:
        return {}


def _merge_achievements(player_ach: list, schema_ach: list) -> list:
    """Combina dados do jogador com nomes/ícones do schema."""
    schema_map = {a["name"]: a for a in schema_ach}
    merged = []
    for pa in player_ach:
        schema = schema_map.get(pa.get("apiname", ""), {})
        merged.append({
            "apiname": pa.get("apiname", ""),
            "name": schema.get("displayName", pa.get("apiname", "")),
            "description": schema.get("description", ""),
            "icon": schema.get("icon", ""),
            "icongray": schema.get("icongray", ""),
            "achieved": pa.get("achieved", 0),
            "unlocktime": pa.get("unlocktime", 0),
        })
    return merged


def sync_all_data(progress_callback=None):
    """
    Orquestra sincronização completa: perfil → jogos → conquistas → gêneros.
    progress_callback(step: int, total: int, msg: str) para feedback de progresso.
    """
    init_db()

    def _progress(step, total, msg):
        if progress_callback:
            progress_callback(step, total, msg)

    # 1. Perfil
    _progress(0, 4, "Buscando perfil do jogador...")
    player = get_player_summary()
    if player:
        upsert_player(player)

    # 2. Jogos
    _progress(1, 4, "Buscando biblioteca de jogos...")
    games = get_owned_games()
    if games:
        upsert_games(games)

    # 3. Conquistas (apenas jogos com horas jogadas para evitar timeout)
    played_games = [g for g in games if g.get("playtime_forever", 0) > 0]
    total_played = len(played_games)
    _progress(2, 4, f"Buscando conquistas de {total_played} jogos...")

    for i, game in enumerate(played_games):
        app_id = game["appid"]
        player_ach = get_player_achievements(app_id)
        if player_ach:
            schema = get_game_schema(app_id)
            schema_ach = schema.get("achievements", [])
            merged = _merge_achievements(player_ach, schema_ach)
            upsert_achievements(app_id, merged)
        time.sleep(0.3)  # respeita rate limit Steam

    # 4. Gêneros (apenas top 50 por horas para não exceder limite da Store API)
    _progress(3, 4, "Buscando gêneros dos jogos...")
    df = get_all_games()
    if not df.empty:
        top_games = df.nlargest(50, "playtime_forever")
        for _, row in top_games.iterrows():
            if row["genres"]:
                continue
            details = get_game_details(int(row["app_id"]))
            if details:
                genres = ",".join(g["description"] for g in details.get("genres", []))
                update_game_genres(int(row["app_id"]), genres)
            time.sleep(0.5)

    _progress(4, 4, "Sincronização concluída!")
