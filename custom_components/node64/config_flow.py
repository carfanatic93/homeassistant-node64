from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import Node64AuthError, Node64Client, Node64ConnectError
from .const import DEFAULT_PORT, DOMAIN

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


class Node64ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

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
