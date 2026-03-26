import streamlit as st
from datetime import datetime
from src.database import init_db, get_all_games, get_achievements_by_game

st.set_page_config(page_title="Conquistas – GameDash", page_icon="🏆", layout="wide")

st.markdown("""
<style>
    .ach-card {
        background: #16202d;
        border: 1px solid #2a475e;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 6px;
    }
    .ach-unlocked { border-left: 3px solid #66c0f4; }
    .ach-locked   { border-left: 3px solid #4a4a4a; opacity: 0.7; }
    h1, h2, h3 { color: #c6d4df; }
    hr { border-color: #2a475e; }
    [data-testid="metric-container"] {
        background: #16202d; border: 1px solid #2a475e; border-radius: 8px; padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

init_db()


def fmt_date(ts: int) -> str:
    if ts == 0:
        return ""
    try:
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y")
    except Exception:
        return ""


def main():
    st.title("🏆 Conquistas")

    games_df = get_all_games()
    if games_df.empty:
        st.warning("Nenhum jogo encontrado. Sincronize os dados na página inicial.")
        return

    # Apenas jogos com horas (provavelmente têm conquistas)
    played = games_df[games_df["playtime_forever"] > 0].sort_values("playtime_forever", ascending=False)

    if played.empty:
        st.info("Nenhum jogo jogado ainda.")
        return

    # Seletor de jogo
    game_options = {row["name"]: int(row["app_id"]) for _, row in played.iterrows()}
    selected_name = st.selectbox("Selecione um jogo", list(game_options.keys()))
    app_id = game_options[selected_name]

    achievements = get_achievements_by_game(app_id)

    if not achievements:
        st.info("Este jogo não tem conquistas registradas. Tente sincronizar novamente.")
        return

    unlocked = [a for a in achievements if a["unlocked"]]
    locked = [a for a in achievements if not a["unlocked"]]
    pct = len(unlocked) / len(achievements) * 100

    # ── Cabeçalho do jogo ──────────────────────────────────────────────────
    col_img, col_stats = st.columns([1, 3])
    with col_img:
        st.image(
            f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",
            use_container_width=True,
        )
    with col_stats:
        st.subheader(selected_name)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", len(achievements))
        c2.metric("Desbloqueadas", len(unlocked))
        c3.metric("Progresso", f"{pct:.1f}%")
        st.progress(pct / 100)
        if pct == 100:
            st.success("🎉 Jogo 100% completado!")

    st.markdown("---")

    # ── Filtro ──────────────────────────────────────────────────────────────
    show = st.radio("Mostrar", ["Todas", "Desbloqueadas", "Bloqueadas"], horizontal=True)
    if show == "Desbloqueadas":
        display = unlocked
    elif show == "Bloqueadas":
        display = locked
    else:
        display = sorted(achievements, key=lambda a: (not a["unlocked"], a["name"]))

    st.markdown(f"**{len(display)} conquistas**")

    # ── Lista de conquistas ─────────────────────────────────────────────────
    for ach in display:
        status_class = "ach-unlocked" if ach["unlocked"] else "ach-locked"
        icon_url = ach["icon_url"] if ach["unlocked"] else (ach["icon_gray_url"] or ach["icon_url"])
        unlock_date = fmt_date(ach.get("unlock_time", 0))

        col_icon, col_info = st.columns([1, 10])
        with col_icon:
            if icon_url:
                st.image(icon_url, width=48)
            else:
                st.markdown("🏅" if ach["unlocked"] else "🔒")
        with col_info:
            status_icon = "✅" if ach["unlocked"] else "🔒"
            title = f"{status_icon} **{ach['name'] or ach['api_name']}**"
            if unlock_date:
                title += f"  <small style='color:#66c0f4'>({unlock_date})</small>"
            st.markdown(title, unsafe_allow_html=True)
            if ach.get("description"):
                st.caption(ach["description"])
        st.markdown('<div style="border-bottom:1px solid #2a475e;margin:4px 0"></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
