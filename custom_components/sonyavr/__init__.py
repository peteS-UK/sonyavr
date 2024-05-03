"""The emotiva component."""

import logging

from homeassistant import config_entries, core
from homeassistant.const import Platform
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_MODEL

from .const import DOMAIN

from .sonyavr import SonyAVR

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.REMOTE]
#PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)

    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener

    _LOGGER.debug("Adding %s from config", hass_data[CONF_HOST])

    sonyavr = SonyAVR(hass_data[CONF_HOST], hass_data[CONF_NAME], hass_data[CONF_MODEL])

    hass_data["sonyavr"] = sonyavr

    hass.data[DOMAIN][entry.entry_id] = hass_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Remove config entry from domain.
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        # Remove options_update_listener.
        entry_data["unsub_options_update_listener"]()

    return unload_ok

