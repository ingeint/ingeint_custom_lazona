# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.tools import float_round, formatLang


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    lazona_price_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda del precio",
        compute="_compute_lazona_price_conversion",
    )
    lazona_conversion_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda convertida",
        compute="_compute_lazona_price_conversion",
    )
    lazona_price_amount = fields.Float(
        string="Importe en lista",
        digits="Product Price",
        compute="_compute_lazona_price_conversion",
    )
    lazona_converted_amount = fields.Float(
        string="Importe convertido",
        digits="Product Price",
        compute="_compute_lazona_price_conversion",
    )
    lazona_price_status = fields.Char(
        string="Estado de conversión",
        compute="_compute_lazona_price_conversion",
    )
    lazona_price_display = fields.Char(
        string="Precio convertido",
        compute="_compute_lazona_price_conversion",
    )
    lazona_round_tax_included = fields.Boolean(
        string="Redondear con IVA incluido",
        help="Aplica el redondeo y la tarifa adicional sobre el precio con los "
             "impuestos de venta del producto y guarda el precio sin impuesto "
             "equivalente. Ej.: con redondeo 1,00 hacia arriba y 16 % de IVA, "
             "21,29 + IVA = 24,70 sube a 25,00 y el precio queda en 21,55.",
    )

    @api.depends(
        "pricelist_id",
        "pricelist_id.currency_id",
        "pricelist_id.company_id",
        "pricelist_id.lazona_show_dual_currency",
        "pricelist_id.lazona_conversion_currency_id",
        "product_tmpl_id",
        "product_id",
        "categ_id",
        "applied_on",
        "compute_price",
        "fixed_price",
        "percent_price",
        "price_discount",
        "price_surcharge",
        "price_round",
        "price_round_method",
        "lazona_round_tax_included",
        "price_min_margin",
        "price_max_margin",
        "base",
        "base_pricelist_id",
        "base_pricelist_id.currency_id",
        "min_quantity",
        "date_start",
        "date_end",
    )
    def _compute_lazona_price_conversion(self):
        now = fields.Datetime.now()
        for item in self:
            item.lazona_price_currency_id = False
            item.lazona_conversion_currency_id = False
            item.lazona_price_amount = 0.0
            item.lazona_converted_amount = 0.0
            item.lazona_price_status = False
            item.lazona_price_display = False

            pricelist = item.pricelist_id
            if not pricelist or not pricelist.lazona_show_dual_currency:
                continue

            source_currency = pricelist.currency_id or item.env.company.currency_id
            target_currency = pricelist.lazona_get_conversion_currency()
            item.lazona_price_currency_id = source_currency
            item.lazona_conversion_currency_id = target_currency

            product = item._lazona_get_product_for_price()
            if not product:
                item._lazona_set_status(_("Precio no definido"))
                continue

            if item.date_start and item.date_start > now:
                item._lazona_set_status(_("Regla no vigente"))
                continue

            if item.date_end and item.date_end < now:
                item._lazona_set_status(_("Regla vencida"))
                continue

            quantity = max(item.min_quantity or 0.0, 1.0)
            uom = product.uom_id
            company = pricelist.company_id or item.env.company

            try:
                amount = item._compute_price(
                    product,
                    quantity,
                    uom,
                    date=now,
                    currency=source_currency,
                )
            except Exception as error:
                item._lazona_set_status(_("Precio no definido: %s") % error)
                continue

            item.lazona_price_amount = amount
            if amount <= 0.0:
                item._lazona_set_status(_("Precio no definido"))
                continue

            if source_currency == target_currency:
                item.lazona_converted_amount = amount
                item.lazona_price_display = item._lazona_format_amount(amount, source_currency)
                continue

            try:
                converted_amount = source_currency._convert(
                    amount,
                    target_currency,
                    company,
                    now,
                    round=False,
                )
            except Exception as error:
                item._lazona_set_status(_("Sin tasa de conversión: %s") % error)
                continue

            item.lazona_converted_amount = converted_amount
            if converted_amount <= 0.0:
                item._lazona_set_status(_("Sin tasa de conversión"))
                continue

            item.lazona_price_display = "%s / %s" % (
                item._lazona_format_amount(amount, source_currency),
                item._lazona_format_amount(converted_amount, target_currency),
            )

    def _round_formula_price(self, price, product, convert):
        taxes = self._lazona_get_round_taxes(product)
        if not taxes:
            return super()._round_formula_price(price, product, convert)
        currency = self.currency_id or self.env.company.currency_id
        price_included = taxes.compute_all(price, currency=currency, quantity=1.0, product=product)["total_included"]
        price_included = super()._round_formula_price(price_included, product, convert)
        return taxes.with_context(force_price_include=True).compute_all(
            price_included, currency=currency, quantity=1.0, product=product)["total_excluded"]

    def _lazona_get_round_taxes(self, product):
        """Impuestos de venta que el catálogo suma al precio (los no incluidos
        en el precio), si la regla redondea con IVA incluido."""
        self.ensure_one()
        if not self.lazona_round_tax_included or not self.price_round:
            return self.env["account.tax"]
        company = self.company_id or self.env.company
        return product.taxes_id.filtered(lambda tax: tax.company_id == company and not tax.price_include)

    def _lazona_get_product_for_price(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        if self.product_tmpl_id:
            return self.product_tmpl_id.product_variant_id or self.product_tmpl_id.product_variant_ids[:1]
        return self.env["product.product"]

    def _lazona_set_status(self, message):
        self.ensure_one()
        self.lazona_price_status = message
        self.lazona_price_display = message

    def _lazona_format_amount(self, amount, currency):
        self.ensure_one()
        currency.ensure_one()
        formatted_rounding = formatLang(
            self.env,
            currency.rounding,
            monetary=True,
            dp="Product Price",
            currency_obj=currency,
        )
        if amount and currency.is_zero(amount):
            formatted = _("< %s") % formatted_rounding
        else:
            formatted = formatLang(
                self.env,
                amount,
                monetary=True,
                dp="Product Price",
                currency_obj=currency,
            )
        if currency.name and currency.name not in formatted:
            formatted = "%s %s" % (formatted, currency.name)
        return formatted
