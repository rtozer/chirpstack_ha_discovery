from homeassistant.components.number import NumberEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    numbers = {}

    async def handle_event(event):
        dev_eui = event.get("deviceInfo", {}).get("devEui")
        device_name = event.get("deviceInfo", {}).get("deviceName")
        data = event.get("object", {})
        discovery_info = data.get("discovery", {})
        downlinks = discovery_info.get("commands", [])
        new_entities = []
        for cmd_info in downlinks:
            if cmd_info.get("type") != "number":
                continue
            unique_id = f"{dev_eui}_{cmd_info['field']}"
            if unique_id not in numbers:
                number = ChirpstackHANumber(dev_eui, cmd_info, device_name)
                numbers[unique_id] = number
                new_entities.append(number)
        if new_entities:
            async_add_entities(new_entities)

    hass.data[DOMAIN]["entity_callbacks"].append(handle_event)
    async_add_entities([])

class ChirpstackHANumber(NumberEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        control_name = cmd_info.get("name", self._field)
        self._attr_name = f"{device_name} {control_name}"
        self._attr_min_value = cmd_info.get("min", 0)
        self._attr_max_value = cmd_info.get("max", 255)
        self._attr_step = cmd_info.get("step", 1)
        self._attr_unit_of_measurement = cmd_info.get("unit")
        self._attr_mode = "box"
        precision = cmd_info.get("precision")
        if precision is not None:
            self._attr_suggested_display_precision = int(precision)
        self._device_name = device_name
        # Set friendly name as 'device_name control_name'
        self._attr_name = f"{device_name} {self._attr_name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, dev_eui)},
            "name": device_name,
            "manufacturer": "ChirpStack",
            "model": "LoRaWAN Device",
        }
        self._value = None
        self._pending_value = None
        self._attr_entity_registry_enabled_default = cmd_info.get("enabled_by_default", True)

        icon = cmd_info.get("icon")
        if icon:
            self._attr_icon = icon
        else:
            self._attr_icon = None
        entity_category = cmd_info.get("entity_category")
        if entity_category:
            self._attr_entity_category = entity_category
        else:
            self._attr_entity_category = None

    @property
    def value(self):
        return self._value

    async def async_set_value(self, value):
        if self.hass is not None:
            self._value = value
            self.async_write_ha_state()
        else:
            self._pending_value = value
        # TODO: Send downlink via MQTT

    async def async_added_to_hass(self):
        if self._pending_value is not None:
            self._value = self._pending_value
            self.async_write_ha_state()
            self._pending_value = None 

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def device_class(self):
        return getattr(self, '_attr_device_class', None)

    @property
    def state_class(self):
        return getattr(self, '_attr_state_class', None)

    @property
    def icon(self):
        return getattr(self, '_attr_icon', None)

    @property
    def entity_category(self):
        return getattr(self, '_attr_entity_category', None)

    @property
    def suggested_display_precision(self):
        return getattr(self, '_attr_suggested_display_precision', None)

    @property
    def mode(self):
        return self._attr_mode 