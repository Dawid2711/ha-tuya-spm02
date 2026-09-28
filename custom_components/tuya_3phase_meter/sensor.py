import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfVoltage, UnitOfElectricCurrent, UnitOfFrequency
from homeassistant.helpers.event import async_track_state_change
from .const import DOMAIN, CONF_PRODUCTION_SENSOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors_config = [
        ("Total Energy Forward", "1", UnitOfEnergy.KILO_WATT_HOUR, 100, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
        ("Total Energy Reverse", "23", UnitOfEnergy.KILO_WATT_HOUR, 100, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
        ("Frequency", "32", UnitOfFrequency.HERTZ, 100, None, SensorStateClass.MEASUREMENT),
        ("Power Factor", "50", None, 100, None, SensorStateClass.MEASUREMENT),
        ("Voltage L1", "102", "V", 10, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
        ("Current L1", "103", "A", 1000, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
        ("Power L1", "104", UnitOfPower.KILO_WATT, 1000, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
        ("Voltage L2", "105", "V", 10, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
        ("Current L2", "106", "A", 1000, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
        ("Power L2", "107", UnitOfPower.KILO_WATT, 1000, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
        ("Voltage L3", "108", "V", 10, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
        ("Current L3", "109", "A", 1000, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
        ("Power L3", "110", UnitOfPower.KILO_WATT, 1000, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    ]

    entities = [
        TuyaMeterSensor(coordinator, name, dp, unit, scale, dev_class, state_class, entry.entry_id)
        for name, dp, unit, scale, dev_class, state_class in sensors_config
    ]

    # Dodaj sensor autokonsumpcji, jeśli skonfigurowano sensor produkcji
    prod_sensor_id = entry.options.get(CONF_PRODUCTION_SENSOR) or entry.data.get(CONF_PRODUCTION_SENSOR)
    if prod_sensor_id:
        entities.append(SelfConsumptionSensor(coordinator, prod_sensor_id, entry.entry_id))

    entities.append(LastUpdateSensor(coordinator, entry.entry_id))
    async_add_entities(entities)

class TuyaMeterSensor(SensorEntity):
    def __init__(self, coordinator, name, dp, unit, scale, device_class, state_class, entry_id):
        self.coordinator = coordinator
        self._dp = dp
        self._scale = scale
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{dp}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {"identifiers": {(DOMAIN, entry_id)}}

    @property
    def native_value(self):
        val = self.coordinator.data.get(self._dp)
        return round(val / self._scale, 3) if val is not None else None

class SelfConsumptionSensor(SensorEntity):
    def __init__(self, coordinator, prod_sensor_id, entry_id):
        self.coordinator = coordinator
        self._prod_sensor_id = prod_sensor_id
        self._attr_name = "Autokonsumpcja (Energia)"
        self._attr_unique_id = f"{entry_id}_self_consumption"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_device_info = {"identifiers": {(DOMAIN, entry_id)}}

    @property
    def native_value(self):
        # Pobierz energię oddaną (DP 23) i energię produkcji
        reverse_energy = self.coordinator.data.get("23")
        prod_state = self.hass.states.get(self._prod_sensor_id)

        if reverse_energy is None or prod_state is None or prod_state.state in ["unavailable", "unknown"]:
            return None

        prod_energy = float(prod_state.state)
        # Autokonsumpcja = Produkcja - Energia oddana
        # (Clamping do 0, żeby uniknąć ujemnych wartości)
        return max(0, prod_energy - (reverse_energy / 100))

class LastUpdateSensor(SensorEntity):
    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._attr_name = "Ostatnia aktualizacja"
        self._attr_unique_id = f"{entry_id}_last_update"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_device_info = {"identifiers": {(DOMAIN, entry_id)}}

    @property
    def native_value(self):
        return self.coordinator.last_update_time
