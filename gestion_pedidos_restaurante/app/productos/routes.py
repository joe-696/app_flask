from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

# Las importaciones se harán después de que la app esté configurada
productos_bp = Blueprint('productos', __name__)

# Variables que serán configuradas por la aplicación principal
Producto = None
db = None

def init_routes(app_db, app_models):
    """Inicializar las rutas con la instancia de db y modelos de la aplicación"""
    global db, Producto
    db = app_db
    Producto = app_models['Producto']

productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/')
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

@productos_bp.route('/nuevo', methods=['GET', 'POST'])
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
            return redirect(url_for('productos.lista_productos'))
            
        except ValueError:
            flash('Por favor ingresa un precio válido', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el producto: {str(e)}', 'error')
    
    # Obtener categorías existentes para el formulario
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [cat[0] for cat in categorias]
    
    return render_template('productos/nuevo.html', categorias=categorias)

@productos_bp.route('/<int:id>')
def ver_producto(id):
    """Ver detalles de un producto específico"""
    producto = Producto.query.get_or_404(id)
    return render_template('productos/detalle.html', producto=producto)

@productos_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
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
            return redirect(url_for('productos.ver_producto', id=id))
            
        except ValueError:
            flash('Por favor ingresa un precio válido', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el producto: {str(e)}', 'error')
    
    # Obtener categorías existentes para el formulario
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [cat[0] for cat in categorias]
    
    return render_template('productos/editar.html', producto=producto, categorias=categorias)

@productos_bp.route('/<int:id>/toggle_disponibilidad', methods=['POST'])
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
    
    return redirect(url_for('productos.ver_producto', id=id))

@productos_bp.route('/<int:id>/eliminar', methods=['POST'])
def eliminar_producto(id):
    """Eliminar un producto"""
    producto = Producto.query.get_or_404(id)
    
    try:
        # Verificar si el producto tiene pedidos asociados
        if producto.detalles_pedido:
            flash(f'No se puede eliminar "{producto.nombre}" porque tiene pedidos asociados. '
                  'Puedes marcarlo como no disponible en su lugar.', 'warning')
            return redirect(url_for('productos.ver_producto', id=id))
        
        nombre = producto.nombre
        db.session.delete(producto)
        db.session.commit()
        
        flash(f'Producto "{nombre}" eliminado correctamente', 'success')
        return redirect(url_for('productos.lista_productos'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el producto: {str(e)}', 'error')
        return redirect(url_for('productos.ver_producto', id=id))

@productos_bp.route('/api/categorias')
def api_categorias():
    """API para obtener todas las categorías"""
    categorias = db.session.query(Producto.categoria).distinct().all()
    return jsonify([cat[0] for cat in categorias])

@productos_bp.route('/api/por_categoria/<categoria>')
def api_productos_por_categoria(categoria):
    """API para obtener productos por categoría"""
    productos = Producto.query.filter_by(categoria=categoria, disponible=True).all()
    return jsonify([producto.to_dict() for producto in productos])