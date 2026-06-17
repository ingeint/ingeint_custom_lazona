# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    lazona_show_dual_currency = fields.Boolean(
        string="Mostrar conversión monetaria",
        default=True,
        help="Muestra el precio en la moneda de la lista y su importe convertido.",
    )
    lazona_conversion_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de conversión",
        help="Moneda usada para mostrar el importe convertido de la regla. Si está vacía, se usa la moneda de la compañía.",
    )

    def lazona_get_conversion_currency(self):
        self.ensure_one()
        if self.lazona_conversion_currency_id:
            return self.lazona_conversion_currency_id

        company = self.company_id or self.env.company
        company_currency = company.currency_id
        if self.currency_id and self.currency_id != company_currency:
            return company_currency

        if "contrary_currency_id" in self.env["res.currency"]._fields and self.currency_id.contrary_currency_id:
            return self.currency_id.contrary_currency_id

        return company_currency
