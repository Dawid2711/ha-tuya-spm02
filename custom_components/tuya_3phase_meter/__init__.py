import logging
from datetime import datetime, timedelta, timezone
import tinytuya
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY
from homeassistant.const import CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = TuyaMeterCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"coordinator": coordinator}

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
            update_interval=timedelta(seconds=3)
        )
        self.config = config
        self.last_update_time = None
        self.device = tinytuya.OutletDevice(
            config[CONF_DEVICE_ID], config[CONF_IP_ADDRESS], config[CONF_LOCAL_KEY]
        )
        self.device.set_version(3.5)
        self.device.set_socketTimeout(10)
        self._refresh_dps = [1, 23, 32, 50, 102, 103, 104, 105, 106, 107, 108, 109, 110]

    def _read_meter(self):
        """Wymuś świeży pomiar, potem odczytaj status."""
        try:
            self.device.heartbeat(nowait=True)
            self.device.updatedps(self._refresh_dps, nowait=False)
            data = self.device.status()
            _LOGGER.debug("Surowe dane z licznika: %s", data)
            return data
        except Exception as err:
            _LOGGER.debug("Błąd w _read_meter: %s", err)
            return {}

    async def _async_update_data(self):
        try:
            data = await self.hass.async_add_executor_job(self._read_meter)
            if data is None or "dps" not in data:
                # Nie rzucamy wyjątku, żeby nie przerywać pracy, jeśli chwilowy brak danych
                _LOGGER.warning("Licznik nie zwrócił danych DPS: %s", data)
                return {}

            self.last_update_time = datetime.now(timezone.utc)
            return data["dps"]
        except Exception as err:
            _LOGGER.error("Błąd odczytu: %s", err)
            raise UpdateFailed(f"Błąd: {err}")
