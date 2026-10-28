# Smart Attendance Management System — SETM Prototype

A local web prototype for a college Smart Attendance Management System with face recognition. Includes student registration, face enrollment through webcam, live face matching, daily attendance, duplicate prevention, and CSV export.

## Requirements
- Python 3.10–3.12 recommended
- Webcam
- Internet connection for the first dependency installation
- macOS, Windows, or Linux

## Run on macOS
1. Extract the ZIP.
2. Open Terminal and move into the extracted folder, for example:
   `cd ~/Downloads/smart_attendance_prototype`
3. Run:
   `chmod +x run_mac_linux.sh && ./run_mac_linux.sh`
4. Open **http://127.0.0.1:5000** in Chrome, Safari, or Edge.
5. Allow camera access when prompted.

The first run may take a few minutes while Python packages install. Keep the Terminal window open while using the app. Press `Ctrl+C` in Terminal to stop it.

## Run on Windows
1. Extract the ZIP.
2. Double-click `run_windows.bat`.
3. Open **http://127.0.0.1:5000** and allow camera access.

## Quick demo
1. Go to **Students** and add a student name and unique roll number.
2. Open **Face Enrollment**, select that student, and capture 8–12 samples. Slightly vary your head angle and expression while keeping the face visible.
3. Open **Live Scan**, allow camera access, and scan the enrolled person.
4. Open **Attendance** to see records and export a CSV report.

## Notes and limitations
- Face detection uses OpenCV's Haar cascade; face matching uses LBPH from OpenCV contrib. It is a simple educational baseline, not state-of-the-art recognition.
- The default matching threshold is intentionally conservative but may need calibration for your lighting/camera. A lower LBPH distance indicates a closer match; the value shown is a distance, not a probability.
- Enroll only people who have explicitly consented. Face samples and the database stay in the local `data/` directory on your computer. Do not use real student biometrics without institutional approval, consent, access controls, and a deletion/retention policy.
- This prototype does not implement liveness detection, anti-spoofing, institutional login, network deployment, or production-grade security. A printed photo or screen may fool a basic demo recognizer.
- The browser camera works on `localhost`. Do not expose this development server to the public internet.
- To reset all demo data, stop the app and delete the `data/` directory. This permanently deletes the local student list, face samples, model, and attendance database.
- If camera access fails, check browser permissions and close other apps using the webcam.

## Run automated tests
The project includes `tests/test_app.py`, a pytest suite for the application API and attendance logic. The tests use a temporary database and mock face-model/camera operations, so they do not require you to turn on your webcam. They test student registration, duplicate and missing fields, enrollment validation, scan responses, duplicate attendance prevention, CSV export, student deletion, and dashboard counts.

### macOS / Linux
Open a second Terminal window in the project folder and run:
```bash
chmod +x run_tests_mac_linux.sh
./run_tests_mac_linux.sh
```

### Windows
Double-click `run_tests_windows.bat`, or run it from Command Prompt.

The command prints each test and a final summary such as `X passed`. The exact number can change if tests are added later. A passing automated suite verifies application logic under controlled conditions; it does **not** prove real-world face-recognition accuracy. The tests mock the camera image and recognizer so they are repeatable and do not use real people's biometric data.

## Automated Testing Dashboard
The sidebar includes **Testing dashboard**. Open it and click **Run automated tests** to execute the real `pytest` suite on the local machine. The page shows per-test pass/fail/skip status, totals, and the technical pytest output. The local Flask app must be running and pytest must be installed in the same Python environment (the included run scripts install it).

The test suite uses a temporary database and mocked camera/model operations. It verifies application/API logic; it does not establish real-world biometric accuracy or test webcam recognition quality.
