from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    description_pickingout = fields.Text(
        string="Ubicación",
        related="product_tmpl_id.description_pickingout",
        readonly=True,
    )