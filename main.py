from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file
import mysql.connector
import os
import requests

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "jctrucking_company"
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"Database connection failed: {e}")
        return None

# ROUTES

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/services")
def services():
    return render_template("servicescustomer.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        address = request.form.get("address")
        contact_no = request.form.get("contact_no")
        username = request.form.get("username")
        password = request.form.get("password")
        birthday = request.form.get("birthday")
        role = request.form.get("role")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if role == "driver":
                cursor.execute(
                    "INSERT INTO driver (username, full_name, password, email, contact_no, birthday, address) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (username, full_name, password, email, contact_no, birthday, address)
                )
            else:
                cursor.execute(
                    "INSERT INTO users (username, full_name, password, email, contact_no, birthday, address, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (username, full_name, password, email, contact_no, birthday, address, role)
                )
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
        finally:
            cursor.close()
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Please fill in both fields.", "danger")
            return redirect(url_for("home"))

        conn = get_db_connection()
        if conn is None:
            flash("Database connection failed!", "danger")
            return redirect(url_for("home"))

        cursor = conn.cursor(dictionary=True)
        try:
            # Admin check
            cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
            admin = cursor.fetchone()
            if admin and admin["password"] == password:
                session["username"] = admin["username"]
                session["is_admin"] = True
                session["role"] = "admin"
                flash("Admin login successful!", "success")
                return redirect(url_for("admindashboard"))

            # Driver check
            cursor.execute("SELECT * FROM driver WHERE username = %s", (username,))
            driver = cursor.fetchone()
            if driver and driver["password"] == password:
                session["username"] = driver["username"]
                session["is_admin"] = False
                session["role"] = "driver"
                flash("Driver login successful!", "success")
                return redirect(url_for("driver_dashboard"))

            # User check
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user and user["password"] == password:
                session["username"] = user["username"]
                session["is_admin"] = False
                session["role"] = user.get("role", "client")
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid credentials", "danger")
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            cursor.close()
            conn.close()
    return render_template("index.html")

# Dashboard page (for regular users)
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        flash("Please log in first.", "danger")
        return redirect(url_for("home"))
    username = session["username"]
    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("home"))
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.execute("""
            SELECT pickup, dropoff, waste_type, volume, schedule, status
            FROM service_requests
            WHERE username = %s
            ORDER BY id DESC
        """, (username,))
        service_requests = cursor.fetchall()
    except Exception as e:
        flash(f"Error: {e}", "danger")
        user = None
        service_requests = []
    finally:
        cursor.close()
        conn.close()
    return render_template("usersdashboard.html", user=user, service_requests=service_requests)

@app.route('/admindashboard')
def admindashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Fetch service requests
    cursor.execute("SELECT * FROM service_requests")
    service_requests = cursor.fetchall()
    # Fetch drivers
    cursor.execute("SELECT username FROM driver")
    drivers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "admindashboard.html",
        service_requests=service_requests,
        drivers=drivers
    )

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

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
            new_username = request.form["username"].strip()
            full_name = request.form["full_name"].strip()
            email = request.form["email"].strip()
            contact_no = request.form["contact_no"].strip()
            age = request.form["age"].strip()
            address = request.form["address"].strip()
            password = request.form["password"].strip()

            if not all([new_username, full_name, email, contact_no, age, address]):
                flash("Please fill in all required fields.", "danger")
                return redirect(url_for("profile"))

            if password:
                cursor.execute("""
                    UPDATE users SET username=%s, full_name=%s, password=%s, email=%s,
                    contact_no=%s, age=%s, address=%s WHERE username=%s
                """, (new_username, full_name, password, email, contact_no, age, address, username))
            else:
                cursor.execute("""
                    UPDATE users SET username=%s, full_name=%s, email=%s,
                    contact_no=%s, age=%s, address=%s WHERE username=%s
                """, (new_username, full_name, email, contact_no, age, address, username))

            conn.commit()
            if new_username != username:
                session["username"] = new_username
            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile"))

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user:
            return render_template("profile.html", user=user)
        flash("User not found.", "danger")
        return redirect(url_for("home"))
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for("home"))
    finally:
        cursor.close()
        conn.close()

# Submit contact request route (moved out of profile)
@app.route('/submit_contact', methods=['POST'])
def submit_contact_request():
    company = request.form['company']
    address = request.form['address']
    email = request.form['email']
    contact = request.form['contact']
    datetime_val = request.form['datetime']
    client = request.form['client']
    note = request.form['note']
    truck_load = request.form['truck_load']

    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO contact_requests (company, address, email, contact, datetime, client, note, truck_load) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (company, address, email, contact, datetime_val, client, note, truck_load)
        )
        conn.commit()
        flash('Your request has been submitted!')
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('dashboard'))

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

@app.route("/tracker")
def tracker():
    return render_template("customertracker.html")

@app.route("/userManagement")
def userManagement():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("home"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")  # or include WHERE/ORDER BY as needed
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("usermanagement.html", users=users)

@app.route("/customer")
def customer():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("home"))
    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("admindashboard"))
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users ORDER BY id DESC")
        users = cursor.fetchall()
    except Exception as e:
        flash(f"Error fetching users: {e}", "danger")
        users = []
    finally:
        cursor.close()
        conn.close()
    return render_template('customer.html', users=users)

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
        if clients:
            return render_template("clients.html", clients=clients)
        flash("No clients found.", "warning")
        return redirect(url_for("admindashboard"))
    except Exception as e:
        flash(f"Error fetching clients: {e}", "danger")
        return redirect(url_for("admindashboard"))
    finally:
        cursor.close()
        conn.close()

@app.route("/submit_order", methods=["POST"])
def submit_order():
    service = request.form.get("service")
    service_date = request.form.get("service_date")
    notes = request.form.get("notes")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO service_orders (service, service_date, notes) VALUES (%s, %s, %s)",
        (service, service_date, notes)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("services"))

@app.route("/service_request", methods=["POST"])
def service_request():
    if "username" not in session or session.get("is_admin") is None:
        flash("Please log in first.", "danger")
        return redirect(url_for("home"))

    pickup = request.form.get("pickup", "").strip()
    dropoff = request.form.get("dropoff", "").strip()
    waste_type = request.form.get("waste_type", "").strip()
    volume = request.form.get("volume", "").strip()
    schedule = request.form.get("schedule", "").strip()
    username = session["username"]

    if not all([pickup, dropoff, waste_type, volume, schedule]):
        flash("Please fill in all fields.", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    if conn is None:
        flash("Database connection failed!", "danger")
        return redirect(url_for("dashboard"))
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO service_requests (username, pickup, dropoff, waste_type, volume, schedule, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, pickup, dropoff, waste_type, volume, schedule, "Pending"))
        conn.commit()
        flash("Service request submitted successfully!", "success")
        return redirect(url_for("payment_page"))
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("dashboard"))

@app.route('/payment')
def payment_page():
    return render_template('payment.html')

@app.route('/gcash_pay', methods=['POST'])
def gcash_pay():
    gcash_api_url = "https://api.paymentwall.com/api/gcash"
    api_key = "YOUR_API_KEY"

    payment_data = {
        "amount": 100,
        "currency": "PHP",
        "description": "Payment for service request",
        "success_url": url_for('payment_success', _external=True),
        "failure_url": url_for('payment_failure', _external=True),
        "api_key": api_key
    }

    response = requests.post(gcash_api_url, json=payment_data)

    if response.status_code == 200:
        payment_url = response.json().get("payment_url")
        return redirect(payment_url)
    else:
        flash("Error processing payment. Please try again.", "danger")
        return redirect(url_for('dashboard'))

@app.route('/payment_success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/payment_failure')
def payment_failure():
    return render_template('payment_failure.html')

@app.route('/track_job/<int:job_id>')
def track_job(job_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM service_requests WHERE id = %s', (job_id,))
    job = cursor.fetchone()
    cursor.close()
    conn.close()
    if not job:
        flash('Job not found.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('track_job.html', job=job)

@app.route('/download_invoice/<invoice_id>')
def download_invoice(invoice_id):
    file_path = f'invoices/{invoice_id}.pdf'
    try:
        return send_file(file_path, as_attachment=True)
    except FileNotFoundError:
        flash('Invoice not found.', 'error')
        return redirect(url_for('dashboard'))

@app.route("/transaction_history")
def transaction_history():
    return render_template("transaction_history.html")

@app.route("/staff-driver", methods=["GET", "POST"])
def staff_driver():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("home"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        staff_id = request.form.get("staff_id")
        new_salary = request.form.get("salary")
        cursor.execute("UPDATE staff SET salary=%s WHERE id=%s", (new_salary, staff_id))
        conn.commit()
        flash("Salary updated!", "success")
    cursor.execute("SELECT * FROM staff")
    staff_list = cursor.fetchall()
    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admindashboard.html", staff_list=staff_list, users=users, username=session["username"])

@app.route("/admin/services")
def admin_services():
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("home"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM service_requests ORDER BY id DESC")
    service_requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("dashboardservice.html", service_requests=service_requests)

@app.route("/update_service_status/<int:service_id>", methods=["POST"])
def update_service_status(service_id):
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("admindashboard"))
    new_status = request.form.get("status")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE service_requests SET status=%s WHERE id=%s", (new_status, service_id))
        conn.commit()
        flash("Status updated!", "success")
    except Exception as e:
        flash(f"Error updating status: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("admindashboard"))

@app.route("/edit_user/<int:user_id>", methods=["POST", "GET"])
def edit_user(user_id):
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("userManagement"))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        contact_no = request.form.get("contact_no")
        age = request.form.get("age")
        address = request.form.get("address")
        cursor.execute("""
            UPDATE users SET full_name=%s, email=%s, contact_no=%s, age=%s, address=%s WHERE id=%s
        """, (full_name, email, contact_no, age, address, user_id))
        conn.commit()
        flash("User updated successfully!", "success")
        cursor.close()
        conn.close()
        return redirect(url_for("userManagement"))
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("edit_user.html", user=user)

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("userManagement"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_deleted=1 WHERE id=%s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("User deleted.", "success")
    return redirect(url_for("userManagement"))

@app.route("/recover_user/<int:user_id>", methods=["POST"])
def recover_user(user_id):
    if "username" not in session or not session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("userManagement"))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_deleted=0 WHERE id=%s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("User recovered.", "success")
    return redirect(url_for("userManagement"))

@app.route("/driverdashboard")
def driver_dashboard():
    if "username" not in session or session.get("role") != "driver":
        flash("Access denied.", "danger")
        return redirect(url_for("login"))

    driver_username = session["username"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT pickup, dropoff, date FROM trips WHERE driver_username = %s ORDER BY date DESC",
        (driver_username,)
    )
    trips = cursor.fetchall()
    salary = len(trips) * 5000  # Each trip: 10,000 / 2 = 5,000 PHP for driver
    cursor.close()
    conn.close()
    return render_template("driverdashboard.html", trips=trips, salary=salary)

@app.route("/dashboard-driver")
def dashboard_driver():
    if "username" not in session or session.get("role") != "driver":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))
    # Fetch driver-specific data here if needed
    return render_template("driverdashboard.html", username=session["username"])

@app.route("/view_route_driver")
def view_route_driver():
    return "<h2>View Route (Driver)</h2>"

@app.route("/trips_driver")
def trips_driver():
    return "<h2>Trips (Driver)</h2>"

@app.route("/trip_update_driver")
def trip_update_driver():
    return "<h2>Trip Update (Driver)</h2>"

@app.route('/assign_trip', methods=['POST'])
def assign_trip():
    service_id = request.form['service_id']
    driver_username = request.form['driver_username']

    # Now, fetch the service request details from the database using service_id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT pickup, dropoff, waste_type, volume, schedule FROM service_requests WHERE id = %s", (service_id,))
    req = cursor.fetchone()

    # Insert into trips table (or update service_requests with driver assignment)
    cursor.execute(
        "INSERT INTO trips (driver_username, pickup, dropoff, schedule, date) VALUES (%s, %s, %s, %s, %s)",
        (driver_username, req['pickup'], req['dropoff'], req['schedule'], req['schedule'])
    )
    conn.commit()
    cursor.close()
    conn.close()
    flash("Trip assigned successfully!", "success")
    return redirect(url_for('admindashboard'))

@app.route('/assigntrips')
def assign_trips():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username FROM driver")
    drivers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("assigntrips.html", drivers=drivers)

if __name__ == "__main__":
    app.run(debug=True)



