"""Lightweight authentication for the client panel.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib, per-user salt). Login
issues an opaque random session token stored in the database. No extra deps.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import List, Optional

from sqlmodel import Session, select

from .models import Account, AuthToken, License, PassOrder, Trader

_ITERATIONS = 200_000


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), stored)


def register_user(session: Session, name: str, email: str, password: str) -> Trader:
    email = email.strip().lower()
    if len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres")
    existing = session.exec(select(Trader).where(Trader.email == email)).first()
    if existing is not None:
        raise ValueError("Ese email ya está registrado")
    trader = Trader(name=name, email=email, hashed_password=hash_password(password))
    session.add(trader)
    session.commit()
    session.refresh(trader)
    return trader


def login(session: Session, email: str, password: str) -> str:
    email = email.strip().lower()
    trader = session.exec(select(Trader).where(Trader.email == email)).first()
    if trader is None or not verify_password(password, trader.hashed_password):
        raise ValueError("Email o contraseña incorrectos")
    token = secrets.token_urlsafe(32)
    session.add(AuthToken(token=token, trader_id=trader.id))
    session.commit()
    return token


def trader_for_token(session: Session, token: Optional[str]) -> Optional[Trader]:
    if not token:
        return None
    row = session.get(AuthToken, token)
    if row is None:
        return None
    return session.get(Trader, row.trader_id)


def logout(session: Session, token: str) -> None:
    row = session.get(AuthToken, token)
    if row is not None:
        session.delete(row)
        session.commit()


def trader_history(session: Session, trader_id: int) -> dict:
    """All of a trader's activity across the three business lines."""
    accounts = session.exec(select(Account).where(Account.trader_id == trader_id)).all()
    licenses = session.exec(select(License).where(License.trader_id == trader_id)).all()
    orders = session.exec(select(PassOrder).where(PassOrder.trader_id == trader_id)).all()
    return {
        "accounts": [a.model_dump() for a in accounts],
        "licenses": [l.model_dump() for l in licenses],
        "pass_orders": [o.model_dump() for o in orders],
    }
