"""Entirely fictional fixtures. Stable IDs are the retrieval evaluation contract."""
import argparse
from datetime import date, timedelta

from sqlalchemy import delete, select

from .database import CatalogMigration, Datasource, Person, Project, Run, connect
from .catalog_records import save_record
from .registry import save_project
from .migrations import migrate_catalog
from .schemas import DatasourceInput, PersonInput, ProjectInput

SCENARIOS = {
    "maint": ("Maintenance", "Fictional Tidewater Sustainment Lab", [
        ("Keel Prognostics", "Forecast ship equipment failures and readiness using historical equipment failures, maintenance work orders and supply parts data.", "Model", "Equipment failure history;Maintenance work orders;Supply inventory", "Python;scikit-learn"),
        ("BearingWatch", "Predict ship machinery breakdowns from equipment failure history, maintenance logs and work orders to forecast readiness.", "Dashboard", "Equipment failure history;Maintenance work orders", "R;Shiny"),
        ("Dockyard Records Exchange", "Curate historical maintenance work orders and equipment failure records for predictive equipment maintenance experiments.", "Dataset", "Equipment failure history;Maintenance work orders", "SQLite;Parquet"),
        ("Work Order Bridge", "Automate cleaning and reconciliation of maintenance work orders between ship repair planning systems.", "Automation", "Maintenance work orders", "Python;SQL"),
        ("Corrosion Atlas", "Map corrosion inspection findings to prioritize hull coating repair and preservation schedules.", "Analytics product", "Hull inspection observations", "Python;GeoPackage"),
        ("Depot Capacity Planner", "Allocate workshop repair capacity and technician schedules for equipment maintenance backlogs.", "Application", "Depot capacity calendar", "TypeScript;SQLite"),
        ("Acoustic Health Kit", "Detect unusual equipment vibration and acoustic anomalies in ship machinery sensor readings.", "Software tool", "Machinery vibration samples", "Python;ONNX"),
        ("Legacy Repair Ledger", "Record equipment repair tickets and historical maintenance work orders in a retired desktop ledger.", "Application", "Maintenance work orders", "Java;CSV"),
    ]),
    "fin": ("Financial management", "Fictional Harbor Resource Office", [
        ("Budget Compass", "Track financial budget execution, obligations and expenditures to identify funding gaps before fiscal close.", "Dashboard", "Budget execution ledger;Obligation transactions", "Python;React"),
        ("Fiscal Lantern", "Visualize budget execution and spending obligations across funding lines and fiscal periods.", "Dashboard", "Budget execution ledger;Obligation transactions", "R;Shiny"),
        ("Obligation Data Cooperative", "Publish reconciled financial budget execution and obligation transaction datasets for spending analysis.", "Dataset", "Budget execution ledger;Obligation transactions", "Parquet;SQL"),
        ("Invoice Reconciler", "Automate financial invoice matching to procurement receipts and flag disbursement discrepancies.", "Automation", "Invoice reconciliation samples", "Python;SQLite"),
        ("Travel Spend Lens", "Analyze travel expenditure patterns and forecast administrative travel funding requirements.", "Analytics product", "Synthetic travel claims", "Python;DuckDB"),
        ("Cost Scenario Studio", "Model lifecycle cost alternatives for fictional equipment investments and financial planning.", "Model", "Lifecycle cost assumptions", "Julia;CSV"),
        ("Fiscal Close Checklist", "Coordinate financial fiscal close reporting tasks and evidence collection across resource teams.", "Application", "Fiscal close task records", "TypeScript;SQLite"),
        ("Legacy Funds Tracker", "Archive financial budget execution reports from a retired spreadsheet reporting workflow.", "Software tool", "Budget execution ledger", "VBA;CSV"),
    ]),
    "log": ("Logistics", "Fictional Bluewater Supply Collective", [
        ("Spare Horizon", "Forecast supply inventory and spare parts demand using equipment maintenance work orders and stock records.", "Model", "Supply inventory;Maintenance work orders", "Python;scikit-learn"),
        ("Stockroom Outlook", "Predict spare parts inventory shortages from supply demand history and maintenance consumption.", "Dashboard", "Supply inventory;Maintenance work orders", "R;Shiny"),
        ("Supply Inventory Commons", "Curate synthetic stock balances and spare parts supply data for logistics and equipment readiness analysis.", "Dataset", "Supply inventory", "Parquet;SQLite"),
        ("Cargo Route Weaver", "Optimize cargo transfer routes and shipment schedules between fictional supply locations.", "Software tool", "Fictional cargo movements", "Python;OR-Tools"),
        ("Receipt Robot", "Automate matching supply receipts to inventory deliveries and purchasing records.", "Automation", "Warehouse receipt samples", "Python;SQL"),
        ("Warehouse Slot Map", "Map stockroom storage slots and item locations to reduce warehouse picking effort.", "Application", "Warehouse slot locations", "TypeScript;SQLite"),
        ("Lead Time Observatory", "Analyze supplier lead time variation and inventory replenishment delays.", "Analytics product", "Supplier lead time samples", "Python;DuckDB"),
        ("Legacy Shipment Board", "Archive historical cargo shipment and supply delivery status reports.", "Dashboard", "Fictional cargo movements", "Java;CSV"),
    ]),
    "ready": ("Readiness", "Fictional Seaglass Mission Center", [
        ("Readiness Mosaic", "Forecast equipment readiness and availability by combining maintenance failures, work orders and supply inventory.", "Analytics product", "Equipment failure history;Maintenance work orders;Supply inventory", "Python;React"),
        ("Availability Prism", "Predict ship equipment availability from historical maintenance breakdowns and spare parts supply constraints.", "Model", "Equipment failure history;Supply inventory", "R;SQL"),
        ("Readiness Snapshot Archive", "Publish synthetic monthly equipment readiness summaries for trend analysis.", "Dataset", "Synthetic readiness snapshots", "Parquet;SQLite"),
        ("Exercise Planner", "Coordinate fictional exercise milestones and readiness assessment schedules.", "Application", "Exercise schedule fixtures", "TypeScript;SQLite"),
        ("Readiness Report Relay", "Automate readiness reporting from approved synthetic equipment status records.", "Automation", "Synthetic readiness snapshots", "Python;SQL"),
        ("Mission Gap Lens", "Visualize gaps between declared mission readiness goals and available synthetic capabilities.", "Dashboard", "Mission capability fixtures", "React;SQLite"),
        ("Scenario Stress Tester", "Evaluate equipment availability under fictional mission workload scenarios.", "Software tool", "Mission capability fixtures", "Python;NumPy"),
        ("Legacy Status Rollup", "Archive retired readiness dashboard reports and monthly equipment availability summaries.", "Dashboard", "Synthetic readiness snapshots", "VBA;CSV"),
    ]),
    "people": ("Personnel", "Fictional Mariner Workforce Studio", [
        ("Billet Beacon", "Forecast personnel staffing gaps using billet requirements, workforce assignments and training qualifications.", "Dashboard", "Synthetic billet roster;Training qualifications", "Python;React"),
        ("Manning Lens", "Predict workforce staffing shortages by matching personnel qualifications to billet requirements.", "Model", "Synthetic billet roster;Training qualifications", "R;SQL"),
        ("Qualifications Commons", "Curate fictional personnel training qualifications and skills records for workforce planning.", "Dataset", "Training qualifications", "Parquet;SQLite"),
        ("Training Reminder Relay", "Automate personnel training certification renewal reminders and qualification reporting.", "Automation", "Training qualifications", "Python;SQL"),
        ("Rotation Sketchpad", "Explore fictional workforce rotation scenarios and personnel assignment schedules.", "Application", "Synthetic billet roster", "TypeScript;SQLite"),
        ("Skills Neighbor", "Find personnel with related technical skills for voluntary knowledge exchange.", "Software tool", "Fictional skills directory", "Python;SQLite"),
        ("Workload Balance Lens", "Analyze administrative workload distribution and staffing capacity across fictional teams.", "Analytics product", "Team workload samples", "Python;DuckDB"),
        ("Legacy Training Binder", "Archive retired training certification reports for fictional workforce records.", "Application", "Training qualifications", "Java;CSV"),
    ]),
    "acq": ("Acquisition", "Fictional Meridian Procurement Lab", [
        ("Contract Report Relay", "Automate acquisition reporting by extracting procurement contract milestones and generating review submissions.", "Automation", "Contract milestone fixtures;Procurement actions", "Python;React"),
        ("Milestone Courier", "Automate procurement contract milestone reporting and acquisition review submissions.", "Application", "Contract milestone fixtures;Procurement actions", "TypeScript;SQLite"),
        ("Procurement Data Shelf", "Curate synthetic acquisition contract milestones and procurement action datasets for reporting.", "Dataset", "Contract milestone fixtures;Procurement actions", "Parquet;SQLite"),
        ("Review Packet Assembler", "Automate acquisition review packet assembly and evidence checklist validation.", "Software tool", "Acquisition review checklists", "Python;SQL"),
        ("Award Timeline Lens", "Visualize procurement contract award lead times and review bottlenecks.", "Dashboard", "Procurement actions", "React;SQLite"),
        ("Vendor Scenario Model", "Model fictional procurement supplier delivery risk from contract scenario assumptions.", "Model", "Supplier scenario fixtures", "Python;NumPy"),
        ("Requirements Thread", "Trace acquisition requirements to review decisions and procurement milestones.", "Analytics product", "Requirement decision fixtures", "Python;DuckDB"),
        ("Legacy Contract Workbook", "Archive retired procurement contract milestone and acquisition reporting workbooks.", "Application", "Contract milestone fixtures", "VBA;CSV"),
    ]),
    "cyber": ("Cybersecurity", "Fictional Breakwater Assurance Workshop", [
        ("Vulnerability Tide", "Prioritize cybersecurity vulnerabilities and threat exposure using synthetic asset scans and remediation logs.", "Analytics product", "Synthetic vulnerability scans;Remediation events", "Python;React"),
        ("Patch Harbor", "Rank cybersecurity vulnerability remediation priorities from asset scan findings and patch history.", "Dashboard", "Synthetic vulnerability scans;Remediation events", "R;Shiny"),
        ("Scan Fixture Commons", "Publish fabricated cybersecurity vulnerability scan datasets for security analytics experiments.", "Dataset", "Synthetic vulnerability scans", "Parquet;SQLite"),
        ("Remediation Relay", "Automate cybersecurity remediation reporting and patch evidence collection.", "Automation", "Remediation events", "Python;SQL"),
        ("Access Review Board", "Coordinate periodic application access reviews using fictional account entitlement records.", "Application", "Fictional account entitlements", "TypeScript;SQLite"),
        ("Network Anomaly Sandbox", "Detect unusual network traffic patterns in fabricated cybersecurity flow records.", "Model", "Fabricated network flows", "Python;scikit-learn"),
        ("Dependency Inventory Kit", "Inventory software dependencies and flag synthetic security advisories for application maintainers.", "Software tool", "Synthetic package inventory", "Python;JSON"),
        ("Legacy Scan Register", "Archive retired cybersecurity vulnerability scan reports and remediation records.", "Dashboard", "Synthetic vulnerability scans", "Java;CSV"),
    ]),
}


def fixtures():
    for prefix, (domain, org, rows) in SCENARIOS.items():
        for n, (name, mission, kind, datasets, tech) in enumerate(rows, 1):
            visibility = "group" if n == 7 else "internal" if n == 6 else "public"
            group = "finance-demo" if prefix == "fin" else "maintenance-demo"
            yield f"{prefix}-{n:02d}", ProjectInput(
                name=name, description=f"{mission} This fictional prototype supports discovery and cross-team evaluation using fabricated records only.",
                mission_problem=mission, project_type={"Software tool": "Software", "Analytics product": "Analytics Product"}.get(kind, kind), domain=domain,
                classification="UNCLASSIFIED", network_accessibility=["Other"],
                primary_poc_email=f"{prefix}.{n}@navylink.example" if n != 5 else None,
                datasource=datasets.split(";")[0],
                date_created=date(2026, 9, 1),
                organization=org if n % 2 else "Fictional Pelagic Digital Cooperative",
                status={1: "Operational", 2: "In Development", 3: "Operational", 4: "Seeking Collaborators", 5: "Concept", 6: "In Development", 7: "Seeking Collaborators", 8: "Retired"}[n],
                technical_summary=f"{tech.replace(';', ' and ')} implementation. {'Batch file exchange demonstrated on synthetic fixtures.' if n == 1 else 'Integration compatibility has not been evaluated.'}",
                contacts=[] if n == 5 else [{"name": f"{['Avery', 'Morgan', 'Riley', 'Casey'][n % 4]} {['Seabrook', 'Vale', 'Fenn', 'Marlowe'][len(prefix) % 4]}", "role": "Fictional project liaison", "method": f"{prefix}.{n}@navylink.example", "visibility": "internal" if n == 3 else "public"}],
                repository_url=f"https://code.navylink.example/{prefix}-{n:02d}", documentation_url=f"https://docs.navylink.example/{prefix}-{n:02d}",
                project_url=f"https://code.navylink.example/{prefix}-{n:02d}",
                access_instructions="Fictional demonstration: ask the listed liaison to confirm dataset availability, licensing and deployment compatibility. No access is granted by this listing.",
                visibility=visibility, allowed_groups=[group] if visibility == "group" else [],
                technologies=tech.split(";"), datasets=[{"name": d, "description": f"Fabricated {d.lower()} for offline evaluation; not operational data."} for d in datasets.split(";")],
                intended_users=[f"Fictional {domain.lower()} analysts", "Fictional capability planners"],
                use_cases=[mission], last_updated=date(2026, 11, 3) - timedelta(days=(n - 1) * 3),
                license="Synthetic example terms; verify reuse permission" if n == 1 else None,
                deployment="Local laptop prototype" if n in (1, 3) else None,
                integration="CSV / Parquet batch import; schema validation required" if n == 1 else None,
            )


def seed(session, reset=False):
    migrate_catalog(session)
    if reset:
        session.execute(delete(Run))
        session.execute(delete(Project))
        session.execute(delete(Person))
        session.execute(delete(Datasource))
        session.execute(delete(CatalogMigration))
        session.connection().exec_driver_sql("DELETE FROM project_fts")
    if session.scalar(select(Project.id).limit(1)):
        bootstrap_records(session)
        return 0
    count = 0
    for project_id, payload in fixtures():
        save_project(session, project_id, payload)
        count += 1
    bootstrap_records(session)
    session.commit()
    return count


def bootstrap_records(session):
    """Derive registry entries from existing metadata without rewriting project documents."""
    migration = "2026-11-personnel-datasources"
    if session.get(CatalogMigration, migration):
        return
    rows = sorted(session.scalars(select(Project)), key=lambda p: {"public": 0, "internal": 1, "group": 2}[p.visibility])
    for project in rows:
        data = project.payload
        for contact in data.get("contacts", []):
            scope = project.visibility if project.visibility != "public" else contact["visibility"]
            if contact["visibility"] == "group":
                scope = "group"
            elif contact["visibility"] == "internal" and scope == "public":
                scope = "internal"
            try:
                person = PersonInput(email=contact["method"], full_name=contact["name"], organization=data["organization"],
                                     job_title=contact.get("role") or "Not provided", visibility=scope,
                                     allowed_groups=data["allowed_groups"] if scope == "group" else [])
            except ValueError:
                continue  # Non-email approved contact methods remain available on the project.
            if session.get(Person, person.email) is None:
                save_record(session, Person, person.email, person)
        for dataset in data.get("datasets", []):
            if session.get(Datasource, dataset["name"]) is None:
                source = DatasourceInput(name=dataset["name"], description=dataset["description"] or "Description not provided in the existing catalog.",
                                         domain=data["domain"], organization=data["organization"], visibility=project.visibility,
                                         allowed_groups=data["allowed_groups"] if project.visibility == "group" else [])
                save_record(session, Datasource, source.name, source)
    session.add(CatalogMigration(name=migration))
    session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Replace demo records and workflow history")
    args = parser.parse_args()
    _, factory = connect()
    with factory() as session:
        print(f"Seeded {seed(session, args.reset)} fictional projects")


if __name__ == "__main__":
    main()
