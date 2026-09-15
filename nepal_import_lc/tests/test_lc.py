# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestNepalImportLc(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env["res.partner"].create({
            "name": "Foreign Supplier Ltd",
            "is_lc_mandatory": True,
        })
        cls.usd = cls.env.ref("base.USD")

    def _new_lc(self, **vals):
        base = {
            "partner_id": self.supplier.id,
            "payment_mode": "lc",
            "lc_type": "sight",
            "currency_id": self.usd.id,
            "lc_value": 100000.0,
            "date_expiry": fields.Date.add(fields.Date.today(), days=90),
            "issuing_bank_id": self.env["res.bank"].create({"name": "Test Bank"}).id,
        }
        base.update(vals)
        return self.env["nepal.lc.master"].create(base)

    def test_sequence_and_documents(self):
        lc = self._new_lc()
        self.assertNotEqual(lc.name, "New", "LC number should be auto-assigned")
        self.assertTrue(lc.name.startswith("LC/"), "LC number should use the LC/ sequence")
        # LC payment mode generates the full documentary checklist incl. LC copy + COO.
        doc_types = set(lc.document_ids.mapped("doc_type"))
        self.assertIn("pragyapan_patra", doc_types)
        self.assertIn("lc_copy", doc_types)
        self.assertIn("coo", doc_types)

    def test_margin_amount_compute(self):
        lc = self._new_lc(margin_rate=25.0)
        self.assertAlmostEqual(lc.margin_amount, 25000.0)

    def test_bci_required(self):
        lc = self._new_lc(lc_value=60000.0)  # sight USD >= 50k
        self.assertTrue(lc.bci_required)
        lc2 = self._new_lc(lc_value=40000.0)
        self.assertFalse(lc2.bci_required)

    def test_lifecycle_flow(self):
        lc = self._new_lc(margin_rate=10.0)
        lc.action_apply()
        self.assertEqual(lc.state, "applied")
        lc.action_issue()
        self.assertEqual(lc.state, "issued")
        lc.action_ship()
        lc.action_present_documents()
        lc.action_pay()
        lc.action_clear_customs()
        lc.action_close()
        self.assertEqual(lc.state, "closed")

    def test_amendment_updates_lc(self):
        lc = self._new_lc(margin_rate=10.0)
        lc.action_apply()
        lc.action_issue()
        new_expiry = fields.Date.add(fields.Date.today(), days=180)
        self.env["nepal.lc.amendment"].create({
            "lc_id": lc.id,
            "new_value": 120000.0,
            "new_expiry": new_expiry,
        })
        self.assertEqual(lc.lc_value, 120000.0)
        self.assertEqual(lc.date_expiry, new_expiry)
        self.assertEqual(lc.amendment_ids[0].amendment_no, 1)

    def test_amendment_blocked_on_draft(self):
        lc = self._new_lc()
        with self.assertRaises(UserError):
            self.env["nepal.lc.amendment"].create({"lc_id": lc.id, "new_value": 50000.0})

    def test_constraint_margin_rate_range(self):
        with self.assertRaises(ValidationError):
            self._new_lc(margin_rate=150.0)

    def test_constraint_positive_value(self):
        with self.assertRaises(ValidationError):
            self._new_lc(lc_value=0.0)

    def test_constraint_expiry_after_issuance(self):
        with self.assertRaises(ValidationError):
            self._new_lc(
                date_lc=fields.Date.today(),
                date_expiry=fields.Date.add(fields.Date.today(), days=-5),
            )

    def test_constraint_latest_shipment_within_expiry(self):
        with self.assertRaises(ValidationError):
            self._new_lc(
                date_expiry=fields.Date.add(fields.Date.today(), days=30),
                date_latest_shipment=fields.Date.add(fields.Date.today(), days=60),
            )

    def test_issued_lc_cannot_be_deleted(self):
        lc = self._new_lc(margin_rate=10.0)
        lc.action_apply()
        lc.action_issue()
        with self.assertRaises(UserError):
            lc.unlink()
        # A draft LC can still be removed.
        draft = self._new_lc()
        draft.unlink()

    def test_po_requires_live_lc(self):
        po = self.env["purchase.order"].create({
            "partner_id": self.supplier.id,
            "import_transaction_type": "lc",
        })
        # No LC attached -> confirm blocked.
        with self.assertRaises(Exception):
            po.button_confirm()
