from __future__ import annotations

from enum import Enum


class DcType(str, Enum):
    API = "api"
    BOT = "bot"
    DCS = "dcs"
    RUBINO = "rubino"
    SOCKET = "socket"
    WALLET = "wallet"
