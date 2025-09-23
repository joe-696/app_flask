from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# La instancia de db se importará desde la aplicación principal
db = SQLAlchemy()

class Producto(db.Model):
    """Modelo para los productos/platillos del restaurante"""
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    disponible = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con detalles de pedido
    detalles_pedido = db.relationship('DetallePedido', backref='producto', lazy=True)
    
    def __repr__(self):
        return f'<Producto {self.nombre}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': self.precio,
            'categoria': self.categoria,
            'disponible': self.disponible
        }

class Pedido(db.Model):
    """Modelo para los pedidos del restaurante"""
    __tablename__ = 'pedidos'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_nombre = db.Column(db.String(100), nullable=False)
    cliente_telefono = db.Column(db.String(20))
    mesa = db.Column(db.String(10))
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, preparando, listo, entregado
    total = db.Column(db.Float, default=0.0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observaciones = db.Column(db.Text)
    
    # Relación con detalles del pedido
    detalles = db.relationship('DetallePedido', backref='pedido', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Pedido {self.id} - {self.cliente_nombre}>'
    
    def calcular_total(self):
        """Calcular el total del pedido basado en sus detalles"""
        total = sum(detalle.subtotal for detalle in self.detalles)
        self.total = total
        return total
    
    def to_dict(self):
        return {
            'id': self.id,
            'cliente_nombre': self.cliente_nombre,
            'cliente_telefono': self.cliente_telefono,
            'mesa': self.mesa,
            'estado': self.estado,
            'total': self.total,
            'fecha': self.fecha.strftime('%Y-%m-%d %H:%M:%S'),
            'observaciones': self.observaciones
        }

class DetallePedido(db.Model):
    """Modelo para los detalles de cada pedido (productos individuales)"""
    __tablename__ = 'detalles_pedido'
    
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    observaciones = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<DetallePedido {self.producto.nombre} x{self.cantidad}>'
    
    def calcular_subtotal(self):
        """Calcular el subtotal del detalle"""
        self.subtotal = self.cantidad * self.precio_unitario
        return self.subtotal
    
    def to_dict(self):
        return {
            'id': self.id,
            'producto_nombre': self.producto.nombre,
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario,
            'subtotal': self.subtotal,
            'observaciones': self.observaciones
        }