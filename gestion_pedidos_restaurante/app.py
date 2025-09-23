from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Crear la aplicación con las carpetas correctas
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

# Configuración de la base de datos SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'restaurante.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# ===== MODELOS =====

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
    estado = db.Column(db.String(20), default='pendiente')
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

class DetallePedido(db.Model):
    """Modelo para los detalles de cada pedido"""
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

# ===== RUTAS PRINCIPALES =====

@app.route('/')
def index():
    """Página principal del restaurante"""
    total_pedidos = Pedido.query.count()
    total_productos = Producto.query.count()
    pedidos_recientes = Pedido.query.order_by(Pedido.fecha.desc()).limit(5).all()
    
    return render_template('index.html', 
                         total_pedidos=total_pedidos,
                         total_productos=total_productos,
                         pedidos_recientes=pedidos_recientes)

@app.route('/menu')
def menu():
    """Mostrar el menú completo"""
    productos = Producto.query.filter_by(disponible=True).all()
    return render_template('menu.html', productos=productos)

# ===== RUTAS DE PEDIDOS =====

@app.route('/pedidos/')
def lista_pedidos():
    """Mostrar lista de todos los pedidos"""
    page = request.args.get('page', 1, type=int)
    estado = request.args.get('estado', 'todos')
    
    if estado == 'todos':
        pedidos = Pedido.query.order_by(Pedido.fecha.desc()).paginate(
            page=page, per_page=10, error_out=False)
    else:
        pedidos = Pedido.query.filter_by(estado=estado).order_by(
            Pedido.fecha.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('pedidos/lista.html', pedidos=pedidos, estado_filtro=estado)

@app.route('/pedidos/nuevo', methods=['GET', 'POST'])
def nuevo_pedido():
    """Crear un nuevo pedido"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            cliente_nombre = request.form.get('cliente_nombre')
            cliente_telefono = request.form.get('cliente_telefono')
            mesa = request.form.get('mesa')
            observaciones = request.form.get('observaciones')
            
            # Crear el pedido
            pedido = Pedido(
                cliente_nombre=cliente_nombre,
                cliente_telefono=cliente_telefono,
                mesa=mesa,
                observaciones=observaciones,
                estado='pendiente'
            )
            
            db.session.add(pedido)
            db.session.flush()  # Para obtener el ID del pedido
            
            # Procesar productos seleccionados
            productos_ids = request.form.getlist('producto_id')
            cantidades = request.form.getlist('cantidad')
            observaciones_detalle = request.form.getlist('observaciones_detalle')
            
            total_pedido = 0
            
            for i, producto_id in enumerate(productos_ids):
                if producto_id and cantidades[i]:
                    producto = Producto.query.get(int(producto_id))
                    cantidad = int(cantidades[i])
                    
                    if producto and cantidad > 0:
                        detalle = DetallePedido(
                            pedido_id=pedido.id,
                            producto_id=producto.id,
                            cantidad=cantidad,
                            precio_unitario=producto.precio,
                            observaciones=observaciones_detalle[i] if i < len(observaciones_detalle) else None
                        )
                        detalle.calcular_subtotal()
                        db.session.add(detalle)
                        total_pedido += detalle.subtotal
            
            pedido.total = total_pedido
            db.session.commit()
            
            flash(f'Pedido #{pedido.id} creado exitosamente', 'success')
            return redirect(url_for('ver_pedido', id=pedido.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el pedido: {str(e)}', 'error')
    
    # GET: mostrar formulario
    productos = Producto.query.filter_by(disponible=True).order_by(Producto.categoria, Producto.nombre).all()
    # Convertir productos a diccionarios para JSON
    productos_dict = [producto.to_dict() for producto in productos]
    return render_template('pedidos/nuevo.html', productos=productos, productos_json=productos_dict)

@app.route('/pedidos/<int:id>')
def ver_pedido(id):
    """Ver detalles de un pedido específico"""
    pedido = Pedido.query.get_or_404(id)
    return render_template('pedidos/detalle.html', pedido=pedido)

@app.route('/pedidos/<int:id>/cambiar_estado', methods=['POST'])
def cambiar_estado(id):
    """Cambiar el estado de un pedido"""
    pedido = Pedido.query.get_or_404(id)
    nuevo_estado = request.form.get('estado')
    
    estados_validos = ['pendiente', 'preparando', 'listo', 'entregado', 'cancelado']
    
    if nuevo_estado in estados_validos:
        pedido.estado = nuevo_estado
        db.session.commit()
        flash(f'Estado del pedido #{pedido.id} cambiado a {nuevo_estado}', 'success')
    else:
        flash('Estado no válido', 'error')
    
    return redirect(url_for('ver_pedido', id=id))

@app.route('/pedidos/<int:id>/eliminar', methods=['POST'])
def eliminar_pedido(id):
    """Eliminar un pedido"""
    pedido = Pedido.query.get_or_404(id)
    
    try:
        db.session.delete(pedido)
        db.session.commit()
        flash(f'Pedido #{id} eliminado correctamente', 'success')
        return redirect(url_for('lista_pedidos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el pedido: {str(e)}', 'error')
        return redirect(url_for('ver_pedido', id=id))

# ===== RUTAS DE PRODUCTOS =====

@app.route('/productos/')
def lista_productos():
    """Mostrar lista de todos los productos"""
    categoria = request.args.get('categoria', 'todos')
    buscar = request.args.get('buscar', '')
    
    query = Producto.query
    
    if categoria != 'todos':
        query = query.filter_by(categoria=categoria)
    
    if buscar:
        query = query.filter(Producto.nombre.contains(buscar))
    
    productos = query.order_by(Producto.categoria, Producto.nombre).all()
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [cat[0] for cat in categorias]
    
    return render_template('productos/lista.html', 
                         productos=productos, 
                         categorias=categorias,
                         categoria_filtro=categoria,
                         buscar=buscar)

@app.route('/productos/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    """Crear un nuevo producto"""
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            precio = float(request.form.get('precio'))
            categoria = request.form.get('categoria')
            nueva_categoria = request.form.get('nueva_categoria')
            disponible = 'disponible' in request.form
            
            # Si se especifica una nueva categoría, usarla
            if nueva_categoria:
                categoria = nueva_categoria
            
            producto = Producto(
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                categoria=categoria,
                disponible=disponible
            )
            
            db.session.add(producto)
            db.session.commit()
            
            flash(f'Producto "{nombre}" creado exitosamente', 'success')
            return redirect(url_for('lista_productos'))
            
        except ValueError:
            flash('Por favor ingresa un precio válido', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el producto: {str(e)}', 'error')
    
    # Obtener categorías existentes para el formulario
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [cat[0] for cat in categorias]
    
    return render_template('productos/nuevo.html', categorias=categorias)

@app.route('/productos/<int:id>')
def ver_producto(id):
    """Ver detalles de un producto específico"""
    producto = Producto.query.get_or_404(id)
    return render_template('productos/detalle.html', producto=producto)

@app.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
def editar_producto(id):
    """Editar un producto existente"""
    producto = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            producto.nombre = request.form.get('nombre')
            producto.descripcion = request.form.get('descripcion')
            producto.precio = float(request.form.get('precio'))
            
            categoria = request.form.get('categoria')
            nueva_categoria = request.form.get('nueva_categoria')
            
            # Si se especifica una nueva categoría, usarla
            if nueva_categoria:
                producto.categoria = nueva_categoria
            else:
                producto.categoria = categoria
                
            producto.disponible = 'disponible' in request.form
            
            db.session.commit()
            
            flash(f'Producto "{producto.nombre}" actualizado exitosamente', 'success')
            return redirect(url_for('ver_producto', id=id))
            
        except ValueError:
            flash('Por favor ingresa un precio válido', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el producto: {str(e)}', 'error')
    
    # Obtener categorías existentes para el formulario
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [cat[0] for cat in categorias]
    
    return render_template('productos/editar.html', producto=producto, categorias=categorias)

@app.route('/productos/<int:id>/toggle_disponibilidad', methods=['POST'])
def toggle_disponibilidad(id):
    """Cambiar la disponibilidad de un producto"""
    producto = Producto.query.get_or_404(id)
    producto.disponible = not producto.disponible
    
    try:
        db.session.commit()
        estado = "disponible" if producto.disponible else "no disponible"
        flash(f'Producto "{producto.nombre}" marcado como {estado}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar disponibilidad: {str(e)}', 'error')
    
    return redirect(url_for('ver_producto', id=id))

@app.route('/productos/<int:id>/eliminar', methods=['POST'])
def eliminar_producto(id):
    """Eliminar un producto"""
    producto = Producto.query.get_or_404(id)
    
    try:
        # Verificar si el producto tiene pedidos asociados
        if producto.detalles_pedido:
            flash(f'No se puede eliminar "{producto.nombre}" porque tiene pedidos asociados. '
                  'Puedes marcarlo como no disponible en su lugar.', 'warning')
            return redirect(url_for('ver_producto', id=id))
        
        nombre = producto.nombre
        db.session.delete(producto)
        db.session.commit()
        
        flash(f'Producto "{nombre}" eliminado correctamente', 'success')
        return redirect(url_for('lista_productos'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el producto: {str(e)}', 'error')
        return redirect(url_for('ver_producto', id=id))

def crear_datos_iniciales():
    """Crear algunos productos iniciales para el restaurante"""
    if Producto.query.count() == 0:
        productos_iniciales = [
            Producto(nombre='Hamburguesa Clásica', precio=8500, categoria='Principal', disponible=True),
            Producto(nombre='Pizza Margherita', precio=12000, categoria='Principal', disponible=True),
            Producto(nombre='Ensalada César', precio=7000, categoria='Ensalada', disponible=True),
            Producto(nombre='Papas Fritas', precio=3500, categoria='Acompañamiento', disponible=True),
            Producto(nombre='Gaseosa', precio=2500, categoria='Bebida', disponible=True),
            Producto(nombre='Agua', precio=1500, categoria='Bebida', disponible=True),
        ]
        
        for producto in productos_iniciales:
            db.session.add(producto)
        
        db.session.commit()
        print("Datos iniciales creados correctamente")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        crear_datos_iniciales()
    
    # Configuración para despliegue en producción
    import os
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    if debug:
        print("Servidor iniciado en http://127.0.0.1:5000")
        app.run(host='127.0.0.1', port=5000, debug=True)
    else:
        print(f"Servidor iniciado en producción en puerto {port}")
        app.run(host='0.0.0.0', port=port, debug=False)