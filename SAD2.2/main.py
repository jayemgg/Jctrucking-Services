from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "jctrucking_company"
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"Database connection failed: {e}")
        return None

# Home page (login page)
@app.route("/")
def home():
    return render_template("index.html")

# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        full_name = request.form["full_name"].strip()
        password = request.form["password"].strip()
        email = request.form["email"].strip()
        contact_no = request.form["contact_no"].strip()
        age = request.form["age"].strip()
        address = request.form["address"].strip()

        if not all([username, full_name, password, email, contact_no, age, address]):
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("register"))

        conn = get_db_connection()
        if conn is None:
            flash("Database connection failed!", "danger")
            return redirect(url_for("register"))

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash("Username already exists. Choose another.", "danger")
                return redirect(url_for("register"))

            cursor.execute(""" 
                INSERT INTO users (username, full_name, password, email, contact_no, age, address)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (username, full_name, password, email, contact_no, age, address))

            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("home"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("register"))
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


# Login route
@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    if not username or not password:
        flash("Please fill in both fields.", "danger")
        return redirect(url_for("home"))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("home"))

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username, password FROM admin WHERE username = %s", (username,))
        admin = cursor.fetchone()

        if admin and admin[1] == password:
            session["username"] = admin[0]
            session["is_admin"] = True
            flash("Admin login successful!", "success")
            return redirect(url_for("admindashboard"))
        else:
            cursor.execute("SELECT username, password FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user and user[1] == password:
                session["username"] = user[0]
                session["is_admin"] = False
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Incorrect username or password.", "danger")
                return redirect(url_for("home"))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("home"))
    finally:
        cursor.close()
        conn.close()

# Dashboard page (for regular users)
@app.route("/dashboard")
def dashboard():
    if "username" not in session or session.get("is_admin") is None:
        flash("Please log in first.", "danger")
        return redirect(url_for("home"))

    username = session["username"]
    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("home"))

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            return render_template("usersdashboard.html", user=user)
        else:
            flash("User not found.", "danger")
            return redirect(url_for("home"))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("home"))
    finally:
        cursor.close()
        conn.close()


# Admin Dashboard page
@app.route("/admindashboard")
def admindashboard():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied. You need to be an admin to view this page.", "danger")
        return redirect(url_for("home"))
    return render_template("admindashboard.html", username=session["username"])

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

# Profile Page
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("home"))

    username = session["username"]
    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("home"))

    cursor = conn.cursor()
    try:
        if request.method == "POST":
            # Retrieve form data
            new_username = request.form["username"].strip()
            full_name = request.form["full_name"].strip()
            email = request.form["email"].strip()
            contact_no = request.form["contact_no"].strip()
            age = request.form["age"].strip()
            address = request.form["address"].strip()
            password = request.form["password"].strip()  # Password field

            if not all([new_username, full_name, email, contact_no, age, address]):
                flash("Please fill in all required fields.", "danger")
                return redirect(url_for("profile"))

            # If password is provided, update password as well
            if password:
                cursor.execute("""
                    UPDATE users
                    SET username = %s, full_name = %s, password = %s, email = %s, contact_no = %s, age = %s, address = %s
                    WHERE username = %s
                """, (new_username, full_name, password, email, contact_no, age, address, username))
            else:
                # If password is not provided, just update the other fields
                cursor.execute("""
                    UPDATE users
                    SET username = %s, full_name = %s, email = %s, contact_no = %s, age = %s, address = %s
                    WHERE username = %s
                """, (new_username, full_name, email, contact_no, age, address, username))

            conn.commit()

            # Update session username if username is changed
            if new_username != username:
                session["username"] = new_username

            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile"))
        
        # GET request to display the profile
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            return render_template("profile.html", user=user)
        else:
            flash("User not found.", "danger")
            return redirect(url_for("home"))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("home"))
    finally:
        cursor.close()
        conn.close()

# Add Truck Functionality (Admin only)
@app.route("/add-truck", methods=["GET", "POST"])
def add_truck():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied. Only admins can add trucks.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        truck_number = request.form["truck_number"].strip()
        model = request.form["model"].strip()
        plate_number = request.form["plate_number"].strip()
        capacity = request.form["capacity"].strip()

        if not all([truck_number, model, plate_number, capacity]):
            flash("Please fill in all fields.", "danger")
            return redirect(url_for("add_truck"))

        conn = get_db_connection()
        if conn is None:
            flash("Database connection failed!", "danger")
            return redirect(url_for("add_truck"))

        cursor = conn.cursor()
        try:
            cursor.execute(""" 
                INSERT INTO trucks (truck_number, model, plate_number, capacity)
                VALUES (%s, %s, %s, %s)
            """, (truck_number, model, plate_number, capacity))
            conn.commit()
            flash("Truck added successfully!", "success")
            return redirect(url_for("admindashboard"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("add_truck"))
        finally:
            cursor.close()
            conn.close()

    return render_template("addtruck.html")

# Tracker Page
@app.route("/tracker")
def tracker():
    return render_template("customertracker.html")

@app.route("/userManagement")
def userManagement():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied. You need to be an admin to view this page.", "danger")
        return redirect(url_for("home"))
    return render_template("userManagement.html", username=session["username"])

# CUSTOMER MANAGEMENT PAGE
@app.route("/customer")
def customer():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied. You need to be an admin to view this page.", "danger")
        return redirect(url_for("home"))
    return render_template("customer.html", username=session["username"])

# Clients Viewer Page ✅

@app.route("/Show-Client")
def show_client():
    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("admindashboard"))

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM clients ORDER BY submitted_at DESC")
        clients = cursor.fetchall()
        
        if clients:  # Check if clients are found
            print(f"Clients found: {clients}")  # Debugging log
            return render_template("clients.html", clients=clients)
        else:
            flash("No clients found.", "warning")
            return redirect(url_for("admindashboard"))
    except Exception as e:
        flash(f"Error fetching clients: {e}", "danger")
        return redirect(url_for("admindashboard"))
    finally:
        cursor.close()
        conn.close()

# Submit route
@app.route("/submit", methods=["POST"])
def submit():
    flash("Form submitted successfully!", "success")
    return redirect(url_for("dashboard"))

# Start the app (put this last)
if __name__ == "__main__":
    print("Current working directory:", os.getcwd())
    app.run(debug=True)

@app.route('/')
def login():
    return '''
    <form method="POST" action="/login">
        <h2>Driver Login</h2>
        <input type="text" name="username" placeholder="Username" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <button type="submit">Login</button>
    </form>
    '''

from flask import Flask, render_template, request, session, redirect
import mysql.connector

app = Flask(__name__)
app.secret_key = '1234567890jeijei'  # For session management

# Database connection - replace with your actual credentials
db = mysql.connector.connect(
    host="localhost",
    user="your_db_user",
    password="your_db_password",
    database="your_db_name"
)

@app.route('/login', methods=['POST'])
def login_post():
    cursor = db.cursor(dictionary=True)  # use dictionary=True to fetch rows as dict
    username = request.form['username']
    password = request.form['password']

    query = "SELECT * FROM drivers WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()

    if user:
        session['user'] = user['username']
        session['user_id'] = user['id']  # assuming 'id' is the primary key column name
        return redirect('/dashboard')
    else:
        return "Invalid username or password"

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('driverdashboard.html')
    else:
        return redirect('/')

@app.route('/submit_order', methods=['POST'])
def submit_order():
    service = request.form['service']
    service_date = request.form['service_date']
    notes = request.form.get('notes', '')

    cursor = db.cursor()
    query = """
        INSERT INTO service_orders (service, service_date, notes)
        VALUES (%s, %s, %s)
    """
    cursor.execute(query, (service, service_date, notes))
    db.commit()

    return "Order submitted successfully!"

from flask import Flask, render_template, request, redirect

app = Flask(__name__)

@app.route('/services')
def services():
    return render_template('servicescustomer.html')


# Optional: Handle the form submission
@app.route("/submit_order", methods=["POST"])
def submit_order():
    service = request.form.get("service")
    service_date = request.form.get("service_date")
    notes = request.form.get("notes")
    print(f"Service: {service}, Date: {service_date}, Notes: {notes}")
    return redirect("/services")

if __name__ == "__main__":
    app.run(debug=True)

