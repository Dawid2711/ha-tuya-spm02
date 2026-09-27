import logging
import tinytuya
import threading
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY
from homeassistant.const import CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    config = entry.data
    coordinator = TuyaMeterCoordinator(hass, config)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Inicjalizacja połączenia
    device = tinytuya.Device(config[CONF_DEVICE_ID], config[CONF_IP_ADDRESS], config[CONF_LOCAL_KEY])
    device.set_version(3.5)
    device.set_socketPersistent(True)
    device.set_socketTimeout(15)

    def data_callback(data):
        if data and 'dps' in data:
            _LOGGER.debug("Otrzymano dane: %s", data['dps'])
            hass.add_job(coordinator.async_set_updated_data, data['dps'])

    device.add_has_returned_data_callback(data_callback)

    # Uruchamiamy słuchanie w wątku
    thread = threading.Thread(target=device.listen, daemon=True)
    thread.start()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

class TuyaMeterCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None # Nie używamy pollingu!
        )
        self.data = {}
