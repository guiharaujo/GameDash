import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import pandas as pd
import random
from collections import defaultdict
from src.database import init_db, get_all_games, get_achievement_summary
from src.recommendations import get_recommendations, get_top_genres
from src.steam_api import get_store_recommendations, get_game_price

st.set_page_config(page_title="Recomendações – GameDash", page_icon="💡", layout="wide")

st.markdown("""
<style>
    h1,h2,h3 { color:#c6d4df; }
    hr { border-color:#2a475e; }
    [data-testid="metric-container"] {
        background:#16202d; border:1px solid #2a475e;
        border-radius:8px; padding:14px;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color:#66c0f4; }
</style>
""", unsafe_allow_html=True)

init_db()

CARD_CSS = """
* { box-sizing:border-box; margin:0; padding:0; }
body { background:transparent; font-family:sans-serif; }
.grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; padding:4px 2px 8px; }
.grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; padding:4px 2px 8px; }
.card {
    position:relative; border-radius:8px; overflow:hidden;
    border:1px solid #2a475e; background:#16202d;
    transition:border-color .2s, transform .2s; cursor:pointer;
}
.card:hover { border-color:#66c0f4; transform:translateY(-3px); box-shadow:0 6px 20px rgba(102,192,244,.15); }
.card img { width:100%; display:block; aspect-ratio:460/215; object-fit:cover; }
.overlay {
    position:absolute; inset:0;
    background:linear-gradient(160deg,rgba(10,20,32,.97),rgba(22,35,50,.95));
    opacity:0; transition:opacity .25s;
    padding:12px; display:flex; flex-direction:column; justify-content:center; gap:5px;
}
.card:hover .overlay { opacity:1; }
.g-title { color:#66c0f4; font-weight:700; font-size:13px; line-height:1.3; }
.g-row   { color:#c6d4df; font-size:11.5px; }
.divider { height:1px; background:#2a475e; margin:2px 0; }
.bar-bg  { flex:1; height:4px; background:#2a475e; border-radius:2px; overflow:hidden; }
.bar-fill{ height:100%; background:linear-gradient(90deg,#1a9fff,#66c0f4); border-radius:2px; }
.tag     { display:inline-block; background:#1a3f5c; color:#66c0f4; border-radius:10px; padding:1px 7px; font-size:10px; margin:1px; }
.p-free  { color:#4caf50; font-size:11px; font-weight:600; }
.p-final { color:#a4d7a5; font-size:11px; font-weight:600; }
.p-orig  { color:#777; text-decoration:line-through; font-size:10px; }
.p-disc  { background:#4c6b22; color:#a4d7a5; border-radius:3px; padding:1px 5px; font-size:10px; font-weight:bold; }
.p-owned { background:#1a3f5c; color:#66c0f4; border-radius:3px; padding:1px 6px; font-size:10px; }
.store-btn {
    display:inline-block; margin-top:4px; color:#66c0f4; font-size:10.5px;
    text-decoration:none; border:1px solid #2a475e; border-radius:4px;
    padding:2px 8px; transition:background .2s;
}
.store-btn:hover { background:#1a3f5c; }
.price-row { display:flex; align-items:center; flex-wrap:wrap; gap:4px; }
.badge-new { position:absolute; top:6px; right:8px; background:rgba(102,192,244,.9); color:#0d1b2a; font-size:10px; font-weight:700; padding:2px 7px; border-radius:4px; }
.badge-owned { position:absolute; top:6px; left:8px; background:rgba(26,63,92,.92); color:#66c0f4; font-size:10px; font-weight:700; padding:2px 7px; border-radius:4px; }
"""


@st.cache_data(ttl=3600)
def load_library_prices(app_ids: tuple) -> dict:
    prices = {}
    for app_id in app_ids:
        prices[app_id] = get_game_price(app_id)
    return prices


@st.cache_data(ttl=3600)
def load_store_pool(genre_names: tuple, owned_ids: tuple) -> list:
    return get_store_recommendations(list(genre_names), set(owned_ids), count=60)


def fmt_price_html(price_dict: dict) -> str:
    if not price_dict:
        return ""
    if price_dict.get("is_free"):
        return '<span class="p-free">Gratuito</span>'
    disc  = price_dict.get("discount", 0)
    final = price_dict.get("final", "")
    orig  = price_dict.get("original", "")
    if not final:
        return ""
    if disc > 0:
        return f'<span class="p-orig">{orig}</span><span class="p-disc">-{disc}%</span><span class="p-final">{final}</span>'
    return f'<span class="p-final">{final}</span>'


def fmt_store_price(game: dict) -> str:
    price = game.get("price", "")
    disc  = game.get("discount", 0)
    orig  = game.get("original_price", "")
    if price == "Gratuito":
        return '<span class="p-free">Gratuito</span>'
    if not price:
        return ""
    if disc > 0:
        return f'<span class="p-orig">{orig}</span><span class="p-disc">-{disc}%</span><span class="p-final">{price}</span>'
    return f'<span class="p-final">{price}</span>'


def main():
    st.title("💡 Recomendações")

    data           = get_recommendations()
    top_genres     = data["top_genres"]
    library_recs   = data["recommended"]
    almost_complete = data["almost_complete"]

    all_games = get_all_games()
    owned_ids = tuple(int(x) for x in all_games["app_id"].tolist()) if not all_games.empty else ()
    owned_set = set(owned_ids)

    # ── Perfil de gamer ────────────────────────────────────────────────────
    played = all_games[all_games["playtime_forever"] > 0] if not all_games.empty else pd.DataFrame()
    total_h = int(played["playtime_forever"].sum()) // 60 if not played.empty else 0
    ach_sum = get_achievement_summary()
    total_ach = int(ach_sum["unlocked"].sum()) if not ach_sum.empty else 0

    st.subheader("🎮 Seu Perfil de Gamer")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🕹️ Jogos na Biblioteca", len(all_games) if not all_games.empty else 0)
    m2.metric("▶️ Jogos Jogados",        len(played))
    m3.metric("⏱️ Horas Totais",         f"{total_h}h")
    m4.metric("🏆 Conquistas",           total_ach)

    # ── DNA de Gêneros ─────────────────────────────────────────────────────
    if top_genres:
        st.markdown("---")
        st.subheader("🧬 Seu DNA Gamer — Gêneros Favoritos")

        col_chart, col_info = st.columns([2, 1])

        with col_chart:
            genre_df = pd.DataFrame(top_genres, columns=["Gênero", "Horas"])
            fig = px.bar(
                genre_df.sort_values("Horas"),
                x="Horas", y="Gênero", orientation="h",
                color="Horas",
                color_continuous_scale=["#0d1b2a", "#1a9fff", "#66c0f4"],
                labels={"Horas": "Horas jogadas"},
                text=genre_df.sort_values("Horas")["Horas"].apply(lambda h: f"{h:.0f}h"),
            )
            fig.update_layout(
                paper_bgcolor="#16202d", plot_bgcolor="#16202d",
                font_color="#c6d4df", showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=30, t=10, b=0), height=max(180, len(top_genres) * 42),
            )
            fig.update_traces(textposition="outside", marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)

        with col_info:
            st.markdown("<br>", unsafe_allow_html=True)
            total_genre_h = sum(h for _, h in top_genres)
            for genre, hours in top_genres:
                pct = hours / total_genre_h * 100 if total_genre_h else 0
                st.markdown(f"**{genre}**")
                st.progress(pct / 100)
                st.caption(f"{hours:.0f}h · {pct:.0f}% do tempo")

    st.markdown("---")

    # ── Biblioteca: nunca jogados ──────────────────────────────────────────
    if not library_recs.empty:
        st.subheader("📦 Na Sua Biblioteca — Nunca Iniciados")
        st.caption("Você já possui esses jogos. Que tal experimentar?")

        lib_app_ids = tuple(int(x) for x in library_recs["app_id"].tolist())
        with st.spinner("Buscando preços..."):
            prices = load_library_prices(lib_app_ids)

        lib_cards = ""
        for _, game in library_recs.iterrows():
            app_id = int(game["app_id"])
            name   = game["name"]
            genres = game.get("genres", "") or ""
            pi     = prices.get(app_id, {})
            ph     = fmt_price_html(pi)
            tags   = "".join(
                f'<span class="tag">{g.strip()}</span>'
                for g in genres.split(",")[:3] if g.strip()
            )
            lib_cards += f"""
            <div class="card">
                <div class="badge-owned">✓ Já Possui</div>
                <img src="https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"
                     alt="{name}" onerror="this.style.background='#2a475e'">
                <div class="overlay">
                    <div class="g-title">{name}</div>
                    <div class="divider"></div>
                    <div class="price-row">{ph}</div>
                    <div style="display:flex;flex-wrap:wrap;gap:2px;margin-top:2px">{tags or '<span style="color:#888;font-size:10px">—</span>'}</div>
                    <a class="store-btn" href="https://store.steampowered.com/app/{app_id}/" target="_blank">Ver na Steam →</a>
                </div>
            </div>"""

        n = len(library_recs)
        grid_cls = "grid3" if n <= 3 else "grid4"
        components.html(
            f"<!DOCTYPE html><html><head><style>{CARD_CSS}</style></head>"
            f"<body><div class='{grid_cls}'>{lib_cards}</div></body></html>",
            height=240,
        )
        st.markdown("---")

    # ── Descubra na Steam Store ────────────────────────────────────────────
    genre_names = tuple(g[0] for g in top_genres) if top_genres else ()
    st.subheader("🛒 Descubra na Steam Store")
    st.caption("Jogos populares que você ainda não possui · Atualiza a cada visita")

    with st.spinner("Buscando recomendações..."):
        pool       = load_store_pool(genre_names, owned_ids)
        store_recs = random.sample(pool, min(12, len(pool))) if len(pool) >= 12 else pool

    if not store_recs:
        st.info("Não foi possível carregar recomendações agora.")
    else:
        store_cards = ""
        for game in store_recs:
            app_id = game["app_id"]
            name   = game["name"]
            disc   = game.get("discount", 0)
            ph     = fmt_store_price(game)
            new_badge = '<div class="badge-new">🔥 Em Alta</div>' if disc == 0 else ""

            store_cards += f"""
            <div class="card">
                {new_badge}
                <img src="{game['header_image']}" alt="{name}" onerror="this.style.background='#2a475e'">
                <div class="overlay">
                    <div class="g-title">{name}</div>
                    <div class="divider"></div>
                    <div class="price-row">{ph if ph else '<span style="color:#888">—</span>'}</div>
                    <a class="store-btn" href="https://store.steampowered.com/app/{app_id}/" target="_blank">Ver na Steam →</a>
                </div>
            </div>"""

        components.html(
            f"<!DOCTYPE html><html><head><style>{CARD_CSS}</style></head>"
            f"<body><div class='grid4'>{store_cards}</div></body></html>",
            height=460,
        )

    # ── Quase 100% ────────────────────────────────────────────────────────
    if not almost_complete.empty:
        st.markdown("---")
        st.subheader("🏆 Foco nas Conquistas — Quase 100%!")
        st.caption("Você está perto de completar esses jogos")

        for _, row in almost_complete.iterrows():
            app_id   = int(row["app_id"])
            name     = row.get("name", "Jogo")
            pct      = float(row["progress"])
            unlocked = int(row["unlocked"])
            total    = int(row["total"])
            remaining = total - unlocked
            color = "#4caf50" if pct >= 90 else "#66c0f4" if pct >= 80 else "#ffa726"

            col_img, col_info = st.columns([1, 4])
            with col_img:
                st.image(
                    f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",
                    use_container_width=True,
                )
            with col_info:
                st.markdown(f"**{name}**")
                pct_label = f"{pct:.1f}%"
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;margin:4px 0">'
                    f'<div style="flex:1;height:8px;background:#2a475e;border-radius:4px;overflow:hidden">'
                    f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:4px;'
                    f'transition:width .5s"></div></div>'
                    f'<span style="color:{color};font-weight:700;font-size:1em">{pct_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                cols = st.columns(3)
                cols[0].caption(f"✅ {unlocked} desbloqueadas")
                cols[1].caption(f"🔒 {remaining} restantes")
                cols[2].caption(f"📊 {total} total")
            st.markdown('<div style="border-bottom:1px solid #2a475e;margin:8px 0"></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
