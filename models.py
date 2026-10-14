from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Auction(db.Model):
    __tablename__ = 'auctions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), default='/static/images/default.png')
    starting_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    seller = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ends_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, closed, upcoming
    category = db.Column(db.String(50), default='General')

    bids = db.relationship('Bid', backref='auction', lazy=True, cascade='all, delete-orphan')

    @property
    def bid_count(self):
        return len(self.bids)

    @property
    def winner(self):
        if self.status == 'closed' and self.bids:
            top_bid = max(self.bids, key=lambda b: b.amount)
            return top_bid.bidder
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'starting_price': self.starting_price,
            'current_price': self.current_price,
            'seller': self.seller,
            'created_at': self.created_at.isoformat(),
            'ends_at': self.ends_at.isoformat(),
            'status': self.status,
            'category': self.category,
            'bid_count': self.bid_count,
            'winner': self.winner,
        }


class Bid(db.Model):
    __tablename__ = 'bids'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    bidder = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'bidder': self.bidder,
            'created_at': self.created_at.isoformat(),
            'auction_id': self.auction_id,
        }
