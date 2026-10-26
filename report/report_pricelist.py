# -*- coding: utf-8 -*-

from odoo import api, models


class ReportPricelist(models.AbstractModel):
    _name = "report.ingeint_custom_lazona.report_pricelist_document"
    _description = "Reporte de lista de precios"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizards = self.env["lazona.pricelist.report.wizard"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "lazona.pricelist.report.wizard",
            "docs": wizards,
            "report_data": {wizard.id: wizard._get_report_data() for wizard in wizards},
            "format_rate": wizards._format_rate,
        }
