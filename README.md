# Group 9 — University Laboratory Equipment Booking and Inventory System

# CPE 310 — OOP with Python | Capstone Project 9 | Weeks 1–5 Comprehensive Assessment
Federal University Oye-Ekiti | Academic Year 2025/2026

Akinbuwa Ayomide Triumphant | CPE/2022/1115 | akinbuwaa

Dmilare Daniel Inioluwa| CPE/2023/1116 | TRIPLE-D2000

Afolabi Olarewaju | CPE/2023/1113 | afolabiolanrewaju341-sudo

Shevire Elijah Ojone| CPE/2023/1120 | Promolordx

Ibrahim Yaru Nurudeen| CPE/2022/1116 | nurudeenibrahim262-cell

Azeez Taiwo Victor| CPE/2023/1115 | taiwovictor1212-droid

Opeyemi Isaac Ayomide| CPE/2022/1118 | opeyemiisaac232-coder

Adeosun Emmanuel Tiwaoluwa| CPE/2023/1121 | adeosunemmanuel



## Overview

A Python OOP system for a Computer Engineering department that catalogues
laboratories and equipment, manages time-slot bookings, schedules preventive
and corrective maintenance, and produces utilisation analytics. A
`PortableEquipment` class demonstrates multiple inheritance (equipment that
can also be tracked by physical location).

## Project layout

```
lab_system/
  __init__.py        # public API
  exceptions.py       # BookingConflictError, EquipmentUnderMaintenanceError,
                       # UnauthorisedBookingError, LabCapacityError
  timeslot.py          # TimeSlot
  booking.py            # Booking, BookingStatus
  resources.py            # LabResource (ABC), Equipment, Laboratory,
                            # SoftwareLicence, TrackableMixin, PortableEquipment
  maintenance.py            # MaintenanceTask (ABC), Preventive/CorrectiveMaintenance
  booking_system.py          # BookingSystem (orchestrator + analytics)
tests/
  conftest.py
  test_lab_system.py          # 26 pytest cases
demo.py                        # live-demo script for the showcase
```

## Running

```bash
pip install pytest
python -m pytest tests/ -v
python demo.py
```

## OOP Concepts Demonstrated

| Week | Concept | Where it appears |
|------|---------|-------------------|
| 1 | Classes & Objects | `Laboratory`, `Equipment`, `Booking` etc. are clean classes with explicit constructors, and every class implements both `__str__` (human-readable) and `__repr__` (debug-oriented). |
| 2 | Encapsulation | `Equipment.serial_no` is a validated `@property` enforcing the `LAB-EQ-XXXX` regex; `Laboratory.capacity` and `SoftwareLicence.active_sessions`/`max_concurrent_users` are validated properties. Booking time slots are checked for non-overlap inside `LabResource.book()` / `Laboratory.book()`. Custom exceptions `BookingConflictError`, `EquipmentUnderMaintenanceError`, `UnauthorisedBookingError`, and `LabCapacityError` enforce invariants instead of silent failure. |
| 3 | Inheritance & ABCs | `LabResource(ABC)` defines the contract (`resource_category`, `is_available`, `book`) implemented by `Equipment`, `Laboratory`, and `SoftwareLicence`. `MaintenanceTask(ABC)` defines `execute()`, implemented by `PreventiveMaintenance` and `CorrectiveMaintenance`. `PortableEquipment(Equipment, TrackableMixin)` demonstrates multiple inheritance via a cooperative `__init__` chain (`super().__init__(**kwargs)` at every level). |
| 4 | Polymorphism & Duck Typing | `TimeSlot` implements `__lt__`/`__eq__` (via `@total_ordering`), `__contains__` (datetime-in-slot test), and `__add__` (merging adjacent slots). `Booking.__str__` renders a formatted calendar card. `BookingSystem.utilisation_report()` duck-types over any iterable of objects exposing `.confirmed_bookings()` rather than checking `isinstance`. |
| 5 | UML Class Diagram | See `docs/uml_diagram.png` (drawn by hand first, then digitised). Captures composition (`Laboratory` ◆ `Equipment`), aggregation (`Booking` ○ `LabResource`), and all other relationships with correct multiplicity. |

## Functional requirements coverage

| Req | Requirement | Implementation |
|-----|-------------|-----------------|
| 156 | Overlap detection | `LabResource.is_available(slot)` checks all `CONFIRMED` bookings; `TimeSlot.overlaps()` implements `start_A < end_B and end_A > start_B`. |
| 157 | Capacity enforcement | `Laboratory.book()` counts concurrent confirmed bookings and raises `LabCapacityError` at capacity. `SoftwareLicence` enforces `max_concurrent_users` the same way. |
| 158 | Maintenance lockout | Creating a `MaintenanceTask` calls `equipment.lock_for_maintenance(date)`, which blocks bookings for the entire day until `execute()` unlocks it. |
| 159 | Condition degradation | `Equipment._register_usage()` tracks cumulative confirmed hours; every 50 hours the condition steps down one level. Reaching `POOR` auto-creates a `CorrectiveMaintenance` task. |
| 160 | Utilisation rate | `BookingSystem.utilisation_rate()` = booked hours / available hours (Mon–Fri 07:00–22:00) × 100, over a date range. |
| 161 | Weekly report | `BookingSystem.weekly_report()` returns per-lab utilisation, equipment in POOR/OUT_OF_SERVICE, maintenance scheduled in the next 7 days, and the top 3 most-booked resources. |

## Test suite

`tests/test_lab_system.py` contains 26 pytest cases (exceeds the 20-minimum
requirement), grouped by week/requirement, covering ABC enforcement,
validated properties, multiple inheritance, rich comparisons, and all four
mandatory functional requirements.

## Design notes / deviations from the starter skeleton

- The starter `BookingConflictError` and `TimeSlot` skeleton were kept
  largely as-is; `TimeSlot` gained a `duration_hours` property used by
  utilisation analytics and condition degradation.
- `LabResource` declares an abstract `resource_category()` method purely to
  keep the base class non-instantiable while still providing concrete,
  reusable `is_available()`/`book()` logic that subclasses extend via
  `super()`.
- `Laboratory.book()` does not reuse `LabResource.book()`'s single-resource
  overlap check, since a lab legitimately accepts multiple *concurrent*
  bookings up to its capacity — capacity counting replaces overlap
  rejection for that one class.
