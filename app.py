import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, Product, User
from flask_migrate import Migrate 
app = Flask(__name__)
app.secret_key = "supersecretkey"
migrate = Migrate(app, db)
# ------------------- Database Config -------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stock.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# ------------------- Upload Config -------------------
UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB limit
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------- Authentication -------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('⚠️ Username already exists!', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('⚠️ Email already registered!', 'error')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('✅ Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'✅ Welcome, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('❌ Invalid username or password!', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('✅ Logged out successfully!', 'success')
    return redirect(url_for('login'))


# ------------------- Protect Routes -------------------
def login_required(func):
    from functools import wraps

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('⚠️ Please login first!', 'error')
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return decorated_function


# ------------------- Stock Routes -------------------
@app.route('/')
@login_required
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        # Handle image upload
        image_file = request.files.get("image")
        image_filename = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_filename = filename
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_product = Product(
            name=name,
            category=category,
            quantity=quantity,
            price=price,
            image=image_filename
        )
        db.session.add(new_product)
        db.session.commit()
        flash('✅ Product added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_product.html')


@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.quantity = int(request.form['quantity'])
        product.price = float(request.form['price'])

        # Handle image update
        image_file = request.files.get("image")
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            product.image = filename
            image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        db.session.commit()
        flash('✅ Product updated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('update_product.html', product=product)


@app.route('/delete/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('🗑️ Product deleted successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/low-stock')
@login_required
def low_stock():
    products = Product.query.filter(Product.quantity <= 5).all()
    return render_template('low_stock.html', products=products)


@app.route('/report')
@login_required
def report():
    products = Product.query.all()
    total_value = sum(p.quantity * p.price for p in products)
    return render_template('report.html', products=products, total_value=total_value)


# ------------------- Run App -------------------
if __name__ == '__main__':

    app.run(debug=True) 
