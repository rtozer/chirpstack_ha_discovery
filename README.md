# Home Assistant Discovery Service for ChirpStack

![version](https://img.shields.io/badge/version-read-from-VERSION-blue)

This service bridges ChirpStack LoRaWAN uplink events to Home Assistant MQTT discovery and state topics. It enables automatic device and sensor discovery in Home Assistant for LoRaWAN devices, and creates Home Assistant controls for downlink commands described in your ChirpStack codec output.

## Versioning
This project follows [Semantic Versioning](https://semver.org/). The current version is maintained in the `VERSION` file at the root of the repository. **The VERSION file is the single source of truth for the project version.**

## ChirpStack Codec Output Format

The service expects your ChirpStack JavaScript codec to output a JSON object with the following fields **on every uplink message**:

- **data**: (object) Key-value pairs of sensor readings (e.g., temperature, battery, etc.)
- **discovery**: (array) List of sensor metadata objects for Home Assistant discovery. Each object should include:
  - `field`: The key in `data` (e.g., "temperature_celsius")
  - `name`: Friendly name for the sensor
  - `unit`: Unit of measurement (e.g., "°C", "%", "kg")
  - `device_class`: (optional) Home Assistant device class (e.g., "temperature", "battery")
- **device**: (object) Device metadata for Home Assistant device registry. Should include:
  - `identifiers`: Array of unique IDs (e.g., DevEUI)
  - `name`: Device name
  - `manufacturer`, `model`, `sw_version`, `hw_version`: (optional) Device info
- **downlinks**: (array, optional) List of downlink command metadata for Home Assistant controls. Each object should include:
  - `field`: Command name (e.g., "tare", "set_interval")
  - `name`: Friendly name for the control
  - `type`: One of the supported types below
  - Additional fields depending on type (see below)
  - `description`: (optional) Help text

> **Note:** The codec should always include the full `discovery`, `device`, and `downlinks` info in every uplink message. The discovery service will only publish Home Assistant discovery/config topics if the discovery/device/downlinks data changes, so there is no risk of spamming Home Assistant with redundant config messages.

### Supported Downlink Types

| Type    | Use Case Example         | Required Fields                | Optional Fields         |
|---------|-------------------------|-------------------------------|------------------------|
| button  | Tare, Reset             | `field`, `name`, `type`       | `description`          |
| number  | Set interval, threshold | `field`, `name`, `type`, `min`, `max`, `step` | `unit`, `description`  |
| select  | Mode, profile           | `field`, `name`, `type`, `options` | `description`      |
| switch  | Enable/disable, on/off  | `field`, `name`, `type`       | `description`          |
| text    | Set label, send string  | `field`, `name`, `type`       | `max`, `description`   |

#### Example Downlink Entries

```json
"downlinks": [
  {
    "field": "tare",
    "name": "Tare Scale",
    "type": "button",
    "description": "Tare the load cell"
  },
  {
    "field": "set_interval",
    "name": "Set Interval",
    "type": "number",
    "min": 1,
    "max": 255,
    "step": 1,
    "unit": "10s",
    "description": "Set reporting interval (in 10s units)"
  },
  {
    "field": "mode",
    "name": "Operating Mode",
    "type": "select",
    "options": ["auto", "manual", "off"],
    "description": "Select device mode"
  },
  {
    "field": "enabled",
    "name": "Enable Device",
    "type": "switch",
    "description": "Enable or disable the device"
  },
  {
    "field": "label",
    "name": "Set Label",
    "type": "text",
    "max": 32,
    "description": "Set a custom label for the device"
  }
]
```

### Example Codec Output

```json
{
  "data": {
    "temperature_celsius": 23.5,
    "weight_kg": 1.23,
    "battery_percent": 87.2
  },
  "discovery": [
    {
      "field": "temperature_celsius",
      "name": "Temperature",
      "unit": "°C",
      "device_class": "temperature"
    },
    {
      "field": "weight_kg",
      "name": "Weight",
      "unit": "kg"
    },
    {
      "field": "battery_percent",
      "name": "Battery",
      "unit": "%",
      "device_class": "battery"
    }
  ],
  "device": {
    "identifiers": ["abcdef1234567890"],
    "name": "CubeCell LoRa Node",
    "manufacturer": "Heltec",
    "model": "HTCC-AB01",
    "sw_version": "1.0.0"
  },
  "downlinks": [
    {
      "field": "tare",
      "name": "Tare Scale",
      "type": "button",
      "description": "Tare the load cell"
    },
    {
      "field": "set_interval",
      "name": "Set Interval",
      "type": "number",
      "min": 1,
      "max": 255,
      "step": 1,
      "unit": "10s",
      "description": "Set reporting interval (in 10s units)"
    },
    {
      "field": "mode",
      "name": "Operating Mode",
      "type": "select",
      "options": ["auto", "manual", "off"],
      "description": "Select device mode"
    },
    {
      "field": "enabled",
      "name": "Enable Device",
      "type": "switch",
      "description": "Enable or disable the device"
    },
    {
      "field": "label",
      "name": "Set Label",
      "type": "text",
      "max": 32,
      "description": "Set a custom label for the device"
    }
  ]
}
```

- The service uses `discovery` and `device` to generate Home Assistant discovery/config topics for sensors.
- The `downlinks` array is used to create Home Assistant controls (button, number, select, switch, text) for sending downlink commands via MQTT.
- The `data` object is published as the state payload for the device.

## Features
- Listens to ChirpStack MQTT uplink events
- Publishes Home Assistant MQTT discovery/config topics for sensors and downlink controls (button, number, select, switch, text)
- **Does not republish state:** Home Assistant reads state directly from the ChirpStack MQTT event using the configured `state_topic` and `value_template`.
- Infers downlink command topics automatically
- Fully configurable via environment variables
- Runs easily in Docker

## Configuration
All configuration is via environment variables:

| Variable                  | Purpose                                      | Default                      |
|---------------------------|----------------------------------------------|------------------------------|
| MQTT_BROKER_HOST          | MQTT broker hostname/IP                      | localhost                    |
| MQTT_BROKER_PORT          | MQTT broker port                             | 1883                         |
| MQTT_USERNAME             | MQTT username (optional)                     | (empty)                      |
| MQTT_PASSWORD             | MQTT password (optional)                     | (empty)                      |
| CHIRPSTACK_UPLINK_TOPIC   | ChirpStack uplink topic (wildcard allowed)   | application/+/device/+/event/up |
| HA_DISCOVERY_PREFIX       | Home Assistant discovery topic prefix        | homeassistant                |
| CHIRPSTACK_DOWNLINK_TOPIC | ChirpStack downlink topic                    | application/+/device/+/command/down |
| LOG_LEVEL                 | Logging level                                | INFO                         |

## Running with Docker

1. Build the image:
   ```sh
   docker build -t ha-discovery-service .
   ```
2. Run the container:
   ```sh
   docker run --rm \
     -e MQTT_BROKER_HOST=mosquitto \
     -e MQTT_BROKER_PORT=1883 \
     -e MQTT_USERNAME=youruser \
     -e MQTT_PASSWORD=yourpass \
     -e HA_DISCOVERY_PREFIX=homeassistant \
     ha-discovery-service
   ```

## Running with Docker Compose

A working `docker-compose.yml` is included for local development and testing. It starts both a Mosquitto MQTT broker and the Home Assistant Discovery Service.

Example `docker-compose.yml`:

```yaml
version: '3.8'

services:
  mosquitto:
    image: eclipse-mosquitto:2
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - mosquitto_data:/mosquitto/data
      - mosquitto_config:/mosquitto/config

  ha-discovery-service:
    build: .
    depends_on:
      - mosquitto
    environment:
      MQTT_BROKER_HOST: mosquitto
      MQTT_BROKER_PORT: 1883
      MQTT_USERNAME: ""
      MQTT_PASSWORD: ""
      HA_DISCOVERY_PREFIX: homeassistant
      CHIRPSTACK_UPLINK_TOPIC: application/+/device/+/event/up
      CHIRPSTACK_DOWNLINK_TOPIC: application/+/device/+/command/down
      LOG_LEVEL: INFO
    restart: unless-stopped

volumes:
  mosquitto_data:
  mosquitto_config:
```

To start the stack:

```sh
docker-compose up --build
```

This will build the service and start both containers. The service will connect to the Mosquitto broker at `mosquitto:1883`.

You can now point ChirpStack and Home Assistant to the same MQTT broker for integration and testing.

## How it Works
- On first uplink (or if discovery info changes), publishes Home Assistant discovery/config topics for all sensors and downlink controls described in the codec output.
- Infers the correct command_topic for each downlink control based on the device's application ID and DevEUI.
- **Home Assistant reads state directly from the ChirpStack MQTT event** (no state republishing is performed by this service).

## Extending
- Add more entity types or customize discovery payloads as needed in `main.py`.
- All config is via environment variables for easy deployment.

## License
MIT
