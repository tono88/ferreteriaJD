# Árbol de archivos

```text
ferreteria_pos_transfer_request/
├── __init__.py
├── __manifest__.py
├── CHANGELOG.md
├── README.md
├── data/
│   ├── sequence.xml
│   └── stock_location.xml
├── demo/
│   └── demo_data.xml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── FILE_TREE.md
│   ├── INSTALLATION.md
│   ├── KNOWN_RISKS.md
│   ├── REFERENCE_ANALYSIS.md
│   ├── TEST_DATA.md
│   ├── TEST_PLAN.md
│   └── VALIDATION_REPORT.md
├── migrations/
│   ├── 18.0.2.2.0/
│   │   └── post-migrate.py
│   └── 18.0.2.3.0/
│       └── post-migrate.py
├── models/
│   ├── __init__.py
│   ├── common.py
│   ├── pos_transfer_request.py
│   ├── res_users.py
│   ├── stock_picking.py
│   ├── transfer_incident.py
│   ├── transfer_request.py
│   └── transfer_user_permission.py
├── security/
│   ├── ir.model.access.csv
│   └── transfer_request_security.xml
├── static/
│   └── src/
│       ├── js/
│       │   ├── transfer_request_button.js
│       │   └── transfer_request_popup.js
│       ├── scss/
│       │   └── transfer_request.scss
│       └── xml/
│           ├── transfer_request_button.xml
│           └── transfer_request_popup.xml
├── tests/
│   ├── __init__.py
│   └── test_transfer_request.py
└── views/
    ├── menus.xml
    ├── res_users_views.xml
    ├── stock_picking_views.xml
    ├── transfer_incident_views.xml
    ├── transfer_request_views.xml
    └── transfer_user_permission_views.xml
```
