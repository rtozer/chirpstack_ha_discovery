import logging
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import Entity
from .const import DOMAIN
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.util import dt as dt_util
import yaml
from influxdb_client import InfluxDBClient, Point, WritePrecision
from homeassistant.helpers import entity_registry as er
from .const import INFLUXDB_CONFIG
import traceback
from homeassistant.core import split_entity_id
import asyncio
from homeassistant.util import slugify

# Helper to check if an entity should be included in InfluxDB

def is_entity_included(entity_id, influxdb_config):
    include = influxdb_config.get("include", {})
    exclude = influxdb_config.get("exclude", {})
    # If include.entities is set, only those entities are included
    if "entities" in include:
        if entity_id not in include["entities"]:
            return False
    # If exclude.entities is set, those entities are excluded
    if "entities" in exclude:
        if entity_id in exclude["entities"]:
            return False
    return True

async def get_last_influxdb_value(hass, influxdb_client, influxdb_config, domain_tag, entity_id_tag, measurement):
    """Query InfluxDB for the last value for a given entity (by domain and entity_id tag) in a background thread."""
    version = influxdb_config.get("version", "2.x")
    bucket = influxdb_config.get("bucket")
    org = influxdb_config.get("org")
    database = influxdb_config.get("database")
    def do_query():
        try:
            if version == "2.x":
                query_api = influxdb_client.query_api()
                flux_query = f'''from(bucket: "{bucket}")\n  |> range(start: -30d)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"{measurement}\" and r[\"domain\"] == \"{domain_tag}\" and r[\"entity_id\"] == \"{entity_id_tag}\")\n  |> filter(fn: (r) => r._field == \"value\" and exists r._value and (r._value >= 0.0 or r._value < 0.0))\n  |> group()\n  |> sort(columns: [\"_time\"], desc: true)\n  |> limit(n:1)'''
                tables = query_api.query(flux_query, org=org)
                for table in tables:
                    for record in table.records:
                        value = record.get_value()
                        return value
            else:  # 1.x
                query = f"SELECT LAST(value) FROM /.*/ WHERE \"domain\"='{domain_tag}' AND \"entity_id\"='{entity_id_tag}'"
                result = influxdb_client.query(query, database=database)
                for _, points in result.items():
                    if points:
                        return points[-1].get("last")
        except Exception as e:
            _LOGGER.warning(f"[InfluxDB] Failed to query last value for {domain_tag}.{entity_id_tag}: {e}")
        return None
    return await hass.async_add_executor_job(do_query)

async def async_setup_entry(hass, entry, async_add_entities):
    sensors = {}
    entity_reg = er.async_get(hass)
    # Repopulate sensors dict and mapping from entity registry
    for entity in entity_reg.entities.values():
        if entity.domain == "sensor" and entity.platform == DOMAIN and entity.config_entry_id == entry.entry_id:
            object_id = entity.entity_id.split(".", 1)[1]  # <dev_eui>_<field>
            dev_eui, _, field = object_id.partition("_")
            device_name = entity.original_name.split(" ")[0] if entity.original_name else dev_eui
            if object_id not in sensors:
                sensor_info = {"field": field}
                sensor = ChirpstackHASensor(dev_eui, sensor_info, device_name)
                sensor.entity_id = entity.entity_id
                sensors[object_id] = sensor
    # Prepare pending history storage
    # hass.data[DOMAIN].setdefault("pending_history", {})
    # Get latest config from hass.data for this entry
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(entry.entry_id, entry.data)
    _LOGGER.debug(f"[InfluxDB] entry_data at setup: {entry_data}")
    influxdb_config = entry_data  # Use the whole config entry data dict
    influxdb_client = None
    influxdb_write_api = None
    version = influxdb_config.get("version", "2.x")
    _LOGGER.debug(f"[InfluxDB] Using version: {version}")
    # Explicitly check required fields for v1 and v2
    if version == "2.x":
        bucket = influxdb_config.get("bucket")
        org = influxdb_config.get("org")
        token = influxdb_config.get("token")
        if not (bucket and org and token):
            _LOGGER.warning(f"[InfluxDB] Missing required v2 fields: bucket={bucket}, org={org}, token={'set' if token else 'not set'}; skipping InfluxDB initialization.")
        else:
            try:
                url = f"http://{influxdb_config.get('host')}:{influxdb_config.get('port', 8086)}"
                _LOGGER.debug(f"[InfluxDB] Attempting to initialize v2 client with url={url}, org={org}, bucket={bucket}, token={'set' if token else 'not set'}")
                influxdb_client = InfluxDBClient(url=url, token=token, org=org, timeout=5_000)
                influxdb_write_api = influxdb_client.write_api()
                _LOGGER.debug(f"[InfluxDB] v2 client initialized successfully.")
            except Exception as e:
                _LOGGER.error(f"[InfluxDB] Failed to initialize InfluxDB v2 client: {e} | config: url={url}, org={org}, bucket={bucket}, token={'set' if token else 'not set'}\n{traceback.format_exc()}")
                influxdb_client = None
                influxdb_write_api = None
    elif version == "1.x":
        database = influxdb_config.get("database")
        if not database:
            _LOGGER.warning(f"[InfluxDB] Missing required v1 field: database={database}; skipping InfluxDB initialization.")
        else:
            try:
                url = f"http://{influxdb_config.get('host')}:{influxdb_config.get('port', 8086)}"
                username = influxdb_config.get("username")
                password = influxdb_config.get("password")
                _LOGGER.debug(f"[InfluxDB] Attempting to initialize v1 client with url={url}, database={database}, username={username}, password={'set' if password else 'not set'}")
                influxdb_client = InfluxDBClient(url=url, token=password, org=username, timeout=5_000)
                influxdb_write_api = influxdb_client.write_api()
                _LOGGER.debug(f"[InfluxDB] v1 client initialized successfully.")
            except Exception as e:
                _LOGGER.error(f"[InfluxDB] Failed to initialize InfluxDB v1 client: {e} | config: url={url}, database={database}, username={username}, password={'set' if password else 'not set'}\n{traceback.format_exc()}")
                influxdb_client = None
                influxdb_write_api = None
    else:
        _LOGGER.warning(f"[InfluxDB] Unknown InfluxDB version: {version}; skipping InfluxDB initialization.")

    async def handle_event(event, entry_id):
        # Always fetch the latest config for this entry
        domain_data = hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(entry_id, {})
        influxdb_config = entry_data  # Use the whole config entry data dict
        dev_eui = event.get("deviceInfo", {}).get("devEui")
        device_name = event.get("deviceInfo", {}).get("deviceName")
        data = event.get("object", {})
        discovery_info = data.get("discovery", {})
        discovery = discovery_info.get("sensors", [])
        history = data.get("history", [])
        _LOGGER.debug(f"[InfluxDB] Received history for {device_name} ({dev_eui}): {history}")
        # --- Normalize tags ---
        tags = influxdb_config.get("tags")
        if not tags:
            tags = {}
        elif isinstance(tags, str):
            try:
                tags = yaml.safe_load(tags)
                if not isinstance(tags, dict):
                    raise ValueError
            except Exception:
                # Try key=value,comma-separated
                try:
                    tags = dict(
                        item.split("=", 1) for item in tags.split(",") if "=" in item
                    )
                except Exception:
                    tags = {}
        elif not isinstance(tags, dict):
            tags = {}
        # --- End normalize tags ---
        new_entities = []
        last_values = {}  # Track last value for each entity_id_tag
        for sensor_info in discovery:
            field = sensor_info["field"]
            unique_id = f"{dev_eui}_{field}"
            # Look up the entity in the registry by unique_id
            entity = next(
                (e for e in entity_reg.entities.values()
                 if e.domain == "sensor" and e.platform == DOMAIN and e.unique_id == unique_id and e.config_entry_id == entry_id),
                None
            )
            if entity:
                # Explicitly assign entity_id for this sensor
                entity_id = entity.entity_id
                if unique_id in sensors:
                    sensor = sensors[unique_id]
                else:
                    sensor = ChirpstackHASensor(dev_eui, sensor_info, device_name)
                    sensor.entity_id = entity_id
                    sensors[unique_id] = sensor
                    new_entities.append(sensor)
                included = is_entity_included(entity_id, influxdb_config)
                state_class = getattr(sensor, "state_class", None)
                has_history = bool(history)
                if state_class == "measurement" and has_history:
                    domain_tag, object_id_tag = split_entity_id(entity_id)
                    last_value = await get_last_influxdb_value(hass, influxdb_client, influxdb_config, domain_tag, object_id_tag, sensor_info.get("unit")) if influxdb_client else None
                    def normalize(v):
                        try:
                            return float(v)
                        except (TypeError, ValueError):
                            return v
                    prev_value = normalize(last_value)
                    influx_points = []
                    for entry in history:
                        if field in entry:
                            value = entry[field]
                            ts = entry.get("timestamp")
                            if ts is not None:
                                norm_value = normalize(value)
                                diff = abs(norm_value - prev_value) if isinstance(norm_value, float) and isinstance(prev_value, float) else None
                                if (isinstance(norm_value, float) and isinstance(prev_value, float) and diff > 1e-6) or (not isinstance(norm_value, float) or not isinstance(prev_value, float)) and norm_value != prev_value:
                                    dt = dt_util.utc_from_timestamp(float(ts))
                                    if influxdb_write_api and included:
                                        domain_tag, object_id_tag = split_entity_id(sensor.entity_id)
                                        point = (
                                            Point(sensor_info.get("unit"))
                                            .tag("domain", domain_tag)
                                            .tag("entity_id", object_id_tag)
                                            .field("value", value)
                                            .time(dt, WritePrecision.S)
                                        )
                                        for k, v in tags.items():
                                            if k in ("entity_id", "domain"):
                                                continue
                                            if v is not None and (not isinstance(v, str) or v.strip()):
                                                point = point.tag(k, v)
                                        influx_points.append(point)
                                    prev_value = norm_value
                    if influx_points and influxdb_write_api:
                        try:
                            influxdb_write_api.write(bucket=bucket if version == '2.x' else database, org=org if version == '2.x' else None, record=influx_points)
                            influxdb_write_api.flush()
                        except Exception as e:
                            _LOGGER.error(f"[InfluxDB] Failed to write to InfluxDB: {e}\n{traceback.format_exc()}")
                    elif influxdb_write_api:
                        _LOGGER.debug(f"[InfluxDB] No points to write for {entity_id} (history empty or not included)")
                    current_value = data.get(field)
                    if (
                        current_value is not None
                        and last_value == current_value
                        and prev_value != current_value
                        and influx_points
                    ):
                        dt = dt_util.utcnow()
                        if influxdb_write_api and included:
                            domain_tag, object_id_tag = split_entity_id(sensor.entity_id)
                            point = (
                                Point(sensor_info.get("unit"))
                                .tag("domain", domain_tag)
                                .tag("entity_id", object_id_tag)
                                .field("value", current_value)
                                .time(dt, WritePrecision.S)
                            )
                            for k, v in tags.items():
                                if v is not None and (not isinstance(v, str) or v.strip()):
                                    point = point.tag(k, v)
                            try:
                                influxdb_write_api.write(bucket=bucket if version == '2.x' else database, org=org if version == '2.x' else None, record=[point])
                                influxdb_write_api.flush()
                            except Exception as e:
                                _LOGGER.error(f"[InfluxDB] Failed to write current value after backfill: {e}\n{traceback.format_exc()}")
                # Always update state for every event
                value = data.get(field)
                if value is not None:
                    await sensor.async_update_state(value)
            else:
                # If the entity is not in the registry, skip history backfill
                _LOGGER.debug(f"[InfluxDB] Skipping history for {unique_id} because entity_id is not in registry.")
        # Update last value for live updates
        # last_values[entity_id_tag] = current_value
        if new_entities:
            async_add_entities(new_entities)

    # For live updates, only write if value changes
    # live_last_values = {}
    # async def live_update(entity, value):
    #     full_entity_id = getattr(entity, "entity_id", None)
    #     if full_entity_id:
    #         domain_tag, entity_id_tag = split_entity_id(full_entity_id)
    #     else:
    #         device_name_clean = getattr(entity, "_device_name", "").lower().replace(' ', '_')
    #         entity_id_tag = f"{device_name_clean}_{getattr(entity, '_field', '')}"
    #         domain_tag = "sensor"
    #     prev_value = live_last_values.get(entity_id_tag)
    #     if value != prev_value:
    #         dt = dt_util.utcnow()
    #         if influxdb_write_api:
    #             point = (
    #                 Point(getattr(entity, "unit_of_measurement", None))
    #                 .tag("domain", domain_tag)
    #                 .tag("entity_id", entity_id_tag)
    #                 .field("value", value)
    #                 .time(dt, WritePrecision.S)
    #             )
    #             for k, v in influxdb_config.get("tags", {}).items():
    #                 point = point.tag(k, v)
    #             try:
    #                 influxdb_write_api.write(bucket=bucket if version == '2.x' else database, org=org if version == '2.x' else None, record=[point])
    #                 _LOGGER.debug(f"[InfluxDB] Live wrote value for {domain_tag}.{entity_id_tag}: {value}")
    #             except Exception as e:
    #                 _LOGGER.error(f"[InfluxDB] Failed to write live value: {e}\n{traceback.format_exc()}")
    #         live_last_values[entity_id_tag] = value

    # Patch async_update_state to use live_update
    # orig_async_update_state = ChirpstackHASensor.async_update_state
    # async def patched_async_update_state(self, value):
    #     await orig_async_update_state(self, value)
    #     await live_update(self, value)
    # ChirpstackHASensor.async_update_state = patched_async_update_state

    # Register callback
    hass.data[DOMAIN]["entity_callbacks"].append(lambda event, entry_id=entry.entry_id: handle_event(event, entry_id))
    async_add_entities([])  # No entities at startup

class ChirpstackHASensor(SensorEntity):
    def __init__(self, dev_eui, sensor_info, device_name):
        self._dev_eui = dev_eui
        self._field = sensor_info["field"]
        self._attr_unique_id = f"{dev_eui}_{self._field}"
        sensor_name = sensor_info.get("name", self._field)
        self._attr_name = f"{device_name} {sensor_name}"
        _LOGGER.debug(f"sensor_info for {self._attr_name}: {sensor_info}")
        unit = sensor_info.get("unit")
        device_class = sensor_info.get("device_class")
        # Fallbacks for missing or unrecognized units
        if not unit:
            # Try to infer from device_class or field name
            if device_class == "temperature" or "temperature" in self._field:
                unit = "°C"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to '°C' for temperature.")
            elif device_class == "weight" or "weight" in self._field:
                unit = "kg"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to 'kg' for weight.")
            elif device_class == "humidity" or "humidity" in self._field:
                unit = "%"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to '%' for humidity.")
            elif device_class == "battery" or "battery" in self._field:
                unit = "%"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to '%' for battery.")
            elif device_class == "pressure" or "pressure" in self._field:
                unit = "hPa"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to 'hPa' for pressure.")
            elif device_class == "voltage" or "voltage" in self._field:
                unit = "V"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to 'V' for voltage.")
            elif device_class == "current" or "current" in self._field:
                unit = "A"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to 'A' for current.")
            elif device_class == "power" or "power" in self._field:
                unit = "W"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to 'W' for power.")
            elif device_class == "energy" or "energy" in self._field:
                unit = "Wh"
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), defaulting to 'Wh' for energy.")
            else:
                unit = None
                _LOGGER.warning(f"No unit provided for {self._attr_name} ({self._field}), and could not infer a default.")
        # Normalize units for Home Assistant compatibility
        if device_class == "temperature":
            if unit in ["°C", "℃", "C", "c"]:
                unit = "\u00B0C"
            elif unit in ["°F", "F", "f"]:
                unit = "\u00B0F"
        # For Home Assistant compatibility, use device_class 'mass' instead of 'weight'
        if device_class == "weight" or (not device_class and "weight" in self._field):
            device_class = "mass"
        # Log the actual unit and device_class values for debugging
        _LOGGER.debug(f"Normalized unit for {self._attr_name}: {repr(unit)}, device_class: {device_class}")
        # Validate unit for known device classes after normalization
        valid_units = {
            "temperature": ["\u00B0C", "\u00B0F"],
            "mass": ["kg", "g", "lb"],
            "humidity": ["%"],
            "battery": ["%"],
            "pressure": ["hPa", "Pa", "mbar", "bar", "psi"],
            "voltage": ["V", "mV"],
            "current": ["A", "mA"],
            "power": ["W", "kW"],
            "energy": ["Wh", "kWh"],
        }
        if device_class in valid_units and unit not in valid_units[device_class]:
            _LOGGER.warning(f"After normalization, unit '{unit}' for {self._attr_name} ({self._field}) is not recognized for device_class '{device_class}'. Valid units: {valid_units[device_class]}")
        self._attr_unit_of_measurement = unit
        self._attr_native_unit_of_measurement = unit
        # Device class
        if device_class:
            self._attr_device_class = device_class
        elif "weight" in self._field:
            self._attr_device_class = "mass"
        elif "temperature" in self._field:
            self._attr_device_class = "temperature"
        elif "humidity" in self._field:
            self._attr_device_class = "humidity"
        elif "pressure" in self._field:
            self._attr_device_class = "pressure"
        elif "voltage" in self._field:
            self._attr_device_class = "voltage"
        elif "current" in self._field:
            self._attr_device_class = "current"
        elif "power" in self._field:
            self._attr_device_class = "power"
        elif "energy" in self._field:
            self._attr_device_class = "energy"
        elif "battery" in self._field:
            self._attr_device_class = "battery"
        elif "signal" in self._field:
            self._attr_device_class = "signal"
        elif "rssi" in self._field:
            self._attr_device_class = "rssi"
        elif "snr" in self._field:
            self._attr_device_class = "snr"
        elif "co2" in self._field:
            self._attr_device_class = "co2"
        elif "co" in self._field:
            self._attr_device_class = "co"
        elif "no2" in self._field:
            self._attr_device_class = "no2"
        else:
            self._attr_device_class = None
        # State class
        self._attr_state_class = sensor_info.get("state_class", "measurement")
        # Suggested display precision
        precision = sensor_info.get("precision")
        if precision is not None:
            self._attr_suggested_display_precision = int(precision)
        # Icon
        icon = sensor_info.get("icon")
        if icon:
            self._attr_icon = icon
        else:
            self._attr_icon = None
        # Entity category
        entity_category = sensor_info.get("entity_category")
        if entity_category:
            self._attr_entity_category = entity_category
        else:
            self._attr_entity_category = None
        self._device_name = device_name
        # Set friendly name as 'device_name sensor_name'
        self._state = None
        self._pending_state = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, dev_eui)},
            "name": device_name,
            "manufacturer": "ChirpStack",
            "model": "LoRaWAN Device",
        }
        # Only log at creation for troubleshooting (after all attributes are set)
        _LOGGER.debug(f"Creating sensor {self._attr_name}: field={self._field}, device_class={self._attr_device_class}, state_class={self._attr_state_class}, precision={getattr(self, '_attr_suggested_display_precision', None)}, unit={self._attr_unit_of_measurement}, icon={getattr(self, '_attr_icon', None)}, entity_category={getattr(self, '_attr_entity_category', None)}")

    @property
    def state(self):
        return self._state

    async def async_update_state(self, value):
        if self.hass is not None:
            self._state = value
            self.async_write_ha_state()
        else:
            self._pending_state = value

    async def async_added_to_hass(self):
        _LOGGER.debug(f"[InfluxDB] async_added_to_hass called for {self._attr_unique_id} (entity_id={getattr(self, 'entity_id', None)})")
        if self._pending_state is not None:
            self._state = self._pending_state
            self.async_write_ha_state()
            self._pending_state = None

    @property
    def unit_of_measurement(self):
        return self._attr_unit_of_measurement

    @property
    def native_unit_of_measurement(self):
        return self._attr_native_unit_of_measurement

    @property
    def device_class(self):
        return self._attr_device_class

    @property
    def state_class(self):
        return self._attr_state_class

    @property
    def icon(self):
        return self._attr_icon

    @property
    def entity_category(self):
        return self._attr_entity_category

    @property
    def suggested_display_precision(self):
        return self._attr_suggested_display_precision


def create_sensor(dev_eui, sensor_info, device_name):
    return ChirpstackHASensor(dev_eui, sensor_info, device_name) 