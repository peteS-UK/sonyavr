from __future__ import annotations

import logging

from .const import DOMAIN

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass

from homeassistant import config_entries, core

from homeassistant.core import callback

from homeassistant.helpers.device_registry import DeviceInfo

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


class SonyAVRDevice(SensorEntity):
    # Representation of a Emotiva Processor

    def __init__(self, device, hass):
        self._device = device
        self._hass = hass
        self._entity_id = "sensor.sonyavr_volume"
        self._unique_id = "sonyavr_" + self._device.name.replace(" ", "_").replace(
            "-", "_"
        ).replace(":", "_")

    async def async_added_to_hass(self):
        """Handle being added to hass."""
        self._device.set_sensor_update_cb(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._device.set_sensor_update_cb(None)

    @callback
    def async_update_callback(self, reason=False):
        """Update the device's state."""
        self.async_schedule_update_ha_state()

    @property
    def name(self):
        return self._device.name + " Volume"

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
    def should_poll(self):
        return False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def entity_id(self):
        return self._entity_id

    @property
    def icon(self):
        if self._device.mute:
            return "mdi:volume-off"
        else:
            return "mdi:volume-high"

    @entity_id.setter
    def entity_id(self, entity_id):
        self._entity_id = entity_id

    @property
    def device_class(self):
        return SensorDeviceClass.SOUND_PRESSURE

    @property
    def native_unit_of_measurement(self):
        if self._device.state_service.volume_model == 3:
            return None
        else:
            return "dB"

    @property
    def native_value(self):
        return self._device.volume
