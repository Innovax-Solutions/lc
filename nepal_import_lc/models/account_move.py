# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    lc_id = fields.Many2one(
        "nepal.lc.master",
        string="LC Reference",
        domain="[('state', 'in', ('issued', 'shipped', 'documents', 'paid', 'cleared'))]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for move in records:
            if move.move_type == "in_invoice" and not move.lc_id:
                orders = move.invoice_line_ids.mapped("purchase_line_id.order_id")
                lc_ids = orders.mapped("lc_id").filtered(lambda l: l.id)
                if lc_ids:
                    move.lc_id = lc_ids[0]
        return records

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type == "in_invoice" and move.lc_id:
                lc = move.lc_id
                if lc.remaining_balance < 0:
                    move.message_post(
                        body=_(
                            "Warning: the utilized amount on LC <b>%(lc)s</b> "
                            "(%(used).2f %(cur)s) now exceeds its value "
                            "(%(value).2f %(cur)s). An amendment may be required."
                        )
                        % {
                            "lc": lc.name,
                            "used": lc.used_amount,
                            "value": lc.lc_value,
                            "cur": lc.currency_id.name,
                        }
                    )
        return res
