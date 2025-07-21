import logging
import json
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.components import mqtt
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.exceptions import HomeAssistantError

print("LOADING CHIRPSTACK_HA FROM", __file__)

DOMAIN = "chirpstack_ha"
_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button", "number", "select", "switch", "text"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    _LOGGER.debug("ChirpStack HA async_setup called")
    # Only set up config entry platforms
    return True

async def async_setup_entry(hass, entry):
    _LOGGER.debug("ChirpStack HA async_setup_entry called")
    # Set up shared data for callbacks
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("entity_callbacks", [])

    def notify_mqtt_required(_event=None):
        hass.async_create_task(
            hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "ChirpStack HA: MQTT Required",
                    "message": (
                        "The ChirpStack HA integration requires the MQTT integration to be set up and running. "
                        "Please [add and configure MQTT](https://my.home-assistant.io/redirect/config_flow_start/?domain=mqtt) in Home Assistant, then restart Home Assistant, and finally reload ChirpStack HA from the Integrations page."
                    ),
                    "notification_id": "chirpstack_ha_mqtt_required"
                },
                blocking=False
            )
        )

    if "mqtt" not in hass.config.components or "mqtt" not in hass.data:
        _LOGGER.error("MQTT integration is not set up or not configured. ChirpStack HA cannot start.")
        message = (
            "The ChirpStack HA integration requires the MQTT integration to be set up and running. "
            "After installing and configuring MQTT, you must restart Home Assistant, and then reload ChirpStack HA from the Integrations page. "
            "You can [add and configure MQTT here](https://my.home-assistant.io/redirect/config_flow_start/?domain=mqtt)."
        )
        if hasattr(hass, "is_running") and hass.is_running:
            hass.async_create_task(
                hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "ChirpStack HA: MQTT Required",
                        "message": message,
                        "notification_id": "chirpstack_ha_mqtt_required"
                    },
                    blocking=False
                )
            )
        else:
            def notify_mqtt_required(_event=None):
                hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "ChirpStack HA: MQTT Required",
                            "message": message,
                            "notification_id": "chirpstack_ha_mqtt_required"
                        },
                        blocking=False
                    )
                )
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, notify_mqtt_required)
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def message_received(msg):
        _LOGGER.debug("Received MQTT message: %s", msg.payload)
        try:
            event = json.loads(msg.payload)
            _LOGGER.debug("Parsed event: %s", event)
            # Notify all registered entity callbacks
            for cb in hass.data[DOMAIN]["entity_callbacks"]:
                await cb(event)
        except Exception as e:
            _LOGGER.exception("Error processing ChirpStack MQTT message: %s", e)

    async def subscribe_mqtt(_event):
        _LOGGER.debug("Home Assistant started, subscribing to MQTT topic")
        try:
            await mqtt.async_subscribe(hass, "application/+/device/+/event/up", message_received)
            _LOGGER.info("ChirpStack HA integration initialized and subscribed to MQTT.")
        except Exception as e:
            _LOGGER.error("Failed to subscribe to MQTT topic: %s", e)
            hass.async_create_task(
                hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "ChirpStack HA Integration Error",
                        "message": f"Failed to subscribe to MQTT topic: {e}",
                        "notification_id": "chirpstack_ha_mqtt_subscribe_error"
                    },
                    blocking=False
                )
            )

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, subscribe_mqtt)
    _LOGGER.debug("ChirpStack HA async_setup_entry exiting (waiting for Home Assistant start)")
    return True

async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Optionally clean up hass.data[DOMAIN] if needed
        pass
    return unload_ok

async def async_reload_entry(hass, entry):
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry) 