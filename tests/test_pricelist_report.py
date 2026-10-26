# -*- coding: utf-8 -*-
import base64
import io
import zipfile

from odoo import fields
from odoo.tests.common import Form, TransactionCase, tagged


@tagged('post_install', '-at_install', 'lazona_pricelist_report')
class TestPricelistReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.other_currency = cls.env['res.currency'].create({
            'name': 'LZT', 'symbol': 'LZ', 'rounding': 0.01})
        cls.env['res.currency.rate'].create({
            'currency_id': cls.other_currency.id, 'company_id': cls.company.id,
            'name': fields.Date.today(), 'rate': 40.0})
        cls.tax = cls.env['account.tax'].create({
            'name': 'IVA 16 report', 'amount': 16.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'company_id': cls.company.id})
        cls.category = cls.env['product.category'].create({'name': 'Repuestos test'})
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Precio 1 test', 'currency_id': cls.currency.id,
            'lazona_conversion_currency_id': cls.other_currency.id})
        # Regla de la captura: costo, margen bruto 35 %, redondeo 1,00 hacia
        # arriba con IVA incluido.
        cls.env['product.pricelist.item'].create({
            'pricelist_id': cls.pricelist.id, 'applied_on': '3_global',
            'compute_price': 'formula', 'base': 'standard_price',
            'price_discount': -35.0, 'gross_margin': True,
            'price_round': 1.0, 'price_round_method': 'UP',
            'lazona_round_tax_included': True,
        })
        cls.product = cls._product('Filtro report', 13.8385)
        cls.no_price = cls._product('Sin precio report', 0.0, list_price=0.0)

    @classmethod
    def _product(cls, name, cost, **vals):
        return cls.env['product.product'].create(dict({
            'name': name, 'standard_price': cost, 'categ_id': cls.category.id,
            'sale_ok': True, 'taxes_id': [(6, 0, cls.tax.ids)]}, **vals))

    def _wizard(self, **vals):
        return self.env['lazona.pricelist.report.wizard'].create(dict({
            'pricelist_id': self.pricelist.id, 'categ_ids': [(6, 0, self.category.ids)],
        }, **vals))

    def _line(self, wizard, product):
        return next(line for line in wizard._get_report_lines() if line['product'] == product)

    def test_price_follows_rule_rounding_with_tax(self):
        line = self._line(self._wizard(), self.product)
        self.assertAlmostEqual(line['price_untaxed'], 21.55, places=2)
        self.assertAlmostEqual(line['price_total'], 25.0, places=2)

    def test_price_matches_sale_price(self):
        line = self._line(self._wizard(), self.product)
        expected = self.pricelist._get_product_price(self.product, 1.0)
        self.assertAlmostEqual(line['price'], expected, places=4)

    def test_conversion_taxes_converted_untaxed_price(self):
        line = self._line(self._wizard(), self.product)
        converted = self.currency._convert(
            line['price'], self.other_currency, self.company, fields.Date.today(), round=False)
        self.assertAlmostEqual(line['converted_untaxed'], round(converted, 2), places=2)
        self.assertAlmostEqual(line['converted_total'], round(round(converted, 2) * 1.16, 2), places=2)

    def test_hide_zero_price(self):
        products = [line['product'] for line in self._wizard()._get_report_lines()]
        self.assertNotIn(self.no_price, products)
        products = [line['product'] for line in self._wizard(hide_zero_price=False)._get_report_lines()]
        self.assertIn(self.no_price, products)

    def test_without_conversion(self):
        line = self._line(self._wizard(show_conversion=False), self.product)
        self.assertNotIn('converted_total', line)

    def test_form_without_pricelist(self):
        # Desde el menú el asistente abre sin lista de precios.
        with Form(self.env['lazona.pricelist.report.wizard']) as form:
            self.assertFalse(form.conversion_currency_id)
            form.pricelist_id = self.pricelist
            self.assertEqual(form.conversion_currency_id, self.other_currency)

    def test_export_xlsx(self):
        wizard = self._wizard()
        action = wizard.action_export_xlsx()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        content = base64.b64decode(wizard.file_data)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            strings = archive.read('xl/sharedStrings.xml').decode()
        self.assertIn('Filtro report', strings)
        self.assertTrue(wizard.file_name.endswith('.xlsx'))

    def test_render_pdf_html(self):
        wizard = self._wizard()
        html, _format = self.env['ir.actions.report']._render_qweb_html(
            'ingeint_custom_lazona.action_report_pricelist', wizard.ids)
        self.assertIn('Filtro report', html.decode())
        self.assertIn('Precio 1 test', html.decode())
