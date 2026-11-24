from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, ConfigSubentryFlow
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Node64AuthError, Node64Client, Node64ConnectError
from .entity import subentry_id
from .const import (
    DEFAULT_PORT,
    DOMAIN,
    MODULES,
    SUB_TYPE_MODULE,
)

CONF_MODULE = "module"

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): selector.TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=65535, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)

MODULE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODULE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[selector.SelectOptionDict(value=key, label=label) for key, label in MODULES.items()],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


class Node64ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUB_TYPE_MODULE: ModuleSubentryFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = Node64Client(
                session,
                f"http://{user_input[CONF_HOST]}:{int(user_input[CONF_PORT])}",
                user_input[CONF_API_KEY],
            )
            try:
                version = await client.version()
            except Node64AuthError:
                errors["base"] = "invalid_auth"
            except Node64ConnectError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{int(user_input[CONF_PORT])}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"node64 {version.get('hostname', user_input[CONF_HOST])}",
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: int(user_input[CONF_PORT]),
                        CONF_API_KEY: user_input[CONF_API_KEY],
                    },
                )

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)


class ModuleSubentryFlow(ConfigSubentryFlow):
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            module = user_input[CONF_MODULE]
            if subentry_id(self._get_entry(), module):
                return self.async_abort(reason="already_configured")
            return self.async_create_entry(title=MODULES[module], data={CONF_MODULE: module})
        return self.async_show_form(step_id="user", data_schema=MODULE_SCHEMA)
