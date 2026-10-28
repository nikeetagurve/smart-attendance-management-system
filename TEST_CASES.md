# Test Cases — Smart Attendance Management System

| ID | Test scenario | Preconditions / steps | Expected result | Actual result | Status |
|---|---|---|---|---|---|
| TC-01 | Add student | Open Students → Add student; enter name and unique roll number | Student is added and appears in directory | Fill during execution | Not run |
| TC-02 | Required fields | Submit the student form with a blank name or roll number | Browser validation prevents incomplete submission | Fill during execution | Not run |
| TC-03 | Duplicate roll number | Add a student using an existing roll number | Clear duplicate-roll-number error is shown | Fill during execution | Not run |
| TC-04 | Enable camera | Open Face enrollment and allow browser camera permission | Live camera preview appears | Fill during execution | Not run |
| TC-05 | Enroll face samples | Select a student, capture at least 3 clear face samples, save | Usable samples are stored and local model is trained | Fill during execution | Not run |
| TC-06 | No face in sample | Capture a scene without a visible face | Sample is rejected with a helpful message | Fill during execution | Not run |
| TC-07 | Scan enrolled face | Enroll a consenting participant, open Live scan and scan them | System may identify the participant and record attendance; verify manually | Fill during execution | Not run |
| TC-08 | Scan unknown face | Scan a person who is not enrolled | System should return no match; verify false-match risk | Fill during execution | Not run |
| TC-09 | Duplicate attendance | Scan the same enrolled participant again on the same date | Second scan reports already marked; no duplicate record | Fill during execution | Not run |
| TC-10 | View attendance | Open Attendance for a date with records | Correct records and times are shown | Fill during execution | Not run |
| TC-11 | Export CSV | Select a date and click Export CSV | CSV downloads with attendance columns | Fill during execution | Not run |
| TC-12 | Remove student | Remove a test student and confirm | Student, face samples and related attendance records are deleted | Fill during execution | Not run |
| TC-13 | Camera permission denied | Deny camera permission and try to enable it | Helpful error is displayed; app remains usable | Fill during execution | Not run |
| TC-14 | Model not trained | Attempt scanning before enrollment | System explains that a model must be trained first | Fill during execution | Not run |

**Execution note:** record Actual result and Pass/Fail only after you run each test. A successful UI flow does not prove biometric accuracy. Test face matching with consenting participants and manually verify outcomes.


## Automated test coverage
The accompanying `tests/test_app.py` pytest suite automates API/application-logic checks for: home page, successful student registration, duplicate roll numbers, missing required fields, enrollment student/sample validation, mocked successful enrollment, scan before model training, successful scan plus duplicate attendance prevention, no-face response, CSV export, student deletion, and dashboard counts. Run `./run_tests_mac_linux.sh` on macOS/Linux or `run_tests_windows.bat` on Windows. Camera and face-recognizer behavior are mocked for repeatability; these tests do not measure real-world biometric accuracy.
