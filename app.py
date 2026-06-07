from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "tuition_secret_key"

# Database Connection
import os
import mysql.connector

db = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    port=int(os.getenv("MYSQLPORT")),
    database=os.getenv("MYSQLDATABASE")
)
#admin login
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor()

        cursor.execute(
            """
            SELECT * FROM admins
            WHERE username=%s AND password=%s
            """,
            (username, password)
        )

        admin = cursor.fetchone()

        if admin:
            session["admin"] = True
            return redirect("/dashboard")

    return render_template("login.html")
# Home Route
@app.route("/")
def home():
    return render_template("home.html")


# Dashboard
@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect("/admin-login")

    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM payments")
    total_payments = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM payments
        WHERE status='Pending'
    """)
    pending_payments = cursor.fetchone()[0]

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_payments=total_payments,
        pending_payments=pending_payments
    )


# View Students
@app.route("/students")
def students():

    if not session.get("admin"):
        return redirect("/admin-login")

    cursor = db.cursor()

    search = request.args.get("search")

    if search:

        cursor.execute(
            """
            SELECT * FROM students
            WHERE name LIKE %s
            """,
            ('%' + search + '%',)
        )

    else:

        cursor.execute(
            "SELECT * FROM students"
        )

    students = cursor.fetchall()

    return render_template(
        "students.html",
        students=students
    )


# Add Student
@app.route("/add-student", methods=["GET", "POST"])
def add_student():

    if not session.get("admin"):
        return redirect("/admin-login")

    if request.method == "POST":

        name = request.form["name"]
        class_name = request.form["class_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO students
            (name, class_name, phone, email, username, password)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (
                name,
                class_name,
                phone,
                email,
                username,
                password
            )
        )

        db.commit()

        return redirect("/students")

    return render_template("add_student.html")


# Edit Student
@app.route("/edit-student/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    if not session.get("admin"):
        return redirect("/admin-login")
    cursor = db.cursor()

    if request.method == "POST":

        name = request.form["name"]
        class_name = request.form["class_name"]
        phone = request.form["phone"]
        email = request.form["email"]

        cursor.execute(
            """
            UPDATE students
            SET
            name=%s,
            class_name=%s,
            phone=%s,
            email=%s
            WHERE id=%s
            """,
            (
                name,
                class_name,
                phone,
                email,
                id
            )
        )

        db.commit()

        return redirect("/students")

    cursor.execute(
        "SELECT * FROM students WHERE id=%s",
        (id,)
    )

    student = cursor.fetchone()

    return render_template(
        "edit_student.html",
        student=student
    )


# Delete Student
@app.route("/delete-student/<int:id>")
def delete_student(id):

    if not session.get("admin"):
        return redirect("/admin-login")

    cursor = db.cursor()

    # Delete student's payments first
    cursor.execute(
        "DELETE FROM payments WHERE student_id=%s",
        (id,)
    )

    # Then delete student
    cursor.execute(
        "DELETE FROM students WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect("/students")

# Student Login
@app.route("/student-login", methods=["GET", "POST"])
def student_login():

    error = None

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor()

        cursor.execute(
            """
            SELECT * FROM students
            WHERE username=%s AND password=%s
            """,
            (username, password)
        )

        student = cursor.fetchone()

        if student:

            session["student_id"] = student[0]

            return redirect("/student-dashboard")

        else:

            error = "Username or Password is incorrect"

    return render_template(
        "student_login.html",
        error=error
    )
# Student Dashboard
@app.route("/student-dashboard")
def student_dashboard():

    if "student_id" not in session:
        return redirect("/student-login")

    cursor = db.cursor()

    cursor.execute(
        """
        SELECT * FROM students
        WHERE id=%s
        """,
        (session["student_id"],)
    )

    student = cursor.fetchone()

    return render_template(
        "student_dashboard.html",
        student=student
    )


# Pay Fee
@app.route("/pay-fee", methods=["GET", "POST"])
def pay_fee():

    if "student_id" not in session:
        return redirect("/student-login")

    if request.method == "POST":

        amount = request.form["amount"]
        payment_month = request.form["payment_month"]

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO payments
            (
                student_id,
                amount,
                payment_month,
                status
            )
            VALUES (%s,%s,%s,%s)
            """,
            (
                session["student_id"],
                amount,
                payment_month,
                "Pending"
            )
        )

        db.commit()

        return redirect("/my-payments")

    return render_template("pay_fee.html")


# My Payments
@app.route("/my-payments")
def my_payments():

    if "student_id" not in session:
        return redirect("/student-login")

    cursor = db.cursor()

    cursor.execute(
        """
        SELECT * FROM payments
        WHERE student_id=%s
        """,
        (session["student_id"],)
    )

    payments = cursor.fetchall()

    return render_template(
        "my_payments.html",
        payments=payments
    )


# Verify Payments Page
@app.route("/verify-payments")
def verify_payments():

    if not session.get("admin"):
        return redirect("/admin-login")
    cursor = db.cursor()

    cursor.execute("""
        SELECT
        payments.id,
        students.name,
        payments.amount,
        payments.payment_month,
        payments.status

        FROM payments

        JOIN students
        ON payments.student_id = students.id

        WHERE payments.status='Pending'
    """)

    payments = cursor.fetchall()

    return render_template(
        "verify_payments.html",
        payments=payments
    )


# Verify Payment
@app.route("/verify/<int:payment_id>")
def verify(payment_id):

    if not session.get("admin"):
        return redirect("/admin-login")

    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE payments
        SET status='Verified'
        WHERE id=%s
        """,
        (payment_id,)
    )

    db.commit()

    return redirect("/verify-payments")

#payment report
@app.route("/payment-report")
def payment_report():

    if not session.get("admin"):
        return redirect("/admin-login")

    cursor = db.cursor()

    cursor.execute("""
        SELECT
        payments.id,
        students.name,
        payments.amount,
        payments.payment_month,
        payments.status

        FROM payments

        JOIN students
        ON students.id = payments.student_id
    """)

    payments = cursor.fetchall()

    return render_template(
        "payment_report.html",
        payments=payments
    )

# Admin Announcements
@app.route("/announcements", methods=["GET", "POST"])
def announcements():

    if not session.get("admin"):
        return redirect("/admin-login")

    cursor = db.cursor()

    if request.method == "POST":

        title = request.form["title"]
        message = request.form["message"]

        cursor.execute(
            """
            INSERT INTO announcements
            (title, message)
            VALUES (%s, %s)
            """,
            (title, message)
        )

        db.commit()

        return redirect("/announcements")

    cursor.execute(
        """
        SELECT *
        FROM announcements
        ORDER BY id DESC
        """
    )

    announcements = cursor.fetchall()

    return render_template(
        "announcements.html",
        announcements=announcements
    )


# Student Announcements
@app.route("/student-announcements")
def student_announcements():

    if "student_id" not in session:
        return redirect("/student-login")

    cursor = db.cursor()

    cursor.execute(
        """
        SELECT *
        FROM announcements
        ORDER BY id DESC
        """
    )

    announcements = cursor.fetchall()

    return render_template(
        "student_announcements.html",
        announcements=announcements
    )

@app.route("/delete-announcement/<int:id>")
def delete_announcement(id):

    if not session.get("admin"):
        return redirect("/admin-login")

    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM announcements WHERE id=%s",
        (id,)
    )

    db.commit()

    return redirect("/announcements") 

#debugg route
@app.route("/show-admin")
def show_admin():

    cursor = db.cursor()

    cursor.execute("SELECT * FROM admins")

    return str(cursor.fetchall())

# Logout
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)


#This is python