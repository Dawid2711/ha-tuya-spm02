import logging
import asyncio
import tinytuya
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY
from homeassistant.const import CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    config = entry.data
    # Inicjalizacja urządzenia
    device = tinytuya.Device(config[CONF_DEVICE_ID], config[CONF_IP_ADDRESS], config[CONF_LOCAL_KEY])
    device.set_version(3.5)
    device.set_socketPersistent(True)
    device.set_socketTimeout(15)

    coordinator = TuyaMeterCoordinator(hass, device)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Uruchamiamy słuchacza w tle
    hass.loop.create_task(coordinator.listen_task())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

class TuyaMeterCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, device):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.device = device
        self.data = {}
        self.running = True

    async def listen_task(self):
        _LOGGER.info("Uruchomiono Asynchroniczny Słuchacz TCP")
        while self.running:
            try:
                # Wykonujemy blokujący odczyt w osobnym wątku, aby nie blokować HA
                data = await self.hass.async_add_executor_job(self.device.receive)
                if data and 'dps' in data:
                    _LOGGER.debug("Otrzymano dane: %s", data['dps'])
                    self.data.update(data['dps'])
                    self.async_set_updated_data(self.data)

                # Heartbeat dla podtrzymania połączenia
                await self.hass.async_add_executor_job(self.device.heartbeat, True)
                await asyncio.sleep(1)
            except Exception as e:
                _LOGGER.debug("Błąd słuchacza: %s", e)
                await asyncio.sleep(5)

    def stop(self):
        self.running = False
        try: self.device.socket.close()
        except: pass
