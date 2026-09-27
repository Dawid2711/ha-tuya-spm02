import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY, CONF_PRODUCTION_SENSOR, CONF_REFRESH_INTERVAL
from homeassistant.const import CONF_IP_ADDRESS

# ---------------------------------------------------------------------------
# Schemat walidacji — wspólny dla konfiguracji początkowej i opcji
# ---------------------------------------------------------------------------
BASE_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): str,
    vol.Required(CONF_DEVICE_ID): str,
    vol.Required(CONF_LOCAL_KEY): str,
    vol.Optional(CONF_PRODUCTION_SENSOR, default=""): str,
    vol.Optional(CONF_REFRESH_INTERVAL, default=10): vol.All(int, vol.Range(min=5, max=60)),
})

# ---------------------------------------------------------------------------
# Konfiguracja początkowa (dodanie integracji)
# ---------------------------------------------------------------------------
class Tuya3PhaseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Sprawdź, czy urządzenie już nie jest skonfigurowane
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Licznik 3-fazowy",
                data=user_input,
                options={},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=BASE_SCHEMA,
            description_placeholders={
                "production_hint": "ID encji sensora produkcji paneli (np. sensor.solar_total)",
                "refresh_hint": "Interwał w sekundach (5-60). Niższy = więcej danych.",
            }
        )


# ---------------------------------------------------------------------------
# Opcje — możliwość zmiany ustawień po instalacji
# ---------------------------------------------------------------------------
class Tuya3PhaseOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Wczytaj obecne wartości z entry.data (konfiguracja) lub entry.options (opcje)
        current = {
            CONF_IP_ADDRESS: self.config_entry.data.get(CONF_IP_ADDRESS, ""),
            CONF_DEVICE_ID: self.config_entry.data.get(CONF_DEVICE_ID, ""),
            CONF_LOCAL_KEY: self.config_entry.data.get(CONF_LOCAL_KEY, ""),
            CONF_PRODUCTION_SENSOR: self.config_entry.options.get(CONF_PRODUCTION_SENSOR, ""),
            CONF_REFRESH_INTERVAL: self.config_entry.options.get(CONF_REFRESH_INTERVAL, 10),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=BASE_SCHEMA,
            description_placeholders={
                "production_hint": "ID encji sensora produkcji paneli. Zostaw puste aby wyłączyć.",
                "refresh_hint": "Interwał w sekundach (5-60). Niższy = więcej danych.",
            }
        )