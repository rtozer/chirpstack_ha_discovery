from homeassistant.components.select import SelectEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    selects = {}

    async def handle_event(event):
        dev_eui = event.get("deviceInfo", {}).get("devEui")
        device_name = event.get("deviceInfo", {}).get("deviceName")
        data = event.get("object", {})
        discovery_info = data.get("discovery", {})
        downlinks = discovery_info.get("commands", [])
        new_entities = []
        for cmd_info in downlinks:
            if cmd_info.get("type") != "select":
                continue
            unique_id = f"{dev_eui}_{cmd_info['field']}"
            if unique_id not in selects:
                select = ChirpstackHASelect(dev_eui, cmd_info, device_name)
                selects[unique_id] = select
                new_entities.append(select)
        if new_entities:
            async_add_entities(new_entities)

    hass.data[DOMAIN]["entity_callbacks"].append(handle_event)
    async_add_entities([])

class ChirpstackHASelect(SelectEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        control_name = cmd_info.get("name", self._field)
        self._attr_name = f"{device_name} {control_name}"
        self._attr_options = cmd_info.get("options", [])
        self._device_name = device_name
        # Set friendly name as 'device_name control_name'
        self._attr_name = f"{device_name} {self._attr_name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, dev_eui)},
            "name": device_name,
            "manufacturer": "ChirpStack",
            "model": "LoRaWAN Device",
        }
        self._attr_current_option = None
        self._pending_option = None
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

    async def async_select_option(self, option):
        if self.hass is not None:
            self._attr_current_option = option
            self.async_write_ha_state()
        else:
            self._pending_option = option
        # TODO: Send downlink via MQTT

    async def async_added_to_hass(self):
        if self._pending_option is not None:
            self._attr_current_option = self._pending_option
            self.async_write_ha_state()
            self._pending_option = None 

    @property
    def options(self):
        return self._attr_options

    @property
    def device_class(self):
        return getattr(self, '_attr_device_class', None)

    @property
    def icon(self):
        return getattr(self, '_attr_icon', None)

    @property
    def entity_category(self):
        return getattr(self, '_attr_entity_category', None) 