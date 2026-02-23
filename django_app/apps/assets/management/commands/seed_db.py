"""
Management command: seed_db
============================
Populates the database with:
  - Plant hierarchy (1 plant → 2 areas → 2 units each → systems)
  - Disciplines (Mechanical, Instrumentation, Electrical, Piping, Civil)
  - Tag classes (Pump, Vessel, Heat Exchanger, Valve, Transmitter, …)
  - Criticality levels (Safety-Critical SIL1/2/3, Production, Asset, Non-Critical)
  - 50 sample tags (same set as the original Streamlit app, but with full hierarchy)
  - Document types
  - A superuser (admin/admin) if none exists

Usage:
  python manage.py seed_db              # safe: won't duplicate
  python manage.py seed_db --flush      # drops all data first
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone


SAMPLE_TAGS = [
    # (tag_number, description, discipline_name, status, is_safety_critical, unit_number)
    ("10-P-101A",   "Centrifugal Pump - Feed Water A",              "Mechanical",      "Active", False, 10),
    ("10-P-101B",   "Centrifugal Pump - Feed Water B",              "Mechanical",      "Active", False, 10),
    ("10-P-102A",   "Booster Pump - Cooling Water A",               "Mechanical",      "Active", False, 10),
    ("10-P-102B",   "Booster Pump - Cooling Water B",               "Mechanical",      "Void",   False, 10),
    ("10-P-103",    "Chemical Dosing Pump",                         "Mechanical",      "Active", False, 10),
    ("10-V-201",    "Feed Water Storage Vessel",                    "Mechanical",      "Active", False, 10),
    ("10-V-202",    "Chemical Injection Pot",                       "Mechanical",      "Active", False, 10),
    ("10-V-203",    "Condensate Collection Vessel",                 "Mechanical",      "Void",   False, 10),
    ("10-TK-101",   "Fuel Oil Day Tank",                            "Mechanical",      "Active", False, 10),
    ("10-TK-102",   "Lube Oil Storage Tank",                        "Mechanical",      "Active", False, 10),
    ("20-E-301",    "Feed Water Preheater",                         "Mechanical",      "Active", False, 20),
    ("20-E-302",    "Cooling Water Heat Exchanger",                 "Mechanical",      "Active", False, 20),
    ("20-E-303",    "Lube Oil Cooler",                              "Mechanical",      "Active", False, 20),
    ("20-HX-301",   "Shell & Tube Heat Exchanger - Process Fluid",  "Mechanical",      "Active", False, 20),
    ("20-HX-302",   "Plate Heat Exchanger - Cooling Water",         "Mechanical",      "Void",   False, 20),
    ("10-FT-1001",  "Flow Transmitter - Feed Water Discharge",      "Instrumentation", "Active", False, 10),
    ("10-FT-1002",  "Flow Transmitter - Cooling Water Supply",      "Instrumentation", "Active", False, 10),
    ("10-FT-1003",  "Flow Transmitter - Fuel Gas Header",           "Instrumentation", "Active", False, 10),
    ("10-FT-1004",  "Flow Transmitter - Chemical Injection",        "Instrumentation", "Active", False, 10),
    ("10-FT-1005",  "Flow Transmitter - Condensate Return",         "Instrumentation", "Active", False, 10),
    ("10-TT-1001",  "Temperature Transmitter - Feed Water Inlet",   "Instrumentation", "Active", False, 10),
    ("10-TT-1002",  "Temperature Transmitter - Feed Water Outlet",  "Instrumentation", "Active", False, 10),
    ("10-TT-1003",  "Temperature Transmitter - Cooling Water",      "Instrumentation", "Active", False, 10),
    ("10-TT-1004",  "Temperature Transmitter - Lube Oil",           "Instrumentation", "Void",   False, 10),
    ("10-PT-1001",  "Pressure Transmitter - Pump Discharge",        "Instrumentation", "Active", False, 10),
    ("10-PT-1002",  "Pressure Transmitter - Feed Header",           "Instrumentation", "Active", False, 10),
    ("10-PT-1003",  "Pressure Transmitter - Fuel Gas",              "Instrumentation", "Active", False, 10),
    ("10-LT-1001",  "Level Transmitter - Feed Water Vessel",        "Instrumentation", "Active", False, 10),
    ("10-LT-1002",  "Level Transmitter - Condensate Vessel",        "Instrumentation", "Active", False, 10),
    ("10-LT-1003",  "Level Transmitter - Chemical Tank",            "Instrumentation", "Active", False, 10),
    ("10-PSV-1001", "Pressure Safety Valve - Pump Discharge",       "Mechanical",      "Active", True,  10),
    ("10-PSV-1002", "Pressure Safety Valve - Feed Vessel",          "Mechanical",      "Active", True,  10),
    ("10-PSV-1003", "Pressure Safety Valve - Fuel Gas",             "Mechanical",      "Active", True,  10),
    ("10-PSV-1004", "Pressure Safety Valve - Chemical Pot",         "Mechanical",      "Active", True,  10),
    ("10-PSV-1004A","Pressure Safety Valve - Chemical Pot A",       "Mechanical",      "Active", True,  10),
    ("10-PSV-1004B","Pressure Safety Valve - Chemical Pot B",       "Mechanical",      "Void",   True,  10),
    ("20-XV-2001",  "Shutdown Valve - Feed Water Inlet",            "Instrumentation", "Active", True,  20),
    ("20-XV-2002",  "Shutdown Valve - Cooling Water",               "Instrumentation", "Active", True,  20),
    ("20-XV-2003",  "Shutdown Valve - Fuel Gas Supply",             "Instrumentation", "Active", True,  20),
    ("20-XV-2004",  "Shutdown Valve - Condensate Outlet",           "Instrumentation", "Void",   True,  20),
    ("20-FCV-2001", "Flow Control Valve - Feed Water",              "Instrumentation", "Active", False, 20),
    ("20-FCV-2002", "Flow Control Valve - Cooling Water Return",    "Instrumentation", "Active", False, 20),
    ("20-PCV-2001", "Pressure Control Valve - Gas Header",          "Instrumentation", "Active", False, 20),
    ("20-LCV-2001", "Level Control Valve - Vessel Outlet",          "Instrumentation", "Active", False, 20),
    ("10-MCC-101",  "Motor Control Centre - Unit 10 Main",          "Electrical",      "Active", False, 10),
    ("10-MTR-101A", "Electric Motor - Feed Pump A",                 "Electrical",      "Active", False, 10),
    ("10-MTR-101B", "Electric Motor - Feed Pump B",                 "Electrical",      "Active", False, 10),
    ("20-MTR-201",  "Electric Motor - Cooling Fan",                 "Electrical",      "Active", False, 20),
    ("10-STR-101",  "Y-Strainer - Pump Suction",                    "Piping",          "Active", False, 10),
    ("10-STR-102",  "Duplex Strainer - Fuel Oil",                   "Piping",          "Active", False, 10),
]


class Command(BaseCommand):
    help = "Seed the database with sample data for development/testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete all existing data before seeding",
        )

    def handle(self, *args, **options):
        from apps.assets.models import (
            Plant, Area, Unit, System,
            Discipline, TagClass, CriticalityLevel,
            Tag, ImportBatch,
        )
        from apps.documents.models import DocumentType

        if options["flush"]:
            self.stdout.write("Flushing existing data…")
            Tag.objects.all().delete()
            Plant.objects.all().delete()
            Discipline.objects.all().delete()
            DocumentType.objects.all().delete()
            self.stdout.write(self.style.WARNING("Data flushed."))

        # ---- Superuser ----
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin")
            self.stdout.write(self.style.SUCCESS("Superuser admin/admin created."))

        # ---- Plant hierarchy ----
        plant, _ = Plant.objects.get_or_create(
            code="SITE-A",
            defaults={"name": "Onshore Gas Processing Plant — Site A", "country": "UK"},
        )
        area10, _ = Area.objects.get_or_create(
            plant=plant, code="AREA-10",
            defaults={"name": "Feed Preparation & Utilities"},
        )
        area20, _ = Area.objects.get_or_create(
            plant=plant, code="AREA-20",
            defaults={"name": "Heat Transfer & Compression"},
        )
        unit10, _ = Unit.objects.get_or_create(
            area=area10, number=10,
            defaults={"name": "Feed Water Treatment", "process_type": "Water Treatment"},
        )
        unit20, _ = Unit.objects.get_or_create(
            area=area20, number=20,
            defaults={"name": "Heat Exchange Unit", "process_type": "Heat Transfer"},
        )
        unit_map = {10: unit10, 20: unit20}

        System.objects.get_or_create(
            unit=unit10, code="10-SYS-001",
            defaults={"name": "Lube Oil System", "system_number": "SYS-001"},
        )
        System.objects.get_or_create(
            unit=unit10, code="10-SYS-002",
            defaults={"name": "Seal Gas System", "system_number": "SYS-002"},
        )

        # ---- Disciplines ----
        disciplines_data = [
            ("MECH", "Mechanical",      "M",  "#3B82F6"),
            ("INST", "Instrumentation", "I",  "#10B981"),
            ("ELEC", "Electrical",      "E",  "#F59E0B"),
            ("PIPE", "Piping",          "P",  "#8B5CF6"),
            ("CIVIL","Civil",           "C",  "#EF4444"),
        ]
        discipline_map = {}
        for code, name, abbrev, colour in disciplines_data:
            disc, _ = Discipline.objects.get_or_create(
                code=code,
                defaults={"name": name, "abbreviation": abbrev, "colour": colour},
            )
            discipline_map[name] = disc

        # ---- Tag Classes ----
        tag_classes = [
            ("P",   "Pump",           "MECH"),
            ("V",   "Vessel",         "MECH"),
            ("TK",  "Tank",           "MECH"),
            ("E",   "Heat Exchanger", "MECH"),
            ("HX",  "Heat Exchanger", "MECH"),
            ("PSV", "Safety Valve",   "MECH"),
            ("FT",  "Flow Transmitter",         "INST"),
            ("TT",  "Temperature Transmitter",  "INST"),
            ("PT",  "Pressure Transmitter",     "INST"),
            ("LT",  "Level Transmitter",        "INST"),
            ("XV",  "Shutdown Valve",           "INST"),
            ("FCV", "Flow Control Valve",       "INST"),
            ("PCV", "Pressure Control Valve",   "INST"),
            ("LCV", "Level Control Valve",      "INST"),
            ("MCC", "Motor Control Centre",     "ELEC"),
            ("MTR", "Electric Motor",           "ELEC"),
            ("STR", "Strainer",                 "PIPE"),
        ]
        for code, name, disc_code in tag_classes:
            disc = Discipline.objects.filter(code=disc_code).first()
            TagClass.objects.get_or_create(
                code=code, defaults={"name": name, "discipline": disc}
            )

        # ---- Criticality Levels ----
        criticality_data = [
            ("SIL3", "Safety Critical — SIL 3", "safety_sil3", "#DC2626", True, True),
            ("SIL2", "Safety Critical — SIL 2", "safety_sil2", "#EF4444", True, True),
            ("SIL1", "Safety Critical — SIL 1", "safety_sil1", "#F97316", True, True),
            ("PROD", "Production Critical",      "production",  "#F59E0B", True, False),
            ("ASSET","Asset Critical",            "asset",       "#EAB308", False, False),
            ("NC",   "Non-Critical",             "non_critical","#6B7280", False, False),
        ]
        criticality_map = {}
        for code, name, level, colour, rcm, sil in criticality_data:
            crit, _ = CriticalityLevel.objects.get_or_create(
                code=code,
                defaults={
                    "name": name, "level": level, "colour": colour,
                    "requires_rcm": rcm, "requires_sil_study": sil,
                },
            )
            criticality_map[code] = crit

        # ---- Document Types ----
        doc_types = [
            ("PID",  "Piping & Instrumentation Diagram",    True),
            ("PFD",  "Process Flow Diagram",                True),
            ("DS",   "Datasheet",                           False),
            ("EL",   "Equipment List",                      True),
            ("LL",   "Line List",                           True),
            ("IO",   "Instrument Index",                    True),
            ("SLD",  "Single Line Diagram",                 True),
            ("GA",   "General Arrangement Drawing",         False),
            ("CALC", "Engineering Calculation",             False),
            ("PROC", "Procedure",                           False),
        ]
        for code, name, verify in doc_types:
            DocumentType.objects.get_or_create(
                code=code, defaults={"name": name, "requires_tag_verification": verify}
            )

        # ---- Import Batch record for seed ----
        batch = ImportBatch.objects.create(
            batch_type="seed",
            filename="seed_db.py",
            status="processing",
            total_rows=len(SAMPLE_TAGS),
            started_at=timezone.now(),
        )

        # ---- Tags ----
        created = 0
        for row in SAMPLE_TAGS:
            tag_number, desc, disc_name, st, safety, unit_num = row
            if Tag.objects.filter(tag_number=tag_number).exists():
                continue
            disc = discipline_map.get(disc_name)
            unit = unit_map.get(unit_num)
            area = unit.area if unit else None
            criticality = criticality_map.get("SIL1" if safety else "NC")
            tag = Tag.objects.create(
                tag_number=tag_number,
                tag_description=desc,
                discipline=disc,
                status=st,
                plant=plant,
                area=area,
                unit=unit,
                criticality_level=criticality,
                is_safety_critical=safety,
                voided_at=timezone.now() if st == "Void" else None,
            )
            created += 1

        batch.created_count = created
        batch.skipped_count = len(SAMPLE_TAGS) - created
        batch.status = "completed"
        batch.completed_at = timezone.now()
        batch.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created} tags created, "
                f"{len(SAMPLE_TAGS) - created} already existed."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Plant hierarchy, disciplines, tag classes, criticality levels and document types seeded."
            )
        )
        self.stdout.write("")
        self.stdout.write("  Admin login: http://localhost:8000/admin/  →  admin / admin")
        self.stdout.write("  API root:    http://localhost:8000/api/v1/")
        self.stdout.write("  Dashboard:   http://localhost:8000/dashboard/")
