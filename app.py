import os
import uuid

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from models import db, Auction, Bid
from werkzeug.utils import secure_filename
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'subastasecret2024xK9mP'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///subastas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB max

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

db.init_app(app)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    """Save uploaded image and return its URL path."""
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(save_path)
    return f"/static/uploads/{unique_name}"

# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def random_username():
    adjectives = ['Veloz', 'Astuto', 'Noble', 'Feroz', 'Sabio', 'Audaz', 'Agil', 'Rapido']
    nouns = ['Puma', 'Condor', 'Jaguar', 'Halcon', 'Lobo', 'Zorro', 'Leon', 'Tigre']
    num = random.randint(10, 99)
    return f"{random.choice(adjectives)}{random.choice(nouns)}{num}"

def get_username():
    if 'username' not in session:
        session['username'] = random_username()
    return session['username']

def update_auction_statuses():
    """Mark auctions as closed if their end time has passed."""
    now = datetime.utcnow()
    expired = Auction.query.filter(
        Auction.ends_at <= now,
        Auction.status == 'active'
    ).all()
    for a in expired:
        a.status = 'closed'
    if expired:
        db.session.commit()

def seed_demo_data():
    """Seed with demo auctions if DB is empty."""
    if Auction.query.count() > 0:
        return

    demos = [
        {
            'title': 'Reloj Rolex Submariner Vintage 1969',
            'description': 'Extraordinario reloj de buceo en acero inoxidable con bisel negro original. Funcionamiento impecable, con su caja y documentos de epoca. Una pieza unica para coleccionistas.',
            'starting_price': 8500.00,
            'current_price': 8500.00,
            'seller': 'EliteTimepieces',
            'category': 'Relojes',
            'image_url': '/static/images/watch.svg',
            'hours': 2,
        },
        {
            'title': 'Pintura al Oleo - Atardecer en el Mediterraneo',
            'description': 'Obra original firmada por el artista espanol Ramon Vidal (1952). Tecnica mixta sobre lienzo de lino. Medidas: 80x60cm. Certificado de autenticidad incluido.',
            'starting_price': 3200.00,
            'current_price': 3200.00,
            'seller': 'GaleriaArtes',
            'category': 'Arte',
            'image_url': '/static/images/painting.svg',
            'hours': 5,
        },
        {
            'title': 'Guitarra Gibson Les Paul Custom 1959 Reissue',
            'description': 'Edicion limitada de la iconica Les Paul Custom del 59. Cuerpo de caoba con tapa de arce flameado, pastillas Burstbucker Pro. En perfecto estado, estuche original incluido.',
            'starting_price': 4700.00,
            'current_price': 4700.00,
            'seller': 'MusicLegends',
            'category': 'Musica',
            'image_url': '/static/images/guitar.svg',
            'hours': 8,
        },
        {
            'title': 'Porsche 911 Carrera S 2019 - Coleccion Privada',
            'description': 'Porsche 911 Carrera S en color Azul Miami. 30,000 km, un solo dueno, mantenimiento oficial Porsche. Llanta de 20 pulgadas Sport Techno, techo solar panoramico.',
            'starting_price': 95000.00,
            'current_price': 95000.00,
            'seller': 'AutosDeElite',
            'category': 'Vehiculos',
            'image_url': '/static/images/car.svg',
            'hours': 24,
        },
        {
            'title': 'Coleccion Primeras Ediciones - Harry Potter (7 tomos)',
            'description': 'Set completo de las primeras ediciones britanicas de la saga de J.K. Rowling. En excelente estado de conservacion. Incluye funda protectora de cuero artesanal.',
            'starting_price': 12000.00,
            'current_price': 12000.00,
            'seller': 'BibliotecaRara',
            'category': 'Libros',
            'image_url': '/static/images/books.svg',
            'hours': 12,
        },
        {
            'title': 'Whisky Macallan 50 Years - Edicion Lalique',
            'description': 'Botella de coleccion del Macallan 50 Years en decantador de cristal Lalique. Una de las botellas de whisky mas exclusivas del mundo. N. de serie: 0347. Caja madera de cedro.',
            'starting_price': 35000.00,
            'current_price': 35000.00,
            'seller': 'SpiritCollectors',
            'category': 'Bebidas',
            'image_url': '/static/images/whisky.svg',
            'hours': 36,
        },
    ]

    for d in demos:
        auction = Auction(
            title=d['title'],
            description=d['description'],
            starting_price=d['starting_price'],
            current_price=d['current_price'],
            seller=d['seller'],
            category=d['category'],
            image_url=d['image_url'],
            ends_at=datetime.utcnow() + timedelta(hours=d['hours']),
            status='active',
        )
        db.session.add(auction)

    db.session.commit()

    # Seed some bids
    bids_data = [
        (1, [('ColeccionistaMX', 8800), ('RelojeroFino', 9200), ('TimeHunter99', 9750)]),
        (2, [('ArteAmante', 3500), ('GaleriaVerde', 4100)]),
        (3, [('RockLegend42', 5000), ('GuitaristaPro', 5400), ('MusicFanatic', 5800)]),
        (4, [('CarLovers', 96000), ('VelocidadMax', 98500)]),
    ]
    for auction_id, bids in bids_data:
        auction = db.session.get(Auction, auction_id)
        if auction:
            for bidder, amount in bids:
                bid = Bid(amount=amount, bidder=bidder, auction_id=auction_id)
                db.session.add(bid)
                auction.current_price = amount
    db.session.commit()


# ──────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    update_auction_statuses()
    username = get_username()
    category = request.args.get('category', 'all')
    status_filter = request.args.get('status', 'active')

    query = Auction.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if category != 'all':
        query = query.filter_by(category=category)

    auctions = query.order_by(Auction.ends_at.asc()).all()
    categories = db.session.query(Auction.category).distinct().all()
    categories = [c[0] for c in categories]

    return render_template('index.html',
                           auctions=auctions,
                           username=username,
                           categories=categories,
                           selected_category=category,
                           selected_status=status_filter)


@app.route('/auction/<int:auction_id>')
def auction_detail(auction_id):
    update_auction_statuses()
    username = get_username()
    auction = db.get_or_404(Auction, auction_id)
    bids = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.created_at.desc()).all()
    return render_template('auction.html', auction=auction, bids=bids, username=username)


@app.route('/create', methods=['GET', 'POST'])
def create_auction():
    username = get_username()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        starting_price = float(request.form.get('starting_price', 0))
        duration_hours = int(request.form.get('duration_hours', 24))
        category = request.form.get('category', 'General')
        seller = request.form.get('seller', username).strip() or username

        if not title or starting_price <= 0:
            return render_template('create.html', username=username,
                                   error='Por favor completa todos los campos correctamente.')

        # Handle image upload
        image_url = '/static/images/default.svg'
        uploaded_file = request.files.get('image')
        if uploaded_file and uploaded_file.filename:
            saved = save_image(uploaded_file)
            if saved:
                image_url = saved
            else:
                return render_template('create.html', username=username,
                                       error='Formato de imagen no permitido. Usa JPG, PNG, WEBP o GIF.')

        auction = Auction(
            title=title,
            description=description,
            starting_price=starting_price,
            current_price=starting_price,
            seller=seller,
            category=category,
            image_url=image_url,
            ends_at=datetime.utcnow() + timedelta(hours=duration_hours),
            status='active',
        )
        db.session.add(auction)
        db.session.commit()
        return redirect(url_for('auction_detail', auction_id=auction.id))

    return render_template('create.html', username=username)


@app.route('/change-username', methods=['POST'])
def change_username():
    data = request.get_json()
    new_name = data.get('username', '').strip()
    if new_name and 3 <= len(new_name) <= 30:
        session['username'] = new_name
        return jsonify({'success': True, 'username': new_name})
    return jsonify({'success': False, 'error': 'Nombre invalido (3-30 caracteres)'}), 400


# ──────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────

@app.route('/api/auctions')
def api_auctions():
    update_auction_statuses()
    auctions = Auction.query.order_by(Auction.ends_at.asc()).all()
    return jsonify([a.to_dict() for a in auctions])


@app.route('/api/auction/<int:auction_id>')
def api_auction(auction_id):
    auction = db.get_or_404(Auction, auction_id)
    bids = [b.to_dict() for b in Bid.query.filter_by(auction_id=auction_id)
            .order_by(Bid.created_at.desc()).all()]
    data = auction.to_dict()
    data['bids'] = bids
    return jsonify(data)


# ──────────────────────────────────────────────────────────────────
# WebSocket Events
# ──────────────────────────────────────────────────────────────────

@socketio.on('join_auction')
def on_join(data):
    room = f"auction_{data['auction_id']}"
    join_room(room)

@socketio.on('leave_auction')
def on_leave(data):
    room = f"auction_{data['auction_id']}"
    leave_room(room)

@socketio.on('place_bid')
def on_place_bid(data):
    auction_id = data.get('auction_id')
    amount = data.get('amount')
    bidder = data.get('bidder', 'Anonimo')

    auction = db.session.get(Auction, auction_id)
    if not auction:
        emit('bid_error', {'message': 'Subasta no encontrada.'})
        return

    if auction.status != 'active':
        emit('bid_error', {'message': 'Esta subasta ya cerro.'})
        return

    if datetime.utcnow() >= auction.ends_at:
        auction.status = 'closed'
        db.session.commit()
        emit('bid_error', {'message': 'Esta subasta ya expiro.'})
        return

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        emit('bid_error', {'message': 'Monto invalido.'})
        return

    min_bid = auction.current_price + 1.0
    if amount < min_bid:
        emit('bid_error', {
            'message': f'La puja minima es ${min_bid:,.2f}.'
        })
        return

    bid = Bid(amount=amount, bidder=bidder, auction_id=auction_id)
    db.session.add(bid)
    auction.current_price = amount
    db.session.commit()

    room = f"auction_{auction_id}"
    socketio.emit('new_bid', {
        'bidder': bidder,
        'amount': amount,
        'auction_id': auction_id,
        'current_price': auction.current_price,
        'bid_count': auction.bid_count,
        'timestamp': bid.created_at.isoformat(),
    }, room=room)


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_demo_data()
    print("\nServidor iniciado en http://localhost:5000\n")
    socketio.run(app, debug=True, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
