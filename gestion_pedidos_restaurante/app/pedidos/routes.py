from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

# Las importaciones se harán después de que la app esté configurada
pedidos_bp = Blueprint('pedidos', __name__)

# Variables que serán configuradas por la aplicación principal
Pedido = None
DetallePedido = None  
Producto = None
db = None

def init_routes(app_db, app_models):
    """Inicializar las rutas con la instancia de db y modelos de la aplicación"""
    global db, Pedido, DetallePedido, Producto
    db = app_db
    Pedido = app_models['Pedido']
    DetallePedido = app_models['DetallePedido']
    Producto = app_models['Producto']

pedidos_bp = Blueprint('pedidos', __name__)

@pedidos_bp.route('/')
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

@pedidos_bp.route('/nuevo', methods=['GET', 'POST'])
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
            return redirect(url_for('pedidos.ver_pedido', id=pedido.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el pedido: {str(e)}', 'error')
    
    # GET: mostrar formulario
    productos = Producto.query.filter_by(disponible=True).order_by(Producto.categoria, Producto.nombre).all()
    return render_template('pedidos/nuevo.html', productos=productos)

@pedidos_bp.route('/<int:id>')
def ver_pedido(id):
    """Ver detalles de un pedido específico"""
    pedido = Pedido.query.get_or_404(id)
    return render_template('pedidos/detalle.html', pedido=pedido)

@pedidos_bp.route('/<int:id>/cambiar_estado', methods=['POST'])
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
    
    return redirect(url_for('pedidos.ver_pedido', id=id))

@pedidos_bp.route('/<int:id>/eliminar', methods=['POST'])
def eliminar_pedido(id):
    """Eliminar un pedido"""
    pedido = Pedido.query.get_or_404(id)
    
    try:
        db.session.delete(pedido)
        db.session.commit()
        flash(f'Pedido #{id} eliminado correctamente', 'success')
        return redirect(url_for('pedidos.lista_pedidos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el pedido: {str(e)}', 'error')
        return redirect(url_for('pedidos.ver_pedido', id=id))

@pedidos_bp.route('/api/estados')
def api_estados():
    """API para obtener estadísticas de pedidos por estado"""
    estados = db.session.query(
        Pedido.estado, 
        db.func.count(Pedido.id)
    ).group_by(Pedido.estado).all()
    
    resultado = {estado: count for estado, count in estados}
    return jsonify(resultado)