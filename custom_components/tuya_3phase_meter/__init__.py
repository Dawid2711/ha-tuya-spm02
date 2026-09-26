import asyncio
from datetime import timedelta
import tinytuya
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY
from homeassistant.const import CONF_IP_ADDRESS

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = TuyaMeterCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    for platform in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, platform))
    return True

class TuyaMeterCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(hass, None, name=DOMAIN, update_interval=timedelta(seconds=10))
        self.config = config
        self.device = tinytuya.OutletDevice(
            config[CONF_DEVICE_ID], config[CONF_IP_ADDRESS], config[CONF_LOCAL_KEY]
        )
        self.device.set_version(3.5)

    async def _async_update_data(self):
        try:
            data = await self.hass.async_add_executor_job(self.device.status)
            if 'dps' not in data:
                raise UpdateFailed("Błąd komunikacji z licznikiem")
            return data['dps']
        except Exception as err:
            raise UpdateFailed(f"Błąd: {err}")
