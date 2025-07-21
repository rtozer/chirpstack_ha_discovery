from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    switches = {}

    async def handle_event(event):
        dev_eui = event.get("deviceInfo", {}).get("devEui")
        device_name = event.get("deviceInfo", {}).get("deviceName")
        data = event.get("object", {})
        discovery_info = data.get("discovery", {})
        downlinks = discovery_info.get("commands", [])
        new_entities = []
        for cmd_info in downlinks:
            if cmd_info.get("type") != "switch":
                continue
            unique_id = f"{dev_eui}_{cmd_info['field']}"
            if unique_id not in switches:
                switch = ChirpstackHASwitch(dev_eui, cmd_info, device_name)
                switches[unique_id] = switch
                new_entities.append(switch)
        if new_entities:
            async_add_entities(new_entities)

    hass.data[DOMAIN]["entity_callbacks"].append(handle_event)
    async_add_entities([])

class ChirpstackHASwitch(SwitchEntity):
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
        self._is_on = False
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

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        if self.hass is not None:
            self._is_on = True
            self.async_write_ha_state()
        else:
            self._pending_state = True
        # TODO: Send downlink via MQTT

    async def async_turn_off(self, **kwargs):
        if self.hass is not None:
            self._is_on = False
            self.async_write_ha_state()
        else:
            self._pending_state = False
        # TODO: Send downlink via MQTT

    async def async_added_to_hass(self):
        if self._pending_state is not None:
            self._is_on = self._pending_state
            self.async_write_ha_state()
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