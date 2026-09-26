import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY
from homeassistant.const import CONF_IP_ADDRESS

class Tuya3PhaseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=f"Licznik {user_input[CONF_IP_ADDRESS]}", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_IP_ADDRESS): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_LOCAL_KEY): str,
            })
        )
