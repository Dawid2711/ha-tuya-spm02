import logging
from datetime import datetime, timedelta
import tinytuya
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_DEVICE_ID, CONF_LOCAL_KEY, CONF_PRODUCTION_SENSOR, CONF_REFRESH_INTERVAL
from homeassistant.const import CONF_IP_ADDRESS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    interval = int(entry.options.get(CONF_REFRESH_INTERVAL, 10))
    coordinator = TuyaMeterCoordinator(hass, entry.data, timedelta(seconds=interval))

    # Pierwsze odświeżenie — jeśli się nie uda, integracja się nie załaduje
    await coordinator.async_config_entry_first_refresh()

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
        manufacturer="Tuya",
        model=coordinator.data.get("19", "SPM02") or "SPM02",
        name="Licznik 3-fazowy",
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "device_identifiers": device.identifiers,
        "production_sensor": entry.data.get(CONF_PRODUCTION_SENSOR),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Nasłuchuj zmian opcji (np. zmiana interwału)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    return True


async def _async_update_options(hass, entry):
    """Gdy użytkownik zmieni opcje integracji — zaktualizuj interwał."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id, {}).get("coordinator")
    if coordinator:
        new_interval = int(entry.options.get(CONF_REFRESH_INTERVAL, 10))
        coordinator.update_interval = timedelta(seconds=new_interval)
        _LOGGER.info("Zaktualizowano interwał na %ds", new_interval)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class TuyaMeterCoordinator(DataUpdateCoordinator):
    """
    Koordynator odczytu licznika Tuya.
    Przy każdym odczycie tworzy ŚWIEŻE połączenie TCP,
    dzięki czemu nie ma problemu z "wiszącymi" socketami.
    """
    def __init__(self, hass, config, interval):
        self._hass = hass
        self._ip = config[CONF_IP_ADDRESS]
        self._device_id = config[CONF_DEVICE_ID]
        self._local_key = config[CONF_LOCAL_KEY]
        self._last_success = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=interval,
        )

    async def _async_update_data(self):
        try:
            data = await self._hass.async_add_executor_job(self._poll_meter)
            if data is None or 'dps' not in data:
                _LOGGER.error("Błąd: licznik nie zwrócił poprawnych danych.")
                raise UpdateFailed("Brak danych od licznika")
            self._last_success = datetime.now()
            return data['dps']
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Błąd komunikacji z licznikiem: %s", err)
            raise UpdateFailed(f"Błąd: {err}")

    def _poll_meter(self):
        """
        Odczytaj status licznika. Przy każdym wywołaniu tworzymy
        ŚWIEŻE połączenie TCP — to kluczowa różnica, która zapobiega
        "wiszącym" socketom i braku aktualizacji przez wiele godzin.
        """
        dev = tinytuya.Device(self._device_id, self._ip, self._local_key)
        dev.set_version(3.5)
        dev.set_socketTimeout(15)
        dev.set_socketRetryLimit(2)

        # Metoda 1: standardowy status()
        try:
            return dev.status()
        except Exception:
            pass

        # Metoda 2: dps() z wymuszeniem nowego połączenia
        try:
            return dev.dps()
        except Exception:
            pass

        # Metoda 3: heartbeat — ostatnia deska ratunku
        try:
            dev.set_socketPersistent(False)
            return dev.status()
        except Exception as err:
            _LOGGER.debug("Wszystkie metody odczytu zawiodły: %s", err)
            return None
