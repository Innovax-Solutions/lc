# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class NepalLcAmendment(models.Model):
    _name = "nepal.lc.amendment"
    _description = "LC Amendment"
    _order = "amendment_no"

    lc_id = fields.Many2one("nepal.lc.master", string="LC", required=True, ondelete="cascade")
    amendment_no = fields.Integer(string="Amendment No.", readonly=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one(related="lc_id.currency_id")
    new_value = fields.Monetary(string="Revised LC Value", currency_field="currency_id")
    new_expiry = fields.Date(string="Revised Expiry Date")
    new_latest_shipment = fields.Date(string="Revised Latest Shipment Date")
    new_tenor_days = fields.Integer(string="Revised Tenor (days)")
    notes = fields.Text(string="Amendment Details")

    @api.constrains("new_value")
    def _check_new_value(self):
        for rec in self:
            if rec.new_value and rec.new_value < 0:
                raise ValidationError(_("Revised LC value cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("lc_id"):
                raise ValidationError(_("An amendment must be linked to an LC."))
            lc = self.env["nepal.lc.master"].browse(vals["lc_id"])
            if lc.state not in lc._amendable_states():
                raise UserError(_("Amendments can only be added to a live (issued / shipped / documents) LC."))
            existing = self.search([("lc_id", "=", lc.id)], order="amendment_no desc", limit=1)
            vals["amendment_no"] = (existing.amendment_no + 1) if existing else 1
        records = super().create(vals_list)
        for record in records:
            lc = record.lc_id
            if record.new_value:
                lc.lc_value = record.new_value
            if record.new_expiry:
                lc.date_expiry = record.new_expiry
            if record.new_latest_shipment:
                lc.date_latest_shipment = record.new_latest_shipment
            if record.new_tenor_days:
                lc.tenor_days = record.new_tenor_days
        return records

    def write(self, vals):
        if not self.env.su:
            raise UserError(_("Amendments cannot be edited once saved."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise UserError(_("Amendments are part of the LC audit trail and cannot be deleted."))
        return super().unlink()


class NepalLcMaster(models.Model):
    _name = "nepal.lc.master"
    _description = "LC Master"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_lc desc, id desc"

    # ------------------------------------------------------------------
    # Identity & parties
    # ------------------------------------------------------------------
    name = fields.Char(string="LC Number", required=True, copy=False, tracking=True, default="New")
    company_id = fields.Many2one(
        "res.company", string="Importer (Company)", required=True,
        default=lambda self: self.env.company, tracking=True,
    )
    payment_mode = fields.Selection(
        [
            ("lc", "Letter of Credit (LC)"),
            ("tt", "Telegraphic Transfer (Advance)"),
            ("dap_daa", "DAP / DAA (Collection)"),
        ],
        string="Payment Mode", required=True, default="lc", tracking=True,
    )
    lc_type = fields.Selection(
        [("sight", "Sight LC"), ("usance", "Usance / Acceptance LC")],
        string="LC Type", tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Beneficiary (Supplier)", required=True, tracking=True,
    )
    beneficiary_country_id = fields.Many2one("res.country", string="Beneficiary Country")
    beneficiary_bank_swift = fields.Char(string="Beneficiary Bank SWIFT/BIC")
    issuing_bank_id = fields.Many2one("res.bank", string="Issuing Bank", tracking=True)
    issuing_bank_branch = fields.Char(string="Issuing Bank Branch")
    advising_bank_name = fields.Char(string="Advising / Negotiating Bank")

    # ------------------------------------------------------------------
    # Commercial
    # ------------------------------------------------------------------
    proforma_invoice_ref = fields.Char(string="Proforma Invoice / Indent No.")
    pi_date = fields.Date(string="Proforma Invoice Date")
    incoterm_id = fields.Many2one("account.incoterms", string="Incoterm (2020)")
    origin_country_id = fields.Many2one("res.country", string="Country of Origin")
    goods_description = fields.Text(string="Goods Description")

    # ------------------------------------------------------------------
    # Financial
    # ------------------------------------------------------------------
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id, tracking=True,
    )
    company_currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Company Currency",
    )
    lc_value = fields.Monetary(string="LC Value", currency_field="currency_id", required=True, tracking=True)
    margin_rate = fields.Float(string="Cash Margin (%)", tracking=True)
    margin_amount = fields.Monetary(
        string="Margin Amount", currency_field="currency_id",
        compute="_compute_margin_amount", store=True,
    )
    exchange_rate = fields.Float(string="NRB Exchange Rate", digits=(12, 6))
    used_amount = fields.Monetary(
        string="Utilized Amount", currency_field="currency_id",
        compute="_compute_used_amount", store=True,
    )
    remaining_balance = fields.Monetary(
        string="Remaining Balance", currency_field="currency_id",
        compute="_compute_used_amount", store=True,
    )

    # ------------------------------------------------------------------
    # Dates / tenor
    # ------------------------------------------------------------------
    date_application = fields.Date(string="Application Date", tracking=True)
    date_lc = fields.Date(string="Issuance Date", default=fields.Date.context_today, tracking=True)
    date_expiry = fields.Date(string="Expiry Date", required=True, tracking=True)
    date_latest_shipment = fields.Date(string="Latest Shipment Date", tracking=True)
    tenor_days = fields.Integer(
        string="Tenor (days)",
        help="Usance/acceptance deferral. Sight LC = 0. Trading firms are "
        "capped at 180 days by NRB.",
    )
    date_payment_due = fields.Date(string="Deferred Payment Due Date")

    margin_deposited = fields.Boolean(string="Margin Deposited", tracking=True)
    margin_deposit_date = fields.Date(string="Margin Deposit Date")
    documents_released = fields.Boolean(string="Documents Released to Importer")

    # ------------------------------------------------------------------
    # Regulatory / logistics
    # ------------------------------------------------------------------
    bibini_form_type = fields.Selection(
        [
            ("form3", "Bi.Bi.Ni Form No. 3 (FCY)"),
            ("form3ga", "Bi.Bi.Ni Form No. 3 \"Ga\" (INR / India)"),
        ],
        string="Bi.Bi.Ni Form",
    )
    exim_code = fields.Char(string="EXIM Code")
    customs_entry_point_id = fields.Many2one(
        "nepal.customs.entry.point", string="Customs Entry Point", tracking=True,
    )
    bci_required = fields.Boolean(string="BCI Report Required", compute="_compute_bci_required")
    bci_ref = fields.Char(string="BCI Report Ref.")

    # ------------------------------------------------------------------
    # Lifecycle & links
    # ------------------------------------------------------------------
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("applied", "Applied"),
            ("issued", "Issued (MT700)"),
            ("shipped", "Shipped"),
            ("documents", "Documents Presented"),
            ("paid", "Paid / Accepted"),
            ("cleared", "Customs Cleared"),
            ("closed", "Closed"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        string="Status", default="draft", required=True, tracking=True,
    )
    amendment_ids = fields.One2many("nepal.lc.amendment", "lc_id", string="Amendments")
    document_ids = fields.One2many("nepal.lc.document", "lc_id", string="Documents")
    purchase_order_ids = fields.One2many("purchase.order", "lc_id", string="Purchase Orders")
    move_ids = fields.One2many("account.move", "lc_id", string="Vendor Bills")
    landed_cost_ids = fields.One2many(
        "stock.landed.cost", "lc_id", string="Landed Costs",
        help="Landed cost entries created from this LC via 'Create Landed "
        "Cost', used to fold shipping/customs/other costs into the real "
        "inventory valuation of the imported products.",
    )
    notes = fields.Text(string="Internal Notes")

    _name_unique = models.Constraint(
        "UNIQUE(name)",
        "An LC with this number already exists.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _amendable_states(self):
        return ("issued", "shipped", "documents")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("lc_value", "margin_rate")
    def _compute_margin_amount(self):
        for lc in self:
            lc.margin_amount = lc.lc_value * (lc.margin_rate or 0.0) / 100.0

    @api.depends(
        "lc_value", "currency_id",
        "move_ids", "move_ids.state", "move_ids.amount_total", "move_ids.currency_id",
    )
    def _compute_used_amount(self):
        for lc in self:
            posted_bills = lc.move_ids.filtered(
                lambda m: m.move_type == "in_invoice" and m.state == "posted"
            )
            used = 0.0
            for bill in posted_bills:
                bill_currency = bill.currency_id or lc.currency_id
                if bill_currency and lc.currency_id and bill_currency != lc.currency_id:
                    used += bill_currency._convert(
                        bill.amount_total, lc.currency_id, lc.company_id,
                        bill.invoice_date or fields.Date.context_today(lc),
                    )
                else:
                    used += bill.amount_total
            lc.used_amount = used
            lc.remaining_balance = lc.lc_value - used

    @api.depends("payment_mode", "lc_type", "lc_value", "currency_id")
    def _compute_bci_required(self):
        for lc in self:
            lc.bci_required = (
                lc.payment_mode == "lc"
                and lc.lc_type == "sight"
                and (lc.currency_id.name or "") == "USD"
                and lc.lc_value >= 50000
            )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("margin_rate")
    def _check_margin_rate(self):
        for lc in self:
            if lc.margin_rate and not (0.0 <= lc.margin_rate <= 100.0):
                raise ValidationError(_("Cash margin must be between 0% and 100%."))

    @api.constrains("lc_value")
    def _check_lc_value(self):
        for lc in self:
            if lc.lc_value <= 0:
                raise ValidationError(_("LC value must be greater than zero."))

    @api.constrains("tenor_days")
    def _check_tenor(self):
        for lc in self:
            if lc.tenor_days and lc.tenor_days < 0:
                raise ValidationError(_("Tenor (days) cannot be negative."))

    @api.constrains("exchange_rate")
    def _check_exchange_rate(self):
        for lc in self:
            if lc.exchange_rate and lc.exchange_rate < 0:
                raise ValidationError(_("Exchange rate cannot be negative."))

    @api.constrains("date_application", "date_lc", "date_expiry", "date_latest_shipment")
    def _check_dates(self):
        for lc in self:
            if lc.date_lc and lc.date_expiry and lc.date_expiry < lc.date_lc:
                raise ValidationError(_("Expiry date cannot be before the issuance date."))
            if lc.date_application and lc.date_expiry and lc.date_expiry < lc.date_application:
                raise ValidationError(_("Expiry date cannot be before the application date."))
            if (
                lc.date_latest_shipment
                and lc.date_expiry
                and lc.date_latest_shipment > lc.date_expiry
            ):
                raise ValidationError(_("Latest shipment date cannot be after the LC expiry date."))

    def unlink(self):
        for lc in self:
            if lc.state not in ("draft", "cancelled"):
                raise UserError(
                    _("LC %s cannot be deleted once issued. Cancel it instead.") % lc.name
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Onchanges / defaults
    # ------------------------------------------------------------------
    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.beneficiary_country_id = self.partner_id.country_id
            self.beneficiary_bank_swift = self.partner_id.beneficiary_bank_swift

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id and not self.exim_code:
            self.exim_code = self.company_id.exim_code

    @api.onchange("currency_id")
    def _onchange_currency_bibini(self):
        if self.currency_id and not self.bibini_form_type:
            self.bibini_form_type = "form3ga" if self.currency_id.name == "INR" else "form3"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("nepal.lc.master") or "New"
            if not vals.get("exim_code"):
                company = self.env["res.company"].browse(
                    vals.get("company_id") or self.env.company.id
                )
                vals["exim_code"] = company.exim_code
        records = super().create(vals_list)
        for lc in records:
            lc._generate_default_documents()
        return records

    def _generate_default_documents(self):
        """Seed the standard document checklist for the payment mode."""
        self.ensure_one()
        if self.document_ids:
            return
        common = [
            ("pi", True),
            ("commercial_invoice", True),
            ("packing_list", True),
            ("transport", True),
            ("pragyapan_patra", True),
            ("bibini", True),
        ]
        if self.payment_mode == "lc":
            checklist = common + [
                ("coo", True),
                ("insurance", True),
                ("lc_copy", True),
            ]
        else:
            checklist = common
        seq = 10
        vals = []
        for doc_type, required in checklist:
            vals.append({
                "lc_id": self.id,
                "doc_type": doc_type,
                "required": required,
                "sequence": seq,
            })
            seq += 10
        self.env["nepal.lc.document"].create(vals)

    # ------------------------------------------------------------------
    # Lifecycle actions
    # ------------------------------------------------------------------
    def action_apply(self):
        for lc in self:
            if lc.state != "draft":
                raise UserError(_("Only a draft LC can be submitted as an application."))
            lc.write({
                "state": "applied",
                "date_application": lc.date_application or fields.Date.context_today(lc),
            })

    def action_issue(self):
        for lc in self:
            if lc.state not in ("draft", "applied"):
                raise UserError(_("Only a draft/applied LC can be issued."))
            lc._check_ready_to_issue()
            lc.write({
                "state": "issued",
                "date_lc": lc.date_lc or fields.Date.context_today(lc),
            })

    def _check_ready_to_issue(self):
        self.ensure_one()
        missing = []
        if self.payment_mode == "lc":
            if not self.issuing_bank_id:
                missing.append(_("Issuing Bank"))
            if not self.lc_type:
                missing.append(_("LC Type (Sight/Usance)"))
        if not self.date_expiry:
            missing.append(_("Expiry Date"))
        if missing:
            raise UserError(
                _("Cannot issue LC %s - the following are required:\n- %s")
                % (self.name, "\n- ".join(missing))
            )

    def action_ship(self):
        self._advance(("issued",), "shipped")

    def action_present_documents(self):
        self._advance(("shipped",), "documents")

    def action_pay(self):
        self._advance(("documents",), "paid")

    def action_clear_customs(self):
        self._advance(("paid",), "cleared")

    def action_close(self):
        self._advance(("cleared",), "closed")

    def _advance(self, from_states, to_state):
        for lc in self:
            if lc.state not in from_states:
                raise UserError(
                    _("LC %(lc)s cannot move to '%(state)s' from its current status.")
                    % {"lc": lc.name, "state": to_state}
                )
            lc.state = to_state

    def action_cancel(self):
        for lc in self:
            if lc.state not in ("draft", "applied", "issued"):
                raise UserError(_("Only a draft/applied/issued LC can be cancelled."))
            lc.state = "cancelled"

    def action_reset_to_draft(self):
        for lc in self:
            if lc.state != "cancelled":
                raise UserError(_("Only a cancelled LC can be reset to draft."))
            lc.state = "draft"

    def action_open_amendment_wizard(self):
        self.ensure_one()
        if self.state not in self._amendable_states():
            raise UserError(_("Amendments can only be made on a live LC (issued / shipped / documents)."))
        return {
            "type": "ir.actions.act_window",
            "name": "Create Amendment",
            "res_model": "nepal.lc.amendment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_lc_id": self.id},
        }

    def action_expire_due(self):
        """Cron: auto-expire overdue live LCs."""
        today = fields.Date.today()
        overdue = self.search([
            ("state", "in", ("issued", "shipped", "documents")),
            ("date_expiry", "<", today),
        ])
        overdue.write({"state": "expired"})

    # ------------------------------------------------------------------
    # Landed cost (Inventory > Landed Costs)
    # ------------------------------------------------------------------
    def action_create_landed_cost(self):
        """Open a new draft stock.landed.cost, pre-linked to this LC and to
        the done incoming receipt(s) tied to this LC's purchase orders, for
        an accountant to fill in the cost lines (freight, customs, bank
        charges, etc.) and validate in Inventory.

        Nothing is computed or posted automatically here - this just saves
        the accountant from having to look up and attach the right receipts
        by hand.
        """
        self.ensure_one()
        pickings = self.purchase_order_ids.picking_ids.filtered(
            lambda p: p.picking_type_id.code == "incoming" and p.state == "done"
        )
        if not pickings:
            raise UserError(_(
                "No validated (done) incoming receipt was found for the "
                "purchase orders linked to this LC. Landed costs can only "
                "be applied once the goods have actually been received "
                "into stock."
            ))
        landed_cost = self.env["stock.landed.cost"].create({
            "lc_id": self.id,
            "picking_ids": [(6, 0, pickings.ids)],
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Landed Cost"),
            "res_model": "stock.landed.cost",
            "res_id": landed_cost.id,
            "view_mode": "form",
            "target": "current",
        }
