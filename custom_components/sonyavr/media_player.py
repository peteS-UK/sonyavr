

from __future__ import annotations

import logging
import asyncio

from .const import DOMAIN

from .sonyavr import SonyAVR

import voluptuous as vol

from homeassistant.components.media_player import (
	PLATFORM_SCHEMA,
	MediaPlayerEntity,
	MediaPlayerEntityFeature,
	MediaPlayerState
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
	CONF_DISCOVER,
	CONF_MANUAL,
	SERVICE_SEND_COMMAND,
	DEFAULT_NAME
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
	{
		vol.Optional(CONF_HOST): cv.string
	}
)

SUPPORT_SONYAVR = (
	MediaPlayerEntityFeature.VOLUME_STEP
	| MediaPlayerEntityFeature.VOLUME_MUTE
	| MediaPlayerEntityFeature.TURN_ON
	| MediaPlayerEntityFeature.TURN_OFF
	| MediaPlayerEntityFeature.SELECT_SOURCE
	| MediaPlayerEntityFeature.VOLUME_SET
	| MediaPlayerEntityFeature.SELECT_SOUND_MODE 
)

async def async_setup_entry(
	hass: core.HomeAssistant,
	config_entry: config_entries.ConfigEntry,
	async_add_entities,
) -> None:

	config = hass.data[DOMAIN][config_entry.entry_id]

	_LOGGER.debug("Host from config %s", config[CONF_HOST])

	if config_entry.options:
		config.update(config_entry.options)

	receivers = []

#	if config[CONF_DISCOVER]:
#		receivers = await hass.async_add_executor_job(Emotiva.discover,3)
#		_configdiscovered = False
#		for receiver in receivers:
#
#			_ip, _xml = receiver
#				
#			emotiva = Emotiva(_ip, _xml)
#
#			#Get additional notify
#			if config.get(CONF_NOTIFICATIONS) is not None:
#				_LOGGER.debug("Adding %s",config[CONF_NOTIFICATIONS])
#				_notify_set = set(config[CONF_NOTIFICATIONS].replace(" ","").split(","))
#			else:
#				_notify_set = set()
#
#			emotiva._events = emotiva._events.union(_notify_set)
#			emotiva._current_state.update(dict((m, None) for m in _notify_set))
#		
#			_LOGGER.debug("Adding %s from discovery", _ip)
#
#			async_add_entities([EmotivaDevice(emotiva, hass)])


	if config[CONF_MANUAL] and not any([config[CONF_HOST] in tup for tup in receivers]):
		_LOGGER.debug("Adding %s from config", config[CONF_HOST])

		sonyavr = SonyAVR(config[CONF_HOST])

#		_notify_set = set()

#		emotiva._events = emotiva._events.union(_notify_set)
#		emotiva._current_state.update(dict((m, None) for m in _notify_set))


		async_add_entities([SonyAVRDevice(sonyavr, hass)])

	# Register entity services
	platform = entity_platform.async_get_current_platform()
	platform.async_register_entity_service(
		SERVICE_SEND_COMMAND,
		{
			vol.Required("Command"): cv.string
		},
		SonyAVRDevice.send_command.__name__,
	)


class SonyAVRDevice(MediaPlayerEntity):
	# Representation of a Emotiva Processor

	def __init__(self, device, hass):

		self._device = device
		self._hass = hass
		self._entity_id = "media_player.sonyavr"
		self._unique_id = "sonyavr_"+"name".replace(" ","_").replace("-","_").replace(":","_")
		self._device_class = "receiver"
		self._notifier_task = None
		
	async def async_added_to_hass(self):
		"""Subscribe to device events."""
		self._device.set_update_cb(self.async_update_callback)
		# self._hass.async_create_task(self._device.run_notifier())
		# changed to stop startup hanging
		#*****
		#self._notifier_task = asyncio.create_task(self._device.run_notifier())
		
		#await self._device.udp_connect()
		#await self._device.async_subscribe_events()


	def async_update_callback(self, reason = False):
		"""Update the device's state."""
		_LOGGER.debug("Calling async_schedule_update_ha_state")
		self.async_schedule_update_ha_state()
		

	async def async_will_remove_from_hass(self) -> None:
		"""Disconnect device object when removed."""
		self._device.set_update_cb(None)
		#*****
		# await self._device.async_unsubscribe_events()
		# await self._device.udp_disconnect()
		#try:
		#	self._notifier_task.cancel()
		#except:
		#	pass

	should_poll = False

	@property
	def should_poll(self):
		return False


	@property
	def icon(self):
		if self._device.state_service.power == True: 
			return "mdi:audio-video"
		else:
			return "mdi:audio-video-off"

	@property
	def name(self):
		# return self._device.name
		return None

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
	def friendly_name(self):
		return self._device.name + " Processor"

	@property
	def unique_id(self):
		return self._unique_id
		
	@property
	def entity_id(self):
		return self._entity_id
	
	@property
	def device_class(self):
		return self._device_class

	@entity_id.setter
	def entity_id(self, entity_id):
		self._entity_id = entity_id

	@property
	def state(self) -> MediaPlayerState | None:
			if self._device.state_service.power == False:
				return MediaPlayerState.OFF
			if self._device.state_service.power == True:
				return MediaPlayerState.ON

			return None

	@property
	def source_list(self):
		#return self._device.sources
		return ""
	
	@property
	def source(self):
		#return self._device.source
		return ""
	
	@property
	def sound_mode_list(self):
		#return self._device.modes	
		return ""
	
	@property
	def sound_mode(self):
		#return self._device.mode
		return ""

	@property
	def supported_features(self) -> MediaPlayerEntityFeature:
			return SUPPORT_SONYAVR

	@property
	def is_volume_muted(self):
		#return self._device.mute
		return False
	
#	@property 
#	def extra_state_attributes(self):
#
#		_attributes = {}
#
#		for ev in self._device._events:
#			if ev.startswith("power") == False:
#				_attributes[ev] = self._device._current_state[ev]
#
#		if self._device.mute == True:
#			_attributes["volume"] = "0"
#		return _attributes
	
	@property
	def volume_level(self):
		#if self._device.volume is None:
		#	# device is muted
		#	return 0.0
		#else:
		#	return float("%.2f" % ((self._device.volume-self._device._volume_min)/self._device._volume_range))
		return 0

	async def async_set_volume_level(self, volume: float) -> None:
		_vol = ((volume * self._device._volume_range)+self._device._volume_min)
		await self._device.async_volume_set(str(_vol))

	async def async_turn_off(self) -> None:
		await self._device.async_turn_off()

	async def async_turn_on(self) -> None:
		await self._device.async_turn_on()

	async def async_mute_volume(self, mute: bool) -> None:
		await self._device.async_set_mute(mute)

	async def async_volume_up(self):
		await self._device.async_volume_up()

	async def async_volume_down(self):
		await self._device.async_volume_down()

	#def update(self):
	#	self._device._update_status(self._device._events, float(self._device._proto_ver))		

	async def async_update(self):
		pass
		#await self._device.async_update_status(self._device._events, float(self._device._proto_ver))

	async def async_select_source(self, source: str) -> None:		
		await self._device.async_set_source(source)

	async def async_select_sound_mode(self, sound_mode: str) -> None:
		await self._device.async_set_mode(sound_mode)

	async def send_command(self, Command, Value):
		await self._device.async_send_command(Command,Value)
