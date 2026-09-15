# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Config-parameter keys for the NRB import-payment thresholds. Seeded in
# data/lc_config_params.xml and editable under Settings > Technical > Parameters
# so they can track each NRB Unified Directive without a code change.
PARAM_TT_USD = "nepal_import_lc.tt_advance_limit_usd"
PARAM_TT_INR = "nepal_import_lc.tt_advance_limit_inr"
PARAM_DAP_USD = "nepal_import_lc.dap_limit_usd"
PARAM_INDIA_LC_INR = "nepal_import_lc.india_lc_mandatory_inr"

# Live LC states a PO/bill may be booked against.
LC_LIVE_STATES = ("issued", "shipped", "documents")


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    import_transaction_type = fields.Selection(
        [
            ("lc", "Letter of Credit (LC)"),
            ("tt", "Telegraphic Transfer (Advance)"),
            ("dap_daa", "DAP / DAA (Collection)"),
            ("pc", "Purchase Consignment (PC)"),
            ("pp", "Pragyapan Patra (PP)"),
        ],
        string="Import Transaction Type",
    )
    lc_id = fields.Many2one(
        "nepal.lc.master",
        string="LC Reference",
        domain="[('partner_id', '=', partner_id), ('state', 'in', "
        "('issued', 'shipped', 'documents')), ('currency_id', '=', currency_id)]",
    )

    @api.onchange("partner_id")
    def _onchange_partner_import_type(self):
        if not self.partner_id:
            return
        p = self.partner_id
        flags = [p.is_lc_mandatory, p.is_pc_mandatory, p.is_pp_mandatory]
        count = sum(bool(f) for f in flags)
        if count == 1:
            if p.is_lc_mandatory:
                self.import_transaction_type = "lc"
            elif p.is_pc_mandatory:
                self.import_transaction_type = "pc"
            else:
                self.import_transaction_type = "pp"
        elif count > 1:
            return {
                "warning": {
                    "title": "Multiple Transaction Types Required",
                    "message": "This vendor has multiple import transaction type requirements. Please select the correct type.",
                }
            }

    @api.onchange("import_transaction_type")
    def _onchange_import_transaction_type(self):
        if self.import_transaction_type != "lc":
            self.lc_id = False

    def _get_param_float(self, key, default=0.0):
        value = self.env["ir.config_parameter"].sudo().get_param(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _check_import_payment_thresholds(self):
        """Enforce the NRB payment-mode thresholds: TT advance ceilings, the
        DAP/DAA ceiling, and the mandatory-LC rule for large India imports."""
        self.ensure_one()
        currency = (self.currency_id.name or "").upper()
        amount = self.amount_total
        mode = self.import_transaction_type

        if mode == "tt":
            limit_usd = self._get_param_float(PARAM_TT_USD)
            limit_inr = self._get_param_float(PARAM_TT_INR)
            if currency == "USD" and limit_usd and amount > limit_usd:
                raise ValidationError(
                    _("Advance payment (TT) is limited to USD %(limit)s per transaction. "
                      "This order (%(amount)s %(cur)s) must be opened under an LC.")
                    % {"limit": limit_usd, "amount": amount, "cur": currency}
                )
            if currency == "INR" and limit_inr and amount > limit_inr:
                raise ValidationError(
                    _("Advance payment (TT) is limited to INR %(limit)s per transaction. "
                      "This order (%(amount)s %(cur)s) must be opened under an LC.")
                    % {"limit": limit_inr, "amount": amount, "cur": currency}
                )

        if mode == "dap_daa":
            limit_usd = self._get_param_float(PARAM_DAP_USD)
            if limit_usd and currency == "USD" and amount > limit_usd:
                raise ValidationError(
                    _("DAP/DAA (collection) imports are limited to USD %(limit)s equivalent. "
                      "This order (%(amount)s %(cur)s) exceeds the limit.")
                    % {"limit": limit_usd, "amount": amount, "cur": currency}
                )

        # India imports above the threshold must go through an LC.
        india_limit = self._get_param_float(PARAM_INDIA_LC_INR)
        if (
            india_limit
            and currency == "INR"
            and amount > india_limit
            and mode not in ("lc",)
        ):
            raise ValidationError(
                _("Imports from India exceeding INR %(limit)s must be opened under an LC "
                  "(NRB rule). This order is %(amount)s %(cur)s.")
                % {"limit": india_limit, "amount": amount, "cur": currency}
            )

    def button_confirm(self, **kwargs):
        for order in self:
            partner = order.partner_id
            if partner.is_lc_mandatory or partner.is_pc_mandatory or partner.is_pp_mandatory:
                if not order.import_transaction_type:
                    raise ValidationError(
                        _("Vendor '%s' requires an import transaction type. "
                          "Please set it before confirming.") % partner.name
                    )
            if order.import_transaction_type:
                order._check_import_payment_thresholds()
            if order.import_transaction_type == "lc":
                if not order.lc_id:
                    raise ValidationError(
                        _("An LC reference is required when the import transaction type is Letter of Credit.")
                    )
                if order.lc_id.state not in LC_LIVE_STATES:
                    raise ValidationError(
                        _("LC '%s' is not live (issued/shipped/documents). "
                          "Only an issued LC can be used on Purchase Orders.") % order.lc_id.name
                    )
        return super().button_confirm(**kwargs)
