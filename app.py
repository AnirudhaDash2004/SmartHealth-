from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from flask import Flask, render_template, request, redirect, session
import pickle
import sqlite3
import os

app=Flask(__name__)
app.secret_key="your_secret_key"

model=pickle.load(open("model.pkl","rb"))

def init_db():
    conn=sqlite3.connect("database.db")
    c=conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            patient_id TEXT,
            contact TEXT,
            age INTEGER,
            bmi REAL,
            heart_rate INTEGER,
            sleep_hours REAL,
            activity_level INTEGER,
            risk TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form["username"]
        password=request.form["password"]

        if username=="admin" and password=="1234":
            session["user"]=username
            return redirect("/admin")
        else:
            return "Invalid Credentials"

    return render_template("login.html")

@app.route("/predict",methods=["POST"])
def predict():
    name=request.form["name"]
    patient_id=request.form["patient_id"]
    contact=request.form["contact"]

    age=int(request.form["age"])
    bmi=float(request.form["bmi"])
    heart_rate=int(request.form["heart_rate"])
    sleep=float(request.form["sleep"])
    activity=int(request.form["activity"])

    prediction=model.predict([[age,bmi,heart_rate,sleep,activity]])[0]

    risk_map={0:"Low Risk",1:"Medium Risk",2:"High Risk"}
    risk=risk_map[prediction]

    if risk=="Low Risk":
        advice="You are healthy! Maintain a balanced diet, regular exercise, and good sleep routine."
    elif risk=="Medium Risk":
        advice="You need to improve your lifestyle. Focus on healthy eating, regular physical activity, and proper sleep."
    else:
        advice="High health risk detected. Immediate medical consultation is recommended. Improve diet, reduce stress, and monitor health closely."

    conn=sqlite3.connect("database.db")
    c=conn.cursor()

    c.execute("""
        INSERT INTO records 
        (name,patient_id,contact,age,bmi,heart_rate,sleep_hours,activity_level,risk)
        VALUES (?,?,?,?,?,?,?,?,?)
    """,(name,patient_id,contact,age,bmi,heart_rate,sleep,activity,risk))

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        risk=risk,
        advice=advice,
        name=name,
        patient_id=patient_id,
        contact=contact,
        age=age,
        bmi=bmi,
        heart_rate=heart_rate,
        sleep=sleep,
        activity=activity
    )

@app.route("/download")
def download():
    from flask import request

    name=request.args.get("name")
    patient_id=request.args.get("patient_id")
    contact=request.args.get("contact")
    age=request.args.get("age")
    bmi=request.args.get("bmi")
    heart_rate=request.args.get("heart_rate")
    sleep=request.args.get("sleep")
    activity=request.args.get("activity")
    risk=request.args.get("risk")

    doc=SimpleDocTemplate("report.pdf")
    styles=getSampleStyleSheet()

    story=[]

    story.append(Paragraph("SmartHealth+ Medical Report",styles['Title']))
    story.append(Spacer(1,12))

    story.append(Paragraph(f"Patient Name: {name}",styles['Normal']))
    story.append(Paragraph(f"Patient ID: {patient_id}",styles['Normal']))
    story.append(Paragraph(f"Contact: {contact}",styles['Normal']))
    story.append(Spacer(1,12))

    story.append(Paragraph("Health Data",styles['Heading2']))
    story.append(Paragraph(f"Age: {age}",styles['Normal']))
    story.append(Paragraph(f"BMI: {bmi}",styles['Normal']))
    story.append(Paragraph(f"Heart Rate: {heart_rate}",styles['Normal']))
    story.append(Paragraph(f"Sleep Hours: {sleep}",styles['Normal']))
    story.append(Paragraph(f"Activity Level: {activity}",styles['Normal']))
    story.append(Spacer(1,12))

    story.append(Paragraph(f"Risk Level: {risk}",styles['Heading2']))

    if risk=="Low Risk":
        advice="You are healthy! Maintain a balanced diet, exercise regularly, and sleep well."
    elif risk=="Medium Risk":
        advice="Improve your lifestyle. Focus on diet, exercise, and sleep quality."
    else:
        advice="High risk detected. Immediate consultation with a doctor is strongly recommended."

    story.append(Paragraph("Recommendation:",styles['Heading2']))
    story.append(Paragraph(advice,styles['Normal']))

    doc.build(story)

    return "PDF Generated! Check your project folder."

@app.route("/admin")
def admin():
    # 🔍 Get search + filter values from URL
    search=request.args.get("search")
    filter_type=request.args.get("filter")

    conn=sqlite3.connect("database.db")
    c=conn.cursor()

    # 🧠 Dynamic query
    query="SELECT * FROM records WHERE 1=1"
    params=[]

    # 🔍 Search (by name OR patient_id)
    if search:
        query+=" AND (name LIKE ? OR patient_id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    # 🎯 Filter
    if filter_type=="high":
        query+=" AND risk='High Risk'"
    elif filter_type=="recent":
        query+=" ORDER BY id DESC LIMIT 5"

    # Run query
    c.execute(query, params)
    data=c.fetchall()

    # 📊 Dashboard stats (KEEP SAME)
    c.execute("SELECT COUNT(*) FROM records WHERE risk='Low Risk'")
    low=c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM records WHERE risk='Medium Risk'")
    medium=c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM records WHERE risk='High Risk'")
    high=c.fetchone()[0]

    c.execute("SELECT AVG(bmi) FROM records")
    avg_bmi=c.fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        data=data,
        low=low,
        medium=medium,
        high=high,
        avg_bmi=avg_bmi
    )
    
@app.route("/delete/<int:id>")
def delete(id):
    conn=sqlite3.connect("database.db")
    c=conn.cursor()

    c.execute("DELETE FROM records WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/edit/<int:id>")
def edit(id):
    conn=sqlite3.connect("database.db")
    c=conn.cursor()

    c.execute("SELECT * FROM records WHERE id=?", (id,))
    record=c.fetchone()

    conn.close()

    return render_template("edit.html", record=record)

@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    name=request.form["name"]
    patient_id=request.form["patient_id"]
    contact=request.form["contact"]

    age=request.form["age"]
    bmi=request.form["bmi"]
    heart_rate=request.form["heart_rate"]
    sleep=request.form["sleep"]
    activity=request.form["activity"]

    conn=sqlite3.connect("database.db")
    c=conn.cursor()

    c.execute("""
        UPDATE records
        SET name=?, patient_id=?, contact=?, age=?, bmi=?, heart_rate=?, sleep_hours=?, activity_level=?
        WHERE id=?
    """, (name, patient_id, contact, age, bmi, heart_rate, sleep, activity, id))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/logout")
def logout():
    session.pop("user",None)
    return redirect("/login")

if __name__=="__main__":
    #app.run(debug=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))