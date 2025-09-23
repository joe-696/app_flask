Sistema de Gestión de Pedidos para Restaurante

Un sistema web simple y funcional desarrollado en Flask para gestionar pedidos de un restaurante.

Características

Gestión de Productos: Crear, editar, ver y administrar productos del menú

Gestión de Pedidos: Crear nuevos pedidos, cambiar estados, y ver historial

Interface Moderna: Diseño responsive con Bootstrap 5

Base de Datos: SQLite integrado (sin configuración adicional)

Modular: Organizado en blueprints para fácil mantenimiento

Estados de Pedido: Pendiente, Preparando, Listo, Entregado, Cancelado

Instalación y Uso

Instalar Dependencias
pip install -r requirements.txt

Ejecutar la Aplicación
python app.py

La aplicación estará disponible en: http://127.0.0.1:5000

Estructura del Proyecto

gestion_pedidos_restaurante/
├── app.py Aplicación principal
├── requirements.txt Dependencias
├── restaurante.db Base de datos SQLite (se crea automáticamente)
└── app/
├── init.py
├── models/
│ ├── init.py
│ └── models.py Modelos de datos (Producto, Pedido, DetallePedido)
├── pedidos/
│ ├── init.py
│ └── routes.py Rutas para gestión de pedidos
├── productos/
│ ├── init.py
│ └── routes.py Rutas para gestión de productos
├── templates/
│ ├── base.html Template base
│ ├── index.html Página principal
│ ├── menu.html Menú público
│ ├── pedidos/
│ │ ├── lista.html Lista de pedidos
│ │ ├── nuevo.html Crear nuevo pedido
│ │ └── detalle.html Ver detalles de pedido
│ └── productos/
│ ├── lista.html Lista de productos
│ └── nuevo.html Crear nuevo producto
└── static/
└── css/

Funcionalidades

Dashboard Principal

Resumen de estadísticas

Pedidos recientes

Accesos rápidos

Gestión de Productos

Crear nuevos productos

Organizar por categorías

Controlar disponibilidad

Editar precios y descripciones

Gestión de Pedidos

Crear pedidos con múltiples productos

Información de cliente y mesa

Estados de seguimiento

Historial completo

Filtros por estado

Base de Datos

Productos: nombre, descripción, precio, categoría, disponibilidad

Pedidos: cliente, mesa, estado, total, fecha, observaciones

Detalles de Pedido: productos individuales con cantidad y subtotales

Datos Iniciales

Al ejecutar por primera vez, se crean automáticamente productos de ejemplo:

Hamburguesa Clásica (8500)

Pizza Margherita (12000)

Ensalada César (7000)

Papas Fritas (3500)

Gaseosa (2500)

Agua (1500)

Tecnologías Utilizadas

Backend: Flask, SQLAlchemy

Frontend: HTML5, CSS3, JavaScript, Bootstrap 5

Base de Datos: SQLite

Icons: Bootstrap Icons