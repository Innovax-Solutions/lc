# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_quick_generate_bill(self):
        """Shortcut button: create a single draft vendor bill directly from
        this PO's billable lines, skipping the standard Create Bill wizard.
        The resulting bill is always left in draft for manual review/posting.
        """
        self.ensure_one()

        if self.state not in ('purchase', 'done'):
            raise UserError(_(
                "You can only generate a vendor bill from a confirmed "
                "purchase order."
            ))

        if self.invoice_status == 'invoiced':
            raise UserError(_(
                "This purchase order has already been fully billed."
            ))

        invoice_line_vals = []
        for line in self.order_line.filtered(lambda l: not l.display_type):
            # Explicitly receipt-based: bill only what has been received
            # and not yet invoiced, regardless of the product's own
            # invoicing policy (ordered vs. received quantities).
            qty_to_bill = line.qty_received - line.qty_invoiced
            if qty_to_bill <= 0:
                continue

            expense_account = (
                line.product_id.property_account_expense_id
                or line.product_id.categ_id.property_account_expense_categ_id
            )
            invoice_line_vals.append((0, 0, {
                'name': line.name,
                'product_id': line.product_id.id,
                'quantity': qty_to_bill,
                'price_unit': line.price_unit,
                'product_uom_id': line.product_uom.id,
                'tax_ids': [(6, 0, line.taxes_id.ids)],
                'purchase_line_id': line.id,
                'account_id': expense_account.id or False,
                'analytic_distribution': line.analytic_distribution
                    if 'analytic_distribution' in line._fields else False,
            }))

        if not invoice_line_vals:
            raise UserError(_(
                "Nothing has been received yet on this purchase order, or "
                "everything received has already been billed."
            ))

        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_date': fields.Date.context_today(self),
            'currency_id': self.currency_id.id,
            'invoice_payment_term_id': self.payment_term_id.id,
            'company_id': self.company_id.id,
            'invoice_line_ids': invoice_line_vals,
        }
        if 'partner_ref' in self.env['account.move']._fields:
            move_vals['ref'] = self.partner_ref or self.name

        move = self.env['account.move'].sudo().create(move_vals)
        # sudo() only for the create step (mirrors core's own bill-creation
        # flow, since purchasing users may not hold direct account.move
        # create rights); the bill is explicitly left in draft below.
        if move.state != 'draft':
            move.sudo().button_draft()

        return {
            'name': _('Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }
