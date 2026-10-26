# Ingeint Custom La Zona

Modulo Odoo para mostrar la conversion monetaria de reglas de listas de precios.

## Contenido

- Configuracion de moneda de conversion por lista de precios.
- Calculo de precio convertido para reglas de listas de precios.
- Vista heredada para mostrar la columna Precio convertido.
- Reporte de lista de precios en PDF o Excel (Ventas > Reportes > Lista de precios,
  o Acción > Reporte de lista de precios desde la lista). Calcula cada precio con
  las reglas vigentes igual que un pedido de venta (margen bruto, tipo de redondeo,
  redondeo con IVA incluido, tarifa adicional y márgenes), muestra el precio sin y
  con IVA y, si aplica, su conversión a la moneda de conversión de la lista.

## Instalacion

Instalar o actualizar el modulo `ingeint_custom_lazona` desde Odoo o mediante `odoo-bin`.
