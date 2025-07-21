from homeassistant.components.button import ButtonEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    buttons = {}

    async def handle_event(event):
        dev_eui = event.get("deviceInfo", {}).get("devEui")
        device_name = event.get("deviceInfo", {}).get("deviceName")
        data = event.get("object", {})
        discovery_info = data.get("discovery", {})
        downlinks = discovery_info.get("commands", [])
        new_entities = []
        for cmd_info in downlinks:
            if cmd_info.get("type") != "button":
                continue
            unique_id = f"{dev_eui}_{cmd_info['field']}"
            if unique_id not in buttons:
                button = ChirpstackHAButton(dev_eui, cmd_info, device_name)
                buttons[unique_id] = button
                new_entities.append(button)
        if new_entities:
            async_add_entities(new_entities)

    hass.data[DOMAIN]["entity_callbacks"].append(handle_event)
    async_add_entities([])

class ChirpstackHAButton(ButtonEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        control_name = cmd_info.get("name", self._field)
        self._attr_name = f"{device_name} {control_name}"
        self._device_name = device_name
        # Set friendly name as 'device_name control_name'
        self._attr_name = f"{device_name} {self._attr_name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, dev_eui)},
            "name": device_name,
            "manufacturer": "ChirpStack",
            "model": "LoRaWAN Device",
        }
        self._pending_state = None
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

    async def async_press(self):
        # TODO: Send downlink via MQTT
        pass

    async def async_added_to_hass(self):
        self._pending_state = None 

    @property
    def device_class(self):
        return getattr(self, '_attr_device_class', None)

    @property
    def icon(self):
        return getattr(self, '_attr_icon', None)

    @property
    def entity_category(self):
        return getattr(self, '_attr_entity_category', None) 