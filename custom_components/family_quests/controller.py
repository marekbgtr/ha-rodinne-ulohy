"""Serialized durable transactions. No success response before disk save."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import logging
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .const import DOMAIN, SIGNAL
from .engine import Engine, RuleError, require, text

_LOGGER = logging.getLogger(__name__)


class Controller:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, 1, DOMAIN + "." + entry.entry_id)
        self.lock = asyncio.Lock()
        self.engine = Engine(tz=hass.config.time_zone)

    async def load(self):
        saved = await self.store.async_load()
        self.engine = Engine(saved, self.hass.config.time_zone)
        now = datetime.now(timezone.utc)
        if saved is None and self.entry.data.get("samples", True):
            for name in ("Maty", "Momo"):
                self.engine.save_person({"name": name}, now, "setup")
            for name, icon, points in (("Prezliecť do pyžama", "👕", 1), ("Umytie zubov", "🦷", 2)):
                self.engine.save_task({"name": name, "icon": icon, "points": points,
                    "group": "Večer", "penalty": 0}, now, "setup")
            self.engine.save_reward({"name": "Spoločný výlet", "icon": "🌳", "cost": 20}, now, "setup")
            pajamas = next(iter(self.engine.s["tasks"]))
            self.engine.save_reward({"name": "Čítanie rozprávky", "icon": "📖", "kind": "task", "task": pajamas}, now, "setup")
        self.engine.tick(now)
        self.engine.s["version"] += 1
        await self.store.async_save(self.engine.s)

    async def transact(self, action=None, data=None, actor="system", admin=False,
                       request_id=None, expected_version=None, now=None):
        now = now or datetime.now(timezone.utc)
        async with self.lock:
            before = deepcopy(self.engine.s)
            try:
                if action:
                    require(isinstance(request_id, str) and 8 <= len(request_id) <= 100,
                            "Chýba identifikátor operácie.")
                    token = actor + ":" + request_id
                    if token in self.engine.s["request_ids"]:
                        return self.engine.snapshot(now, admin)
                    require(type(expected_version) is int and expected_version == self.engine.s["version"],
                            "Údaje sa medzitým zmenili. Obnov kartu a zopakuj akciu.")
                self.engine.tick(now)
                if action:
                    self.engine.apply(action, data or {}, now, actor, admin)
                    self.engine.s["request_ids"].append(token)
                    self.engine.s["request_ids"] = self.engine.s["request_ids"][-1000:]
                changed = before != self.engine.s
                if changed:
                    self.engine.s["version"] += 1
                    await self.store.async_save(self.engine.s)
            except Exception:
                self.engine.s = before
                raise
            if changed:
                async_dispatcher_send(self.hass, SIGNAL)
                # Notify only on a persisted transition to ready, including fully funded pools.
                for req_id, req in self.engine.s["requests"].items():
                    if req["status"] != "pending" or before["requests"].get(req_id, {}).get("status") == "pending":
                        continue
                    person = self.engine.person(req["person"])
                    try:
                        self.hass.bus.async_fire("family_quests_reward_requested", {
                            "config_entry_id": self.entry.entry_id,
                            "request_id": req_id,
                            "person_id": req["person"],
                            "person_name": ", ".join(self.engine.person(pid)["name"] for pid in self.engine.contributions(req)) if req.get("shared") else person["name"],
                            "shared": req.get("shared", False),
                            "contributors": self.engine.contributions(req) if req.get("shared") else {},
                            "reward_id": req["reward"]["id"],
                            "reward_name": req["reward"]["name"],
                            "cost": req["reward"]["cost"],
                            "symbol": person["symbol"],
                            "requested_at": req.get("ready_at", req["at"]),
                        })
                    except Exception:
                        # A notification failure must not undo an already saved request.
                        _LOGGER.exception("Žiadosť je uložená, ale udalosť upozornenia zlyhala")
            return self.engine.snapshot(now, admin)

    async def tick(self, _now):
        try:
            await self.transact()
        except Exception:
            _LOGGER.exception("Nepodarilo sa aktualizovať Rodinné úlohy; zmeny neboli potvrdené")
