from collections import defaultdict
import pandas as pd
from src.database import get_all_games, get_achievement_summary


def get_top_genres(df: pd.DataFrame, top_n: int = 3) -> list:
    """Retorna os top N gêneros baseado em horas totais jogadas."""
    genre_hours = defaultdict(float)
    for _, row in df.iterrows():
        if not row["genres"]:
            continue
        hours = row["playtime_forever"] / 60
        for genre in row["genres"].split(","):
            genre = genre.strip()
            if genre:
                genre_hours[genre] += hours
    return sorted(genre_hours.items(), key=lambda x: x[1], reverse=True)[:top_n]


def get_recommendations() -> dict:
    """
    Retorna um dicionário com:
    - top_genres: [(gênero, horas)]
    - recommended: DataFrame de jogos recomendados (poucos jogados nos top gêneros)
    - almost_complete: DataFrame de jogos quase 100% nas conquistas
    """
    df = get_all_games()
    if df.empty:
        return {"top_genres": [], "recommended": pd.DataFrame(), "almost_complete": pd.DataFrame()}

    top_genres = get_top_genres(df)
    top_genre_names = [g[0] for g in top_genres]

    # Jogos nunca jogados (0 horas) que combinam com os top gêneros
    unplayed = df[df["playtime_forever"] == 0]

    recommended_rows = []
    unmatched_rows = []
    for _, row in unplayed.iterrows():
        if row["genres"]:
            game_genres = [g.strip() for g in row["genres"].split(",")]
            if any(g in top_genre_names for g in game_genres):
                recommended_rows.append(row)
                continue
        unmatched_rows.append(row)

    # Se não houver jogos não jogados com gêneros compatíveis, mostra todos os não jogados
    if not recommended_rows:
        recommended_rows = unmatched_rows

    recommended = pd.DataFrame(recommended_rows).sort_values("name") if recommended_rows else pd.DataFrame()

    # Jogos quase 100% em conquistas (entre 70% e 99%)
    summary = get_achievement_summary()
    almost_complete = pd.DataFrame()
    if not summary.empty:
        near = summary[(summary["progress"] >= 70) & (summary["progress"] < 100)]
        if not near.empty:
            near = near.merge(df[["app_id", "name", "img_logo_url"]], on="app_id", how="left")
            almost_complete = near.sort_values("progress", ascending=False)

    return {
        "top_genres": top_genres,
        "recommended": recommended,
        "almost_complete": almost_complete,
    }
