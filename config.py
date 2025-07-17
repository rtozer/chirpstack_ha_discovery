import os

class Config:
    MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
    CHIRPSTACK_UPLINK_TOPIC = os.getenv("CHIRPSTACK_UPLINK_TOPIC", "application/+/device/+/event/up")
    HA_DISCOVERY_PREFIX = os.getenv("HA_DISCOVERY_PREFIX", "homeassistant")
    CHIRPSTACK_DOWNLINK_TOPIC = os.getenv("CHIRPSTACK_DOWNLINK_TOPIC", "application/+/device/+/command/down")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def get_config():
    return Config() 