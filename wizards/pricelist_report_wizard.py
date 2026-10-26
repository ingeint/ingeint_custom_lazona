# -*- coding: utf-8 -*-

import base64
import io
from collections import OrderedDict

import xlsxwriter

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_datetime


class LazonaPricelistReportWizard(models.TransientModel):
    _name = "lazona.pricelist.report.wizard"
    _description = "Reporte de lista de precios"

    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de precios",
        required=True,
        default=lambda self: self._default_pricelist(),
    )
    currency_id = fields.Many2one(related="pricelist_id.currency_id")
    date = fields.Datetime(
        string="Fecha",
        required=True,
        default=fields.Datetime.now,
        help="Fecha usada para elegir las reglas vigentes y la tasa de cambio.",
    )
    quantity = fields.Float(
        string="Cantidad",
        default=1.0,
        digits="Product Unit of Measure",
        help="Cantidad con la que se evalúan las reglas (cantidad mínima).",
    )
    categ_ids = fields.Many2many(
        "product.category",
        string="Categorías",
        help="Vacío: todas las categorías. Incluye las subcategorías.",
    )
    product_ids = fields.Many2many(
        "product.product",
        string="Productos",
        domain=[("sale_ok", "=", True)],
        help="Vacío: todos los productos vendibles.",
    )
    only_available = fields.Boolean(string="Solo con existencia")
    hide_zero_price = fields.Boolean(string="Ocultar productos sin precio", default=True)
    show_stock = fields.Boolean(string="Mostrar existencia")
    show_conversion = fields.Boolean(
        string="Mostrar precio convertido",
        default=True,
        help="Agrega las columnas en la moneda de conversión de la lista de precios.",
    )
    conversion_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de conversión",
        compute="_compute_conversion_currency_id",
    )
    file_data = fields.Binary(string="Archivo", readonly=True, attachment=False)
    file_name = fields.Char(string="Nombre del archivo", readonly=True)

    @api.model
    def _default_pricelist(self):
        if self.env.context.get("active_model") == "product.pricelist":
            return self.env.context.get("active_id")
        return False

    @api.depends("pricelist_id")
    def _compute_conversion_currency_id(self):
        for wizard in self:
            currency = self.env["res.currency"]
            if wizard.pricelist_id:
                currency = wizard.pricelist_id.lazona_get_conversion_currency()
                if currency == wizard.pricelist_id.currency_id:
                    currency = self.env["res.currency"]
            wizard.conversion_currency_id = currency

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def _get_company(self):
        self.ensure_one()
        return self.pricelist_id.company_id or self.env.company

    def _get_products(self):
        self.ensure_one()
        company = self._get_company()
        domain = [
            ("sale_ok", "=", True),
            "|", ("company_ids", "=", False), ("company_ids", "in", company.ids),
        ]
        if self.categ_ids:
            domain.append(("categ_id", "child_of", self.categ_ids.ids))
        if self.product_ids:
            domain.append(("id", "in", self.product_ids.ids))
        if self.only_available:
            domain.append(("qty_available", ">", 0))
        return self.env["product.product"].search(domain, order="categ_id, default_code, name, id")

    def _get_report_lines(self):
        """Precio de cada producto con las reglas de la lista, tal como lo
        calcula un pedido de venta (_compute_price_rule): margen bruto, tipo
        de redondeo, redondeo con IVA incluido, tarifa adicional y márgenes de
        ingeint_custom / ingeint_custom_lazona."""
        self.ensure_one()
        pricelist = self.pricelist_id
        company = self._get_company()
        self = self.with_company(company)
        pricelist = pricelist.with_company(company)
        currency = pricelist.currency_id
        conversion_currency = self.show_conversion and self.conversion_currency_id
        products = self.with_context(active_test=True)._get_products()
        if not products:
            return []

        quantity = self.quantity or 1.0
        prices = pricelist._compute_price_rule(products, quantity, currency=currency, date=self.date)
        lines = []
        for product in products:
            price, rule_id = prices.get(product.id, (0.0, False))
            if self.hide_zero_price and currency.compare_amounts(price, 0.0) <= 0:
                continue
            taxes = product.taxes_id.filtered(lambda tax: tax.company_id == company)
            totals = taxes.compute_all(price, currency=currency, quantity=1.0, product=product)
            line = {
                "product": product,
                "default_code": product.default_code or "",
                "name": product.with_context(display_default_code=False).display_name,
                "category": product.categ_id.display_name or "",
                "uom": product.uom_id.name,
                "qty_available": product.qty_available,
                "rule_id": rule_id,
                "price": price,
                "price_untaxed": currency.round(totals["total_excluded"]),
                "tax_amount": currency.round(totals["total_included"] - totals["total_excluded"]),
                "price_total": currency.round(totals["total_included"]),
                "taxes": ", ".join(taxes.mapped("name")),
            }
            if conversion_currency:
                # Igual que un pedido en la moneda de la compañía: se convierte
                # el precio sin impuesto y el IVA se calcula sobre ese importe.
                converted = currency._convert(price, conversion_currency, company, self.date, round=False)
                converted_totals = taxes.compute_all(
                    converted, currency=conversion_currency, quantity=1.0, product=product)
                line.update({
                    "converted_untaxed": conversion_currency.round(converted_totals["total_excluded"]),
                    "converted_total": conversion_currency.round(converted_totals["total_included"]),
                })
            lines.append(line)
        return lines

    def _get_report_data(self):
        self.ensure_one()
        company = self._get_company()
        currency = self.pricelist_id.currency_id
        conversion_currency = self.show_conversion and self.conversion_currency_id
        lines = self._get_report_lines()
        groups = OrderedDict()
        for line in lines:
            groups.setdefault(line["category"], []).append(line)
        rate = False
        if conversion_currency:
            rate = currency._convert(1.0, conversion_currency, company, self.date, round=False)
        return {
            "company": company,
            "pricelist": self.pricelist_id,
            "currency": currency,
            "conversion_currency": conversion_currency,
            "rate": rate,
            "date": self.date,
            "date_display": format_datetime(self.env, self.date, dt_format="dd/MM/yyyy HH:mm"),
            "show_stock": self.show_stock,
            "lines": lines,
            "groups": groups,
        }

    def _check_lines(self, data):
        if not data["lines"]:
            raise UserError(_("No hay productos con precio para los filtros indicados."))

    def _check_products(self):
        if not self.with_company(self._get_company())._get_products():
            raise UserError(_("No hay productos para los filtros indicados."))

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def action_print_pdf(self):
        self.ensure_one()
        # Los precios se calculan una sola vez, al renderizar el reporte.
        self._check_products()
        return self.env.ref("ingeint_custom_lazona.action_report_pricelist").report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        data = self._get_report_data()
        self._check_lines(data)
        self.write({
            "file_data": base64.b64encode(self._build_xlsx(data)),
            "file_name": "%s.xlsx" % self._get_file_title(),
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/?model=%s&id=%s&field=file_data&filename_field=file_name&download=true"
                   % (self._name, self.id),
            "target": "self",
        }

    def _get_file_title(self):
        self.ensure_one()
        return _("Lista de precios - %s - %s") % (
            self.pricelist_id.name, fields.Date.to_string(fields.Date.context_today(self, self.date)))

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------

    def _get_xlsx_columns(self, data):
        currency = data["currency"]
        conversion_currency = data["conversion_currency"]
        columns = [
            ("default_code", _("Código"), 16, "text"),
            ("name", _("Producto"), 50, "text"),
            ("category", _("Categoría"), 30, "text"),
            ("uom", _("UdM"), 10, "text"),
        ]
        if data["show_stock"]:
            columns.append(("qty_available", _("Existencia"), 12, "qty"))
        columns += [
            ("price_untaxed", _("Precio sin IVA (%s)") % currency.name, 18, "price"),
            ("tax_amount", _("IVA (%s)") % currency.name, 14, "price"),
            ("price_total", _("Precio con IVA (%s)") % currency.name, 18, "price"),
        ]
        if conversion_currency:
            columns += [
                ("converted_untaxed", _("Precio sin IVA (%s)") % conversion_currency.name, 18, "converted"),
                ("converted_total", _("Precio con IVA (%s)") % conversion_currency.name, 18, "converted"),
            ]
        return columns

    @api.model
    def _xlsx_number_format(self, currency):
        decimals = currency.decimal_places
        return "#,##0" + ("." + "0" * decimals if decimals else "")

    def _build_xlsx(self, data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet(_("Lista de precios")[:31])
        title_fmt = workbook.add_format({"bold": True, "font_size": 14})
        label_fmt = workbook.add_format({"bold": True})
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#D9E1F2", "border": 1, "text_wrap": True, "valign": "vcenter"})
        text_fmt = workbook.add_format({"border": 1})
        qty_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        price_fmt = workbook.add_format({"border": 1, "num_format": self._xlsx_number_format(data["currency"])})
        converted_fmt = price_fmt
        if data["conversion_currency"]:
            converted_fmt = workbook.add_format({
                "border": 1, "num_format": self._xlsx_number_format(data["conversion_currency"])})
        formats = {"text": text_fmt, "qty": qty_fmt, "price": price_fmt, "converted": converted_fmt}

        sheet.write(0, 0, data["company"].name, title_fmt)
        sheet.write(1, 0, _("Lista de precios"), label_fmt)
        sheet.write(1, 1, "%s (%s)" % (data["pricelist"].name, data["currency"].name))
        sheet.write(2, 0, _("Fecha"), label_fmt)
        sheet.write(2, 1, data["date_display"])
        row = 3
        if data["conversion_currency"]:
            sheet.write(row, 0, _("Tasa"), label_fmt)
            sheet.write(row, 1, "1 %s = %s %s" % (
                data["currency"].name, self._format_rate(data["rate"]), data["conversion_currency"].name))
            row += 1

        row += 1
        columns = self._get_xlsx_columns(data)
        for col, (_key, label, width, _kind) in enumerate(columns):
            sheet.set_column(col, col, width)
            sheet.write(row, col, label, header_fmt)
        sheet.freeze_panes(row + 1, 0)
        sheet.autofilter(row, 0, row + len(data["lines"]), len(columns) - 1)
        for line in data["lines"]:
            row += 1
            for col, (key, _label, _width, kind) in enumerate(columns):
                sheet.write(row, col, line.get(key, ""), formats[kind])
        workbook.close()
        return output.getvalue()

    @api.model
    def _format_rate(self, rate):
        return ("%.4f" % (rate or 0.0)).rstrip("0").rstrip(".")
