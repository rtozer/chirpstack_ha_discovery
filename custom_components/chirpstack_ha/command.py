from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.text import TextEntity
import logging

_LOGGER = logging.getLogger(__name__)

class ChirpstackHAButton(ButtonEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        self._attr_name = cmd_info.get("name", self._field)
        self._device_name = device_name
        self._attr_device_info = {
            "identifiers": {(dev_eui,)},
            "name": device_name,
        }

    async def async_press(self):
        _LOGGER.info(f"Button pressed: {self._attr_unique_id}")
        # TODO: Send downlink via MQTT

class ChirpstackHANumber(NumberEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        self._attr_name = cmd_info.get("name", self._field)
        self._attr_min_value = cmd_info.get("min", 0)
        self._attr_max_value = cmd_info.get("max", 255)
        self._attr_step = cmd_info.get("step", 1)
        self._attr_unit_of_measurement = cmd_info.get("unit")
        self._device_name = device_name
        self._attr_device_info = {
            "identifiers": {(dev_eui,)},
            "name": device_name,
        }
        self._value = None

    @property
    def value(self):
        return self._value

    async def async_set_value(self, value):
        _LOGGER.info(f"Number set: {self._attr_unique_id} = {value}")
        self._value = value
        self.async_write_ha_state()
        # TODO: Send downlink via MQTT

class ChirpstackHASelect(SelectEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        self._attr_name = cmd_info.get("name", self._field)
        self._attr_options = cmd_info.get("options", [])
        self._device_name = device_name
        self._attr_device_info = {
            "identifiers": {(dev_eui,)},
            "name": device_name,
        }
        self._attr_current_option = None

    async def async_select_option(self, option):
        _LOGGER.info(f"Select option: {self._attr_unique_id} = {option}")
        self._attr_current_option = option
        self.async_write_ha_state()
        # TODO: Send downlink via MQTT

class ChirpstackHASwitch(SwitchEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        self._attr_name = cmd_info.get("name", self._field)
        self._device_name = device_name
        self._attr_device_info = {
            "identifiers": {(dev_eui,)},
            "name": device_name,
        }
        self._is_on = False

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        _LOGGER.info(f"Switch ON: {self._attr_unique_id}")
        self._is_on = True
        self.async_write_ha_state()
        # TODO: Send downlink via MQTT

    async def async_turn_off(self, **kwargs):
        _LOGGER.info(f"Switch OFF: {self._attr_unique_id}")
        self._is_on = False
        self.async_write_ha_state()
        # TODO: Send downlink via MQTT

class ChirpstackHAText(TextEntity):
    def __init__(self, dev_eui, cmd_info, device_name):
        self._dev_eui = dev_eui
        self._field = cmd_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        self._attr_name = cmd_info.get("name", self._field)
        self._attr_max = cmd_info.get("max", 255)
        self._device_name = device_name
        self._attr_device_info = {
            "identifiers": {(dev_eui,)},
            "name": device_name,
        }
        self._attr_native_value = ""

    async def async_set_value(self, value: str):
        _LOGGER.info(f"Text set: {self._attr_unique_id} = {value}")
        self._attr_native_value = value
        self.async_write_ha_state()
        # TODO: Send downlink via MQTT


def create_command_entity(dev_eui, cmd_info, device_name):
    t = cmd_info["type"]
    if t == "button":
        return ChirpstackHAButton(dev_eui, cmd_info, device_name)
    elif t == "number":
        return ChirpstackHANumber(dev_eui, cmd_info, device_name)
    elif t == "select":
        return ChirpstackHASelect(dev_eui, cmd_info, device_name)
    elif t == "switch":
        return ChirpstackHASwitch(dev_eui, cmd_info, device_name)
    elif t == "text":
        return ChirpstackHAText(dev_eui, cmd_info, device_name)
    else:
        _LOGGER.warning(f"Unknown command type: {t}")
        return None 