"""Rodinné úlohy: local integration and bundled dashboard card."""
from datetime import timedelta
from pathlib import Path
import logging
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN
from .controller import Controller
from .engine import RuleError

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    hass.data.setdefault(DOMAIN, {})
    await hass.http.async_register_static_paths([
        StaticPathConfig("/family_quests-static", str(Path(__file__).parent / "frontend"), False)
    ])
    websocket_api.async_register_command(hass, ws_get)
    websocket_api.async_register_command(hass, ws_action)
    return True


async def async_setup_entry(hass, entry):
    controller = Controller(hass, entry)
    await controller.load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    entry.async_on_unload(async_track_time_interval(hass, controller.tick, timedelta(seconds=30)))
    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


def get_controller(hass):
    items = hass.data.get(DOMAIN, {})
    if not items:
        raise RuleError("Najprv pridaj integráciu Rodinné úlohy v Nastaveniach.")
    return next(iter(items.values()))


@websocket_api.websocket_command({vol.Required("type"): "family_quests/get"})
@websocket_api.async_response
async def ws_get(hass, connection, msg):
    try:
        result = await get_controller(hass).transact(admin=connection.user.is_admin)
        connection.send_result(msg["id"], result)
    except RuleError as exc:
        connection.send_error(msg["id"], "family_quests_error", str(exc))
    except Exception:
        _LOGGER.exception("Rodinné úlohy: čítanie zlyhalo")
        connection.send_error(msg["id"], "storage_error", "Údaje sa nepodarilo načítať. Pozri systémový denník HA.")


@websocket_api.websocket_command({
    vol.Required("type"): "family_quests/action",
    vol.Required("action"): str,
    vol.Required("data"): dict,
    vol.Required("request_id"): str,
    vol.Required("expected_version"): int,
})
@websocket_api.async_response
async def ws_action(hass, connection, msg):
    try:
        # Authorization is server-side, never derived from card configuration.
        result = await get_controller(hass).transact(
            action=msg["action"], data=msg["data"], actor=connection.user.id,
            admin=connection.user.is_admin, request_id=msg["request_id"],
            expected_version=msg["expected_version"])
        connection.send_result(msg["id"], result)
    except (RuleError, KeyError, TypeError, ValueError) as exc:
        connection.send_error(msg["id"], "family_quests_error", str(exc))
    except Exception:
        _LOGGER.exception("Rodinné úlohy: operácia sa neuložila")
        connection.send_error(msg["id"], "storage_error", "Zmenu sa nepodarilo uložiť. Obnov kartu a skontroluj stav.")
