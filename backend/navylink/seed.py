"""Entirely fictional fixtures. Stable IDs are the retrieval evaluation contract."""
import argparse
from datetime import date, timedelta

from sqlalchemy import delete, select

from .database import Project, Run, connect
from .registry import save_project
from .schemas import ProjectInput

SCENARIOS = {
    "maint": ("Maintenance", "Fictional Tidewater Sustainment Lab", [
        ("Keel Prognostics", "Forecast ship equipment failures and readiness using historical equipment failures, maintenance work orders and supply parts data.", "Model", ["failure", "forecast", "equipment", "maintenance", "readiness"], "Equipment failure history;Maintenance work orders;Supply inventory", "Python;scikit-learn"),
        ("BearingWatch", "Predict ship machinery breakdowns from equipment failure history, maintenance logs and work orders to forecast readiness.", "Dashboard", ["failure", "forecast", "equipment", "maintenance", "readiness"], "Equipment failure history;Maintenance work orders", "R;Shiny"),
        ("Dockyard Records Exchange", "Curate historical maintenance work orders and equipment failure records for predictive equipment maintenance experiments.", "Dataset", ["equipment", "failure", "maintenance", "dataset"], "Equipment failure history;Maintenance work orders", "SQLite;Parquet"),
        ("Work Order Bridge", "Automate cleaning and reconciliation of maintenance work orders between ship repair planning systems.", "Automation", ["maintenance", "workorder", "automation"], "Maintenance work orders", "Python;SQL"),
        ("Corrosion Atlas", "Map corrosion inspection findings to prioritize hull coating repair and preservation schedules.", "Analytics product", ["corrosion", "inspection", "repair"], "Hull inspection observations", "Python;GeoPackage"),
        ("Depot Capacity Planner", "Allocate workshop repair capacity and technician schedules for equipment maintenance backlogs.", "Application", ["maintenance", "capacity", "scheduling"], "Depot capacity calendar", "TypeScript;SQLite"),
        ("Acoustic Health Kit", "Detect unusual equipment vibration and acoustic anomalies in ship machinery sensor readings.", "Software tool", ["equipment", "anomaly", "sensor"], "Machinery vibration samples", "Python;ONNX"),
        ("Legacy Repair Ledger", "Record equipment repair tickets and historical maintenance work orders in a retired desktop ledger.", "Application", ["maintenance", "workorder", "history"], "Maintenance work orders", "Java;CSV"),
    ]),
    "fin": ("Financial management", "Fictional Harbor Resource Office", [
        ("Budget Compass", "Track financial budget execution, obligations and expenditures to identify funding gaps before fiscal close.", "Dashboard", ["finance", "execution", "budget", "dashboard"], "Budget execution ledger;Obligation transactions", "Python;React"),
        ("Fiscal Lantern", "Visualize budget execution and spending obligations across funding lines and fiscal periods.", "Dashboard", ["finance", "execution", "budget", "dashboard"], "Budget execution ledger;Obligation transactions", "R;Shiny"),
        ("Obligation Data Cooperative", "Publish reconciled financial budget execution and obligation transaction datasets for spending analysis.", "Dataset", ["finance", "execution", "dataset"], "Budget execution ledger;Obligation transactions", "Parquet;SQL"),
        ("Invoice Reconciler", "Automate financial invoice matching to procurement receipts and flag disbursement discrepancies.", "Automation", ["finance", "invoice", "automation"], "Invoice reconciliation samples", "Python;SQLite"),
        ("Travel Spend Lens", "Analyze travel expenditure patterns and forecast administrative travel funding requirements.", "Analytics product", ["finance", "travel", "forecast"], "Synthetic travel claims", "Python;DuckDB"),
        ("Cost Scenario Studio", "Model lifecycle cost alternatives for fictional equipment investments and financial planning.", "Model", ["finance", "cost", "scenario"], "Lifecycle cost assumptions", "Julia;CSV"),
        ("Fiscal Close Checklist", "Coordinate financial fiscal close reporting tasks and evidence collection across resource teams.", "Application", ["finance", "reporting", "workflow"], "Fiscal close task records", "TypeScript;SQLite"),
        ("Legacy Funds Tracker", "Archive financial budget execution reports from a retired spreadsheet reporting workflow.", "Software tool", ["finance", "execution", "reporting"], "Budget execution ledger", "VBA;CSV"),
    ]),
    "log": ("Logistics", "Fictional Bluewater Supply Collective", [
        ("Spare Horizon", "Forecast supply inventory and spare parts demand using equipment maintenance work orders and stock records.", "Model", ["logistics", "forecast", "maintenance", "equipment"], "Supply inventory;Maintenance work orders", "Python;scikit-learn"),
        ("Stockroom Outlook", "Predict spare parts inventory shortages from supply demand history and maintenance consumption.", "Dashboard", ["logistics", "forecast", "maintenance"], "Supply inventory;Maintenance work orders", "R;Shiny"),
        ("Supply Inventory Commons", "Curate synthetic stock balances and spare parts supply data for logistics and equipment readiness analysis.", "Dataset", ["logistics", "equipment", "readiness", "dataset"], "Supply inventory", "Parquet;SQLite"),
        ("Cargo Route Weaver", "Optimize cargo transfer routes and shipment schedules between fictional supply locations.", "Software tool", ["logistics", "routing", "shipment"], "Fictional cargo movements", "Python;OR-Tools"),
        ("Receipt Robot", "Automate matching supply receipts to inventory deliveries and purchasing records.", "Automation", ["logistics", "automation", "receipts"], "Warehouse receipt samples", "Python;SQL"),
        ("Warehouse Slot Map", "Map stockroom storage slots and item locations to reduce warehouse picking effort.", "Application", ["logistics", "warehouse", "storage"], "Warehouse slot locations", "TypeScript;SQLite"),
        ("Lead Time Observatory", "Analyze supplier lead time variation and inventory replenishment delays.", "Analytics product", ["logistics", "supplier", "delay"], "Supplier lead time samples", "Python;DuckDB"),
        ("Legacy Shipment Board", "Archive historical cargo shipment and supply delivery status reports.", "Dashboard", ["logistics", "shipment", "history"], "Fictional cargo movements", "Java;CSV"),
    ]),
    "ready": ("Readiness", "Fictional Seaglass Mission Center", [
        ("Readiness Mosaic", "Forecast equipment readiness and availability by combining maintenance failures, work orders and supply inventory.", "Analytics product", ["readiness", "forecast", "equipment", "maintenance", "failure"], "Equipment failure history;Maintenance work orders;Supply inventory", "Python;React"),
        ("Availability Prism", "Predict ship equipment availability from historical maintenance breakdowns and spare parts supply constraints.", "Model", ["readiness", "forecast", "equipment", "maintenance", "failure"], "Equipment failure history;Supply inventory", "R;SQL"),
        ("Readiness Snapshot Archive", "Publish synthetic monthly equipment readiness summaries for trend analysis.", "Dataset", ["readiness", "equipment", "dataset"], "Synthetic readiness snapshots", "Parquet;SQLite"),
        ("Exercise Planner", "Coordinate fictional exercise milestones and readiness assessment schedules.", "Application", ["readiness", "exercise", "scheduling"], "Exercise schedule fixtures", "TypeScript;SQLite"),
        ("Readiness Report Relay", "Automate readiness reporting from approved synthetic equipment status records.", "Automation", ["readiness", "reporting", "automation"], "Synthetic readiness snapshots", "Python;SQL"),
        ("Mission Gap Lens", "Visualize gaps between declared mission readiness goals and available synthetic capabilities.", "Dashboard", ["readiness", "gap", "capability"], "Mission capability fixtures", "React;SQLite"),
        ("Scenario Stress Tester", "Evaluate equipment availability under fictional mission workload scenarios.", "Software tool", ["readiness", "equipment", "scenario"], "Mission capability fixtures", "Python;NumPy"),
        ("Legacy Status Rollup", "Archive retired readiness dashboard reports and monthly equipment availability summaries.", "Dashboard", ["readiness", "equipment", "history"], "Synthetic readiness snapshots", "VBA;CSV"),
    ]),
    "people": ("Personnel", "Fictional Mariner Workforce Studio", [
        ("Billet Beacon", "Forecast personnel staffing gaps using billet requirements, workforce assignments and training qualifications.", "Dashboard", ["personnel", "forecast", "training"], "Synthetic billet roster;Training qualifications", "Python;React"),
        ("Manning Lens", "Predict workforce staffing shortages by matching personnel qualifications to billet requirements.", "Model", ["personnel", "forecast", "training"], "Synthetic billet roster;Training qualifications", "R;SQL"),
        ("Qualifications Commons", "Curate fictional personnel training qualifications and skills records for workforce planning.", "Dataset", ["personnel", "training", "dataset"], "Training qualifications", "Parquet;SQLite"),
        ("Training Reminder Relay", "Automate personnel training certification renewal reminders and qualification reporting.", "Automation", ["personnel", "training", "automation"], "Training qualifications", "Python;SQL"),
        ("Rotation Sketchpad", "Explore fictional workforce rotation scenarios and personnel assignment schedules.", "Application", ["personnel", "rotation", "scheduling"], "Synthetic billet roster", "TypeScript;SQLite"),
        ("Skills Neighbor", "Find personnel with related technical skills for voluntary knowledge exchange.", "Software tool", ["personnel", "training", "networking"], "Fictional skills directory", "Python;SQLite"),
        ("Workload Balance Lens", "Analyze administrative workload distribution and staffing capacity across fictional teams.", "Analytics product", ["personnel", "capacity", "workload"], "Team workload samples", "Python;DuckDB"),
        ("Legacy Training Binder", "Archive retired training certification reports for fictional workforce records.", "Application", ["personnel", "training", "history"], "Training qualifications", "Java;CSV"),
    ]),
    "acq": ("Acquisition", "Fictional Meridian Procurement Lab", [
        ("Contract Report Relay", "Automate acquisition reporting by extracting procurement contract milestones and generating review submissions.", "Automation", ["acquisition", "automation", "reporting"], "Contract milestone fixtures;Procurement actions", "Python;React"),
        ("Milestone Courier", "Automate procurement contract milestone reporting and acquisition review submissions.", "Application", ["acquisition", "automation", "reporting"], "Contract milestone fixtures;Procurement actions", "TypeScript;SQLite"),
        ("Procurement Data Shelf", "Curate synthetic acquisition contract milestones and procurement action datasets for reporting.", "Dataset", ["acquisition", "reporting", "dataset"], "Contract milestone fixtures;Procurement actions", "Parquet;SQLite"),
        ("Review Packet Assembler", "Automate acquisition review packet assembly and evidence checklist validation.", "Software tool", ["acquisition", "automation", "review"], "Acquisition review checklists", "Python;SQL"),
        ("Award Timeline Lens", "Visualize procurement contract award lead times and review bottlenecks.", "Dashboard", ["acquisition", "timeline", "delay"], "Procurement actions", "React;SQLite"),
        ("Vendor Scenario Model", "Model fictional procurement supplier delivery risk from contract scenario assumptions.", "Model", ["acquisition", "supplier", "scenario"], "Supplier scenario fixtures", "Python;NumPy"),
        ("Requirements Thread", "Trace acquisition requirements to review decisions and procurement milestones.", "Analytics product", ["acquisition", "requirements", "traceability"], "Requirement decision fixtures", "Python;DuckDB"),
        ("Legacy Contract Workbook", "Archive retired procurement contract milestone and acquisition reporting workbooks.", "Application", ["acquisition", "reporting", "history"], "Contract milestone fixtures", "VBA;CSV"),
    ]),
    "cyber": ("Cybersecurity", "Fictional Breakwater Assurance Workshop", [
        ("Vulnerability Tide", "Prioritize cybersecurity vulnerabilities and threat exposure using synthetic asset scans and remediation logs.", "Analytics product", ["cybersecurity", "vulnerability", "remediation"], "Synthetic vulnerability scans;Remediation events", "Python;React"),
        ("Patch Harbor", "Rank cybersecurity vulnerability remediation priorities from asset scan findings and patch history.", "Dashboard", ["cybersecurity", "vulnerability", "remediation"], "Synthetic vulnerability scans;Remediation events", "R;Shiny"),
        ("Scan Fixture Commons", "Publish fabricated cybersecurity vulnerability scan datasets for security analytics experiments.", "Dataset", ["cybersecurity", "dataset", "vulnerability"], "Synthetic vulnerability scans", "Parquet;SQLite"),
        ("Remediation Relay", "Automate cybersecurity remediation reporting and patch evidence collection.", "Automation", ["cybersecurity", "automation", "reporting"], "Remediation events", "Python;SQL"),
        ("Access Review Board", "Coordinate periodic application access reviews using fictional account entitlement records.", "Application", ["cybersecurity", "access", "review"], "Fictional account entitlements", "TypeScript;SQLite"),
        ("Network Anomaly Sandbox", "Detect unusual network traffic patterns in fabricated cybersecurity flow records.", "Model", ["cybersecurity", "anomaly", "network"], "Fabricated network flows", "Python;scikit-learn"),
        ("Dependency Inventory Kit", "Inventory software dependencies and flag synthetic security advisories for application maintainers.", "Software tool", ["cybersecurity", "dependencies", "software"], "Synthetic package inventory", "Python;JSON"),
        ("Legacy Scan Register", "Archive retired cybersecurity vulnerability scan reports and remediation records.", "Dashboard", ["cybersecurity", "vulnerability", "history"], "Synthetic vulnerability scans", "Java;CSV"),
    ]),
}


def fixtures():
    for prefix, (domain, org, rows) in SCENARIOS.items():
        for n, (name, mission, kind, tags, datasets, tech) in enumerate(rows, 1):
            visibility = "group" if n == 7 else "internal" if n == 6 else "public"
            group = "finance-demo" if prefix == "fin" else "maintenance-demo"
            yield f"{prefix}-{n:02d}", ProjectInput(
                name=name, description=f"{mission} This fictional prototype supports discovery and cross-team evaluation using fabricated records only.",
                mission_problem=mission, project_type=kind, domain=domain,
                organization=org if n % 2 else "Fictional Pelagic Digital Cooperative",
                status={1: "Operational", 2: "In Development", 3: "Operational", 4: "Seeking Collaborators", 5: "Concept", 6: "In Development", 7: "Seeking Collaborators", 8: "Retired"}[n],
                technical_summary=f"{tech.replace(';', ' and ')} implementation. {'Batch file exchange demonstrated on synthetic fixtures.' if n == 1 else 'Integration compatibility has not been evaluated.'}",
                contacts=[] if n == 5 else [{"name": f"{['Avery', 'Morgan', 'Riley', 'Casey'][n % 4]} {['Seabrook', 'Vale', 'Fenn', 'Marlowe'][len(prefix) % 4]}", "role": "Fictional project liaison", "method": f"{prefix}.{n}@navylink.example", "visibility": "internal" if n == 3 else "public"}],
                repository_url=f"https://code.navylink.example/{prefix}-{n:02d}", documentation_url=f"https://docs.navylink.example/{prefix}-{n:02d}",
                access_instructions="Fictional demonstration: ask the listed liaison to confirm dataset availability, licensing and deployment compatibility. No access is granted by this listing.",
                visibility=visibility, allowed_groups=[group] if visibility == "group" else [],
                technologies=tech.split(";"), tags=tags, datasets=[{"name": d, "description": f"Fabricated {d.lower()} for offline evaluation; not operational data."} for d in datasets.split(";")],
                intended_users=[f"Fictional {domain.lower()} analysts", "Fictional capability planners"],
                use_cases=[mission], last_updated=date(2026, 11, 3) - timedelta(days=(n - 1) * 3),
                license="Synthetic example terms; verify reuse permission" if n == 1 else None,
                deployment="Local laptop prototype" if n in (1, 3) else None,
                integration="CSV / Parquet batch import; schema validation required" if n == 1 else None,
            )


def seed(session, reset=False):
    if reset:
        session.execute(delete(Run))
        session.execute(delete(Project))
        session.connection().exec_driver_sql("DELETE FROM project_fts")
    if session.scalar(select(Project.id).limit(1)):
        return 0
    count = 0
    for project_id, payload in fixtures():
        save_project(session, project_id, payload)
        count += 1
    session.commit()
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Replace demo records and workflow history")
    args = parser.parse_args()
    _, factory = connect()
    with factory() as session:
        print(f"Seeded {seed(session, args.reset)} fictional projects")


if __name__ == "__main__":
    main()
