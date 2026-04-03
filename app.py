from flask import Flask, render_template, request, redirect, session, send_file
import mysql.connector
from sklearn.linear_model import LinearRegression

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

# -------- DATABASE --------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="SriVishnu@143",
    database="academic_system"
)
cursor = db.cursor()

# -------- LOGIN --------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (u, p))
        if cursor.fetchone():
            session["admin"] = u
            return redirect("/dashboard")

    return render_template("login.html")


# -------- LOGOUT --------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")


# -------- DASHBOARD --------
@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect("/")

    # TOTAL STUDENTS
    cursor.execute("SELECT COUNT(*) FROM students")
    total = cursor.fetchone()[0]

    # OVERALL AVG
    cursor.execute("SELECT AVG(percentage) FROM students")
    avg = cursor.fetchone()[0]
    avg = round(avg if avg else 0, 2)

    # TOPPER
    cursor.execute("SELECT name FROM students ORDER BY percentage DESC LIMIT 1")
    topper = cursor.fetchone()

    # 🔥 STUDENT DATA (FIXED)
    cursor.execute("SELECT name, percentage FROM students")
    data = cursor.fetchall()

    names = [row[0] for row in data]
    marks = [row[1] for row in data]

    # 🔥 CLASS-WISE DATA
    cursor.execute("""
        SELECT c.class_name, COUNT(s.id), AVG(s.percentage)
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id
        GROUP BY c.class_name
    """)

    class_data = cursor.fetchall()

    class_names = []
    class_counts = []
    class_avg = []

    for row in class_data:
        class_names.append(row[0])
        class_counts.append(row[1])
        class_avg.append(round(row[2] if row[2] else 0, 2))

    return render_template(
        "dashboard.html",
        total=total,
        avg=avg,
        topper=topper,
        class_names=class_names,
        class_counts=class_counts,
        class_avg=class_avg,
        names=names,
        marks=marks
    )

# -------- ADD STUDENT --------
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()

    error = None  # 🔥 for UI message

    if request.method == "POST":
        data = request.form

        name = data["name"]
        rollno = data["rollno"]
        class_id = data["class_id"]

        # ✅ CHECK DUPLICATE ROLL
        cursor.execute("SELECT * FROM students WHERE rollno=%s", (rollno,))
        if cursor.fetchone():
            error = "Roll number already exists ❌"
            return render_template("add_student.html", classes=classes, error=error)

        # MARKS
        marks = list(map(int, [
            data["english"],
            data["mathematics"],
            data["physics"],
            data["chemistry"],
            data["computer_science"]
        ]))

        total = sum(marks)
        per = round(total / 5, 2)

        # INSERT
        cursor.execute("""
        INSERT INTO students(
        name, rollno, class_id,
        english, mathematics, physics, chemistry, computer_science,
        total, percentage
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            name,
            rollno,
            class_id,
            *marks,
            total,
            per
        ))

        db.commit()
        return redirect("/students")

    return render_template("add_student.html", classes=classes, error=error)

# -------- VIEW STUDENTS --------
@app.route("/students")
def students():
    cursor.execute("""
        SELECT s.*, c.class_name 
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        ORDER BY c.class_name
    """)
    
    data = cursor.fetchall()

    grouped = {}
    for row in data:
        class_name = row[11]  # class_name

        if class_name not in grouped:
            grouped[class_name] = []

        grouped[class_name].append(row)

    return render_template("students.html", grouped=grouped)
    
# -------- STUDENT DETAILS --------
@app.route("/student/<int:id>")
def student_details(id):
    cursor.execute("""
        SELECT 
            s.id,
            s.name,
            s.rollno,
            s.english,
            s.mathematics,
            s.physics,
            s.chemistry,
            s.computer_science,
            s.total,
            s.percentage,
            c.class_name
        FROM students s
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE s.id = %s
    """, (id,))

    student = cursor.fetchone()

    return render_template("student_details.html", student=student)


# -------- DELETE --------
@app.route("/delete/<int:id>")
def delete(id):
    cursor.execute("DELETE FROM students WHERE id=%s", (id,))
    db.commit()
    return redirect("/students")


# -------- UPDATE --------
from mysql.connector import IntegrityError

@app.route("/update/<int:id>", methods=["GET", "POST"])
def update(id):
    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()

    error = None

    if request.method == "POST":
        data = request.form

        try:
            name = data["name"]
            rollno = data["rollno"]
            class_id = data["class_id"]

            marks = list(map(int, [
                data["english"],
                data["mathematics"],
                data["physics"],
                data["chemistry"],
                data["computer_science"]
            ]))

            total = sum(marks)
            per = round(total / 5, 2)

            cursor.execute("""
            UPDATE students SET
            name=%s, rollno=%s, class_id=%s,
            english=%s, mathematics=%s, physics=%s,
            chemistry=%s, computer_science=%s,
            total=%s, percentage=%s
            WHERE id=%s
            """, (
                name,
                rollno,
                class_id,
                *marks,
                total,
                per,
                id
            ))

            db.commit()
            return redirect("/students")

        except IntegrityError:
            error = "⚠ Roll number already exists!"

    cursor.execute("SELECT * FROM students WHERE id=%s", (id,))
    student = cursor.fetchone()

    return render_template(
        "update_student.html",
        student=student,
        classes=classes,
        error=error
    )
# -------- ANALYTICS --------
def predict(marks):
    X = [[80,85,90,88,92],[60,65,58,55,60],[40,35,30,25,20]]
    y = [85,60,30]

    model = LinearRegression()
    model.fit(X, y)

    return int(model.predict([marks])[0])


def weak_student(s):
    subjects = {
        "English": s[3],
        "Mathematics": s[4],
        "Physics": s[5],
        "Chemistry": s[6],
        "Computer": s[7]
    }
    return min(subjects, key=subjects.get)


@app.route("/analytics")
def analytics():
    cursor.execute("SELECT * FROM students")
    data = cursor.fetchall()

    results = []
    for s in data:
        results.append({
            "name": s[1],
            "current": s[9],
            "predicted": predict([s[3], s[4], s[5], s[6], s[7]]),
            "weak": weak_student(s)
        })

    return render_template("analytics.html", results=results)


# -------- AI ASSISTANT --------
@app.route("/assistant", methods=["GET", "POST"])
def assistant():
    answer = ""

    q = request.args.get("q") or ""

    if request.method == "POST":
        q = request.form["question"].lower()

    if q:
        if "topper" in q:
            cursor.execute("SELECT name FROM students ORDER BY percentage DESC LIMIT 1")
            res = cursor.fetchone()
            answer = f"🏆 Topper is {res[0]}" if res else "No data"

        elif "average" in q:
            cursor.execute("SELECT AVG(percentage) FROM students")
            avg = cursor.fetchone()[0]
            answer = f"📊 Average is {round(avg,2)}%" if avg else "No data"

        elif "weak" in q:
            cursor.execute("SELECT * FROM students")
            students = cursor.fetchall()

            weak_list = []
            for s in students:
                weak_list.append(f"{s[1]} ({weak_student(s)})")

            answer = "⚠ Weak Subjects:\n" + ", ".join(weak_list)

        else:
            answer = "Try: topper, average, weak"

    return render_template("assistant.html", answer=answer)


# -------- PDF REPORT --------
@app.route("/report/<int:id>")
def report(id):
    cursor.execute("SELECT * FROM students WHERE id=%s", (id,))
    s = cursor.fetchone()

    if not s:
        return "No Data"

    filename = f"report_{s[1]}.pdf"

    doc = SimpleDocTemplate(filename)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("🏆 Academic Performance Report", styles['Title']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Name: {s[1]}", styles['Normal']))
    content.append(Paragraph(f"Roll No: {s[2]}", styles['Normal']))
    content.append(Spacer(1, 10))

    # Table
    data = [
        ["Subject", "Marks"],
        ["English", s[3]],
        ["Mathematics", s[4]],
        ["Physics", s[5]],
        ["Chemistry", s[6]],
        ["Computer Science", s[7]]
    ]

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))

    content.append(table)
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"Total: {s[8]}", styles['Normal']))
    content.append(Paragraph(f"Percentage: {s[9]}%", styles['Normal']))

    doc.build(content)

    return send_file(filename, as_attachment=True)


# -------- RUN --------
if __name__ == "__main__":
    app.run(debug=True)