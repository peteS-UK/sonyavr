

from __future__ import annotations

import logging

from collections.abc import Iterable
from typing import Any

from .const import DOMAIN

from .sonyavr import SonyAVR

import voluptuous as vol

from homeassistant.components.remote import (
	ATTR_DELAY_SECS,
	ATTR_NUM_REPEATS,
	DEFAULT_DELAY_SECS,
	RemoteEntity
)

from homeassistant import config_entries, core

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
	config_validation as cv,
	discovery_flow,
	entity_platform,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.device_registry import DeviceInfo

_LOGGER = logging.getLogger(__name__)


from .const import (
	DEFAULT_NAME
)


async def async_setup_entry(
	hass: core.HomeAssistant,
	config_entry: config_entries.ConfigEntry,
	async_add_entities,
) -> None:

	config = hass.data[DOMAIN][config_entry.entry_id]

	if config_entry.options:
		config.update(config_entry.options)

	sonyavr = SonyAVR(config[CONF_HOST], config[CONF_NAME], config[CONF_MODEL])

	async_add_entities([SonyAVRDevice(sonyavr, hass)])

	

class SonyAVRDevice(RemoteEntity):
	# Representation of a Sony AVR

	def __init__(self, device, hass):

		self._device = device
		self._hass = hass
		self._entity_id = "remote.sonyavr"
		self._unique_id = "sonyavr_"+self._device.name.replace(" ","_").replace("-","_").replace(":","_")
		
	async def async_added_to_hass(self):
		"""Subscribe to device events."""
		await super().async_added_to_hass()		
		await self._device.command_service.async_connect()


	async def async_will_remove_from_hass(self) -> None:
  
		await self._device.command_service.async_disconnect()


	should_poll = False

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
			manufacturer='Sony',
			model=self._device.model)

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

