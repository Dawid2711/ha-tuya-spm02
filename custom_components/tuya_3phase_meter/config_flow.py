import voluptuous as vol
import tinytuya
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY, CONF_PRODUCTION_SENSOR, CONF_REFRESH_INTERVAL
from homeassistant.const import CONF_IP_ADDRESS

# Klucze chmury Tuya
CONF_API_REGION = "api_region"
CONF_API_ID = "api_id"
CONF_API_SECRET = "api_secret"
CONF_API_UID = "api_uid"

BASE_MANUAL_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): str,
    vol.Required(CONF_DEVICE_ID): str,
    vol.Required(CONF_LOCAL_KEY): str,
    vol.Optional(CONF_PRODUCTION_SENSOR, default=""): str,
    vol.Optional(CONF_REFRESH_INTERVAL, default=10): vol.All(int, vol.Range(min=5, max=60)),
})

class Tuya3PhaseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.cloud_devices = []
        self.production_sensor = ""

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Krok 1: Menu wyboru metody konfiguracji."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["manual", "cloud"]
        )

    async def async_step_manual(self, user_input=None) -> FlowResult:
        """Konfiguracja ręczna."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Licznik 3-fazowy ({user_input[CONF_IP_ADDRESS]})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=BASE_MANUAL_SCHEMA,
            errors=errors,
        )

    async def async_step_cloud(self, user_input=None) -> FlowResult:
        """Krok chmury: pobieranie poświadczeń Tuya IoT."""
        errors = {}
        if user_input is not None:
            self.production_sensor = user_input.get(CONF_PRODUCTION_SENSOR, "")
            try:
                devices = await self.hass.async_add_executor_job(
                    self._fetch_tuya_cloud_devices,
                    user_input[CONF_API_REGION],
                    user_input[CONF_API_ID],
                    user_input[CONF_API_SECRET],
                    user_input[CONF_API_UID]
                )
                if not devices:
                    errors["base"] = "no_devices_found"
                else:
                    self.cloud_devices = devices
                    return await self.async_step_select_device()
            except Exception as e:
                errors["base"] = "cannot_connect_cloud"

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema({
                vol.Required(CONF_API_REGION, default="eu"): vol.In({"cn": "China", "us": "America", "eu": "Europe", "in": "India"}),
                vol.Required(CONF_API_ID): str,
                vol.Required(CONF_API_SECRET): str,
                vol.Required(CONF_API_UID): str,
                vol.Optional(CONF_PRODUCTION_SENSOR, default=""): str,
            }),
            errors=errors,
        )

    def _fetch_tuya_cloud_devices(self, region, api_id, api_secret, api_uid):
        cloud = tinytuya.Cloud(apiRegion=region, apiID=api_id, apiSecret=api_secret, apiUID=api_uid)
        result = cloud.getdevices()
        if isinstance(result, list):
            return result
        return []

    async def async_step_select_device(self, user_input=None) -> FlowResult:
        """Wybór konkretnego urządzenia z listy znalezionej w chmurze."""
        errors = {}
        if user_input is not None:
            selected_dev_id = user_input["selected_device"]
            dev_info = next((d for d in self.cloud_devices if d.get("id") == selected_dev_id), None)

            if dev_info:
                await self.async_set_unique_id(dev_info["id"])
                self._abort_if_unique_id_configured()

                data = {
                    CONF_IP_ADDRESS: dev_info.get("ip", ""),
                    CONF_DEVICE_ID: dev_info["id"],
                    CONF_LOCAL_KEY: dev_info["local_key"],
                    CONF_PRODUCTION_SENSOR: self.production_sensor,
                }
                return self.async_create_entry(
                    title=dev_info.get("name", "Licznik SPM02"),
                    data=data,
                )

        device_options = {
            d["id"]: f"{d.get('name', 'Urządzenie')} (IP: {d.get('ip', 'brak')}, ID: {d['id']})"
            for d in self.cloud_devices
        }

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("selected_device"): vol.In(device_options)
            }),
            errors=errors,
        )

class Tuya3PhaseOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_PRODUCTION_SENSOR, default=self.config_entry.options.get(CONF_PRODUCTION_SENSOR, "")): str,
                vol.Optional(CONF_REFRESH_INTERVAL, default=self.config_entry.options.get(CONF_REFRESH_INTERVAL, 10)): vol.All(int, vol.Range(min=5, max=60)),
            })
        )
