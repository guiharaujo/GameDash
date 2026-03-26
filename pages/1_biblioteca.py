import streamlit as st
import pandas as pd
from src.database import init_db, get_all_games, get_achievement_summary

st.set_page_config(page_title="Biblioteca – GameDash", page_icon="📚", layout="wide")

st.markdown("""
<style>
    [data-testid="metric-container"] {
        background: #16202d; border: 1px solid #2a475e; border-radius: 8px; padding: 12px;
    }
    .game-card {
        background: #16202d;
        border: 1px solid #2a475e;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        transition: border-color 0.2s;
    }
    .game-card:hover { border-color: #66c0f4; }
    h1, h2, h3 { color: #c6d4df; }
    hr { border-color: #2a475e; }
</style>
""", unsafe_allow_html=True)

init_db()


def format_hours(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h == 0:
        return f"{m}min"
    return f"{h}h {m:02d}min"


def main():
    st.title("📚 Biblioteca de Jogos")

    games_df = get_all_games()
    if games_df.empty:
        st.warning("Nenhum jogo encontrado. Sincronize os dados na página inicial.")
        return

    ach_summary = get_achievement_summary()

    # Merge com conquistas
    if not ach_summary.empty:
        games_df = games_df.merge(
            ach_summary[["app_id", "total", "unlocked", "progress"]],
            on="app_id",
            how="left",
        )
        games_df["total"] = games_df["total"].fillna(0).astype(int)
        games_df["unlocked"] = games_df["unlocked"].fillna(0).astype(int)
        games_df["progress"] = games_df["progress"].fillna(0)
    else:
        games_df["total"] = 0
        games_df["unlocked"] = 0
        games_df["progress"] = 0.0

    # ── Filtros ────────────────────────────────────────────────────────────
    col_search, col_sort, col_filter = st.columns([3, 2, 2])
    with col_search:
        search = st.text_input("🔍 Buscar jogo", placeholder="Digite o nome...")
    with col_sort:
        sort_by = st.selectbox("Ordenar por", ["Horas (desc)", "Horas (asc)", "Nome A-Z", "Conquistas"])
    with col_filter:
        show_only = st.selectbox("Filtrar", ["Todos os jogos", "Jogados", "Não jogados"])

    # Aplicar filtros
    df = games_df.copy()
    if search:
        df = df[df["name"].str.contains(search, case=False, na=False)]
    if show_only == "Jogados":
        df = df[df["playtime_forever"] > 0]
    elif show_only == "Não jogados":
        df = df[df["playtime_forever"] == 0]

    sort_map = {
        "Horas (desc)": ("playtime_forever", False),
        "Horas (asc)": ("playtime_forever", True),
        "Nome A-Z": ("name", True),
        "Conquistas": ("unlocked", False),
    }
    col, asc = sort_map[sort_by]
    df = df.sort_values(col, ascending=asc)

    # ── Resumo ─────────────────────────────────────────────────────────────
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Jogos encontrados", len(df))
    c2.metric("Horas totais", format_hours(int(df["playtime_forever"].sum())))
    c3.metric("Jogados", int((df["playtime_forever"] > 0).sum()))

    st.markdown("---")
    st.subheader(f"🎮 {len(df)} jogos")

    # ── Grade de jogos ─────────────────────────────────────────────────────
    cols_per_row = 5
    rows = [df.iloc[i:i+cols_per_row] for i in range(0, len(df), cols_per_row)]

    for row_df in rows:
        cols = st.columns(cols_per_row)
        for col_idx, (_, game) in enumerate(row_df.iterrows()):
            with cols[col_idx]:
                # Capa do jogo via Steam Store
                img_url = f"https://cdn.akamai.steamstatic.com/steam/apps/{game['app_id']}/header.jpg"
                st.image(img_url, use_container_width=True)

                name = game["name"]
                st.markdown(f"**{name[:22]}{'…' if len(name) > 22 else ''}**")
                st.caption(f"⏱ {format_hours(int(game['playtime_forever']))}")

                if game["total"] > 0:
                    pct = float(game["progress"])
                    st.progress(pct / 100)
                    st.caption(f"🏆 {int(game['unlocked'])}/{int(game['total'])} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
