from flask import Flask, render_template, request, redirect, url_for, flash, session
import datetime, pytz
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
    firstName = db.Column(db.String(120), nullable=False)
    lastName = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    admin = db.Column(db.String(2))

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

# Function sets a time zone, defines when Market starts and ends. 
def is_market_open():
    tz = pytz.timezone('US\Eastern')
    time_now = datetime.datetime.now(tz)
    start_market = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_market = now.replace(hour=16, minute=0, second=0, microsecond=0)
# Checks if current time is within the Weekdays and within 9am to 4pm
    if 0 <= now.weekday() <= 4 and start_market <= now <= end_market:
        return True
    return False    
# ROUTES
@app.route("/", methods=['GET', 'POST'])
def login():
    #Check if user sumitted something and store the username and password provided by user then quesries User to find the
    #first user those variable
     if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, password=password).first()
        #If user exist store their id and move them to dashboard if not redirect them to login.
        if user:
            session['user_id'] = user.id
            flash('Login successful!', 'Success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
        
     return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    stocks = Stock.query.all()
    return render_template("dashboard.html", stocks=stocks)

@app.route("/buy_sell")
def buy_sell():
    stocks = Stock.query.all()
    return render_template("buy_sell.html", stocks=stocks)

@app.route('/buy', methods=['POST'])
def buy():
    if not is_market_open():
        flash('The Market is closed at the moment.' \
        'Plese Try your Purchase again during Monday - Friday from 9am - 4pm.')
        return redirect(url_for('buy_sell'))
    stock_symbol = request.form['stock_symbol'].upper()
    quantity = int(request.form['quantity'])
    user_id = session['user_id']
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
    if not is_market_open():

        flash('The Market is closed at the moment.' \
        'Plese Try your Se again during Monday - Friday from 9am - 4pm.')
        return redirect(url_for('buy_sell'))
    stock_symbol = request.form['stock_symbol'].upper()
    quantity = int(request.form['quantity'])
    user_id = session['user_id']
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
    session.pop('user_id', None)
    flash('Logout Successfull')
    return redirect(url_for('login'))

@app.route("/withdraw-deposit")
def withdrawDeposit():
    return render_template("withdraw-deposit.html")

@app.route('/order-history')
def orderHistory():
    user_id = session.get('user_id')
    if not user_id:
        flash('User not found.', 'error')
        return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
    return render_template('order-history.html', user=user)

@app.route('/portfolio')
def portfolio():
    user_id = session.get('user_id')
    if not user_id:
        flash('User not found.', 'error')
        return redirect(url_for('login'))
    user = User.query.get_or_404(user_id)
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
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        password = request.form['password']
        admin = request.form['admin']
        
        if not username or not email or not firstName or not lastName or not password:
            flash('Please fill in all fields', 'error')
            return redirect(url_for('create_account'))
        
        try:
            new_user = User(username=username, email=email, firstName=firstName, lastName=lastName, password=password, admin=admin)
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
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in with an admin account.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if user.admin != 'y':
        flash('User is not logged in as an admin.', 'error')
        return redirect(url_for('dashboard'))
    
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