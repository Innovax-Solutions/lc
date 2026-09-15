# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    exim_code = fields.Char(
        string="EXIM Code",
        size=13,
        help="13-character Export-Import code issued by the Department of "
        "Customs via the Nepal National Single Window. The first 9 digits are "
        "the firm's PAN, the next 2 the ownership type, the last 2 a unique "
        "serial. Required on every Pragyapan Patra and LC.",
    )
