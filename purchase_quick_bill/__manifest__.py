{
    'name': 'Purchase Quick Vendor Bill',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'One-click draft vendor bill generation from Purchase Orders, based on received quantities',
    'description': """
Purchase Quick Vendor Bill
===========================

Odoo 19 removed the "Create Bill" button from the Purchase Order form
(billing now happens via "Upload Bill" or from the Accounting app).
This module restores an equivalent one-click shortcut directly on the PO.

Adds a "Generate Bill" button on confirmed Purchase Orders that creates a
draft vendor bill (account.move) directly from quantities that have been
received but not yet billed - regardless of each product's individual
invoicing policy setting (ordered vs. received quantities).

Key behavior
------------
* Available on any confirmed Purchase Order (no dependency on LC / import
  workflows) - works as a general-purpose shortcut.
* Only bills quantity actually received and not yet invoiced
  (qty_received - qty_invoiced, per line), so nothing is billed ahead of
  receipt even if a product is set to "ordered quantities" policy.
* The generated bill is always left in Draft state - the accountant
  reviews and posts it manually.
* If the PO is already fully billed, not yet confirmed, or nothing has
  been received yet, the button raises a clear validation error instead
  of silently doing nothing.
""",
    'author': 'Tshering Sherpa',
    'license': 'LGPL-3',
    'depends': ['purchase', 'account'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
