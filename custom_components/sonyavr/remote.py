

from __future__ import annotations

import logging
import asyncio

from collections.abc import Iterable
from typing import Any

from .const import DOMAIN

from .emotiva import SonyAVR

import voluptuous as vol

from homeassistant.components.remote import (
	ATTR_DELAY_SECS,
	ATTR_NUM_REPEATS,
	DEFAULT_DELAY_SECS,
	RemoteEntity
)

from homeassistant import config_entries, core

from homeassistant.const import CONF_HOST, CONF_NAME
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
	CONF_NOTIFICATIONS,
	CONF_NOTIFY_PORT,
	CONF_CTRL_PORT,
	CONF_PROTO_VER,
	CONF_DISCOVER,
	CONF_MANUAL,
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

	receivers = []

	if config[CONF_DISCOVER]:
		receivers = await hass.async_add_executor_job(SonyAVR.discover,3)
		_configdiscovered = False
		for receiver in receivers:

			_ip, _xml = receiver
				
			emotiva = SonyAVR(_ip, _xml)
			_LOGGER.debug("Adding %s from discovery", _ip)
			async_add_entities([EmotivaDevice(emotiva, hass)])

	if config[CONF_MANUAL] and not any([config[CONF_HOST] in tup for tup in receivers]):
		_LOGGER.debug("Adding %s:%s from config", config[CONF_HOST]
				, config[CONF_NAME])

		emotiva = SonyAVR(config[CONF_HOST], transp_xml = "", 
					_ctrl_port = config[CONF_CTRL_PORT], _notify_port = config[CONF_NOTIFY_PORT],
					_proto_ver = config[CONF_PROTO_VER], _name = config[CONF_NAME])

		async_add_entities([EmotivaDevice(emotiva, hass)])

	

class EmotivaDevice(RemoteEntity):
	# Representation of a Emotiva Processor

	def __init__(self, device, hass):

		self._device = device
		self._hass = hass
		self._entity_id = "remote.emotivaprocessor"
		self._unique_id = "emotiva_"+self._device.name.replace(" ","_").replace("-","_").replace(":","_")

	async def async_added_to_hass(self):
		"""Handle being added to hass."""
		await super().async_added_to_hass()
		

	async def async_will_remove_from_hass(self) -> None:
		pass

#	@property
#	def icon(self):
#		return "mdi:audio-video"

	@property
	def name(self):
		# return self._device.name
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
			manufacturer='Emotiva',
			model=self._device.model)

	should_poll = False

	@property
	def should_poll(self):
		return False

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
		await self._device.async_send_command_no_ack("power_off","0")

	async def async_turn_on(self) -> None:
		await self._device.async_send_command_no_ack("power_on","0")

	async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
		#await self._device.async_send_command(Command,Value)
		try:
			emo_Command = command[0].replace(" ","").split(",")[0]
			Value = command[0].replace(" ","").split(",")[1]
			if len(emo_Command) == 0 or len(Value) == 0:
				_LOGGER.error("Invalid remote command format.  Must be command,value")
				return False
			else:
				await self._device.async_send_command_no_ack(emo_Command,Value)
		except:
			_LOGGER.error("Invalid remote command format.  Must be command,value")
			return False
		

