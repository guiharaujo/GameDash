import streamlit as st
import streamlit.components.v1 as components
from src.database import init_db, get_player, get_all_games, get_achievement_summary
from src.steam_api import sync_all_data

st.set_page_config(
    page_title="GameDash",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS global Steam-style
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b2838 100%);
        border-right: 1px solid #2a475e;
    }
    /* Cards de métrica */
    [data-testid="metric-container"] {
        background: #16202d;
        border: 1px solid #2a475e;
        border-radius: 8px;
        padding: 16px;
    }
    /* Botão primário */
    .stButton > button {
        background: linear-gradient(135deg, #1a9fff 0%, #0078c8 100%);
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        transition: opacity 0.2s;
    }
    .stButton > button:hover {
        opacity: 0.85;
    }
    /* Títulos de seção */
    h1, h2, h3 { color: #c6d4df; }
    /* Separador */
    hr { border-color: #2a475e; }
    /* Imagens arredondadas */
    img { border-radius: 4px; }

    /* Cards de jogo com hover */
    .game-hover-card {
        position: relative;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #2a475e;
        background: #16202d;
        cursor: pointer;
        transition: border-color 0.2s, transform 0.2s;
    }
    .game-hover-card:hover {
        border-color: #66c0f4;
        transform: translateY(-3px);
    }
    .game-hover-card img {
        width: 100%;
        display: block;
        border-radius: 0;
    }
    .game-hover-card .gh-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(170deg, rgba(10,20,32,0.97) 0%, rgba(22,32,45,0.95) 100%);
        opacity: 0;
        transition: opacity 0.25s ease;
        padding: 10px 12px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 6px;
    }
    .game-hover-card:hover .gh-overlay { opacity: 1; }
    .gh-title {
        color: #66c0f4;
        font-weight: 700;
        font-size: 0.82em;
        line-height: 1.3;
    }
    .gh-row {
        color: #c6d4df;
        font-size: 0.75em;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .gh-bar-bg {
        flex: 1;
        height: 5px;
        background: #2a475e;
        border-radius: 3px;
        overflow: hidden;
    }
    .gh-bar-fill {
        height: 100%;
        background: #66c0f4;
        border-radius: 3px;
    }
    .gh-genre {
        display: inline-block;
        background: #1a3f5c;
        color: #66c0f4;
        border-radius: 10px;
        padding: 1px 7px;
        font-size: 0.68em;
        margin: 1px;
        white-space: nowrap;
    }
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
    st.title("🎮 GameDash")
    st.caption("Seu dashboard pessoal da Steam")

    # ── Auto-sync na primeira abertura ────────────────────────────────────
    player = get_player()
    if not player and "auto_synced" not in st.session_state:
        st.session_state["auto_synced"] = True
        with st.spinner("🔄 Primeira abertura — carregando seus dados da Steam..."):
            try:
                sync_all_data()
            except Exception:
                pass
        st.rerun()

    # ── Sidebar ────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Controles")
        if st.button("🔄 Atualizar dados", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(step, total, msg):
                progress_bar.progress(step / total if total > 0 else 0)
                status_text.text(msg)

            with st.spinner("Sincronizando com a Steam..."):
                try:
                    sync_all_data(progress_callback=update_progress)
                    st.success("Dados atualizados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

        st.markdown("---")
        st.markdown("##### Navegação")

    # ── Perfil ─────────────────────────────────────────────────────────────
    player = get_player()

    if not player:
        st.warning("Não foi possível carregar o perfil. Clique em **Atualizar dados**.")
        return

    col_avatar, col_info = st.columns([1, 4])
    with col_avatar:
        if player.get("avatar_full_url"):
            st.image(player["avatar_full_url"], width=120)
    with col_info:
        st.subheader(player.get("name", "Jogador"))
        if player.get("country"):
            st.caption(f"🌍 {player['country']}")
        if player.get("profile_url"):
            st.markdown(f"[Ver perfil na Steam]({player['profile_url']})")
        if player.get("updated_at"):
            st.caption(f"Última sincronização: {player['updated_at'].strftime('%d/%m/%Y %H:%M')}")

    st.markdown("---")

    # ── Métricas ───────────────────────────────────────────────────────────
    games_df = get_all_games()
    ach_summary = get_achievement_summary()

    total_games = len(games_df) if not games_df.empty else 0
    total_minutes = int(games_df["playtime_forever"].sum()) if not games_df.empty else 0
    games_played = int((games_df["playtime_forever"] > 0).sum()) if not games_df.empty else 0
    total_unlocked = int(ach_summary["unlocked"].sum()) if not ach_summary.empty else 0
    total_achievements = int(ach_summary["total"].sum()) if not ach_summary.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎮 Total de Jogos", total_games)
    c2.metric("▶️ Jogos Jogados", games_played)
    c3.metric("⏱️ Horas Totais", format_hours(total_minutes))
    c4.metric("🏆 Conquistas", f"{total_unlocked}/{total_achievements}")

    st.markdown("---")

    # ── Top jogos com hover ────────────────────────────────────────────────
    if not games_df.empty:
        st.subheader("🕹️ Jogos Mais Jogados")

        top5 = games_df.nlargest(5, "playtime_forever")
        if not ach_summary.empty:
            top5 = top5.merge(
                ach_summary[["app_id", "total", "unlocked", "progress"]],
                on="app_id", how="left"
            )
            top5["total"]    = top5["total"].fillna(0).astype(int)
            top5["unlocked"] = top5["unlocked"].fillna(0).astype(int)
            top5["progress"] = top5["progress"].fillna(0)
        else:
            top5["total"] = top5["unlocked"] = top5["progress"] = 0

        cards_items = ""
        for _, row in top5.iterrows():
            app_id   = int(row["app_id"])
            name     = row["name"]
            hours    = format_hours(int(row["playtime_forever"]))
            unlocked = int(row["unlocked"])
            total    = int(row["total"])
            progress = float(row["progress"])
            genres   = row.get("genres", "") or ""
            img_url  = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"

            genre_badges = "".join(
                f'<span class="genre-tag">{g.strip()}</span>'
                for g in genres.split(",") if g.strip()
            ) or '<span style="color:#888;font-size:0.72em">—</span>'

            ach_html = ""
            if total > 0:
                ach_html = f"""
                <div class="info-row">
                    <span>🏆 {unlocked}/{total}</span>
                    <div class="bar-bg"><div class="bar-fill" style="width:{progress:.0f}%"></div></div>
                    <span>{progress:.0f}%</span>
                </div>"""

            cards_items += f"""
            <div class="card">
                <img src="{img_url}" alt="{name}">
                <div class="overlay">
                    <div class="game-title">{name}</div>
                    <div class="info-row">⏱ {hours}</div>
                    {ach_html}
                    <div class="genres">{genre_badges}</div>
                </div>
            </div>"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; font-family: sans-serif; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    padding: 4px 2px;
  }}
  .card {{
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #2a475e;
    background: #16202d;
    transition: border-color .2s, transform .2s;
    cursor: pointer;
  }}
  .card:hover {{
    border-color: #66c0f4;
    transform: translateY(-3px);
  }}
  .card img {{
    width: 100%;
    display: block;
    aspect-ratio: 460/215;
    object-fit: cover;
  }}
  .overlay {{
    position: absolute;
    inset: 0;
    background: linear-gradient(160deg,rgba(10,20,32,.96),rgba(22,35,50,.94));
    opacity: 0;
    transition: opacity .25s;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 6px;
  }}
  .card:hover .overlay {{ opacity: 1; }}
  .game-title {{
    color: #66c0f4;
    font-weight: 700;
    font-size: 13px;
    line-height: 1.3;
  }}
  .info-row {{
    color: #c6d4df;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 5px;
  }}
  .bar-bg {{
    flex: 1;
    height: 5px;
    background: #2a475e;
    border-radius: 3px;
    overflow: hidden;
  }}
  .bar-fill {{
    height: 100%;
    background: #66c0f4;
    border-radius: 3px;
  }}
  .genres {{
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    margin-top: 2px;
  }}
  .genre-tag {{
    background: #1a3f5c;
    color: #66c0f4;
    border-radius: 10px;
    padding: 1px 7px;
    font-size: 10px;
    white-space: nowrap;
  }}
</style>
</head>
<body>
  <div class="grid">
    {cards_items}
  </div>
</body>
</html>"""

        components.html(html, height=220)


if __name__ == "__main__":
    main()
