import logging
from datetime import timedelta
import tinytuya
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY, CONF_PRODUCTION_SENSOR
from homeassistant.const import CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = TuyaMeterCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    # Get or create device in device registry using first refresh data
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
        manufacturer="Tuya",
        model=coordinator.data.get("19", "SPM02"),  # From DP 19
        name=f"Licznik {entry.data[CONF_IP_ADDRESS]}",
    )
    device_identifiers = device.identifiers

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "device_identifiers": device_identifiers,
        "production_sensor": entry.data.get(CONF_PRODUCTION_SENSOR),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

class TuyaMeterCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=10)
        )
        self.config = config
        self.device = tinytuya.OutletDevice(
            config[CONF_DEVICE_ID], config[CONF_IP_ADDRESS], config[CONF_LOCAL_KEY]
        )
        self.device.set_version(3.5)

    async def _async_update_data(self):
        try:
            data = await self.hass.async_add_executor_job(self.device.status)
            if data is None or 'dps' not in data:
                _LOGGER.error("Błąd komunikacji z licznikiem (brak danych): %s", data)
                raise UpdateFailed("Błąd komunikacji z licznikiem")
            return data['dps']
        except Exception as err:
            _LOGGER.error("Błąd odczytu: %s", err)
            raise UpdateFailed(f"Błąd: {err}")