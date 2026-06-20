"""Laboratory Booking System for equipment and lab resource management.

Implements five mandatory functional requirements:
- Req 156: Overlap detection for equipment bookings
- Req 157: Capacity enforcement for laboratory bookings
- Req 158: Maintenance lockout preventing bookings during maintenance
- Req 159: Condition degradation tracking with usage
- Req 160/161: Utilisation rate calculation and weekly reporting
"""

from datetime import datetime, date, timedelta
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod


# ============================================================================
# EXCEPTIONS
# ============================================================================

class BookingConflictError(Exception):
    """Raised when a booking would overlap with an existing booking."""
    pass


class EquipmentUnderMaintenanceError(Exception):
    """Raised when attempting to book equipment that is under maintenance."""
    pass


class LabCapacityError(Exception):
    """Raised when lab capacity would be exceeded by a booking."""
    pass


# ============================================================================
# ENUMS
# ============================================================================

class Condition(Enum):
    """Equipment condition state."""
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


# ============================================================================
# VALUE OBJECTS
# ============================================================================

@dataclass(frozen=True)
class TimeSlot:
    """Represents a time interval for a booking."""
    start: datetime
    end: datetime

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError("start must be before end")

    def overlaps(self, other: 'TimeSlot') -> bool:
        """Check if this TimeSlot overlaps with another."""
        return self.start < other.end and other.start < self.end

    def duration_hours(self) -> float:
        """Return duration in hours."""
        return (self.end - self.start).total_seconds() / 3600


# ============================================================================
# RESOURCE HIERARCHY
# ============================================================================

class Resource(ABC):
    """Abstract base class for all bookable resources."""

    def __init__(self, resource_id: str, name: str, asset_code: str, manufacturer: str, model: str):
        self.resource_id = resource_id
        self.name = name
        self.asset_code = asset_code
        self.manufacturer = manufacturer
        self.model = model
        self.bookings: List[Tuple[TimeSlot, str]] = []  # (TimeSlot, user)
        self.condition = Condition.GOOD
        self.usage_hours = 0.0
        self.under_maintenance = False
        self.maintenance_date: Optional[date] = None

    @abstractmethod
    def can_book(self, slot: TimeSlot) -> bool:
        """Check if this resource can be booked for the given time slot."""
        pass

    def add_booking(self, slot: TimeSlot, user: str):
        """Add a booking for this resource."""
        if not self.can_book(slot):
            raise BookingConflictError(
                f"Booking conflict for {self.resource_id}: slot {slot.start} to {slot.end}"
            )
        self.bookings.append((slot, user))
        self.usage_hours += slot.duration_hours()
        self._degrade_condition(slot.duration_hours())

    def _degrade_condition(self, hours_used: float):
        """Degrade condition based on usage hours (Req 159)."""
        self.usage_hours += hours_used
        # Thresholds: GOOD 0-100h, FAIR 100-200h, POOR 200+h
        if self.usage_hours >= 200:
            self.condition = Condition.POOR
        elif self.usage_hours >= 100:
            self.condition = Condition.FAIR

    def schedule_maintenance(self, maintenance_date: date):
        """Schedule maintenance for this resource (blocks bookings on that date)."""
        self.under_maintenance = True
        self.maintenance_date = maintenance_date


class Equipment(Resource):
    """Stationary equipment residing in a laboratory."""

    def __init__(self, resource_id: str, name: str, asset_code: str, manufacturer: str, model: str):
        super().__init__(resource_id, name, asset_code, manufacturer, model)
        self.lab: Optional['Laboratory'] = None

    def can_book(self, slot: TimeSlot) -> bool:
        """Check if equipment can be booked (not under maintenance, no overlaps)."""
        if self.under_maintenance and slot.start.date() == self.maintenance_date:
            raise EquipmentUnderMaintenanceError(
                f"{self.resource_id} is under maintenance on {self.maintenance_date}"
            )
        for existing_slot, _ in self.bookings:
            if existing_slot.overlaps(slot):
                return False
        return True


class PortableEquipment(Resource):
    """Mobile equipment that can move between laboratories."""

    def __init__(self, resource_id: str, name: str, asset_code: str, manufacturer: str, 
                 model: str, initial_lab_code: str):
        super().__init__(resource_id, name, asset_code, manufacturer, model)
        self.current_lab_code = initial_lab_code

    def can_book(self, slot: TimeSlot) -> bool:
        """Check if portable equipment can be booked (not under maintenance, no overlaps)."""
        if self.under_maintenance and slot.start.date() == self.maintenance_date:
            raise EquipmentUnderMaintenanceError(
                f"{self.resource_id} is under maintenance on {self.maintenance_date}"
            )
        for existing_slot, _ in self.bookings:
            if existing_slot.overlaps(slot):
                return False
        return True


class Laboratory(Resource):
    """A laboratory with capacity constraints."""

    def __init__(self, resource_id: str, name: str, lab_code: str, description: str, capacity: int):
        super().__init__(resource_id, name, lab_code, "", "")
        self.lab_code = lab_code
        self.description = description
        self.capacity = capacity
        self.equipment: List[Equipment] = []

    def add_equipment(self, equipment: Equipment):
        """Add equipment to this laboratory."""
        equipment.lab = self
        self.equipment.append(equipment)

    def can_book(self, slot: TimeSlot) -> bool:
        """Check if lab can be booked (capacity not exceeded, no maintenance conflict)."""
        if self.under_maintenance and slot.start.date() == self.maintenance_date:
            raise EquipmentUnderMaintenanceError(
                f"{self.resource_id} is under maintenance on {self.maintenance_date}"
            )
        
        # Count concurrent bookings during this slot
        concurrent_count = sum(1 for existing_slot, _ in self.bookings 
                               if existing_slot.overlaps(slot))
        
        if concurrent_count >= self.capacity:
            raise LabCapacityError(
                f"Lab {self.resource_id} capacity ({self.capacity}) would be exceeded "
                f"during {slot.start} to {slot.end}"
            )
        return True


# ============================================================================
# MAINTENANCE
# ============================================================================

class CorrectiveMaintenance:
    """Represents a corrective maintenance task for equipment."""

    def __init__(self, equipment: Resource, scheduled_date: date, reason: str):
        self.equipment = equipment
        self.scheduled_date = scheduled_date
        self.reason = reason
        self.status = "scheduled"

    def execute(self):
        """Execute the maintenance task (block equipment from bookings)."""
        self.equipment.schedule_maintenance(self.scheduled_date)
        self.status = "executed"


# ============================================================================
# BOOKING SYSTEM
# ============================================================================

class BookingSystem:
    """Main system for managing laboratory and equipment bookings."""

    def __init__(self, department_name: str):
        self.department_name = department_name
        self.laboratories: Dict[str, Laboratory] = {}
        self.resources: Dict[str, Resource] = {}

    def add_laboratory(self, lab: Laboratory):
        """Register a laboratory with the system."""
        self.laboratories[lab.resource_id] = lab
        self.resources[lab.resource_id] = lab
        # Also register lab equipment as resources
        for equipment in lab.equipment:
            self.resources[equipment.resource_id] = equipment

    def add_resource(self, resource: Resource):
        """Register a resource (equipment or portable equipment) with the system."""
        self.resources[resource.resource_id] = resource

    def book(self, resource_id: str, slot: TimeSlot, user: str) -> bool:
        """Book a resource for a user (Req 156: overlap detection)."""
        if resource_id not in self.resources:
            raise ValueError(f"Unknown resource: {resource_id}")

        resource = self.resources[resource_id]
        resource.add_booking(slot, user)
        return True

    def utilisation_rate(self, resource_id: str, start_date: date, end_date: date) -> float:
        """Calculate utilisation rate for a resource over a date range (Req 160).
        
        Returns percentage of time the resource was booked.
        """
        if resource_id not in self.resources:
            raise ValueError(f"Unknown resource: {resource_id}")

        resource = self.resources[resource_id]
        
        # Calculate total hours in the date range
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        total_hours = (end_dt - start_dt).total_seconds() / 3600
        
        # Sum booked hours within the date range
        booked_hours = 0.0
        for slot, _ in resource.bookings:
            if slot.start.date() <= end_date and slot.end.date() >= start_date:
                # Clamp the slot to the date range
                clamped_start = max(slot.start, start_dt)
                clamped_end = min(slot.end, end_dt)
                if clamped_start < clamped_end:
                    booked_hours += (clamped_end - clamped_start).total_seconds() / 3600
        
        return (booked_hours / total_hours * 100) if total_hours > 0 else 0.0

    def weekly_report(self, as_of: date) -> Dict[str, any]:
        """Generate a weekly report of all resources (Req 161)."""
        # Calculate week start (Monday)
        week_start = as_of - timedelta(days=as_of.weekday())
        week_end = week_start + timedelta(days=6)

        report = {
            "report_date": str(as_of),
            "week_start": str(week_start),
            "week_end": str(week_end),
            "resources": {}
        }

        for resource_id, resource in self.resources.items():
            util_rate = self.utilisation_rate(resource_id, week_start, week_end)
            bookings_count = sum(1 for slot, _ in resource.bookings
                                if slot.start.date() >= week_start and slot.end.date() <= week_end)

            report["resources"][resource_id] = {
                "name": resource.name,
                "utilisation_rate": f"{util_rate:.1f}%",
                "bookings_this_week": bookings_count,
                "condition": resource.condition.value,
                "usage_hours": f"{resource.usage_hours:.1f}h"
            }

        return report
