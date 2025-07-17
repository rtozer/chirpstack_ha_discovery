import os
import json
import logging
import paho.mqtt.client as mqtt
from config import get_config

cfg = get_config()
logging.basicConfig(level=cfg.LOG_LEVEL)

# Cache to avoid re-sending discovery/config unless changed
published_discovery = {}

def on_connect(client, userdata, flags, rc):
    logging.info("Connected to MQTT broker")
    client.subscribe(cfg.CHIRPSTACK_UPLINK_TOPIC)


def on_message(client, userdata, msg):
    try:
        event = json.loads(msg.payload)
        # Extract dev_eui, device_name, application_name from deviceInfo
        dev_eui = event.get("deviceInfo", {}).get("devEui")
        device_name = event.get("deviceInfo", {}).get("deviceName")
        application_id = event.get("deviceInfo", {}).get("applicationId", "1")
        application_name = event.get("deviceInfo", {}).get("applicationName")
        # Compose <application name>-<device name> if both are available
        if application_name and device_name:
            ha_device_name = f"{application_name}-{device_name}"
        else:
            ha_device_name = device_name or dev_eui
        if not dev_eui:
            logging.warning("No devEui found in event: %r", event)
            return

        # Extract decoded payload from 'object'
        data = event.get("object", {})
        if isinstance(data, dict):
            discovery_info = data.get("discovery", {})
            discovery = discovery_info.get("sensors", [])
            downlinks = discovery_info.get("commands", [])
        else:
            logging.warning("Event object is not a dict (may be base64 string or codec failed), skipping message. object=%r event=%r", data, event)
            return

        # Compose a hashable key for discovery cache (no device section)
        disc_key = (dev_eui, json.dumps(discovery), json.dumps(downlinks))
        # Only publish discovery/config if the info has changed for this device
        if published_discovery.get(dev_eui) != disc_key and discovery:
            publish_ha_discovery(dev_eui, ha_device_name, application_id, discovery, downlinks, msg.topic)
            published_discovery[dev_eui] = disc_key
        # No state republish needed; Home Assistant will use ChirpStack event directly
    except Exception as e:
        logging.exception("Error processing message")


def publish_ha_discovery(dev_eui, ha_device_name, application_id, discovery, downlinks, chirpstack_topic):
    # Sensors
    for sensor in discovery:
        unique_id = f"{dev_eui}_{sensor['field']}"
        topic = f"{cfg.HA_DISCOVERY_PREFIX}/sensor/{unique_id}/config"
        payload = {
            "name": sensor.get("name", sensor["field"]),
            # Use ChirpStack uplink event topic as state_topic
            "state_topic": chirpstack_topic,
            # Value template extracts from value_json.object.<field>
            "value_template": f"{{{{ value_json.object.{sensor['field']} }}}}",
            "unit_of_measurement": sensor.get("unit"),
            "unique_id": unique_id,
            "device_class": sensor.get("device_class"),
            # Use <application name>-<device name> for grouping in HA
            "device": {
                "identifiers": [dev_eui],
                "name": ha_device_name
            }
        }
        # If the sensor specifies a display precision, include it
        if "precision" in sensor:
            payload["suggested_display_precision"] = sensor["precision"]
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        mqtt_client.publish(topic, json.dumps(payload), retain=True)
        logging.info(f"Published HA sensor discovery: {topic}")
    # Downlink controls
    for dl in downlinks:
        unique_id = f"{dev_eui}_{dl['field']}"
        command_topic = f"application/{application_id}/device/{dev_eui}/command/down"
        base_payload = {
            "name": dl.get("name", dl["field"]),
            "command_topic": command_topic,
            "unique_id": unique_id,
            "device": {
                "identifiers": [dev_eui],
                "name": ha_device_name
            }
        }
        entity_type = dl["type"]
        if entity_type == "button":
            payload = base_payload.copy()
            payload["payload_press"] = json.dumps({dl["field"]: True})
            topic = f"{cfg.HA_DISCOVERY_PREFIX}/button/{unique_id}/config"
            logging.info(f"Published HA button discovery: {topic}")
        elif entity_type == "number":
            payload = base_payload.copy()
            payload["min"] = dl.get("min", 0)
            payload["max"] = dl.get("max", 255)
            payload["step"] = dl.get("step", 1)
            payload["unit_of_measurement"] = dl.get("unit")
            payload["mode"] = "box"
            payload["command_template"] = json.dumps({dl["field"]: "{{ value }}"})
            topic = f"{cfg.HA_DISCOVERY_PREFIX}/number/{unique_id}/config"
            logging.info(f"Published HA number discovery: {topic}")
        elif entity_type == "select":
            payload = base_payload.copy()
            payload["options"] = dl.get("options", [])
            payload["command_template"] = json.dumps({dl["field"]: "{{ value }}"})
            topic = f"{cfg.HA_DISCOVERY_PREFIX}/select/{unique_id}/config"
            logging.info(f"Published HA select discovery: {topic}")
        elif entity_type == "switch":
            payload = base_payload.copy()
            payload["payload_on"] = json.dumps({dl["field"]: True})
            payload["payload_off"] = json.dumps({dl["field"]: False})
            topic = f"{cfg.HA_DISCOVERY_PREFIX}/switch/{unique_id}/config"
            logging.info(f"Published HA switch discovery: {topic}")
        elif entity_type == "text":
            payload = base_payload.copy()
            payload["command_template"] = json.dumps({dl["field"]: "{{ value }}"})
            payload["max"] = dl.get("max", 255)
            topic = f"{cfg.HA_DISCOVERY_PREFIX}/text/{unique_id}/config"
            logging.info(f"Published HA text discovery: {topic}")
        else:
            logging.warning(f"Unknown downlink type: {entity_type}")
            continue
        payload = {k: v for k, v in payload.items() if v is not None}
        mqtt_client.publish(topic, json.dumps(payload), retain=True)

# MQTT setup
mqtt_client = mqtt.Client()
if cfg.MQTT_USERNAME:
    mqtt_client.username_pw_set(cfg.MQTT_USERNAME, cfg.MQTT_PASSWORD)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(cfg.MQTT_BROKER_HOST, cfg.MQTT_BROKER_PORT)
mqtt_client.loop_forever() 