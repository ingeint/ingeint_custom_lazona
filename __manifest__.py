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
    "version": "0.1",
    "depends": [
        "account",
        "sale_management",
        "ingeint_custom",
        "l10n_ve_custom",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "report/report_delivery_document.xml",
        "report/report_purchase_document.xml",
        "views/product_pricelist_views.xml",
        "views/templates.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
