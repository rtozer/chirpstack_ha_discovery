import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
import logging
_LOGGER = logging.getLogger(__name__)

INFLUXDB_DEFAULTS = {
    "version": "2.x",
    "host": "localhost",
    "port": 8086,
    "database": "home_assistant",
    "bucket": "",
    "username": "",
    "password": "",
    "token": "",
    "org": "",
    "include_entities": "",
    "exclude_entities": "",
    "tags": "",
}

INFLUXDB_VERSIONS = ["1.x", "2.x"]

OPTIONAL_FIELDS = [
    "tags", "include_entities", "exclude_entities", "username", "password", "database", "bucket", "org", "token"
]

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        self._version = None
        self._data = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Select InfluxDB version."""
        errors = {}
        if user_input is not None:
            self._version = user_input["version"]
            return await self.async_step_details()
        schema = vol.Schema({
            vol.Required("version", default=self._version or INFLUXDB_DEFAULTS["version"]): vol.In(INFLUXDB_VERSIONS),
        })
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_details(self, user_input=None):
        """Step 2: Show fields for selected InfluxDB version."""
        errors = {}
        version = self._version or INFLUXDB_DEFAULTS["version"]
        data = user_input or {}
        if user_input is not None:
            # Validate required fields
            if not user_input["host"]:
                errors["host"] = "required"
            if version == "1.x" and not user_input["database"]:
                errors["database"] = "required"
            if version == "2.x" and (not user_input["bucket"] or not user_input["org"] or not user_input["token"]):
                if not user_input["bucket"]:
                    errors["bucket"] = "required"
                if not user_input["org"]:
                    errors["org"] = "required"
                if not user_input["token"]:
                    errors["token"] = "required"
            # Parse tags as YAML or key=value pairs
            tags = None
            tags_input = user_input.get("tags", "")
            if tags_input:
                try:
                    tags = yaml.safe_load(tags_input)
                    if not isinstance(tags, dict):
                        raise ValueError
                except Exception:
                    # Try key=value,comma-separated
                    try:
                        tags = dict(
                            item.split("=", 1) for item in tags_input.split(",") if "=" in item
                        )
                    except Exception:
                        errors["tags"] = "invalid_tags"
            if not errors:
                entry = dict(user_input)
                entry["version"] = version
                # Unified robust field removal logic
                for key in OPTIONAL_FIELDS:
                    remove_key = False
                    if key == "tags" and user_input.get("remove_tags"):
                        remove_key = True
                    elif key == "include_entities" and user_input.get("remove_include_entities"):
                        remove_key = True
                    elif key == "exclude_entities" and user_input.get("remove_exclude_entities"):
                        remove_key = True
                    value = user_input.get(key, None)
                    if remove_key or value is None or (isinstance(value, str) and not value.strip()):
                        entry.pop(key, None)
                    else:
                        entry[key] = value
                if tags is not None:
                    entry["tags"] = tags
                _LOGGER.debug(f"[ConfigFlow] Creating entry with data: {entry}")
                # Update hass.data[DOMAIN][entry_id] immediately if possible
                if hasattr(self, 'hass') and hasattr(self, 'config_entry'):
                    domain_data = self.hass.data.setdefault(DOMAIN, {})
                    domain_data[self.config_entry.entry_id] = entry
                return self.async_create_entry(title="ChirpStack HA", data=entry)
        # Prepare tags field as string
        tags_str = data.get("tags", "")
        if isinstance(tags_str, dict):
            try:
                tags_str = yaml.safe_dump(tags_str)
            except Exception:
                tags_str = str(tags_str)
        schema_dict = {
            vol.Required("host", default=data.get("host", INFLUXDB_DEFAULTS["host"])): str,
            vol.Required("port", default=data.get("port", INFLUXDB_DEFAULTS["port"])): int,
        }
        if version == "1.x":
            schema_dict[vol.Required("database", default=data.get("database", INFLUXDB_DEFAULTS["database"]))] = str
            schema_dict[vol.Optional("username", default=data.get("username", INFLUXDB_DEFAULTS["username"]))] = str
            schema_dict[vol.Optional("password", default=data.get("password", INFLUXDB_DEFAULTS["password"]))] = str
        else:  # 2.x
            schema_dict[vol.Required("bucket", default=data.get("bucket", INFLUXDB_DEFAULTS["bucket"]))] = str
            schema_dict[vol.Required("org", default=data.get("org", INFLUXDB_DEFAULTS["org"]))] = str
            schema_dict[vol.Required("token", default=data.get("token", INFLUXDB_DEFAULTS["token"]))] = str
        schema_dict[vol.Optional("include_entities", default=data.get("include_entities", INFLUXDB_DEFAULTS["include_entities"]))] = str
        schema_dict[vol.Optional("exclude_entities", default=data.get("exclude_entities", INFLUXDB_DEFAULTS["exclude_entities"]))] = str
        # Only show remove checkboxes if the field has a value
        if data.get("tags"):
            schema_dict[vol.Optional("remove_tags", default=False)] = bool
        if data.get("include_entities"):
            schema_dict[vol.Optional("remove_include_entities", default=False)] = bool
        if data.get("exclude_entities"):
            schema_dict[vol.Optional("remove_exclude_entities", default=False)] = bool
        schema_dict[vol.Optional("tags", default=tags_str)]= str
        schema = vol.Schema(schema_dict)
        return self.async_show_form(
            step_id="details",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "tags_hint": "Enter tags as YAML (key: value) or comma-separated key=value pairs. Example: source: HA, location: lab or source=HA,location=lab",
                "entities_hint": "Comma-separated entity IDs. Example: sensor.temp1,sensor.temp2",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self._version = None

    async def async_step_init(self, user_input=None):
        """Step 1: Select InfluxDB version for options flow."""
        errors = {}
        data = user_input or self.config_entry.data
        version = data.get("version", INFLUXDB_DEFAULTS["version"])
        if user_input is not None and "version" in user_input:
            self._version = user_input["version"]
            return await self.async_step_details()
        schema = vol.Schema({
            vol.Required("version", default=version): vol.In(INFLUXDB_VERSIONS),
        })
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_details(self, user_input=None):
        """Step 2: Show fields for selected InfluxDB version in options flow."""
        errors = {}
        data = user_input or self.config_entry.data
        version = self._version or data.get("version", INFLUXDB_DEFAULTS["version"])
        if user_input is not None:
            # Validate required fields
            if not user_input["host"]:
                errors["host"] = "required"
            if version == "1.x" and not user_input["database"]:
                errors["database"] = "required"
            if version == "2.x" and (not user_input["bucket"] or not user_input["org"] or not user_input["token"]):
                if not user_input["bucket"]:
                    errors["bucket"] = "required"
                if not user_input["org"]:
                    errors["org"] = "required"
                if not user_input["token"]:
                    errors["token"] = "required"
            # Parse tags as YAML or key=value pairs
            tags = None
            tags_input = user_input.get("tags", "")
            if tags_input:
                try:
                    tags = yaml.safe_load(tags_input)
                    if not isinstance(tags, dict):
                        raise ValueError
                except Exception:
                    # Try key=value,comma-separated
                    try:
                        tags = dict(
                            item.split("=", 1) for item in tags_input.split(",") if "=" in item
                        )
                    except Exception:
                        errors["tags"] = "invalid_tags"
            if not errors:
                entry = dict(self.config_entry.data)
                entry.update(user_input)
                entry["version"] = version
                # Unified robust field removal logic
                for key in OPTIONAL_FIELDS:
                    remove_key = False
                    if key == "tags" and user_input.get("remove_tags"):
                        remove_key = True
                    elif key == "include_entities" and user_input.get("remove_include_entities"):
                        remove_key = True
                    elif key == "exclude_entities" and user_input.get("remove_exclude_entities"):
                        remove_key = True
                    value = user_input.get(key, None)
                    if remove_key or value is None or (isinstance(value, str) and not value.strip()):
                        entry.pop(key, None)
                    else:
                        entry[key] = value
                _LOGGER.debug(f"[OptionsFlow] Updating entry with data: {entry}")
                self.hass.config_entries.async_update_entry(self.config_entry, data=entry)
                # Update hass.data[DOMAIN][entry_id] immediately
                domain_data = self.hass.data.setdefault(DOMAIN, {})
                domain_data[self.config_entry.entry_id] = entry
                return self.async_create_entry(title="", data={})
        # Prepare tags field as string
        tags_str = data.get("tags", "")
        if isinstance(tags_str, dict):
            try:
                tags_str = yaml.safe_dump(tags_str)
            except Exception:
                tags_str = str(tags_str)
        schema_dict = {
            vol.Required("host", default=data.get("host", INFLUXDB_DEFAULTS["host"])): str,
            vol.Required("port", default=data.get("port", INFLUXDB_DEFAULTS["port"])): int,
        }
        if version == "1.x":
            schema_dict[vol.Required("database", default=data.get("database", INFLUXDB_DEFAULTS["database"]))] = str
            schema_dict[vol.Optional("username", default=data.get("username", INFLUXDB_DEFAULTS["username"]))] = str
            schema_dict[vol.Optional("password", default=data.get("password", INFLUXDB_DEFAULTS["password"]))] = str
        else:  # 2.x
            schema_dict[vol.Required("bucket", default=data.get("bucket", INFLUXDB_DEFAULTS["bucket"]))] = str
            schema_dict[vol.Required("org", default=data.get("org", INFLUXDB_DEFAULTS["org"]))] = str
            schema_dict[vol.Required("token", default=data.get("token", INFLUXDB_DEFAULTS["token"]))] = str
        schema_dict[vol.Optional("include_entities", default=data.get("include_entities", INFLUXDB_DEFAULTS["include_entities"]))] = str
        schema_dict[vol.Optional("exclude_entities", default=data.get("exclude_entities", INFLUXDB_DEFAULTS["exclude_entities"]))] = str
        # Only show remove checkboxes if the field has a value
        if data.get("tags"):
            schema_dict[vol.Optional("remove_tags", default=False)] = bool
        if data.get("include_entities"):
            schema_dict[vol.Optional("remove_include_entities", default=False)] = bool
        if data.get("exclude_entities"):
            schema_dict[vol.Optional("remove_exclude_entities", default=False)] = bool
        schema_dict[vol.Optional("tags", default=tags_str)] = str
        schema = vol.Schema(schema_dict)
        return self.async_show_form(
            step_id="details",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "tags_hint": "Enter tags as YAML (key: value) or comma-separated key=value pairs. Example: source: HA, location: lab or source=HA,location=lab",
                "entities_hint": "Comma-separated entity IDs. Example: sensor.temp1,sensor.temp2",
            },
        ) 