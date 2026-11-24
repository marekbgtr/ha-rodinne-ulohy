"""Household revision plus dynamic point sensors for participants."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, SIGNAL, VERSION


async def async_setup_entry(hass, entry, async_add_entities):
    controller = hass.data[DOMAIN][entry.entry_id]
    known = set()
    async_add_entities([BoardSensor(controller, entry)])

    @callback
    def add_people():
        added = []
        for pid in controller.engine.s["people"]:
            if pid not in known:
                known.add(pid)
                added.append(PointsSensor(controller, entry, pid))
        if added:
            async_add_entities(added)

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL, add_people))
    add_people()


class BoardSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:clipboard-check-outline"

    def __init__(self, controller, entry):
        self.controller = controller
        self._attr_unique_id = entry.entry_id + "_board"
        self._attr_name = "Prehľad"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)},
            name="Rodinné úlohy", manufacturer="Rodinné úlohy", model="Lokálna integrácia", sw_version=VERSION)

    @property
    def native_value(self):
        return self.controller.engine.s["version"]

    @property
    def extra_state_attributes(self):
        return {"family_quests_board": True, "version": VERSION}

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL, self._updated))

    @callback
    def _updated(self):
        self.async_write_ha_state()


class PointsSensor(BoardSensor):
    _attr_icon = "mdi:star-outline"

    def __init__(self, controller, entry, pid):
        super().__init__(controller, entry)
        self.pid = pid
        self._attr_unique_id = entry.entry_id + "_" + pid + "_points"

    @property
    def name(self):
        return self.controller.engine.s["people"][self.pid]["name"] + " body"

    @property
    def native_value(self):
        return self.controller.engine.balance(self.pid)

    @property
    def extra_state_attributes(self):
        p = self.controller.engine.s["people"][self.pid]
        return {"participant_id": self.pid, "symbol": p["symbol"], "unit_label": p["unit"], "active": p["active"]}
