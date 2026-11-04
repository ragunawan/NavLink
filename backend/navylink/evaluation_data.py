"""Human-authored synthetic relevance labels, intentionally independent of ranking."""
QUERIES = [
    ("Predict equipment failures from maintenance work orders and supply inventory", ["maint-01", "maint-02", "maint-03", "ready-01", "ready-02", "log-01"]),
    ("Budget execution dashboards", ["fin-01", "fin-02", "fin-08"]),
    ("Financial datasets", ["fin-03"]),
    ("Applications that automate acquisition reporting", ["acq-01", "acq-02", "acq-04"]),
    ("Cybersecurity analytics systems for vulnerability remediation", ["cyber-01", "cyber-02", "cyber-04"]),
    ("Forecast spare parts inventory shortages", ["log-01", "log-02"]),
    ("Find workforce staffing gaps and training qualifications", ["people-01", "people-02", "people-03", "people-04"]),
    ("Automate cleaning maintenance work orders", ["maint-04"]),
    ("Hull corrosion inspection and coating repair", ["maint-05"]),
    ("Coordinate exercise readiness assessment schedules", ["ready-04"]),
    ("Automate invoice matching procurement receipts", ["fin-04", "log-05"]),
    ("Optimize cargo transfer shipment routes", ["log-04"]),
    ("Analyze supplier lead time replenishment delays", ["log-07"]),
    ("Analyze administrative workload staffing capacity", ["people-07"]),
    ("Detect unusual network traffic in fabricated flow records", ["cyber-06"]),
]
SIMILAR_PAIRS = [("maint-01", "maint-02"), ("fin-01", "fin-02"), ("log-01", "log-02"), ("ready-01", "ready-02"), ("people-01", "people-02"), ("acq-01", "acq-02"), ("cyber-01", "cyber-02"), ("maint-01", "ready-01"), ("fin-01", "fin-03"), ("maint-01", "maint-03")]
UNRELATED_PAIRS = [("maint-01", "people-05"), ("fin-01", "cyber-06"), ("log-04", "people-04"), ("ready-04", "fin-04"), ("people-01", "cyber-02"), ("acq-01", "maint-05"), ("cyber-01", "log-06"), ("fin-05", "maint-07"), ("log-07", "ready-04"), ("people-07", "cyber-03")]
PROPOSALS = [
    {"description": "Build a predictive maintenance platform to forecast ship equipment failures and readiness from historical maintenance work orders and supply data.", "duplicates": ["maint-01", "maint-02", "ready-01", "ready-02"], "complementary": ["maint-03", "log-01", "log-03"]},
    {"description": "Build a financial dashboard to track budget execution obligations and expenditures across funding lines.", "duplicates": ["fin-01", "fin-02"], "complementary": ["fin-03"]},
    {"description": "Automate acquisition contract milestone reporting and procurement review submissions.", "duplicates": ["acq-01", "acq-02"], "complementary": ["acq-03", "acq-04"]},
    {"description": "Forecast personnel staffing gaps by matching workforce billet requirements to training qualifications.", "duplicates": ["people-01", "people-02"], "complementary": ["people-03", "people-04"]},
    {"description": "Design a marble sculpture exhibition featuring underwater portraits and coral art installations.", "duplicates": [], "complementary": []},
    {"description": "Prioritize cybersecurity vulnerabilities and threat exposure using asset scans and remediation logs.", "duplicates": ["cyber-01", "cyber-02"], "complementary": ["cyber-03"]},
    {"description": "Publish historical maintenance work orders and equipment failure records as a dataset.", "intended_solution": "Dataset", "datasets": ["Maintenance work orders"], "duplicates": [], "complementary": ["maint-03", "maint-01"]},
    {"description": "Publish fictional travel claim fixtures for later financial analytics experiments.", "intended_solution": "Dataset", "datasets": ["Synthetic travel claims"], "duplicates": [], "complementary": ["fin-05"]},
    {"description": "Share fictional contract milestone data for external visualization experiments.", "intended_solution": "Dataset", "datasets": ["Contract milestone fixtures"], "duplicates": [], "complementary": ["acq-03"]},
    {"description": "Build an image gallery for coral restoration photography and ceramic art installations.", "duplicates": [], "complementary": []},
]
