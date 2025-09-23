#!/usr/bin/env python3
# Script para verificar el contenido de la base de datos

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar desde app.py directamente
exec(open('app.py').read())

# Verificar pedidos
with app.app_context():
    pedidos = Pedido.query.all()
    print(f"Total pedidos en la base de datos: {len(pedidos)}")
    
    if pedidos:
        print("\nPrimeros 5 pedidos:")
        for p in pedidos[:5]:
            print(f"- Pedido {p.id}: {p.cliente_nombre}, Mesa {p.mesa}, Estado: {p.estado}")
    else:
        print("No hay pedidos en la base de datos")
        
    # Verificar productos también
    productos = Producto.query.all()
    print(f"\nTotal productos: {len(productos)}")
    if productos:
        print("Algunos productos:")
        for prod in productos[:3]:
            print(f"- {prod.nombre}: ${prod.precio}")