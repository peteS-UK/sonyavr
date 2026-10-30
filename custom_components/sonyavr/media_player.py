from __future__ import annotations

import asyncio
import logging

import probatio
from homeassistant import config_entries, core
from homeassistant.components.media_player import (
    PLATFORM_SCHEMA,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.const import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
)
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    entity_platform,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.start import async_at_started

from .const import (
    CONF_POWER_CYCLE_INIT,
    CONF_SOUND_MODES,
    CONF_SOURCE_NAMES,
    CONF_SOURCES,
    CONF_ZONES,
    DOMAIN,
    SERVICE_SEND_COMMAND,
    SERVICE_UPDATE_STATE,
)
from .sonyavr import SOURCE_MENU_MAP, ZONE_FOLLOW_MAIN, ZONE_FOLLOW_MAIN_NAME
from .source_names import default_name, display_list, display_name

_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        probatio.Required(CONF_HOST): cv.string,
        probatio.Required(CONF_NAME): cv.string,
        probatio.Required(CONF_MODEL): cv.string,
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
    | MediaPlayerEntityFeature.VOLUME_STEP
)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    config = hass.data[DOMAIN][config_entry.entry_id]

    if config_entry.options:
        config.update(config_entry.options)

    sonyavr = config["sonyavr"]

    # Opt-in Zone 2 / Zone 3 media players
    zones = sorted(config_entry.options.get(CONF_ZONES, []))
    config["zones"] = zones
    entities = [SonyAVRDevice(sonyavr, config_entry)]
    entities += [
        SonyAVRZone(sonyavr, config_entry, int(zone.split()[-1])) for zone in zones
    ]
    async_add_entities(entities)

    # Register entity services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SEND_COMMAND,
        {
            probatio.Required("Command"): cv.string,
            probatio.Optional("Value"): cv.string,
        },
        SonyAVRDevice.send_command.__name__,
    )
    platform.async_register_entity_service(
        SERVICE_UPDATE_STATE,
        {},
        SonyAVRDevice.update_status.__name__,
    )


class SonyAVRDevice(MediaPlayerEntity):
    # Representation of a Sony AVR

    def __init__(self, device, config_entry):
        self._device = device
        self._config_entry = config_entry
        self._entity_id = "media_player.sonyavr"
        self._unique_id = "sonyavr_" + self._device.name.replace(" ", "_").replace(
            "-", "_"
        ).replace(":", "_")
        self._device_class = "receiver"
        self._notifier_task: asyncio.Task | None = None

    async def _async_startup(self, loop):
        self._notifier_task = self.hass.async_create_background_task(
            self._device.run_notifier(), name="sonyavr notifier task"
        )
        self._ping_task = self.hass.async_create_background_task(
            self._device.run_ping_watcher(), name="sonyavr ping watcher task"
        )
        await self._device.command_service.async_connect()

        await asyncio.sleep(1)

        if self._device.state_service.power is None:
            _LOGGER.debug("Power state is uninitialised, so initialising all states")
            _power_state = await self._device.async_get_power_state()
            _power_cycle = self._config_entry.options.get(CONF_POWER_CYCLE_INIT, True)

            # Turn on and off to force the feedback
            if not _power_state and _power_cycle:
                _LOGGER.debug("_power_state is False, so turning on")
                await self._device.async_turn_on()
                await asyncio.sleep(20)
            await self._device.async_update_status()
            _LOGGER.debug("Device states initialised")
            if not _power_state and _power_cycle:
                await asyncio.sleep(1)
                await self._device.async_turn_off()

    async def async_added_to_hass(self):
        """Subscribe to device events."""
        self._device.set_update_cb(self.async_update_callback)

        async_at_started(self.hass, self._async_startup)

    def async_update_callback(self, reason=False):
        """Update the device's state."""
        _LOGGER.debug("Updating Media Player state")
        self.async_schedule_update_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect device object when removed."""
        self._device.set_update_cb(None)

        await self._device.command_service.async_disconnect()

        try:
            await self._device.stop_notifier()

            if self._notifier_task is not None:
                self._notifier_task.cancel()
                try:
                    await self._notifier_task
                except asyncio.CancelledError:
                    _LOGGER.debug("Notifier task cancelled")
                self._notifier_task = None

        except Exception:
            _LOGGER.exception("Error stopping notifier")

        try:
            await self._device.stop_ping_watcher()

            if self._ping_task is not None:
                self._ping_task.cancel()
                try:
                    await self._ping_task
                except asyncio.CancelledError:
                    _LOGGER.debug("Ping Watcher task cancelled")
                self._ping_task = None
        except Exception:
            _LOGGER.exception("Error stopping ping watcher")

    @property
    def should_poll(self):
        return False

    @property
    def icon(self):
        if self._device.state_service.power:
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
            manufacturer="Sony",
            model=self._device.model,
        )

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
        if not self._device.state_service.power:
            return MediaPlayerState.OFF
        elif self._device.state_service.power:
            return MediaPlayerState.ON
        else:
            return None

    @property
    def source_list(self):
        return display_list(
            self._device.sources,
            self._config_entry.options.get(CONF_SOURCES),
            self._config_entry.options.get(CONF_SOURCE_NAMES),
        )

    @property
    def source(self):
        return display_name(
            self._device.source, self._config_entry.options.get(CONF_SOURCE_NAMES)
        )

    @property
    def sound_mode_list(self):
        visible = self._config_entry.options.get(CONF_SOUND_MODES)
        if not visible:
            return self._device.modes
        return tuple(m for m in self._device.modes if m in visible)

    @property
    def sound_mode(self):
        return self._device.mode

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        return SUPPORT_SONYAVR

    @property
    def is_volume_muted(self):
        return self._device.mute

    @property
    def extra_state_attributes(self):
        _attributes = {}

        _attributes["volume"] = self._device.volume
        return _attributes

    @property
    def volume_level(self):
        if self._device.volume is None or self._device.volume_range == 0:
            # 	# device is muted or range isn't yet defined
            return 0.0
        else:
            return float(
                "%.2f"
                % (
                    (self._device.volume - self._device.volume_min)
                    / self._device.volume_range
                )
            )

    async def async_set_volume_level(self, volume: float) -> None:
        _vol = (volume * self._device.volume_range) + self._device.volume_min
        await self._device.async_volume_set(_vol)

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

    async def async_update(self):
        await self._device.async_update_status()

    async def async_select_source(self, source: str) -> None:
        await self._device.async_set_source(
            default_name(source, self._config_entry.options.get(CONF_SOURCE_NAMES))
        )

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self._device.async_set_mode(sound_mode)

    async def send_command(self, Command, Value=None):
        await self._device.async_send_command(Command, Value)

    async def update_status(self):
        _LOGGER.debug("Updating status")
        await self._device.async_update_status()


SUPPORT_SONYAVR_ZONE = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
)


class SonyAVRZone(MediaPlayerEntity):
    """Zone 2 or Zone 3 of the AVR.

    Power and input are reported by the AVR when they change; until then the
    state is unknown. Volume is requested at startup.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = "receiver"
    _attr_supported_features = SUPPORT_SONYAVR_ZONE

    def __init__(self, device, config_entry, zone):
        self._device = device
        self._config_entry = config_entry
        self._zone = zone
        main_id = "sonyavr_" + self._device.name.replace(" ", "_").replace(
            "-", "_"
        ).replace(":", "_")
        self._attr_unique_id = f"{main_id}_zone{zone}"
        self._attr_name = f"Zone {zone}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, main_id)})

    @property
    def _state(self):
        return self._device.state_service.zones[self._zone]

    @property
    def _names(self):
        return self._config_entry.options.get(CONF_SOURCE_NAMES)

    async def async_added_to_hass(self):
        self._device.set_zone_update_cb(self._zone, self.async_write_ha_state)
        async_at_started(self.hass, self._async_startup)

    async def _async_startup(self, _hass):
        # Let the main entity connect first
        await asyncio.sleep(5)
        await self._device.async_zone_update_status(self._zone)

    async def async_will_remove_from_hass(self) -> None:
        self._device.set_zone_update_cb(self._zone, None)

    @property
    def icon(self):
        return "mdi:speaker-multiple" if self._state.power else "mdi:speaker-off"

    @property
    def state(self) -> MediaPlayerState | None:
        if self._state.power is None:
            return None
        return MediaPlayerState.ON if self._state.power else MediaPlayerState.OFF

    @property
    def source_list(self):
        main = display_list(
            self._device.sources,
            self._config_entry.options.get(CONF_SOURCES),
            self._names,
        )
        return (ZONE_FOLLOW_MAIN_NAME, *main)

    @property
    def source(self):
        source = self._state.source
        if source is None:
            return None
        if source == ZONE_FOLLOW_MAIN:
            return ZONE_FOLLOW_MAIN_NAME
        return display_name(SOURCE_MENU_MAP.get(source, source), self._names)

    @property
    def is_volume_muted(self):
        return self._state.muted

    @property
    def volume_level(self):
        volume = self._state.volume
        if volume is None or not self._device.volume_range:
            return None
        level = (volume - self._device.volume_min) / self._device.volume_range
        return round(min(max(level, 0.0), 1.0), 2)

    @property
    def extra_state_attributes(self):
        return {"volume": self._state.volume}

    async def async_turn_on(self) -> None:
        await self._device.async_zone_turn_on(self._zone)

    async def async_turn_off(self) -> None:
        await self._device.async_zone_turn_off(self._zone)

    async def async_mute_volume(self, mute: bool) -> None:
        await self._device.async_zone_set_mute(self._zone, mute)

    async def async_set_volume_level(self, volume: float) -> None:
        vol = (volume * self._device.volume_range) + self._device.volume_min
        await self._device.async_zone_volume_set(self._zone, vol)

    async def async_volume_up(self) -> None:
        await self._device.async_zone_volume_up(self._zone)

    async def async_volume_down(self) -> None:
        await self._device.async_zone_volume_down(self._zone)

    async def async_select_source(self, source: str) -> None:
        if source != ZONE_FOLLOW_MAIN_NAME:
            source = default_name(source, self._names)
        await self._device.async_zone_set_source(self._zone, source)
