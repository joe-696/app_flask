from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
import os

# Crear la aplicación con las carpetas correctas
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

# Configuración de la base de datos SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'restaurante.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta_muy_segura_aqui_2025'

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ===== DECORADORES DE PERMISOS =====

def requiere_permiso(rol_requerido):
    """Decorador para verificar permisos por rol"""
    def decorador(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.rol != rol_requerido and current_user.rol != 'admin':
                flash('No tienes permisos para acceder a esta sección', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorador

# ===== MODELOS =====

class Usuario(UserMixin, db.Model):
    """Modelo para usuarios del sistema con roles"""
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    nombre_completo = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='mesero')  # admin, mesero, cocinero
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'

class Mesa(db.Model):
    """Modelo para las mesas del restaurante"""
    __tablename__ = 'mesas'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    capacidad = db.Column(db.Integer, nullable=False, default=4)
    estado = db.Column(db.String(20), default='disponible')  # disponible, ocupada, reservada
    ubicacion = db.Column(db.String(50))  # interior, terraza, vip
    activa = db.Column(db.Boolean, default=True)
    
    # Relación con pedidos
    pedidos = db.relationship('Pedido', backref='mesa_info', lazy=True)
    
    def __repr__(self):
        return f'<Mesa {self.numero}>'

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
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'))  # Relación con Mesa
    mesa_numero = db.Column(db.String(10))  # Mantener compatibilidad
    estado = db.Column(db.String(20), default='pendiente')
    total = db.Column(db.Float, default=0.0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observaciones = db.Column(db.Text)
    
    # Referencias de usuario
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))  # Quien tomó el pedido
    cocinero_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))  # Quien lo preparó
    
    # Relaciones
    detalles = db.relationship('DetallePedido', backref='pedido', lazy=True, cascade='all, delete-orphan')
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='pedidos_tomados')
    cocinero = db.relationship('Usuario', foreign_keys=[cocinero_id], backref='pedidos_preparados')
    
    # Mantener compatibilidad con propiedad mesa
    @property
    def mesa(self):
        return self.mesa_numero or (self.mesa_info.numero if self.mesa_info else None)
    
    @mesa.setter
    def mesa(self, value):
        self.mesa_numero = value
    
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

# ===== RUTAS DE AUTENTICACIÓN =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and usuario.check_password(password) and usuario.activo:
            login_user(usuario)
            usuario.ultimo_acceso = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            flash(f'¡Bienvenido {usuario.nombre_completo}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    flash('Has cerrado sesión exitosamente', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
@requiere_permiso('admin')
def register():
    """Registro de nuevos usuarios (solo admin)"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        nombre_completo = request.form.get('nombre_completo')
        rol = request.form.get('rol')
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return render_template('auth/register.html')
        
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return render_template('auth/register.html')
        
        # Crear nuevo usuario
        usuario = Usuario(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            rol=rol
        )
        usuario.set_password(password)
        
        db.session.add(usuario)
        db.session.commit()
        
        flash(f'Usuario {username} creado exitosamente', 'success')
        return redirect(url_for('empleados'))
    
    return render_template('auth/register.html')

# ===== RUTAS DE EMPLEADOS =====

@app.route('/empleados/')
@login_required
@requiere_permiso('admin')
def empleados():
    """Lista de empleados"""
    page = request.args.get('page', 1, type=int)
    empleados = Usuario.query.paginate(page=page, per_page=10, error_out=False)
    return render_template('empleados/lista.html', empleados=empleados)

@app.route('/empleados/<int:id>')
@login_required
@requiere_permiso('admin')
def ver_empleado(id):
    """Ver detalles de empleado"""
    empleado = Usuario.query.get_or_404(id)
    return render_template('empleados/detalle.html', empleado=empleado)

@app.route('/empleados/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requiere_permiso('admin')
def editar_empleado(id):
    """Editar empleado"""
    empleado = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        empleado.nombre_completo = request.form.get('nombre_completo')
        empleado.email = request.form.get('email')
        empleado.rol = request.form.get('rol')
        empleado.activo = 'activo' in request.form
        
        # Cambiar contraseña si se proporciona
        new_password = request.form.get('password')
        if new_password:
            empleado.set_password(new_password)
        
        db.session.commit()
        flash(f'Empleado {empleado.username} actualizado exitosamente', 'success')
        return redirect(url_for('ver_empleado', id=id))
    
    return render_template('empleados/editar.html', empleado=empleado)

@app.route('/empleados/<int:id>/toggle')
@login_required
@requiere_permiso('admin')
def toggle_empleado(id):
    """Activar/desactivar empleado"""
    empleado = Usuario.query.get_or_404(id)
    empleado.activo = not empleado.activo
    db.session.commit()
    
    estado = 'activado' if empleado.activo else 'desactivado'
    flash(f'Empleado {empleado.username} {estado}', 'success')
    return redirect(url_for('empleados'))

# ===== RUTAS DE MESAS =====

@app.route('/mesas/')
@login_required
def mesas():
    """Lista de mesas"""
    mesas = Mesa.query.filter_by(activa=True).all()
    return render_template('mesas/lista.html', mesas=mesas)

@app.route('/mesas/nueva', methods=['GET', 'POST'])
@login_required
@requiere_permiso('admin')
def nueva_mesa():
    """Crear nueva mesa"""
    if request.method == 'POST':
        numero = request.form.get('numero')
        capacidad = int(request.form.get('capacidad', 4))
        ubicacion = request.form.get('ubicacion')
        
        # Verificar que no exista mesa con ese número
        if Mesa.query.filter_by(numero=numero).first():
            flash('Ya existe una mesa con ese número', 'error')
            return render_template('mesas/nueva.html')
        
        mesa = Mesa(numero=numero, capacidad=capacidad, ubicacion=ubicacion)
        db.session.add(mesa)
        db.session.commit()
        
        flash(f'Mesa {numero} creada exitosamente', 'success')
        return redirect(url_for('mesas'))
    
    return render_template('mesas/nueva.html')

@app.route('/mesas/<int:id>/estado', methods=['POST'])
@login_required
def cambiar_estado_mesa(id):
    """Cambiar estado de mesa"""
    mesa = Mesa.query.get_or_404(id)
    nuevo_estado = request.form.get('estado')
    
    if nuevo_estado in ['disponible', 'ocupada', 'reservada']:
        mesa.estado = nuevo_estado
        db.session.commit()
        flash(f'Mesa {mesa.numero} marcada como {nuevo_estado}', 'success')
    
    return redirect(url_for('mesas'))

# ===== RUTAS DE REPORTES =====

@app.route('/reportes/')
@login_required
@requiere_permiso('admin')
def reportes():
    """Dashboard de reportes"""
    return render_template('reportes/dashboard.html')

@app.route('/reportes/ventas')
@login_required
@requiere_permiso('admin')
def reporte_ventas():
    """Reporte de ventas"""
    fecha_inicio = request.args.get('fecha_inicio', date.today().replace(day=1))
    fecha_fin = request.args.get('fecha_fin', date.today())
    
    # Convertir strings a fechas si es necesario
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    if isinstance(fecha_fin, str):
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    
    # Consultas de reportes
    pedidos = Pedido.query.filter(
        Pedido.fecha >= fecha_inicio,
        Pedido.fecha <= fecha_fin
    ).all()
    
    total_ventas = sum(p.total for p in pedidos)
    pedidos_por_dia = {}
    
    for pedido in pedidos:
        dia = pedido.fecha.date()
        if dia not in pedidos_por_dia:
            pedidos_por_dia[dia] = {'cantidad': 0, 'total': 0}
        pedidos_por_dia[dia]['cantidad'] += 1
        pedidos_por_dia[dia]['total'] += pedido.total
    
    return render_template('reportes/ventas.html', 
                         pedidos=pedidos, 
                         total_ventas=total_ventas,
                         pedidos_por_dia=pedidos_por_dia,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin)

@app.route('/reportes/productos')
@login_required
@requiere_permiso('admin')
def reporte_productos():
    """Reporte de productos más vendidos"""
    # Consulta para productos más vendidos
    from sqlalchemy import func
    
    productos_vendidos = db.session.query(
        Producto.nombre,
        func.sum(DetallePedido.cantidad).label('total_vendido'),
        func.sum(DetallePedido.subtotal).label('ingresos')
    ).join(DetallePedido).group_by(Producto.id).order_by(
        func.sum(DetallePedido.cantidad).desc()
    ).limit(10).all()
    
    return render_template('reportes/productos.html', productos_vendidos=productos_vendidos)

# ===== RUTAS PRINCIPALES =====

@app.route('/')
@login_required
def index():
    """Página principal del restaurante"""
    total_pedidos = Pedido.query.count()
    total_productos = Producto.query.count()
    total_usuarios = Usuario.query.filter_by(activo=True).count()
    total_mesas = Mesa.query.filter_by(activa=True).count()
    
    # Estadísticas del día actual
    hoy = date.today()
    pedidos_hoy = Pedido.query.filter(
        Pedido.fecha >= hoy,
        Pedido.fecha < hoy.replace(day=hoy.day + 1) if hoy.day < 28 else hoy.replace(month=hoy.month + 1, day=1)
    ).count()
    
    pedidos_recientes = Pedido.query.order_by(Pedido.fecha.desc()).limit(5).all()
    
    return render_template('index.html', 
                         total_pedidos=total_pedidos,
                         total_productos=total_productos,
                         total_usuarios=total_usuarios,
                         total_mesas=total_mesas,
                         pedidos_hoy=pedidos_hoy,
                         pedidos_recientes=pedidos_recientes)

@app.route('/menu')
def menu():
    """Mostrar el menú completo (público)"""
    productos = Producto.query.filter_by(disponible=True).all()
    return render_template('menu.html', productos=productos)

# ===== RUTAS DE PEDIDOS =====

@app.route('/pedidos/')
@login_required
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
@login_required
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
    """Crear datos iniciales para el restaurante"""
    
    # Crear usuario administrador por defecto
    if Usuario.query.count() == 0:
        admin = Usuario(
            username='admin',
            email='admin@restaurante.com',
            nombre_completo='Administrador del Sistema',
            rol='admin'
        )
        admin.set_password('admin123')  # Cambiar en producción
        db.session.add(admin)
        
        # Crear usuarios de ejemplo
        mesero1 = Usuario(
            username='mesero1',
            email='mesero1@restaurante.com',
            nombre_completo='Juan Pérez',
            rol='mesero'
        )
        mesero1.set_password('mesero123')
        db.session.add(mesero1)
        
        cocinero1 = Usuario(
            username='cocinero1',
            email='cocinero1@restaurante.com',
            nombre_completo='María González',
            rol='cocinero'
        )
        cocinero1.set_password('cocinero123')
        db.session.add(cocinero1)
        
        print("Usuarios iniciales creados")
    
    # Crear mesas por defecto
    if Mesa.query.count() == 0:
        mesas_iniciales = [
            Mesa(numero='1', capacidad=2, ubicacion='interior'),
            Mesa(numero='2', capacidad=4, ubicacion='interior'),
            Mesa(numero='3', capacidad=4, ubicacion='interior'),
            Mesa(numero='4', capacidad=6, ubicacion='interior'),
            Mesa(numero='5', capacidad=2, ubicacion='terraza'),
            Mesa(numero='6', capacidad=4, ubicacion='terraza'),
            Mesa(numero='VIP1', capacidad=8, ubicacion='vip'),
        ]
        
        for mesa in mesas_iniciales:
            db.session.add(mesa)
        
        print("Mesas iniciales creadas")
    
    # Crear productos iniciales
    if Producto.query.count() == 0:
        productos_iniciales = [
            Producto(nombre='Hamburguesa Clásica', precio=18.50, categoria='Principal', disponible=True,
                    descripcion='Hamburguesa de carne con lechuga, tomate, cebolla y papas fritas'),
            Producto(nombre='Pizza Margherita', precio=25.00, categoria='Principal', disponible=True,
                    descripcion='Pizza tradicional con tomate, mozzarella y albahaca fresca'),
            Producto(nombre='Ensalada César', precio=15.00, categoria='Ensalada', disponible=True,
                    descripcion='Lechuga romana, crutones, queso parmesano y aderezo césar'),
            Producto(nombre='Papas Fritas', precio=8.00, categoria='Acompañamiento', disponible=True,
                    descripcion='Papas fritas doradas y crujientes con sal marina'),
            Producto(nombre='Limonada', precio=6.00, categoria='Bebida', disponible=True,
                    descripcion='Limonada natural refrescante con hielo y menta'),
            Producto(nombre='Pollo a la Plancha', precio=22.00, categoria='Principal', disponible=True,
                    descripcion='Pechuga de pollo a la plancha con verduras y arroz'),
            Producto(nombre='Ceviche Mixto', precio=28.00, categoria='Marina', disponible=True,
                    descripcion='Ceviche de pescado y mariscos con camote y choclo'),
            Producto(nombre='Lomo Saltado', precio=26.00, categoria='Principal', disponible=True,
                    descripcion='Lomo de res saltado con cebolla, tomate y papas fritas'),
        ]
        
        for producto in productos_iniciales:
            db.session.add(producto)
        
        print("Productos iniciales creados")
    
    # Crear pedidos de ejemplo
    if Pedido.query.count() == 0:
        # Obtener usuarios y mesa para el ejemplo
        admin = Usuario.query.filter_by(username='admin').first()
        mesero = Usuario.query.filter_by(rol='mesero').first()
        mesa1 = Mesa.query.filter_by(numero='1').first()
        mesa2 = Mesa.query.filter_by(numero='2').first()
        
        if admin and mesa1:
            # Pedido ejemplo 1
            pedido1 = Pedido(
                cliente_nombre='Carlos Mendoza',
                cliente_telefono='987654321',
                mesa_id=mesa1.id,
                mesa_numero=mesa1.numero,
                estado='entregado',
                usuario_id=mesero.id if mesero else admin.id,
                observaciones='Sin cebolla'
            )
            
            # Pedido ejemplo 2
            pedido2 = Pedido(
                cliente_nombre='Ana Torres',
                cliente_telefono='123456789',
                mesa_id=mesa2.id if mesa2 else mesa1.id,
                mesa_numero=mesa2.numero if mesa2 else mesa1.numero,
                estado='preparando',
                usuario_id=admin.id,
                observaciones='Extra salsa'
            )
            
            db.session.add(pedido1)
            db.session.add(pedido2)
            
            # Commit para obtener IDs
            db.session.commit()
            
            # Productos para los detalles
            hamburguesa = Producto.query.filter_by(nombre='Hamburguesa Clásica').first()
            papas = Producto.query.filter_by(nombre='Papas Fritas').first()
            limonada = Producto.query.filter_by(nombre='Limonada').first()
            
            if hamburguesa and papas and limonada:
                # Detalles pedido 1
                detalle1 = DetallePedido(
                    pedido_id=pedido1.id,
                    producto_id=hamburguesa.id,
                    cantidad=1,
                    precio_unitario=hamburguesa.precio
                )
                detalle1.calcular_subtotal()
                
                detalle2 = DetallePedido(
                    pedido_id=pedido1.id,
                    producto_id=papas.id,
                    cantidad=1,
                    precio_unitario=papas.precio
                )
                detalle2.calcular_subtotal()
                
                # Detalles pedido 2
                detalle3 = DetallePedido(
                    pedido_id=pedido2.id,
                    producto_id=limonada.id,
                    cantidad=2,
                    precio_unitario=limonada.precio
                )
                detalle3.calcular_subtotal()
                
                db.session.add_all([detalle1, detalle2, detalle3])
                
                # Calcular totales
                pedido1.calcular_total()
                pedido2.calcular_total()
        
        print("Pedidos de ejemplo creados")
    
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