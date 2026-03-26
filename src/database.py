import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Boolean, DateTime, Text, Float
)
from sqlalchemy.orm import DeclarativeBase, Session
import pandas as pd


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "gamedash.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"
    steam_id = Column(String, primary_key=True)
    name = Column(String)
    avatar_url = Column(String)
    avatar_full_url = Column(String)
    profile_url = Column(String)
    country = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Game(Base):
    __tablename__ = "games"
    app_id = Column(Integer, primary_key=True)
    name = Column(String)
    img_icon_url = Column(String)
    img_logo_url = Column(String)
    playtime_forever = Column(Integer, default=0)   # minutos
    playtime_2weeks = Column(Integer, default=0)    # minutos
    genres = Column(Text, default="")               # JSON-like "Ação,RPG"
    last_synced = Column(DateTime, default=datetime.utcnow)


class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(Integer)
    api_name = Column(String)
    name = Column(String)
    description = Column(Text)
    icon_url = Column(String)
    icon_gray_url = Column(String)
    unlocked = Column(Boolean, default=False)
    unlock_time = Column(Integer, default=0)  # unix timestamp


def init_db():
    Base.metadata.create_all(engine)


# ── Player ──────────────────────────────────────────────────────────────────

def upsert_player(data: dict):
    with Session(engine) as session:
        steam_id = data.get("steamid") or data.get("steam_id", "")
        player = session.get(Player, steam_id) or Player(steam_id=steam_id)
        player.name = data.get("personaname", "")
        player.avatar_url = data.get("avatar", "")
        player.avatar_full_url = data.get("avatarfull", "")
        player.profile_url = data.get("profileurl", "")
        player.country = data.get("loccountrycode", "")
        player.updated_at = datetime.utcnow()
        session.merge(player)
        session.commit()


def get_player() -> dict:
    with Session(engine) as session:
        player = session.query(Player).first()
        if not player:
            return {}
        return {
            "steam_id": player.steam_id,
            "name": player.name,
            "avatar_url": player.avatar_url,
            "avatar_full_url": player.avatar_full_url,
            "profile_url": player.profile_url,
            "country": player.country,
            "updated_at": player.updated_at,
        }


# ── Games ────────────────────────────────────────────────────────────────────

def upsert_games(games_list: list):
    with Session(engine) as session:
        for g in games_list:
            game = session.get(Game, g["appid"]) or Game(app_id=g["appid"])
            game.name = g.get("name", f"App {g['appid']}")
            game.img_icon_url = g.get("img_icon_url", "")
            game.img_logo_url = g.get("img_logo_url", "")
            game.playtime_forever = g.get("playtime_forever", 0)
            game.playtime_2weeks = g.get("playtime_2weeks", 0)
            if "genres" in g:
                game.genres = g["genres"]
            game.last_synced = datetime.utcnow()
            session.merge(game)
        session.commit()


def update_game_genres(app_id: int, genres: str):
    with Session(engine) as session:
        game = session.get(Game, app_id)
        if game:
            game.genres = genres
            session.commit()


def get_all_games() -> pd.DataFrame:
    with Session(engine) as session:
        games = session.query(Game).all()
        if not games:
            return pd.DataFrame()
        return pd.DataFrame([{
            "app_id": g.app_id,
            "name": g.name,
            "img_icon_url": g.img_icon_url,
            "img_logo_url": g.img_logo_url,
            "playtime_forever": g.playtime_forever,
            "playtime_2weeks": g.playtime_2weeks,
            "genres": g.genres or "",
            "last_synced": g.last_synced,
        } for g in games])


# ── Achievements ─────────────────────────────────────────────────────────────

def upsert_achievements(app_id: int, achievements_list: list):
    with Session(engine) as session:
        # Remove as existentes para esse jogo e reinsere
        session.query(Achievement).filter(Achievement.app_id == app_id).delete()
        for a in achievements_list:
            ach = Achievement(
                app_id=app_id,
                api_name=a.get("apiname", ""),
                name=a.get("name", ""),
                description=a.get("description", ""),
                icon_url=a.get("icon", ""),
                icon_gray_url=a.get("icongray", ""),
                unlocked=bool(a.get("achieved", 0)),
                unlock_time=a.get("unlocktime", 0),
            )
            session.add(ach)
        session.commit()


def get_achievements_by_game(app_id: int) -> list:
    with Session(engine) as session:
        rows = session.query(Achievement).filter(Achievement.app_id == app_id).all()
        return [{
            "app_id": a.app_id,
            "api_name": a.api_name,
            "name": a.name,
            "description": a.description,
            "icon_url": a.icon_url,
            "icon_gray_url": a.icon_gray_url,
            "unlocked": a.unlocked,
            "unlock_time": a.unlock_time,
        } for a in rows]


def get_all_achievements() -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.query(Achievement).all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([{
            "app_id": a.app_id,
            "api_name": a.api_name,
            "name": a.name,
            "description": a.description,
            "icon_url": a.icon_url,
            "icon_gray_url": a.icon_gray_url,
            "unlocked": a.unlocked,
            "unlock_time": a.unlock_time,
        } for a in rows])


def get_achievement_summary() -> pd.DataFrame:
    """Retorna por jogo: total de conquistas e desbloqueadas."""
    df = get_all_achievements()
    if df.empty:
        return pd.DataFrame()
    summary = df.groupby("app_id").agg(
        total=("api_name", "count"),
        unlocked=("unlocked", "sum"),
    ).reset_index()
    summary["progress"] = (summary["unlocked"] / summary["total"] * 100).round(1)
    return summary
