from flask import Flask, render_template, request, redirect, url_for, flash 
import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/capstone'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

db = SQLAlchemy(app)

# DATABASE MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    orders = db.relationship('Order', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"
    
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(10), nullable=False)
    order_type = db.Column(db.String(4), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_share = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now())
    
    def __repr__(self):
        return f"<Order {self.order_type} {self.quantity} {self.stock_symbol}>"

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_symbol = db.Column(db.String(5), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price_per_share = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Stock {self.stock_symbol}>"
    
# Create tables
with app.app_context():
    db.create_all()

# ROUTES
@app.route("/", methods=['GET', 'POST'])
def login():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/buy_sell")
def buy_sell():
    stocks = Stock.query.all()
    return render_template("buy_sell.html", stocks=stocks)

@app.route('/buy', methods=['POST'])
def buy():
    stock_symbol = request.form['stock_symbol'].upper()
    quantity = int(request.form['quantity'])
    user_id = 1  # Hardcoded for now. Replace with session['user_id'] when log in is added
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('buy_sell'))
    
    # Check if stock exists
    stock = Stock.query.filter_by(stock_symbol=stock_symbol).first()
    if not stock:
        flash('Stock not available.', 'error')
        return redirect(url_for('buy_sell'))
    
    # Check if enough quantity available
    if stock.quantity < quantity:
        flash('Stock sold out.', 'error')
        return redirect(url_for('buy_sell'))
    
    try:
        new_order = Order(
            user_id=user.id,
            stock_symbol=stock_symbol,
            order_type='BUY',
            quantity=quantity,
            price_per_share=stock.price_per_share,  # Use current stock price

        )
        
        # Update stock quantity
        stock.quantity -= quantity
        
        db.session.add(new_order)
        db.session.commit()
        flash('Order placed successfully', 'success')
        return redirect(url_for('portfolio'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error placing order: {str(e)}', 'error')
        return redirect(url_for('buy_sell'))

@app.route('/sell', methods=['POST'])
def sell():
    stock_symbol = request.form['stock_symbol'].upper()
    quantity = int(request.form['quantity'])
    user_id = 1  # Hardcoded for now. Replace with session['user_id'] when log in is added

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('buy_sell'))
    
    # Check if stock is in stock
    stock = Stock.query.filter_by(stock_symbol=stock_symbol).first()
    if not stock:
        flash('Stock not found.', 'error')
        return redirect(url_for('buy_sell'))
    
    # Check if user has enough shares to sell
    assets = {}
    for order in user.orders:
        if order.order_type == 'BUY':
            assets[order.stock_symbol] = assets.get(order.stock_symbol, 0) + order.quantity
        elif order.order_type == 'SELL':
            assets[order.stock_symbol] = assets.get(order.stock_symbol, 0) - order.quantity
    
    if assets.get(stock_symbol, 0) < quantity:
        flash('You do not have enough shares to sell.', 'error')
        return redirect(url_for('buy_sell'))
    
    try:
        new_order = Order(
            user_id=user.id,
            stock_symbol=stock_symbol,
            order_type='SELL',
            quantity=quantity,
            price_per_share=stock.price_per_share,
        )
        
        # Update stock quantity and add back to available stocks
        stock.quantity += quantity
        
        db.session.add(new_order)
        db.session.commit()
        flash('Sell order placed successfully!', 'success')
        return redirect(url_for('portfolio'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error placing sell order: {str(e)}', 'error')
        return redirect(url_for('buy_sell'))

@app.route("/contact")
def contact():
    return render_template("contact.html") 

@app.route("/account")
def account():
    return render_template("account.html")

@app.route("/log-out")
def logout():
    return redirect(url_for('login'))

@app.route("/withdraw-deposit")
def withdrawDeposit():
    return render_template("withdraw-deposit.html")

@app.route('/order-history')
def orderHistory():
    user = User.query.get_or_404(1)
    return render_template('order-history.html', user=user)

@app.route('/portfolio')
def portfolio():
    user = User.query.get_or_404(1)
    assets = {}
    for order in user.orders:
        if order.order_type == 'BUY':
            assets[order.stock_symbol] = assets.get(order.stock_symbol, 0) + order.quantity
        elif order.order_type == 'SELL':
            assets[order.stock_symbol] = assets.get(order.stock_symbol, 0) - order.quantity
    holdings = {}
    total_portfolio_value = 0.0
    # Get current stock prices
    for symbol, quantity in assets.items():
        if quantity > 0:
            stock = Stock.query.filter_by(stock_symbol=symbol).first()
            if stock:
                current_price = stock.price_per_share
            else:
                current_price = 0.0
            total_value = quantity * current_price
            holdings[symbol] = { 'quantity': quantity, 'current_price': current_price, 'total_value': total_value }
            total_portfolio_value += total_value
    
    return render_template("portfolio.html", holdings=holdings, total_portfolio_value=total_portfolio_value)

@app.route('/create-account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        
        if not username or not email:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('create_account'))
        
        try:
            new_user = User(username=username, email=email)
            db.session.add(new_user)
            db.session.commit()
            flash('User added successfully!', 'success')
            return redirect(url_for('create_account'))
        except Exception as e:
            flash(f'Error adding user: {str(e)}', 'error')
            return redirect(url_for('create_account'))
    
    return render_template('create-account.html')

@app.route("/edit-stocks", methods=['GET', 'POST'])
def edit_stocks():
    if request.method == 'POST':
        stock_symbol = request.form['stock_symbol'].upper()
        name = request.form['name']
        price_per_share = request.form['price_per_share']
        quantity = request.form['quantity']
        
        if not stock_symbol or not name or not price_per_share or not quantity:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('edit_stocks'))
        
        try:
            new_stock = Stock(
                stock_symbol=stock_symbol, 
                name=name, 
                price_per_share=float(price_per_share), 
                quantity=float(quantity)
            )
            db.session.add(new_stock)
            db.session.commit()
            flash('Stock created successfully!', 'success')
            return redirect(url_for('edit_stocks'))
        except Exception as e:
            flash(f'Error creating stock: {str(e)}', 'error')
            return redirect(url_for('edit_stocks'))
    
    return render_template('edit-stocks.html')

if __name__ == '__main__':
    app.run(debug=True)