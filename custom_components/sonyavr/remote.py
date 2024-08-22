from __future__ import annotations

import logging

from homeassistant import config_entries, core
from homeassistant.components.remote import (
    RemoteEntity,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    config = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        config.update(config_entry.options)

    sonyavr = config["sonyavr"]

    async_add_entities([SonyAVRDevice(sonyavr, hass)])


class SonyAVRDevice(RemoteEntity):
    # Representation of a Sony AVR

    def __init__(self, device, hass):
        self._device = device
        self._hass = hass
        self._entity_id = "remote.sonyavr"
        self._unique_id = "sonyavr_" + self._device.name.replace(" ", "_").replace(
            "-", "_"
        ).replace(":", "_")

    async def async_added_to_hass(self):
        """Subscribe to device events."""
        await super().async_added_to_hass()
        # await self._device.command_service.async_connect()
        self._device.set_remote_update_cb(self.async_update_callback)

    def async_update_callback(self, reason=False):
        """Update the device's state."""
        self.async_schedule_update_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        self._device.set_remote_update_cb(None)
        # await self._device.command_service.async_disconnect()

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return "Remote"

    @property
    def has_entity_name(self):
        return True

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._unique_id)
            },
            name=self._device.name,
            manufacturer="Sony",
            model=self._device.model,
        )

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def entity_id(self):
        return self._entity_id

    @entity_id.setter
    def entity_id(self, entity_id):
        self._entity_id = entity_id

    async def async_turn_off(self) -> None:
        await self._device.async_turn_off()

    async def async_turn_on(self) -> None:
        await self._device.async_turn_on()

    async def async_mute_on(self) -> None:
        await self._device.async_mute_on()

    async def async_mute_off(self) -> None:
        await self._device.async_mute_off()

    async def async_update(self):
        pass

    @property
    def state(self):
        if not self._device.state_service.power:
            return "off"
        elif self._device.state_service.power:
            return "on"
        else:
            return None

    @property
    def is_volume_muted(self):
        return self._device.mute

    @property
    def volume_level(self):
        if self._device.volume is None:
            # 	# device is muted
            return 0.0
        else:
            return float(
                "%.2f"
                % (
                    (self._device.volume - self._device.volume_min)
                    / self._device.volume_range
                )
            )
