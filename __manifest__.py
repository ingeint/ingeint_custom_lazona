# -*- coding: utf-8 -*-
{
    "name": "Ingeint Custom La Zona",
    "summary": "Conversión monetaria para productos en listas de precios",
    "description": """
        Agrega una visualización consistente de precios en doble moneda para reglas de listas de precios.
    """,
    "author": "INGEINT SA",
    "website": "http://www.ingeint.com",
    "category": "Sales",
    "version": "0.2",
    "depends": [
        "account",
        "sale_management",
        "ingeint_custom",
        "stock",
        "odoo_pos_ingeint"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/product_pricelist_views.xml",
        "views/product_pricelist_item_views.xml",
        "views/templates.xml",
        "views/product_catalog.xml",
        "wizards/pricelist_report_wizard_views.xml",
        "report/pricelist_report.xml",
        "report/pricelist_report_templates.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
