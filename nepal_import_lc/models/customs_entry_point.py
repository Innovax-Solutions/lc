# -*- coding: utf-8 -*-
from odoo import models, fields


class NepalCustomsEntryPoint(models.Model):
    _name = "nepal.customs.entry.point"
    _description = "Nepal Customs Entry Point"
    _order = "name"

    name = fields.Char(string="Entry Point", required=True)
    code = fields.Char(string="Code", required=True)
    border_type = fields.Selection(
        [
            ("india", "India Border"),
            ("china", "China Border"),
            ("air", "Air (TIA)"),
            ("other", "Other"),
        ],
        string="Border",
        default="india",
    )
    nrb_approved = fields.Boolean(
        string="NRB-Approved",
        default=True,
        help="On Nepal Rastra Bank's pre-approved list of customs points "
        "that may be named in an LC.",
    )
    active = fields.Boolean(default=True)
