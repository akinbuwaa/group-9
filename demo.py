"""Live demo script for the project showcase.
Run: python demo.py
Walks through the four mandatory functional requirements end-to-end.
"""

from datetime import datetime, date, timedelta

from lab_system import (
    BookingConflictError, EquipmentUnderMaintenanceError, LabCapacityError,
    TimeSlot, Equipment, Laboratory, PortableEquipment, Condition,
    CorrectiveMaintenance, BookingSystem,
)


def hr(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    system = BookingSystem("Computer Engineering Department")

    lab = Laboratory("LAB-EMB", "Embedded Systems Lab", "ESL01", "Embedded Systems Lab", capacity=2)
    scope = Equipment("EQ-SCOPE-1", "Oscilloscope", "LAB-EQ-0001", "Tektronix", "TBS1052B")
    lab.add_equipment(scope)
    system.add_laboratory(lab)

    pe = PortableEquipment("EQ-LA-1", "Logic Analyzer", "LAB-EQ-0099", "Saleae", "Pro8",
                            initial_lab_code="ESL01")
    system.add_resource(pe)

    monday = datetime(2026, 6, 22)

    hr("Req 156: Overlap detection")
    system.book("EQ-SCOPE-1", TimeSlot(monday.replace(hour=8), monday.replace(hour=10)), "alice")
    try:
        system.book("EQ-SCOPE-1", TimeSlot(monday.replace(hour=9), monday.replace(hour=11)), "bob")
    except BookingConflictError as e:
        print("Blocked as expected:", e)

    hr("Req 157: Capacity enforcement (lab capacity=2)")
    system.book("LAB-EMB", TimeSlot(monday.replace(hour=8), monday.replace(hour=10)), "carol")
    system.book("LAB-EMB", TimeSlot(monday.replace(hour=8), monday.replace(hour=10)), "dave")
    try:
        system.book("LAB-EMB", TimeSlot(monday.replace(hour=8), monday.replace(hour=10)), "erin")
    except LabCapacityError as e:
        print("Blocked as expected:", e)

    hr("Req 158: Maintenance lockout")
    task = CorrectiveMaintenance(pe, scheduled_date=monday.date(), reason="Calibration drift")
    try:
        system.book("EQ-LA-1", TimeSlot(monday.replace(hour=14), monday.replace(hour=16)), "frank")
    except EquipmentUnderMaintenanceError as e:
        print("Blocked as expected:", e)
    report = task.execute()
    print("Maintenance complete:", report)

    hr("Req 159: Condition degradation")
    eq = Equipment("EQ-CNC-1", "CNC Router", "LAB-EQ-0040", "Shapeoko", "Pro")
    print("Initial condition:", eq.condition.value)
    day = 0
    hours = 0
    while hours < 153:  # cross 3 degradation thresholds -> POOR
        eq.book(TimeSlot(monday.replace(hour=7) + timedelta(days=day),
                          monday.replace(hour=21) + timedelta(days=day)), f"student{day}")
        hours += 14
        day += 1
        if eq.condition == Condition.POOR:
            break
    print("Condition after heavy use:", eq.condition.value)

    hr("Req 160/161: Utilisation rate & weekly report")
    rate = system.utilisation_rate("EQ-SCOPE-1", monday.date(), monday.date())
    print(f"EQ-SCOPE-1 utilisation on {monday.date()}: {rate}%")
    report = system.weekly_report(as_of=monday.date())
    for k, v in report.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
