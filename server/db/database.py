import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import Base

DB_PATH = os.path.join(os.path.dirname(__file__), "tag_verify.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_database()


async def seed_database():
    """Seed the database with 50 sample tags if empty."""
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM tags"))
        count = result.scalar()
        if count and count > 0:
            return  # Already seeded

        from datetime import datetime
        from .models import Tag

        sample_tags = [
            # Unit 10 — Mechanical
            ("10-P-101A", "Centrifugal Pump - Feed Water A", "Mechanical", "Active"),
            ("10-P-101B", "Centrifugal Pump - Feed Water B", "Mechanical", "Active"),
            ("10-P-102A", "Booster Pump - Cooling Water A", "Mechanical", "Active"),
            ("10-P-102B", "Booster Pump - Cooling Water B", "Mechanical", "Void"),
            ("10-P-103",  "Chemical Dosing Pump", "Mechanical", "Active"),
            ("10-V-201",  "Feed Water Storage Vessel", "Mechanical", "Active"),
            ("10-V-202",  "Chemical Injection Pot", "Mechanical", "Active"),
            ("10-V-203",  "Condensate Collection Vessel", "Mechanical", "Void"),
            ("10-TK-101", "Fuel Oil Day Tank", "Mechanical", "Active"),
            ("10-TK-102", "Lube Oil Storage Tank", "Mechanical", "Active"),
            # Unit 20 — Heat Transfer
            ("20-E-301",  "Feed Water Preheater", "Mechanical", "Active"),
            ("20-E-302",  "Cooling Water Heat Exchanger", "Mechanical", "Active"),
            ("20-E-303",  "Lube Oil Cooler", "Mechanical", "Active"),
            ("20-HX-301", "Shell & Tube Heat Exchanger - Process Fluid", "Mechanical", "Active"),
            ("20-HX-302", "Plate Heat Exchanger - Cooling Water", "Mechanical", "Void"),
            # Unit 10 — Instrumentation (Flow)
            ("10-FT-1001", "Flow Transmitter - Feed Water Discharge", "Instrumentation", "Active"),
            ("10-FT-1002", "Flow Transmitter - Cooling Water Supply", "Instrumentation", "Active"),
            ("10-FT-1003", "Flow Transmitter - Fuel Gas Header", "Instrumentation", "Active"),
            ("10-FT-1004", "Flow Transmitter - Chemical Injection", "Instrumentation", "Active"),
            ("10-FT-1005", "Flow Transmitter - Condensate Return", "Instrumentation", "Active"),
            # Unit 10 — Instrumentation (Temperature)
            ("10-TT-1001", "Temperature Transmitter - Feed Water Inlet", "Instrumentation", "Active"),
            ("10-TT-1002", "Temperature Transmitter - Feed Water Outlet", "Instrumentation", "Active"),
            ("10-TT-1003", "Temperature Transmitter - Cooling Water", "Instrumentation", "Active"),
            ("10-TT-1004", "Temperature Transmitter - Lube Oil", "Instrumentation", "Void"),
            # Unit 10 — Instrumentation (Pressure)
            ("10-PT-1001", "Pressure Transmitter - Pump Discharge", "Instrumentation", "Active"),
            ("10-PT-1002", "Pressure Transmitter - Feed Header", "Instrumentation", "Active"),
            ("10-PT-1003", "Pressure Transmitter - Fuel Gas", "Instrumentation", "Active"),
            ("10-LT-1001", "Level Transmitter - Feed Water Vessel", "Instrumentation", "Active"),
            ("10-LT-1002", "Level Transmitter - Condensate Vessel", "Instrumentation", "Active"),
            ("10-LT-1003", "Level Transmitter - Chemical Tank", "Instrumentation", "Active"),
            # Unit 10 — Safety
            ("10-PSV-1001", "Pressure Safety Valve - Pump Discharge", "Mechanical", "Active"),
            ("10-PSV-1002", "Pressure Safety Valve - Feed Vessel", "Mechanical", "Active"),
            ("10-PSV-1003", "Pressure Safety Valve - Fuel Gas", "Mechanical", "Active"),
            ("10-PSV-1004", "Pressure Safety Valve - Chemical Pot", "Mechanical", "Active"),
            ("10-PSV-1004A", "Pressure Safety Valve - Chemical Pot A", "Mechanical", "Active"),
            ("10-PSV-1004B", "Pressure Safety Valve - Chemical Pot B", "Mechanical", "Void"),
            # Unit 20 — Valves
            ("20-XV-2001", "Shutdown Valve - Feed Water Inlet", "Instrumentation", "Active"),
            ("20-XV-2002", "Shutdown Valve - Cooling Water", "Instrumentation", "Active"),
            ("20-XV-2003", "Shutdown Valve - Fuel Gas Supply", "Instrumentation", "Active"),
            ("20-XV-2004", "Shutdown Valve - Condensate Outlet", "Instrumentation", "Void"),
            ("20-FCV-2001", "Flow Control Valve - Feed Water", "Instrumentation", "Active"),
            ("20-FCV-2002", "Flow Control Valve - Cooling Water Return", "Instrumentation", "Active"),
            ("20-PCV-2001", "Pressure Control Valve - Gas Header", "Instrumentation", "Active"),
            ("20-LCV-2001", "Level Control Valve - Vessel Outlet", "Instrumentation", "Active"),
            # Electrical
            ("10-MCC-101",  "Motor Control Centre - Unit 10 Main", "Electrical", "Active"),
            ("10-MTR-101A", "Electric Motor - Feed Pump A", "Electrical", "Active"),
            ("10-MTR-101B", "Electric Motor - Feed Pump B", "Electrical", "Active"),
            ("20-MTR-201",  "Electric Motor - Cooling Fan", "Electrical", "Active"),
            # Piping
            ("10-STR-101",  "Y-Strainer - Pump Suction", "Piping", "Active"),
            ("10-STR-102",  "Duplex Strainer - Fuel Oil", "Piping", "Active"),
        ]

        now = datetime.utcnow()
        for tag_number, description, discipline, status in sample_tags:
            tag = Tag(
                tag_number=tag_number,
                tag_description=description,
                discipline=discipline,
                status=status,
                created_at=now,
                updated_at=now,
                voided_at=now if status == "Void" else None,
                created_by="system",
            )
            session.add(tag)
        await session.commit()
