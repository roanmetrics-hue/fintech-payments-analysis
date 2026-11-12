"""
main.py - Corre todo el proyecto de principio a fin.

Pasos: cargar -> limpiar -> transformar -> analizar -> graficar

Para correrlo, desde la carpeta del proyecto:
    python main.py
"""

import matplotlib.pyplot as plt
import pandas as pd

from limpieza import cargar, limpiar, resumen
from analisis import (
    transformar,
    tasa_fallidos_por_region,
    dinero_por_producto_y_metodo,
    dinero_por_producto_con_y_sin,
    fallidos_por_riesgo,
    fallidos_por_dia_semana,
    fallidos_por_fecha_valida,
)

from visualizacion import (
    grafico_dinero_por_producto,
    grafico_tasas_por_region,
    grafico_tasas_por_riesgo,
    grafico_mapa_producto_metodo,
)

RUTA_PAGOS = "data/pagos_fintech.csv"

# # Formato de las tablas en la terminal: más ancho, miles con coma y sin ".00" en los enteros.

pd.set_option("display.width", 120)
pd.set_option("display.float_format", lambda v: f"{v:,.0f}" if v == int(v) else f"{v:,.2f}")


def titulo(texto):
    """Imprime un separador con un título, para que la salida se lea por partes."""
    print()
    print("=" * 70)
    print(texto)
    print("=" * 70)


def main():
    # 1. Cargar
    titulo("1. CARGAR")
    original = cargar(RUTA_PAGOS)
    print("Filas y columnas:", original.shape)

    # 2. Limpiar
    titulo("2. LIMPIAR")
    limpio = limpiar(original)
    resumen(original, limpio)

    # 3. Transformar
    titulo("3. TRANSFORMAR")
    print("Filas y columnas antes de transformar:", limpio.shape)
    df = transformar(limpio)
    print("Filas y columnas después de transformar:", df.shape)
    nuevas = [col for col in df.columns if col not in limpio.columns]
    print(f"Columnas nuevas ({len(nuevas)}):", ", ".join(nuevas))

    # 4. Analizar: una tabla por pregunta
    titulo("4. ANALIZAR")

    print("\nPregunta 1: ¿Qué región tiene la mayor tasa de pagos fallidos y de contracargos?")
    tasas_region = tasa_fallidos_por_region(df)
    print(tasas_region)
    sin_vacios = tasas_region.drop(index="Sin región")
    print(f"-> Respuesta: {sin_vacios.index[0]} tiene la tasa más alta ({sin_vacios['tasa_total'].iloc[0]:.2f} %), "
          f"casi empatada con {sin_vacios.index[1]} y {sin_vacios.index[2]}.")
    print(f"   {sin_vacios['tasa_total'].idxmin()} es la más baja porque no tiene contracargos.")

    print("\nPregunta 2: ¿Qué tipo de producto y qué método de pago mueven más dinero? (US$)")
    dinero = dinero_por_producto_y_metodo(df)
    print(dinero)
    producto_top = dinero["Total"].drop("Total").idxmax()
    metodo_top = dinero.loc["Total"].drop("Total").idxmax()
    print(f"-> Respuesta: el producto que más dinero mueve es {producto_top} "
          f"(US${dinero.loc[producto_top, 'Total']:,.0f}) y el método es {metodo_top} "
          f"(US${dinero.loc['Total', metodo_top]:,.0f}).")

    print("\nPregunta 2, con y sin los pagos de 50 000 (US$):")
    con_y_sin = dinero_por_producto_con_y_sin(df)
    print(con_y_sin)
    print(f"-> Con los 50 000, el primero sería {con_y_sin['con_50000'].idxmax()}; "
          f"sin ellos, {con_y_sin['sin_50000'].idxmax()}.")

    print("\nPregunta 3: ¿Los clientes de riesgo alto fallan más que los de riesgo bajo?")
    tasas_riesgo = fallidos_por_riesgo(df)
    print(tasas_riesgo)
    alto = tasas_riesgo.loc["High", "tasa_total"]
    bajo = tasas_riesgo.loc["Low", "tasa_total"]
    print(f"-> Respuesta: sí. El riesgo alto falla {alto:.2f} % contra {bajo:.2f} % del bajo "
          f"({alto / bajo:.1f} veces más), sobre todo por contracargos.")
    
    
    print("\nExtra: ¿Cambia la tasa de fallidos según el día de la semana?")
    tasas_dia = fallidos_por_dia_semana(df)
    print(tasas_dia)
    print(f"-> Más alta: {tasas_dia['tasa_total'].idxmax()} ({tasas_dia['tasa_total'].max():.2f} %); "
          f"más baja: {tasas_dia['tasa_total'].idxmin()} ({tasas_dia['tasa_total'].min():.2f} %).")

    print("\nControl: ¿las fechas 2024-02-30 fallan igual que las válidas?")
    print(fallidos_por_fecha_valida(df))

    # 5. Graficar: cada función recibe la tabla de su pregunta y guarda el PNG
    titulo("5. GRAFICAR")
    graficos = [
        grafico_dinero_por_producto(con_y_sin),
        grafico_tasas_por_region(tasas_region),
        grafico_tasas_por_riesgo(tasas_riesgo),
        grafico_mapa_producto_metodo(dinero),
    ]
    for fig in graficos:
        plt.close(fig)  # libero la memoria; ya están guardados
    print(f"{len(graficos)} gráficos guardados en la carpeta graficos/")

    titulo("LISTO")


if __name__ == "__main__":
    main()
