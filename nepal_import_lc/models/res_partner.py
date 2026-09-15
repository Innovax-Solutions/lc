# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_lc_mandatory = fields.Boolean(string="LC Mandatory")
    is_pc_mandatory = fields.Boolean(string="Purchase Consignment Mandatory")
    is_pp_mandatory = fields.Boolean(string="Pragyapan Patra Mandatory")
    # Foreign-supplier (beneficiary) banking details, used to pre-fill LCs.
    beneficiary_bank_swift = fields.Char(
        string="Beneficiary Bank SWIFT/BIC",
        help="SWIFT/BIC of the supplier's (beneficiary's) bank, used when "
        "opening an LC in their favour.",
    )
