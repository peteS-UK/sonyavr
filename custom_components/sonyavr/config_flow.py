import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import probatio
from homeassistant import config_entries, core
from homeassistant.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_PORT,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_MAX_VOLUME,
    CONF_PING_INTERVAL,
    CONF_POWER_CYCLE_INIT,
    CONF_SOUND_MODES,
    CONF_SOURCE_NAMES,
    CONF_SOURCES,
    CONF_ZONES,
    DOMAIN,
)
from .sonyavr import SOUND_FIELD_MENU_MAP, SOURCE_MENU_MAP
from .source_names import clean_names

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): cv.string,
        probatio.Required(CONF_NAME): cv.string,
        probatio.Required(CONF_MODEL): cv.string,
        probatio.Optional(CONF_PORT, default=33335): cv.string,
    }
)

OPTIONS_SCHEMA = probatio.Schema(
    {
        probatio.Optional("max_volume"): probatio.All(
            NumberSelector(
                NumberSelectorConfig(min=-100, max=100, mode=NumberSelectorMode.SLIDER)
            ),
            probatio.Coerce(int),
        ),
        probatio.Optional("ping_interval"): probatio.All(
            NumberSelector(
                NumberSelectorConfig(min=0, max=600, mode=NumberSelectorMode.SLIDER)
            ),
            probatio.Coerce(int),
        ),
        probatio.Optional(CONF_POWER_CYCLE_INIT, default=True): BooleanSelector(),
        probatio.Optional(CONF_ZONES): SelectSelector(
            SelectSelectorConfig(
                options=["Zone 2", "Zone 3"],
                multiple=True,
                mode=SelectSelectorMode.LIST,
            )
        ),
    }
)

SHOW_SCHEMA = probatio.Schema(
    {
        probatio.Optional(CONF_SOURCES): SelectSelector(
            SelectSelectorConfig(
                options=sorted(SOURCE_MENU_MAP.values(), key=str.casefold),
                multiple=True,
                mode=SelectSelectorMode.LIST,
            )
        ),
        probatio.Optional(CONF_SOUND_MODES): SelectSelector(
            SelectSelectorConfig(
                options=sorted(SOUND_FIELD_MENU_MAP.values(), key=str.casefold),
                multiple=True,
                mode=SelectSelectorMode.LIST,
            )
        ),
    }
)


async def validate_auth(hass: core.HomeAssistant, data: dict) -> None:
    if "host" not in data.keys():
        data["host"] = ""

    if "name" not in data.keys():
        data["name"] = ""

    if "model" not in data.keys():
        data["model"] = ""

    if "port" not in data.keys():
        data["port"] = ""

    if (
        (len(data["host"]) < 3)
        or (len(data["name"]) < 1)
        or (len(data["model"]) < 1)
        or (len(data["port"]) < 1)
    ):
        # Manual entry requires host and name
        raise ValueError


class SonyAVRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_auth(self.hass, user_input)
            except ValueError:
                errors["base"] = "data"
            if not errors:
                # Input is valid, set data.
                self.data = user_input
                return self.async_create_entry(title="Sony AVR", data=self.data)

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init", menu_options=["config", "show", "names"]
        )

    def _save(self, new: dict[str, Any]):
        return self.async_create_entry(
            title="", data={**self.config_entry.options, **new}
        )

    async def async_step_config(self, user_input: dict[str, Any] | None = None):
        """General configuration."""
        if user_input is not None:
            # An emptied multi-select may be omitted; save it as "no zones"
            return self._save({CONF_ZONES: [], **user_input})

        options = self.config_entry.options
        return self.async_show_form(
            step_id="config",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {
                    CONF_MAX_VOLUME: options.get(CONF_MAX_VOLUME),
                    CONF_PING_INTERVAL: options.get(CONF_PING_INTERVAL, 60),
                    CONF_POWER_CYCLE_INIT: options.get(CONF_POWER_CYCLE_INIT, True),
                    CONF_ZONES: options.get(CONF_ZONES, []),
                },
            ),
        )

    async def async_step_show(self, user_input: dict[str, Any] | None = None):
        """Choose which inputs and sound modes are shown."""
        if user_input is not None:
            return self._save(user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="show",
            data_schema=self.add_suggested_values_to_schema(
                SHOW_SCHEMA,
                {
                    CONF_SOURCES: options.get(
                        CONF_SOURCES, list(SOURCE_MENU_MAP.values())
                    ),
                    CONF_SOUND_MODES: options.get(
                        CONF_SOUND_MODES, list(SOUND_FIELD_MENU_MAP.values())
                    ),
                },
            ),
        )

    async def async_step_names(self, user_input: dict[str, Any] | None = None):
        """Optional custom display names for the inputs being shown."""
        if user_input is not None:
            return self._save({CONF_SOURCE_NAMES: clean_names(user_input)})

        sources = self.config_entry.options.get(CONF_SOURCES) or list(
            SOURCE_MENU_MAP.values()
        )
        current = self.config_entry.options.get(CONF_SOURCE_NAMES, {})
        schema = probatio.Schema(
            {
                probatio.Optional(source, default=current.get(source, "")): TextSelector()
                for source in sorted(SOURCE_MENU_MAP.values(), key=str.casefold)
                if source in sources
            }
        )
        return self.async_show_form(step_id="names", data_schema=schema)