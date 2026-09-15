# -*- coding: utf-8 -*-
{
    "name": "Nepal Import LC Management",
    "version": "19.0.1.0.0",
    "summary": "Letter of Credit management for Nepal foreign imports",
    "description": """
Nepal Import LC Management
==========================
Manages the full Letter-of-Credit lifecycle the way Nepali commercial banks and Nepal Rastra Bank (NRB) practise it:

- LC master with parties (issuing/advising bank, beneficiary), commercial terms (Proforma Invoice, Incoterm), financials (cash margin, utilization) and the Bi.Bi.Ni / EXIM / customs-entry-point regulatory fields.
- A staged lifecycle: Draft, Applied, Issued (MT700), Shipped, Documents Presented, Paid/Accepted, Customs Cleared, Closed (with auto-expiry).
- A documentary checklist (PI, invoice, packing list, BL/AWB, COO, insurance, Pragyapan Patra, LC copy) generated per payment mode.
- One-click 'Create Landed Cost' that pre-attaches this LC's received shipments to a draft Inventory landed cost, ready for an accountant to add cost lines and validate.
- NRB import-payment thresholds (TT advance, DAP/DAA, mandatory-LC for large India imports) enforced on PO confirmation, configurable as system parameters.
""",
    "category": "Purchase",
    "author": "Innovax Solutions Pvt. Ltd.",
    "website": "https://www.innovaxsolutions.com.np",
    "license": "AGPL-3",
    "depends": ["purchase", "stock", "account", "stock_landed_costs"],
    "data": [
        "security/ir.model.access.csv",
        "security/lc_security.xml",
        "data/lc_data.xml",
        "data/customs_entry_points.xml",
        "data/lc_cron.xml",
        "views/customs_entry_point_views.xml",
        "views/lc_master_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/purchase_order_views.xml",
        "views/menu.xml",
        "wizard/lc_amendment_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
