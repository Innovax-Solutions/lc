# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError


class LcAmendmentWizard(models.TransientModel):
    _name = "nepal.lc.amendment.wizard"
    _description = "LC Amendment Wizard"

    lc_id = fields.Many2one("nepal.lc.master", required=True)
    currency_id = fields.Many2one(related="lc_id.currency_id")
    current_value = fields.Monetary(
        string="Current LC Value", related="lc_id.lc_value", currency_field="currency_id"
    )
    current_expiry = fields.Date(string="Current Expiry Date", related="lc_id.date_expiry")
    current_latest_shipment = fields.Date(
        string="Current Latest Shipment", related="lc_id.date_latest_shipment"
    )
    current_tenor = fields.Integer(string="Current Tenor (days)", related="lc_id.tenor_days")
    new_value = fields.Monetary(string="New LC Value", currency_field="currency_id")
    new_expiry = fields.Date(string="New Expiry Date")
    new_latest_shipment = fields.Date(string="New Latest Shipment Date")
    new_tenor_days = fields.Integer(string="New Tenor (days)")
    notes = fields.Text(string="Reason / Notes", required=True)

    def action_apply(self):
        self.ensure_one()
        if not any([self.new_value, self.new_expiry, self.new_latest_shipment, self.new_tenor_days]):
            raise UserError(
                "Please specify at least one change (value, expiry, latest shipment or tenor)."
            )
        if self.lc_id.state not in self.lc_id._amendable_states():
            raise UserError("Amendments can only be made on a live LC (issued / shipped / documents).")

        self.env["nepal.lc.amendment"].create({
            "lc_id": self.lc_id.id,
            "new_value": self.new_value,
            "new_expiry": self.new_expiry,
            "new_latest_shipment": self.new_latest_shipment,
            "new_tenor_days": self.new_tenor_days,
            "notes": self.notes,
        })

        changes = []
        if self.new_value:
            changes.append(
                f"LC Value: {self.current_value:.2f} → {self.new_value:.2f} {self.currency_id.name}"
            )
        if self.new_expiry:
            changes.append(f"Expiry Date: {self.current_expiry} → {self.new_expiry}")
        if self.new_latest_shipment:
            changes.append(
                f"Latest Shipment: {self.current_latest_shipment or '-'} → {self.new_latest_shipment}"
            )
        if self.new_tenor_days:
            changes.append(f"Tenor: {self.current_tenor or 0} → {self.new_tenor_days} days")
        self.lc_id.message_post(
            body=(
                "<b>Amendment Applied</b><br/>"
                + "<br/>".join(changes)
                + f"<br/><i>Reason: {self.notes}</i>"
            )
        )
        return {"type": "ir.actions.act_window_close"}
