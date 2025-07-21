# ChirpStack Home Assistant Integration

**Integration Name:** ChirpStack Home Assistant Integration  
**Version:** 0.1.0  
**Documentation:** https://github.com/rtozer/chirpstack_ha_discovery  
**Codeowners:** @yourusername  

This custom integration connects ChirpStack LoRaWAN uplink events to Home Assistant, dynamically creating sensors and controls for your devices. It uses the Home Assistant-configured MQTT broker and does not require a separate Docker service.

## Features
- Listens to ChirpStack MQTT uplink events
- Dynamically creates Home Assistant entities (sensors, buttons, numbers, selects, etc.)
- Uses the Home Assistant MQTT integration (no separate MQTT config needed)
- HACS compatible

## Installation

### HACS (Recommended)
1. Add this repository as a custom repository in HACS (type: Integration).
2. Install "ChirpStack Home Assistant Integration" from HACS.
3. Restart Home Assistant.

### Manual
1. Copy the `chirpstack_ha` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration
No configuration is needed. The integration uses the MQTT broker configured in Home Assistant.

## Usage
- Entities will be created automatically based on ChirpStack uplink events and your codec output.
- See the main project documentation for codec output format and entity support.

## License
MIT 

## ChirpStack Codec Discovery Schema

Your ChirpStack codec must output a JSON object with a `discovery` key describing the sensors and commands for the device. Example schema:

```json
{
  "battery_percent": 70.2,
  "weight_kg": -0.77,
  "temperature_celsius": 29.0,
  "discovery": {
    "sensors": [
      {
        "field": "temperature_celsius",
        "name": "Temperature",
        "unit": "°C",
        "precision": 2,
        "device_class": "temperature"
      },
      {
        "field": "weight_kg",
        "name": "Weight",
        "unit": "kg",
        "precision": 3
      },
      {
        "field": "battery_percent",
        "name": "Battery",
        "unit": "%",
        "precision": 1,
        "device_class": "battery"
      }
    ],
    "commands": [
      {
        "field": "tare",
        "name": "Tare Scale",
        "type": "button",
        "description": "Tare the load cell",
        "enabled_by_default": false
      },
      {
        "field": "set_interval",
        "name": "Set Interval",
        "type": "number",
        "min": 1,
        "max": 255,
        "step": 1,
        "unit": "10s",
        "description": "Set reporting interval (in 10s units)",
        "enabled_by_default": false
      },
      {
        "field": "calibrate",
        "name": "Calibrate",
        "type": "number",
        "min": 1,
        "max": 200,
        "step": 1,
        "unit": "kg",
        "description": "Calibrate the load cell with a reference weight (kg)",
        "enabled_by_default": false
      },
      {
        "field": "undo",
        "name": "Undo",
        "type": "select",
        "options": ["Undo Tare", "Undo Tare & Calibrate"],
        "description": "Restore previous tare or tare and calibration",
        "enabled_by_default": false
      }
    ]
  }
}
```

## Example JS Function for Discovery

To make your codec output the correct discovery format, use a helper function like this in your ChirpStack codec:

```js
function getDiscovery() {
  return {
    sensors: [
      { field: "temperature_celsius", name: "Temperature", unit: "°C", precision: 2, device_class: "temperature" },
      { field: "weight_kg", name: "Weight", unit: "kg", precision: 3 },
      { field: "battery_percent", name: "Battery", unit: "%", precision: 1, device_class: "battery" }
    ],
    commands: [
      { field: "tare", name: "Tare Scale", type: "button", description: "Tare the load cell", enabled_by_default: false },
      { field: "set_interval", name: "Set Interval", type: "number", min: 1, max: 255, step: 1, unit: "10s", description: "Set reporting interval (in 10s units)", enabled_by_default: false },
      { field: "calibrate", name: "Calibrate", type: "number", min: 1, max: 200, step: 1, unit: "kg", description: "Calibrate the load cell with a reference weight (kg)", enabled_by_default: false },
      { field: "undo", name: "Undo", type: "select", options: ["Undo Tare", "Undo Tare & Calibrate"], description: "Restore previous tare or tare and calibration", enabled_by_default: false }
    ]
  };
}

// In your decodeUplink function:
function decodeUplink(input) {
  // ... decode your payload ...
  var data = {
    battery_percent: 70.2,
    weight_kg: -0.77,
    temperature_celsius: 29.0,
    discovery: getDiscovery()
  };
  return { data: data };
}
``` 