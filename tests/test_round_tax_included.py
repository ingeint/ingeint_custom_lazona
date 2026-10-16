# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'lazona_round_tax')
class TestRoundTaxIncluded(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.tax = cls.env['account.tax'].create({
            'name': 'IVA 16 test', 'amount': 16.0, 'amount_type': 'percent',
            'type_tax_use': 'sale', 'company_id': cls.company.id})
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Round tax test', 'currency_id': cls.currency.id})

    def _rule(self, **vals):
        return self.env['product.pricelist.item'].create(dict({
            'pricelist_id': self.pricelist.id, 'applied_on': '3_global',
            'compute_price': 'formula', 'base': 'standard_price',
            'price_discount': -35.0, 'gross_margin': True,
            'price_round': 1.0, 'price_round_method': 'UP',
            'lazona_round_tax_included': True,
        }, **vals))

    def _product(self, cost, taxes=None):
        return self.env['product.product'].create({
            'name': 'Round tax product', 'standard_price': cost,
            'taxes_id': [(6, 0, (taxes if taxes is not None else self.tax).ids)]})

    def _price(self, rule, product):
        return rule._compute_price(product, 1.0, product.uom_id, False, self.currency)

    def _catalog(self, product):
        return product.with_context(pricelist=self.pricelist.id).catalog_price_tax_included

    def test_rounds_tax_included_price_up(self):
        rule = self._rule()
        product = self._product(13.8385)  # 21.29 sin IVA -> 24.70 con IVA
        self.assertAlmostEqual(self._price(rule, product), 21.55, places=2)
        self.assertAlmostEqual(self._catalog(product), 25.0, places=2)

    def test_half_up_without_gross_margin(self):
        rule = self._rule(gross_margin=False, price_discount=0.0, price_round_method='HALF-UP')
        product = self._product(20.86)  # 24.1976 con IVA -> 24
        self.assertAlmostEqual(self._catalog(product), 24.0, places=2)

    def test_surcharge_applies_to_tax_included_price(self):
        rule = self._rule(price_surcharge=-0.01)
        product = self._product(13.8385)
        self.assertAlmostEqual(self._catalog(product), 24.99, places=2)

    def test_flag_off_keeps_untaxed_rounding(self):
        rule = self._rule(lazona_round_tax_included=False)
        product = self._product(13.8385)
        self.assertAlmostEqual(self._price(rule, product), 22.0, places=2)

    def test_product_without_taxes(self):
        rule = self._rule()
        product = self._product(13.8385, taxes=self.env['account.tax'])
        self.assertAlmostEqual(self._price(rule, product), 22.0, places=2)
