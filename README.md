# ChirpStack Home Assistant Integration

**Integration Name:** ChirpStack Home Assistant Integration  
**Version:** 0.1.0  
**Documentation:** https://github.com/rtozer/chirpstack_ha_discovery  
**Codeowners:** @rtozer  

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
