import logging
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    sensors = {}

    async def handle_event(event):
        dev_eui = event.get("deviceInfo", {}).get("devEui")
        device_name = event.get("deviceInfo", {}).get("deviceName")
        data = event.get("object", {})
        discovery_info = data.get("discovery", {})
        discovery = discovery_info.get("sensors", [])
        new_entities = []
        for sensor_info in discovery:
            unique_id = f"{dev_eui}_{sensor_info['field']}"
            if unique_id not in sensors:
                sensor = ChirpstackHASensor(dev_eui, sensor_info, device_name)
                sensors[unique_id] = sensor
                new_entities.append(sensor)
            # Update state
            value = data.get(sensor_info["field"])
            if value is not None:
                await sensors[unique_id].async_update_state(value)
        if new_entities:
            async_add_entities(new_entities)

    # Register callback
    hass.data[DOMAIN]["entity_callbacks"].append(handle_event)
    async_add_entities([])  # No entities at startup

class ChirpstackHASensor(SensorEntity):
    def __init__(self, dev_eui, sensor_info, device_name):
        self._dev_eui = dev_eui
        self._field = sensor_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        sensor_name = sensor_info.get("name", self._field)
        self._attr_name = f"{device_name} {sensor_name}"
        unit = sensor_info.get("unit")
        if not unit:
            _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field})")
        self._attr_unit_of_measurement = unit
        # Device class
        device_class = sensor_info.get("device_class")
        if device_class:
            self._attr_device_class = device_class
        elif "weight" in self._field:
            self._attr_device_class = "weight"
        elif "temperature" in self._field:
            self._attr_device_class = "temperature"
        elif "humidity" in self._field:
            self._attr_device_class = "humidity"
        elif "pressure" in self._field:
            self._attr_device_class = "pressure"
        elif "voltage" in self._field:
            self._attr_device_class = "voltage"
        elif "current" in self._field:
            self._attr_device_class = "current"
        elif "power" in self._field:
            self._attr_device_class = "power"
        elif "energy" in self._field:
            self._attr_device_class = "energy"
        elif "distance" in self._field:
            self._attr_device_class = "distance"
        elif "speed" in self._field:
            self._attr_device_class = "speed"
        elif "direction" in self._field:
            self._attr_device_class = "direction"
        elif "altitude" in self._field:
            self._attr_device_class = "altitude"
        elif "latitude" in self._field:
            self._attr_device_class = "latitude"
        elif "longitude" in self._field:
            self._attr_device_class = "longitude"
        elif "battery" in self._field:
            self._attr_device_class = "battery"
        elif "signal" in self._field:
            self._attr_device_class = "signal"
        elif "rssi" in self._field:
            self._attr_device_class = "rssi"
        elif "snr" in self._field:
            self._attr_device_class = "snr"
        elif "co2" in self._field:
            self._attr_device_class = "co2"
        elif "co" in self._field:
            self._attr_device_class = "co"
        elif "no2" in self._field:
            self._attr_device_class = "no2"
        else:
            self._attr_device_class = None
        # State class
        self._attr_state_class = sensor_info.get("state_class", "measurement")
        # Suggested display precision
        precision = sensor_info.get("precision")
        if precision is not None:
            self._attr_suggested_display_precision = int(precision)
        # Icon
        icon = sensor_info.get("icon")
        if icon:
            self._attr_icon = icon
        else:
            self._attr_icon = None
        # Entity category
        entity_category = sensor_info.get("entity_category")
        if entity_category:
            self._attr_entity_category = entity_category
        else:
            self._attr_entity_category = None
        self._device_name = device_name
        # Set friendly name as 'device_name sensor_name'
        self._state = None
        self._pending_state = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, dev_eui)},
            "name": device_name,
            "manufacturer": "ChirpStack",
            "model": "LoRaWAN Device",
        }
        _LOGGER.debug(f"Creating sensor {self._attr_name}: field={self._field}, device_class={self._attr_device_class}, state_class={self._attr_state_class}, precision={getattr(self, '_attr_suggested_display_precision', None)}, unit={self._attr_unit_of_measurement}, icon={getattr(self, '_attr_icon', None)}, entity_category={getattr(self, '_attr_entity_category', None)}")

    @property
    def state(self):
        return self._state

    async def async_update_state(self, value):
        if self.hass is not None:
            self._state = value
            self.async_write_ha_state()
        else:
            self._pending_state = value

    async def async_added_to_hass(self):
        if self._pending_state is not None:
            self._state = self._pending_state
            self.async_write_ha_state()
            self._pending_state = None

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def device_class(self):
        return self._attr_device_class

    @property
    def state_class(self):
        return self._attr_state_class

    @property
    def icon(self):
        return self._attr_icon

    @property
    def entity_category(self):
        return self._attr_entity_category

    @property
    def suggested_display_precision(self):
        return self._attr_suggested_display_precision


def create_sensor(dev_eui, sensor_info, device_name):
    return ChirpstackHASensor(dev_eui, sensor_info, device_name) 