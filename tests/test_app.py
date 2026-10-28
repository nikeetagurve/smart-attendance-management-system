"""Automated API tests for the Smart Attendance SETM prototype.

These tests use temporary SQLite files and mocked camera/model operations, so
pytest does not need webcam access or real face images.
"""
import csv
import io
import os
import sys

import numpy as np
import pytest

# Make the project root importable when pytest is run from this directory.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app as attendance_app  # noqa: E402


class FakeRecognizer:
    def __init__(self, label=1, distance=24.5):
        self.label = label
        self.distance = distance

    def predict(self, _face):
        return self.label, self.distance


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provide an isolated Flask test client and a fresh temporary database."""
    data_dir = tmp_path / "data"
    faces_dir = data_dir / "faces"
    faces_dir.mkdir(parents=True)
    monkeypatch.setattr(attendance_app, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(attendance_app, "FACES_DIR", str(faces_dir))
    monkeypatch.setattr(attendance_app, "MODEL_PATH", str(data_dir / "face_model.yml"))
    monkeypatch.setattr(attendance_app, "DB_PATH", str(data_dir / "test_attendance.db"))
    attendance_app.init_db()
    attendance_app.app.config.update(TESTING=True)
    with attendance_app.app.test_client() as test_client:
        yield test_client


def add_student(client, name="Aarya Khobragade", roll_no="01"):
    return client.post("/api/students", json={
        "name": name,
        "roll_no": roll_no,
        "department": "CSE (AI & DS)",
        "year": "Second Year",
    })


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"attenda" in response.data.lower()


def test_add_student_success(client):
    response = add_student(client)
    assert response.status_code == 200
    assert response.get_json()["id"] == 1
    rows = client.get("/api/students").get_json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Aarya Khobragade"
    assert rows[0]["roll_no"] == "01"


def test_duplicate_roll_number_is_rejected(client):
    assert add_student(client).status_code == 200
    response = add_student(client, name="Another Student", roll_no="01")
    assert response.status_code == 409
    assert "already registered" in response.get_json()["error"]


@pytest.mark.parametrize("payload", [{"name": "", "roll_no": "02"}, {"name": "Test Student", "roll_no": ""}, {}])
def test_missing_student_fields_are_rejected(client, payload):
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "required" in response.get_json()["error"]


def test_enrollment_requires_existing_student(client, monkeypatch):
    monkeypatch.setattr(attendance_app, "recognizer", FakeRecognizer())
    response = client.post("/api/enroll", json={"student_id": 999, "images": ["a", "b", "c"]})
    assert response.status_code == 404
    assert "registered student" in response.get_json()["error"]


def test_enrollment_requires_at_least_three_samples(client, monkeypatch):
    add_student(client)
    monkeypatch.setattr(attendance_app, "recognizer", FakeRecognizer())
    response = client.post("/api/enroll", json={"student_id": 1, "images": ["sample"]})
    assert response.status_code == 400
    assert "at least 3" in response.get_json()["error"]


def test_enrollment_saves_samples_and_trains_model(client, monkeypatch):
    add_student(client)
    monkeypatch.setattr(attendance_app, "recognizer", FakeRecognizer())
    monkeypatch.setattr(attendance_app, "decode_image", lambda _data: np.zeros((20, 20, 3), dtype=np.uint8))
    monkeypatch.setattr(attendance_app, "get_face", lambda _image: np.zeros((200, 200), dtype=np.uint8))

    def fake_imwrite(path, _image):
        with open(path, "wb") as sample_file:
            sample_file.write(b"mock-face-sample")
        return True

    monkeypatch.setattr(attendance_app.cv2, "imwrite", fake_imwrite)
    monkeypatch.setattr(attendance_app, "rebuild_model", lambda: 3)
    response = client.post("/api/enroll", json={"student_id": 1, "images": ["one", "two", "three"]})
    assert response.status_code == 200
    assert response.get_json()["saved"] == 3


def test_scan_without_trained_model_returns_helpful_error(client, monkeypatch):
    monkeypatch.setattr(attendance_app, "recognizer", FakeRecognizer())
    monkeypatch.setattr(attendance_app, "model_ready", lambda: False)
    response = client.post("/api/scan", json={"image": "data:image/jpeg;base64,AA=="})
    assert response.status_code == 400
    assert "model yet" in response.get_json()["error"]


def test_scan_marks_attendance_and_prevents_duplicate(client, monkeypatch):
    add_student(client)
    monkeypatch.setattr(attendance_app, "recognizer", FakeRecognizer(label=1, distance=24.5))
    monkeypatch.setattr(attendance_app, "model_ready", lambda: True)
    monkeypatch.setattr(attendance_app, "decode_image", lambda _data: np.zeros((20, 20, 3), dtype=np.uint8))
    monkeypatch.setattr(attendance_app, "get_face", lambda _image: np.zeros((200, 200), dtype=np.uint8))

    first = client.post("/api/scan", json={"image": "mock-image"}).get_json()
    second = client.post("/api/scan", json={"image": "mock-image"}).get_json()
    assert first["recognized"] is True
    assert first["duplicate"] is False
    assert first["message"] == "Attendance marked present."
    assert second["recognized"] is True
    assert second["duplicate"] is True
    assert second["message"] == "Attendance was already marked today."
    records = client.get("/api/attendance").get_json()
    assert len(records) == 1
    assert records[0]["roll_no"] == "01"


def test_scan_returns_no_face_when_detector_finds_nothing(client, monkeypatch):
    add_student(client)
    monkeypatch.setattr(attendance_app, "recognizer", FakeRecognizer())
    monkeypatch.setattr(attendance_app, "model_ready", lambda: True)
    monkeypatch.setattr(attendance_app, "decode_image", lambda _data: np.zeros((20, 20, 3), dtype=np.uint8))
    monkeypatch.setattr(attendance_app, "get_face", lambda _image: None)
    response = client.post("/api/scan", json={"image": "mock-image"})
    assert response.status_code == 200
    assert response.get_json()["recognized"] is False
    assert "No face detected" in response.get_json()["message"]


def test_attendance_csv_export_contains_headers_and_student(client):
    add_student(client)
    with attendance_app.db() as conn:
        from datetime import date
        conn.execute(
            "INSERT INTO attendance (student_id, attendance_date, attendance_time, status) VALUES (?, ?, ?, ?)",
            (1, date.today().isoformat(), "09:15:00", "Present"),
        )
    response = client.get("/api/attendance/export")
    assert response.status_code == 200
    assert "text/csv" in response.content_type
    reader = csv.reader(io.StringIO(response.data.decode("utf-8-sig")))
    rows = list(reader)
    assert rows[0] == ["Student Name", "Roll Number", "Department", "Year", "Date", "Time", "Status"]
    assert rows[1][0:2] == ["Aarya Khobragade", "01"]


def test_delete_student_removes_student_record(client, monkeypatch):
    add_student(client)
    monkeypatch.setattr(attendance_app, "rebuild_model", lambda: 0)
    response = client.delete("/api/students/1")
    assert response.status_code == 200
    assert client.get("/api/students").get_json() == []


def test_status_endpoint_reports_counts(client):
    add_student(client)
    data = client.get("/api/status").get_json()
    assert data["students"] == 1
    assert data["today_present"] == 0
    assert data["total_records"] == 0
