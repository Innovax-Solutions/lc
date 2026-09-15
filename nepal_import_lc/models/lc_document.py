# -*- coding: utf-8 -*-
from odoo import models, fields


class NepalLcDocument(models.Model):
    """The documentary set tracked against an import LC - from the proforma
    invoice through the transport documents to the Pragyapan Patra (customs
    declaration). A default checklist is generated per payment mode when the
    LC is created."""

    _name = "nepal.lc.document"
    _description = "LC Document"
    _order = "sequence, id"

    DOC_TYPES = [
        ("pi", "Proforma Invoice / Indent"),
        ("commercial_invoice", "Commercial Invoice"),
        ("packing_list", "Packing List"),
        ("transport", "Bill of Lading / Airway Bill"),
        ("coo", "Certificate of Origin (COO)"),
        ("insurance", "Insurance Policy / Certificate"),
        ("bibini", "Bi.Bi.Ni Form (NRB)"),
        ("lc_copy", "Certified LC Copy"),
        ("pragyapan_patra", "Pragyapan Patra (Customs Declaration)"),
        ("ctd", "Customs Transit Declaration (CTD)"),
        ("bci", "BCI / Inspection Report"),
        ("other", "Other"),
    ]

    lc_id = fields.Many2one(
        "nepal.lc.master", string="LC", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    doc_type = fields.Selection(DOC_TYPES, string="Document", required=True)
    name = fields.Char(string="Reference / No.")
    required = fields.Boolean(string="Required", default=True)
    received = fields.Boolean(string="Received")
    received_date = fields.Date(string="Received On")
    attachment = fields.Binary(string="File", attachment=True)
    attachment_filename = fields.Char(string="Filename")
    notes = fields.Char(string="Notes")
