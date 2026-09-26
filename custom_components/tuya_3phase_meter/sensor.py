import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Direct strings for max HA compatibility
UNIT_VOLT = "V"
UNIT_AMPERE = "A"
UNIT_HERTZ = "Hz"


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device_identifiers = data["device_identifiers"]
    production_sensor = data.get("production_sensor")

    sensors_config = [
        # Ogólne
        ("Total Energy Forward", "1", UnitOfEnergy.KILO_WATT_HOUR, 100, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
        ("Total Energy Reverse", "23", UnitOfEnergy.KILO_WATT_HOUR, 100, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
        ("Frequency", "32", UNIT_HERTZ, 100, None, SensorStateClass.MEASUREMENT),
        ("Power Factor", "50", None, 100, None, SensorStateClass.MEASUREMENT),

        # Faza L1
        ("Voltage L1", "102", UNIT_VOLT, 10, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
        ("Current L1", "103", UNIT_AMPERE, 1000, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
        ("Power L1", "104", UnitOfPower.WATT, 1, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),

        # Faza L2
        ("Voltage L2", "105", UNIT_VOLT, 10, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
        ("Current L2", "106", UNIT_AMPERE, 1000, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
        ("Power L2", "107", UnitOfPower.WATT, 1, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),

        # Faza L3
        ("Voltage L3", "108", UNIT_VOLT, 10, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
        ("Current L3", "109", UNIT_AMPERE, 1000, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
        ("Power L3", "110", UnitOfPower.WATT, 1, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    ]

    entities = []
    for name, dp, unit, scale, dev_class, state_class in sensors_config:
        entities.append(
            TuyaMeterSensor(
                coordinator,
                name,
                dp,
                unit,
                scale,
                dev_class,
                state_class,
                entry.entry_id,
                device_identifiers,
            )
        )

    # Autokonsumpcja – dodaj tylko jeśli użytkownik podał sensor produkcji
    if production_sensor:
        entities.append(
            TuyaSelfConsumptionSensor(
                coordinator,
                production_sensor,
                entry.entry_id,
                device_identifiers,
            )
        )

    async_add_entities(entities)


class TuyaMeterSensor(SensorEntity):
    def __init__(
        self,
        coordinator,
        name,
        dp,
        unit,
        scale,
        device_class,
        state_class,
        entry_id,
        device_identifiers,
    ):
        self.coordinator = coordinator
        self._dp = dp
        self._scale = scale
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{dp}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {"identifiers": device_identifiers}

    @property
    def native_value(self):
        val = self.coordinator.data.get(self._dp)
        if val is None:
            return None
        return round(val / self._scale, 3)

    @property
    def available(self):
        return self.coordinator.last_update_success


class TuyaSelfConsumptionSensor(SensorEntity):
    """
    Sensor autokonsumpcji:
    Autokonsumpcja = Produkcja z paneli - Energia oddana do sieci

    Działa tylko gdy użytkownik w konfiguracji podał sensor produkcji PV.
    Wymaga, by oba sensory (produkcja i energia oddana) miały wartości
    w kWh i rosły w czasie (state_class: total_increasing).
    """
    def __init__(self, coordinator, production_sensor_entity, entry_id, device_identifiers):
        self.coordinator = coordinator
        self._production_entity = production_sensor_entity
        self._attr_name = "Self Consumption"
        self._attr_unique_id = f"{entry_id}_self_consumption"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_device_info = {"identifiers": device_identifiers}
        self._attr_icon = "mdi:solar-power"

    @property
    def native_value(self):
        # Pobierz energie oddana z naszego licznika (DP 23, skala 100)
        export_raw = self.coordinator.data.get("23")
        if export_raw is None:
            return None
        export_kwh = export_raw / 100.0

        # Pobierz produkcje z paneli z sensora uzytkownika
        prod_state = self.coordinator.hass.states.get(self._production_entity)
        if prod_state is None:
            return None
        try:
            production_kwh = float(prod_state.state)
        except (ValueError, TypeError):
            return None

        # Autokonsumpcja = Produkcja - Eksport (nigdy nie może być ujemna)
        consumption = production_kwh - export_kwh
        if consumption < 0:
            consumption = 0.0

        return round(consumption, 3)

    @property
    def available(self):
        prod_state = self.coordinator.hass.states.get(self._production_entity)
        return (
            self.coordinator.last_update_success
            and prod_state is not None
            and prod_state.state not in ("unknown", "unavailable")
        )

    @property
    def extra_state_attributes(self):
        """Dodatkowe atrybuty – pokazuj składniki obliczeń."""
        export_raw = self.coordinator.data.get("23")
        export_kwh = round(export_raw / 100.0, 3) if export_raw is not None else None
        prod_state = self.coordinator.hass.states.get(self._production_entity)
        prod_kwh = None
        if prod_state is not None:
            try:
                prod_kwh = round(float(prod_state.state), 3)
            except (ValueError, TypeError):
                pass

        return {
            "Production (kWh)": prod_kwh,
            "Grid Export (kWh)": export_kwh,
            "Production Sensor": self._production_entity,
        }
