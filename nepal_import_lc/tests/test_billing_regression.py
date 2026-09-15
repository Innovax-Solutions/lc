# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestBillingRegression(AccountTestInvoicingCommon):
    """Guard the regular (non-import) purchase/billing flow against the
    account.move and purchase.order overrides this module installs."""

    def test_plain_vendor_bill_posts_without_lc(self):
        bill = self.init_invoice(
            "in_invoice", partner=self.partner_a, products=self.product_a, post=False
        )
        self.assertFalse(bill.lc_id, "A plain vendor bill must not auto-acquire an LC")
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        self.assertFalse(bill.lc_id)

    def test_customer_invoice_unaffected(self):
        inv = self.init_invoice(
            "out_invoice", partner=self.partner_a, products=self.product_a, post=False
        )
        inv.action_post()
        self.assertEqual(inv.state, "posted")
        self.assertFalse(inv.lc_id)

    def test_plain_po_confirm_without_import_type(self):
        po = self.env["purchase.order"].create({
            "partner_id": self.partner_a.id,
            "order_line": [(0, 0, {
                "product_id": self.product_a.id,
                "product_qty": 3.0,
                "price_unit": 100.0,
            })],
        })
        po.button_confirm()
        self.assertEqual(po.state, "purchase")
        self.assertFalse(po.import_transaction_type)
        self.assertFalse(po.lc_id)
