"""Sensors for everHome EcoTracker cloud data."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EverHomeDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class EverHomeSensorDescription(SensorEntityDescription):
    """Description for everHome sensors."""

    scale: float = 1.0


SENSOR_DESCRIPTIONS: dict[str, EverHomeSensorDescription] = {
    "power": EverHomeSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "powerAvg": EverHomeSensorDescription(
        key="powerAvg",
        translation_key="power_avg",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "powerPhase1": EverHomeSensorDescription(
        key="powerPhase1",
        translation_key="power_phase_1",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "powerPhase2": EverHomeSensorDescription(
        key="powerPhase2",
        translation_key="power_phase_2",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "powerPhase3": EverHomeSensorDescription(
        key="powerPhase3",
        translation_key="power_phase_3",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "energyCounterIn": EverHomeSensorDescription(
        key="energyCounterIn",
        translation_key="energy_counter_in",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=0.001,
    ),
    "energyCounterInT1": EverHomeSensorDescription(
        key="energyCounterInT1",
        translation_key="energy_counter_in_t1",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=0.001,
    ),
    "energyCounterInT2": EverHomeSensorDescription(
        key="energyCounterInT2",
        translation_key="energy_counter_in_t2",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=0.001,
    ),
    "energyCounterOut": EverHomeSensorDescription(
        key="energyCounterOut",
        translation_key="energy_counter_out",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=0.001,
    ),
    "energyCounterIOut": EverHomeSensorDescription(
        key="energyCounterIOut",
        translation_key="energy_counter_out",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=0.001,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up everHome sensors."""
    coordinator: EverHomeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_entities: set[str] = set()

    def add_new_entities() -> None:
        entities: list[EverHomeSensor] = []
        for device, metric in _iter_metrics(coordinator.data or []):
            unique_key = _unique_metric_key(device, metric)
            if unique_key in known_entities:
                continue
            known_entities.add(unique_key)
            entities.append(EverHomeSensor(coordinator, device, metric))

        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class EverHomeSensor(CoordinatorEntity[EverHomeDataUpdateCoordinator], SensorEntity):
    """Representation of an everHome numeric state or property."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EverHomeDataUpdateCoordinator,
        device: dict[str, Any],
        metric: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = str(device["id"])
        self._device_name = str(device.get("name") or f"EcoTracker {self._device_id}")
        self._metric = metric
        self._source = metric["source"]
        self._key = metric["key"]
        description = SENSOR_DESCRIPTIONS.get(
            self._key,
            EverHomeSensorDescription(
                key=self._key,
                name=_humanize_key(self._key),
                state_class=SensorStateClass.MEASUREMENT,
            ),
        )
        self.entity_description = description
        self._attr_unique_id = _unique_metric_key(device, metric)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="Christian Laux",
            name=self._device_name,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current native value."""
        device = _find_device(self.coordinator.data or [], self._device_id)
        if device is None:
            return None

        raw_value = _metric_raw_value(device, self._source, self._key)
        value = _as_float(raw_value)
        if value is None:
            return None
        return round(value * self.entity_description.scale, 6)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the everHome device and source metadata."""
        return {
            "everhome_device_id": self._device_id,
            "everhome_source": self._source,
            "everhome_key": self._key,
        }


def _iter_metrics(
    devices: Iterable[dict[str, Any]],
) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
    """Yield numeric states and properties from everHome devices."""
    for device in devices:
        if "id" not in device:
            continue

        states = device.get("states") or {}
        if isinstance(states, dict):
            for key, value in states.items():
                if _as_float(value) is not None:
                    yield device, {"source": "states", "key": str(key)}

        properties = device.get("properties") or []
        if isinstance(properties, list):
            for prop in properties:
                if not isinstance(prop, dict):
                    continue
                key = prop.get("key")
                value = prop.get("value", prop.get("defaultValue"))
                if key is not None and _as_float(value) is not None:
                    yield device, {"source": "properties", "key": str(key)}


def _metric_raw_value(device: dict[str, Any], source: str, key: str) -> Any:
    """Return a metric value from a device."""
    if source == "states":
        return (device.get("states") or {}).get(key)

    for prop in device.get("properties") or []:
        if isinstance(prop, dict) and prop.get("key") == key:
            return prop.get("value", prop.get("defaultValue"))
    return None


def _find_device(devices: Iterable[dict[str, Any]], device_id: str) -> dict[str, Any] | None:
    """Find a device by id."""
    for device in devices:
        if str(device.get("id")) == device_id:
            return device
    return None


def _as_float(value: Any) -> float | None:
    """Return value as float if possible."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique_metric_key(device: dict[str, Any], metric: dict[str, Any]) -> str:
    """Build a stable unique id for a metric."""
    return f"{device['id']}_{metric['source']}_{metric['key']}"


def _humanize_key(key: str) -> str:
    """Turn an API key into a readable fallback name."""
    label = key.replace("_", " ")
    chars: list[str] = []
    for char in label:
        if char.isupper() and chars:
            chars.append(" ")
        chars.append(char)
    return " ".join("".join(chars).split()).title()
