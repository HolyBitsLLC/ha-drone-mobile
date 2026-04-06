"""Base entity for DroneMobile."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DroneMobileCoordinator


class DroneMobileEntity(CoordinatorEntity[DroneMobileCoordinator]):
    """Base class for DroneMobile entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DroneMobileCoordinator,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        vehicle_id = coordinator.data["vehicle_id"]
        self._attr_unique_id = f"{vehicle_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        data = self.coordinator.data
        info = data.get("info", {})
        model_parts = [
            p
            for p in [
                str(info.get("year", "")) if info.get("year") else None,
                info.get("make"),
                info.get("model"),
            ]
            if p
        ]
        return DeviceInfo(
            identifiers={(DOMAIN, data["vehicle_id"])},
            name=data["name"],
            manufacturer=MANUFACTURER,
            model=" ".join(model_parts) if model_parts else None,
        )
