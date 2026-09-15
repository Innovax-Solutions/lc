# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLandedCost(models.Model):
    """Traceability link back to the import LC this landed cost was created
    from, so the LC form can show its own landed cost entries and the
    landed cost audit trail shows which LC it came from."""

    _inherit = "stock.landed.cost"

    lc_id = fields.Many2one(
        "nepal.lc.master", string="Import LC", copy=False,
        help="Import LC this landed cost was generated from via the LC's "
        "'Create Landed Cost' button.",
    )
