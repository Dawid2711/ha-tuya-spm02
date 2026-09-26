import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Używamy bezpośrednich ciągów znaków dla maksymalnej kompatybilności
UNIT_VOLT = "V"
UNIT_AMPERE = "A"
UNIT_HERTZ = "Hz"

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # name, dp, unit, scale, device_class, state_class
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
        entities.append(TuyaMeterSensor(coordinator, name, dp, unit, scale, dev_class, state_class, entry.entry_id))

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

    @property
    def native_value(self):
        val = self.coordinator.data.get(self._dp)
        if val is None:
            return None
        return round(val / self._scale, 3)

    @property
    def available(self):
        return self.coordinator.last_update_success
