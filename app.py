from flask import Flask, render_template, request, jsonify, send_file
import os, io, base64, sqlite3, csv, json, subprocess, sys, re
from datetime import datetime, date
import numpy as np
import cv2

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
FACES_DIR = os.path.join(DATA_DIR, "faces")
MODEL_PATH = os.path.join(DATA_DIR, "face_model.yml")
DB_PATH = os.path.join(DATA_DIR, "attendance.db")
os.makedirs(FACES_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

CASCADE_PATH = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
recognizer = None
if hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create"):
    recognizer = cv2.face.LBPHFaceRecognizer_create()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT DEFAULT 'CSE (AI & DS)',
            year TEXT DEFAULT 'Second Year',
            created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            attendance_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Present',
            UNIQUE(student_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(id)
        )""")

def load_model():
    global recognizer
    if recognizer is None:
        return False
    if os.path.exists(MODEL_PATH):
        try:
            recognizer.read(MODEL_PATH)
            return True
        except cv2.error:
            return False
    return False

def decode_image(data_url):
    if not data_url or "," not in data_url:
        raise ValueError("No image was received.")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("The camera image could not be read.")
    return image

def get_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    # Use the largest detected face.
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))
    face = cv2.equalizeHist(face)
    return face

def rebuild_model():
    global recognizer
    if recognizer is None:
        return 0
    samples, labels = [], []
    with db() as conn:
        students = conn.execute("SELECT id FROM students ORDER BY id").fetchall()
    for student in students:
        folder = os.path.join(FACES_DIR, str(student["id"]))
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            image = cv2.imread(os.path.join(folder, filename), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                image = cv2.resize(image, (200, 200))
                samples.append(cv2.equalizeHist(image))
                labels.append(int(student["id"]))
    if samples:
        recognizer.train(samples, np.array(labels, dtype=np.int32))
        recognizer.write(MODEL_PATH)
        return len(samples)
    if os.path.exists(MODEL_PATH):
        os.remove(MODEL_PATH)
    return 0

def model_ready():
    return recognizer is not None and load_model()

@app.route("/")
def index():
    return render_template("index.html")



@app.route("/api/tests/run", methods=["POST"])
def run_automated_tests():
    """Run the project's pytest suite and return real, per-test results."""
    tests_dir = os.path.join(APP_DIR, "tests")
    if not os.path.isdir(tests_dir):
        return jsonify({"error": "Automated tests folder was not found."}), 500
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "--tb=short", tests_dir],
            cwd=APP_DIR, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Tests exceeded the 120-second time limit."}), 504
    except Exception as exc:
        return jsonify({"error": f"Could not start pytest: {exc}"}), 500

    output = (result.stdout or "") + "\n" + (result.stderr or "")
    cases = []
    for line in output.splitlines():
        match = re.match(r"^(.+?)\s+(PASSED|FAILED|SKIPPED|ERROR)(?:\s+.*)?$", line.strip())
        if match:
            node, status_text = match.groups()
            short_name = node.split("::")[-1]
            pretty = re.sub(r"^test_", "", short_name).replace("_", " ").capitalize()
            cases.append({"name": pretty, "id": short_name, "status": status_text.lower()})
    summary_match = re.search(r"(\d+\s+passed)?(?:,?\s*(\d+)\s+failed)?(?:,?\s*(\d+)\s+error)?(?:,?\s*(\d+)\s+skipped)?", output.splitlines()[-2] if len(output.splitlines()) > 1 else "")
    # Derive counts from individual results so the dashboard reports actual execution.
    counts = {key: sum(1 for case in cases if case["status"] == key) for key in ("passed", "failed", "error", "skipped")}
    return jsonify({"success": result.returncode == 0, "exit_code": result.returncode, "cases": cases,
                    "counts": counts, "total": len(cases), "output": output[-12000:]})

@app.route("/api/status")
def status():
    with db() as conn:
        student_count = conn.execute("SELECT COUNT(*) c FROM students").fetchone()["c"]
        today_count = conn.execute("SELECT COUNT(*) c FROM attendance WHERE attendance_date=?", (date.today().isoformat(),)).fetchone()["c"]
        recent = conn.execute("""SELECT s.name, s.roll_no, a.attendance_time, a.status
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.attendance_date=? ORDER BY a.id DESC LIMIT 6""", (date.today().isoformat(),)).fetchall()
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM attendance").fetchone()["c"]
    return jsonify({
        "students": student_count, "today_present": today_count, "total_records": total,
        "model_available": recognizer is not None,
        "recent": [dict(r) for r in recent],
        "today": date.today().strftime("%d %b %Y")
    })

@app.route("/api/students", methods=["GET"])
def students():
    with db() as conn:
        rows = conn.execute("""SELECT s.*, (SELECT COUNT(*) FROM attendance a WHERE a.student_id=s.id) AS attendance_count
            FROM students s ORDER BY s.name COLLATE NOCASE""").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/students", methods=["POST"])
def add_student():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    roll_no = (data.get("roll_no") or "").strip()
    department = (data.get("department") or "CSE (AI & DS)").strip()
    year = (data.get("year") or "Second Year").strip()
    if not name or not roll_no:
        return jsonify({"error": "Student name and roll number are required."}), 400
    try:
        with db() as conn:
            cur = conn.execute("INSERT INTO students (roll_no,name,department,year,created_at) VALUES (?,?,?,?,?)",
                (roll_no, name, department, year, datetime.now().isoformat(timespec="seconds")))
            student_id = cur.lastrowid
        os.makedirs(os.path.join(FACES_DIR, str(student_id)), exist_ok=True)
        return jsonify({"id": student_id, "message": "Student added. Next, enroll face samples."})
    except sqlite3.IntegrityError:
        return jsonify({"error": "That roll number is already registered."}), 409

@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    with db() as conn:
        conn.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
    import shutil
    shutil.rmtree(os.path.join(FACES_DIR, str(student_id)), ignore_errors=True)
    rebuild_model()
    return jsonify({"message": "Student and their local face samples were deleted."})

@app.route("/api/enroll", methods=["POST"])
def enroll():
    if recognizer is None:
        return jsonify({"error": "Face recognition requires opencv-contrib-python. Install dependencies from requirements.txt."}), 500
    data = request.get_json(force=True)
    student_id = int(data.get("student_id", 0))
    images = data.get("images") or []
    with db() as conn:
        student = conn.execute("SELECT id FROM students WHERE id=?", (student_id,)).fetchone()
    if not student:
        return jsonify({"error": "Choose a registered student first."}), 404
    if len(images) < 3:
        return jsonify({"error": "Capture at least 3 samples. 8–12 varied samples are recommended."}), 400
    folder = os.path.join(FACES_DIR, str(student_id))
    os.makedirs(folder, exist_ok=True)
    saved = 0
    errors = []
    for idx, data_url in enumerate(images):
        try:
            image = decode_image(data_url)
            face = get_face(image)
            if face is None:
                errors.append(f"Sample {idx+1}: no face detected")
                continue
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{idx}.png"
            cv2.imwrite(os.path.join(folder, filename), face)
            saved += 1
        except Exception:
            errors.append(f"Sample {idx+1}: image could not be processed")
    if saved:
        total_samples = rebuild_model()
        return jsonify({"message": f"Saved {saved} face sample(s). Model trained with {total_samples} sample(s).",
                        "saved": saved, "errors": errors})
    return jsonify({"error": "No usable face samples were saved. Face the camera, improve lighting, and try again.", "details": errors}), 400

@app.route("/api/scan", methods=["POST"])
def scan():
    if recognizer is None:
        return jsonify({"error": "Face recognition is unavailable. Install dependencies from requirements.txt."}), 500
    if not model_ready():
        return jsonify({"error": "No trained face model yet. Register a student and enroll face samples first."}), 400
    data = request.get_json(force=True)
    try:
        image = decode_image(data.get("image"))
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    face = get_face(image)
    if face is None:
        return jsonify({"recognized": False, "message": "No face detected. Center your face and try again."})
    label, confidence = recognizer.predict(face)
    # LBPH distance is lower for a closer match; this is only a demo threshold.
    threshold = 72.0
    if confidence > threshold:
        return jsonify({"recognized": False, "confidence": round(float(confidence), 1),
                        "message": "Face not matched. Register this student or try better lighting."})
    with db() as conn:
        student = conn.execute("SELECT * FROM students WHERE id=?", (int(label),)).fetchone()
        if not student:
            return jsonify({"recognized": False, "message": "No registered student matched."})
        today = date.today().isoformat()
        now = datetime.now().strftime("%H:%M:%S")
        try:
            conn.execute("INSERT INTO attendance (student_id,attendance_date,attendance_time,status) VALUES (?,?,?,'Present')",
                         (int(label), today, now))
            status_text = "Attendance marked present."
            duplicate = False
        except sqlite3.IntegrityError:
            status_text = "Attendance was already marked today."
            duplicate = True
    return jsonify({"recognized": True, "name": student["name"], "roll_no": student["roll_no"],
                    "confidence": round(float(confidence), 1), "time": now,
                    "duplicate": duplicate, "message": status_text})

@app.route("/api/attendance")
def attendance():
    selected_date = request.args.get("date", date.today().isoformat())
    with db() as conn:
        rows = conn.execute("""SELECT s.name, s.roll_no, s.department, a.attendance_date, a.attendance_time, a.status
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.attendance_date=? ORDER BY a.attendance_time DESC""", (selected_date,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/attendance/export")
def export_attendance():
    selected_date = request.args.get("date", date.today().isoformat())
    with db() as conn:
        rows = conn.execute("""SELECT s.name, s.roll_no, s.department, s.year, a.attendance_date, a.attendance_time, a.status
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.attendance_date=? ORDER BY s.name COLLATE NOCASE""", (selected_date,)).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Roll Number", "Department", "Year", "Date", "Time", "Status"])
    for row in rows:
        writer.writerow([row[k] for k in row.keys()])
    mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True,
                     download_name=f"attendance_{selected_date}.csv")

@app.route("/api/attendance/clear-today", methods=["POST"])
def clear_today():
    with db() as conn:
        conn.execute("DELETE FROM attendance WHERE attendance_date=?", (date.today().isoformat(),))
    return jsonify({"message": "Today's attendance records were cleared."})

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "Image upload too large. Try again."}), 413

init_db()
if recognizer is not None:
    load_model()

if __name__ == "__main__":
    print("\\nSmart Attendance Prototype")
    print("Open http://127.0.0.1:5000 in your browser.")
    if recognizer is None:
        print("WARNING: Face recognition module unavailable. Install requirements.")
    app.run(host="127.0.0.1", port=5000, debug=False)
