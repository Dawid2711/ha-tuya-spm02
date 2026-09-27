import logging
import threading
import tinytuya
from datetime import datetime, timezone
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY
from homeassistant.const import CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = TuyaMeterCoordinator(hass, entry.data)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator}

    # Uruchamiamy coordinatora
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator.stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

class TuyaMeterCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.config = config
        self.hass = hass
        self.last_update_time = None
        self.running = True

        self.device = tinytuya.Device(config[CONF_DEVICE_ID], config[CONF_IP_ADDRESS], config[CONF_LOCAL_KEY])
        self.device.set_version(3.5)
        self.device.set_socketPersistent(True)

        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def _listen_loop(self):
        while self.running:
            try:
                # 1. Nasłuchiwanie na dane
                data = self.device.receive()
                if data and 'dps' in data:
                    self.last_update_time = datetime.now(timezone.utc)
                    self.hass.add_job(self.async_set_updated_data, data['dps'])

                # 2. Jeśli brak danych, "puknij" do licznika
                self.device.heartbeat(nowait=True)

            except Exception as err:
                _LOGGER.debug("Socket listener error: %s", err)
                try: self.device.socket.close()
                except: pass

    def stop(self):
        self.running = False
        try: self.device.socket.close()
        except: pass
