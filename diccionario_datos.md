# Diccionario de datos — Proyecto Final M03

Una fintech registra los pagos que hacen sus clientes por sus productos (billetera, tarjetas y préstamos).
Los datos vienen **tal como salieron del sistema**: tienen errores que tú debes encontrar y corregir.

## pagos_fintech.csv (100 000 filas)

Cada fila es un pago.

| Columna | Qué es |
|---|---|
| `payment_id` | Identificador del pago (debería ser único) |
| `customer_id` | Cliente que hizo el pago |
| `product_id` | Producto que se pagó (ver `productos.csv`) |
| `payment_amount` | Monto del pago, en la moneda de `currency` |
| `payment_status` | Estado del pago: pagado, pendiente, fallido o contracargo (*chargeback*) |
| `currency` | Moneda del pago |
| `pay_method` | Método de pago: tarjeta, efectivo o transferencia |
| `pay_dt` | Fecha y hora del pago |
| `region_id` | Región del cliente (ver `regiones.csv`) |
| `status_customer` | Estado de la cuenta del cliente |
| `risk_segment` | Segmento de riesgo del cliente |
| `kyc_level` | Nivel de verificación de identidad del cliente (*Know Your Customer*) |
| `income_bracket` | Rango de ingresos del cliente |
| `signup_dt` | Fecha en que el cliente abrió su cuenta |

## productos.csv

| Columna | Qué es |
|---|---|
| `product_id` | Identificador del producto |
| `product_type` | Tipo: Wallet (billetera), Card (tarjeta) o Loan (préstamo) |
| `interest_rate` | Tasa de interés anual del producto |
| `currency` | Moneda del producto |

## regiones.csv

| Columna | Qué es |
|---|---|
| `region_id` | Identificador de la región |
| `region_name` | Nombre de la región |
| `country` | País (código de dos letras) |

## Antes de empezar

- Carga con `pd.read_csv("pagos_fintech.csv")` y empieza **diagnosticando**: tipos, nulos, duplicados y valores únicos de cada columna de texto.
- No borres nada sin justificarlo: cada decisión de limpieza va explicada en un comentario.
