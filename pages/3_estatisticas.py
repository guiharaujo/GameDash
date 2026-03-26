import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import pandas as pd
from datetime import date, datetime
from src.database import init_db, get_all_games
from src.steam_api import get_most_played_steam_games, get_store_recommendations

st.set_page_config(page_title="Estatísticas – GameDash", page_icon="📊", layout="wide")

st.markdown("""
<style>
    h1,h2,h3 { color:#c6d4df; }
    hr { border-color:#2a475e; }
    [data-testid="metric-container"] {
        background:#16202d; border:1px solid #2a475e;
        border-radius:8px; padding:14px;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color:#66c0f4; }
    [data-testid="metric-container"] [data-testid="stMetricLabel"] { color:#8fa3b0; }
</style>
""", unsafe_allow_html=True)

init_db()


@st.cache_data(ttl=3600)
def load_top_steam():
    return get_most_played_steam_games(10)


@st.cache_data(ttl=3600)
def load_top_promos():
    import requests
    try:
        resp = requests.get(
            "https://store.steampowered.com/api/featuredcategories/",
            params={"cc": "br", "l": "portuguese"}, timeout=10,
        )
        specials = resp.json().get("specials", {}).get("items", [])
        specials = sorted(specials, key=lambda x: x.get("discount_percent", 0), reverse=True)
        results = []
        for item in specials[:5]:
            app_id = item.get("id")
            final  = item.get("final_price", 0)
            orig   = item.get("original_price", 0)
            disc   = item.get("discount_percent", 0)
            results.append({
                "app_id": app_id,
                "name": item.get("name", ""),
                "discount": disc,
                "price": f"R$ {final/100:.2f}".replace(".", ",") if final else "Gratuito",
                "original_price": f"R$ {orig/100:.2f}".replace(".", ",") if orig else "",
                "savings": f"R$ {(orig-final)/100:.2f}".replace(".", ",") if orig and final else "",
                "header_image": item.get("header_image") or f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg",
                "expiration": item.get("discount_expiration", 0),
            })
        return results
    except Exception:
        return []


@st.cache_data(ttl=3600)
def load_game_prices(app_ids: tuple) -> dict:
    import requests, time
    prices = {}
    for app_id in app_ids:
        try:
            resp = requests.get(
                "https://store.steampowered.com/api/appdetails",
                params={"appids": app_id, "cc": "br", "l": "portuguese", "filters": "price_overview,basic"},
                timeout=8,
            )
            data = resp.json().get(str(app_id), {})
            if data.get("success"):
                d = data.get("data", {})
                if d.get("is_free"):
                    prices[app_id] = {"label": "Gratuito", "discount": 0, "original": ""}
                else:
                    p = d.get("price_overview", {})
                    final = p.get("final", 0)
                    orig  = p.get("initial", 0)
                    disc  = p.get("discount_percent", 0)
                    def fmt(c): return f"R$ {c/100:.2f}".replace(".", ",")
                    prices[app_id] = {
                        "label": fmt(final) if final else "—",
                        "original": fmt(orig) if disc > 0 else "",
                        "discount": disc,
                    }
            else:
                prices[app_id] = {"label": "—", "discount": 0, "original": ""}
        except Exception:
            prices[app_id] = {"label": "—", "discount": 0, "original": ""}
        time.sleep(0.2)
    return prices


CARD_CSS = """
* { box-sizing:border-box; margin:0; padding:0; }
body { background:transparent; font-family:sans-serif; }
.grid { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; padding:4px 2px 8px; }
.card {
    position:relative; border-radius:8px; overflow:hidden;
    border:1px solid #2a475e; background:#16202d;
    transition:border-color .2s, transform .2s; cursor:pointer;
}
.card:hover { border-color:#66c0f4; transform:translateY(-3px); box-shadow:0 6px 20px rgba(102,192,244,.15); }
.card img { width:100%; display:block; aspect-ratio:460/215; object-fit:cover; }
.rank-badge {
    position:absolute; top:6px; left:8px; z-index:2;
    background:rgba(10,20,32,.88); color:#66c0f4;
    font-weight:700; font-size:14px; padding:2px 8px; border-radius:4px;
}
.rank-badge.gold   { color:#ffd700; border:1px solid rgba(255,215,0,.4); }
.rank-badge.silver { color:#c0c0c0; border:1px solid rgba(192,192,192,.4); }
.rank-badge.bronze { color:#cd7f32; border:1px solid rgba(205,127,50,.4); }
.overlay {
    position:absolute; inset:0;
    background:linear-gradient(160deg,rgba(10,20,32,.97),rgba(22,35,50,.95));
    opacity:0; transition:opacity .25s;
    padding:12px; display:flex; flex-direction:column; justify-content:center; gap:5px;
}
.card:hover .overlay { opacity:1; }
.g-title { color:#66c0f4; font-weight:700; font-size:13px; line-height:1.3; margin-bottom:2px; }
.g-row { color:#c6d4df; font-size:11.5px; display:flex; align-items:center; gap:5px; }
.bar-bg { flex:1; height:4px; background:#2a475e; border-radius:2px; overflow:hidden; }
.bar-fill { height:100%; background:linear-gradient(90deg,#1a9fff,#66c0f4); border-radius:2px; }
.price-row { display:flex; align-items:center; flex-wrap:wrap; gap:4px; margin-top:3px; }
.p-free  { color:#4caf50; font-size:12px; font-weight:600; }
.p-final { color:#a4d7a5; font-size:12px; font-weight:600; }
.p-orig  { color:#888; text-decoration:line-through; font-size:10px; }
.p-disc  { background:#4c6b22; color:#a4d7a5; border-radius:3px; padding:1px 5px; font-size:10px; font-weight:bold; }
.p-owned { background:#1a3f5c; color:#66c0f4; border-radius:3px; padding:1px 6px; font-size:10px; }
.divider { height:1px; background:#2a475e; margin:3px 0; }
.store-btn {
    display:inline-block; margin-top:3px; color:#66c0f4; font-size:10.5px;
    text-decoration:none; border:1px solid #2a475e; border-radius:4px;
    padding:2px 8px; transition:background .2s; width:fit-content;
}
.store-btn:hover { background:#1a3f5c; }
"""


def rank_badge(rank):
    cls = {1: "gold", 2: "silver", 3: "bronze"}.get(rank, "")
    label = {1: "🥇 #1", 2: "🥈 #2", 3: "🥉 #3"}.get(rank, f"#{rank}")
    return f'<div class="rank-badge {cls}">{label}</div>'


def price_html(info: dict) -> str:
    if not info:
        return ""
    if info.get("label") == "Gratuito":
        return '<span class="p-free">Gratuito para Jogar</span>'
    disc = info.get("discount", 0)
    label = info.get("label", "")
    orig  = info.get("original", "")
    if not label or label == "—":
        return ""
    if disc > 0:
        return f'<span class="p-orig">{orig}</span><span class="p-disc">-{disc}%</span><span class="p-final">{label}</span>'
    return f'<span class="p-final">{label}</span>'


def build_top10_cards(games, owned_ids, prices):
    cards = ""
    max_peak = max((g["peak_in_game"] for g in games), default=1)
    for game in games:
        app_id = game["app_id"]
        name   = game["name"]
        rank   = game["rank"]
        peak   = game["peak_in_game"]
        peak_s = f"{peak:,}".replace(",", ".")
        pct    = peak / max_peak * 100
        lw     = game.get("last_week_rank", rank)
        delta  = lw - rank
        owned  = app_id in owned_ids
        pi     = prices.get(app_id, {})

        trend = ""
        if delta > 0:
            trend = f'<span style="color:#4caf50;font-size:11px">▲ +{delta}</span>'
        elif delta < 0:
            trend = f'<span style="color:#ef5350;font-size:11px">▼ {delta}</span>'
        else:
            trend = '<span style="color:#888;font-size:11px">→</span>'

        owned_span = '<span class="p-owned">✓ Possuo</span>' if owned else ''
        ph = price_html(pi)

        cards += f"""
        <div class="card">
            {rank_badge(rank)}
            <img src="https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"
                 alt="{name}" onerror="this.style.background='#2a475e'">
            <div class="overlay">
                <div class="g-title">{name}</div>
                <div class="divider"></div>
                <div class="g-row">
                    <span>👥 {peak_s} jogadores</span>
                    {trend}
                </div>
                <div class="g-row">
                    <div class="bar-bg"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>
                    <span style="font-size:10px;color:#8fa3b0">{pct:.0f}%</span>
                </div>
                <div class="price-row">{owned_span}{ph}</div>
                <a class="store-btn" href="https://store.steampowered.com/app/{app_id}/" target="_blank">Ver na Steam →</a>
            </div>
        </div>"""
    return cards


def main():
    mes = date.today().strftime("%B de %Y").capitalize()
    st.title(f"📊 Steam Global — {mes}")

    games_df  = get_all_games()
    owned_ids = set(int(x) for x in games_df["app_id"].tolist()) if not games_df.empty else set()

    # ── Carrega dados ──────────────────────────────────────────────────────
    with st.spinner("Carregando dados da Steam..."):
        top_steam = load_top_steam()
        promos    = load_top_promos()

    if not top_steam:
        st.warning("Não foi possível carregar o ranking.")
        return

    app_ids = tuple(g["app_id"] for g in top_steam)
    with st.spinner("Buscando preços..."):
        prices = load_game_prices(app_ids)

    # ── Métricas globais ───────────────────────────────────────────────────
    total_peak  = sum(g["peak_in_game"] for g in top_steam)
    top1        = top_steam[0]
    biggest_up  = max(top_steam, key=lambda g: (g.get("last_week_rank", g["rank"]) - g["rank"]))
    biggest_up_delta = biggest_up.get("last_week_rank", biggest_up["rank"]) - biggest_up["rank"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Jogadores no Top 10", f"{total_peak:,}".replace(",", "."))
    c2.metric("🥇 Mais Jogado Agora",   top1["name"][:22])
    c3.metric("📈 Maior Alta",
              biggest_up["name"][:22],
              f"+{biggest_up_delta} posições" if biggest_up_delta > 0 else "Estável")
    owned_in_top = sum(1 for g in top_steam if g["app_id"] in owned_ids)
    c4.metric("🎮 Do Top 10 que Possuo", f"{owned_in_top} / 10")

    st.markdown("---")

    # ── Cards top 10 ──────────────────────────────────────────────────────
    st.subheader("🌍 Top 10 Jogos Mais Jogados na Steam")
    st.caption("Pico de jogadores simultâneos nas últimas 24h · Passe o mouse para ver detalhes")

    cards_html = build_top10_cards(top_steam, owned_ids, prices)
    components.html(
        f"<!DOCTYPE html><html><head><style>{CARD_CSS}</style></head>"
        f"<body><div class='grid'>{cards_html}</div></body></html>",
        height=230,
    )

    # ── Tabela detalhada ───────────────────────────────────────────────────
    with st.expander("📋 Ver ranking completo em tabela", expanded=False):
        rows = []
        for g in top_steam:
            pi    = prices.get(g["app_id"], {})
            delta = g.get("last_week_rank", g["rank"]) - g["rank"]
            trend = f"▲ +{delta}" if delta > 0 else (f"▼ {delta}" if delta < 0 else "→")
            rows.append({
                "Rank":         f"#{g['rank']}",
                "Jogo":         g["name"],
                "Pico jogadores": f"{g['peak_in_game']:,}".replace(",", "."),
                "Variação":     trend,
                "Preço":        pi.get("label", "—"),
                "Possuo":       "✓" if g["app_id"] in owned_ids else "",
            })
        df_table = pd.DataFrame(rows)
        st.dataframe(
            df_table, use_container_width=True, hide_index=True,
            column_config={
                "Rank":     st.column_config.TextColumn(width="small"),
                "Jogo":     st.column_config.TextColumn(width="large"),
                "Possuo":   st.column_config.TextColumn(width="small"),
                "Variação": st.column_config.TextColumn(width="small"),
            }
        )

    # ── Gráfico de barras ──────────────────────────────────────────────────
    df_bar = pd.DataFrame(top_steam)
    df_bar["horas_s"] = df_bar["peak_in_game"].apply(lambda v: f"{v:,}".replace(",", "."))
    df_bar = df_bar.sort_values("peak_in_game")

    fig = px.bar(
        df_bar, x="peak_in_game", y="name", orientation="h",
        color="peak_in_game",
        color_continuous_scale=["#0d1b2a", "#1a9fff", "#66c0f4"],
        labels={"peak_in_game": "Pico de jogadores", "name": ""},
        text="horas_s",
    )
    fig.update_layout(
        paper_bgcolor="#16202d", plot_bgcolor="#16202d",
        font_color="#c6d4df", showlegend=False, coloraxis_showscale=False,
        margin=dict(l=0, r=30, t=10, b=0), height=300,
        xaxis=dict(gridcolor="#2a475e", tickformat=","),
        yaxis=dict(gridcolor="#2a475e"),
    )
    fig.update_traces(textposition="outside", marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Promoções ──────────────────────────────────────────────────────────
    st.subheader("🔥 Top 5 Promoções Ativas na Steam")
    st.caption("Maiores descontos no momento · Ordenado por % de desconto")

    if not promos:
        st.warning("Não foi possível carregar promoções.")
        return

    # Métricas das promoções
    max_disc = max(p["discount"] for p in promos)
    avg_disc = sum(p["discount"] for p in promos) / len(promos)
    owned_promos = sum(1 for p in promos if p["app_id"] in owned_ids)

    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("🏷️ Maior Desconto", f"{max_disc}% OFF")
    pc2.metric("📉 Desconto Médio", f"{avg_disc:.0f}% OFF")
    pc3.metric("✓ Que Já Possuo",  f"{owned_promos} / {len(promos)}")

    promo_css = CARD_CSS + """
    .promo-disc {
        position:absolute; top:0; right:0; z-index:2;
        background:linear-gradient(135deg,#4c6b22,#6a9f2a);
        color:#fff; font-weight:800; font-size:18px;
        padding:8px 12px; border-radius:0 8px 0 8px;
        text-shadow:0 1px 3px rgba(0,0,0,.5);
    }
    .savings { color:#a4d7a5; font-size:11px; }
    """

    promo_cards = ""
    for p in promos:
        app_id = p["app_id"]
        owned  = app_id in owned_ids
        exp_s  = ""
        if p.get("expiration"):
            try:
                exp_s = datetime.fromtimestamp(p["expiration"]).strftime("⏰ Até %d/%m às %H:%M")
            except Exception:
                pass

        savings_s = f'<div class="savings">💰 Economize {p["savings"]}</div>' if p.get("savings") else ""
        owned_s   = '<span class="p-owned">✓ Já Possuo</span>' if owned else ""

        promo_cards += f"""
        <div class="card">
            <div class="promo-disc">-{p['discount']}%</div>
            <img src="{p['header_image']}" alt="{p['name']}" onerror="this.style.background='#2a475e'">
            <div class="overlay">
                <div class="g-title">{p['name']}</div>
                <div class="divider"></div>
                <div class="price-row">
                    <span class="p-orig">{p['original_price']}</span>
                    <span class="p-disc">-{p['discount']}%</span>
                    <span class="p-final">{p['price']}</span>
                </div>
                {savings_s}
                {f'<div class="g-row" style="color:#8fa3b0;font-size:10.5px">{exp_s}</div>' if exp_s else ''}
                <div style="margin-top:2px">{owned_s}</div>
                <a class="store-btn" href="https://store.steampowered.com/app/{app_id}/" target="_blank">Ver oferta →</a>
            </div>
        </div>"""

    components.html(
        f"<!DOCTYPE html><html><head><style>{promo_css}</style></head>"
        f"<body><div class='grid'>{promo_cards}</div></body></html>",
        height=230,
    )


if __name__ == "__main__":
    main()
