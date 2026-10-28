# Software Requirements Specification (SRS)
## Smart Attendance Management System with Face Recognition
**Project type:** SETM Lab prototype

## 1. Purpose
The system demonstrates how a college can register students, enroll face samples with consent, scan a face, and record attendance once per student per day.

## 2. Scope
The prototype runs locally on one computer. It provides student management, webcam face enrollment, local face matching, daily attendance records, and CSV export. It is not an institution-wide production system.

## 3. Users
- **Administrator / faculty:** register and remove student records, enroll face samples, run scans, view and export attendance.
- **Student / participant:** provides face samples only with informed consent; does not directly access the admin interface in this prototype.

## 4. Functional requirements
- FR-01: The system shall allow faculty to register a student with a unique roll number.
- FR-02: The system shall reject a registration without a name or roll number.
- FR-03: The system shall reject duplicate roll numbers.
- FR-04: The system shall capture face images from a webcam for a selected student.
- FR-05: The system shall detect a face in captured images and save usable face samples locally.
- FR-06: The system shall train/update the local face matching model from enrolled samples.
- FR-07: The system shall compare a scan against enrolled samples and return a match or no-match response.
- FR-08: The system shall record a recognized student's attendance with local date and time.
- FR-09: The system shall prevent more than one attendance record per student per day.
- FR-10: The system shall display attendance records for a selected date.
- FR-11: The system shall export selected-date attendance as CSV.
- FR-12: The system shall allow removal of a student and their associated samples and attendance records.

## 5. Non-functional requirements
- NFR-01 Usability: the interface shall use clear navigation and understandable status messages.
- NFR-02 Performance: a local scan should return a result within a few seconds on a typical laptop, depending on hardware.
- NFR-03 Privacy: student records, face samples, model and attendance database shall remain in the local project data directory.
- NFR-04 Reliability: the system shall handle missing faces, duplicate roll numbers, and repeated daily scans without crashing.
- NFR-05 Compatibility: use a recent desktop browser and a supported Python environment.
- NFR-06 Maintainability: source code and dependencies shall be included in the project folder.

## 6. Constraints and assumptions
- A webcam and permission to use it are available.
- Face samples are captured with the participant's explicit consent.
- OpenCV Haar cascade + LBPH are used for educational demonstration only.
- No liveness/anti-spoofing, role-based login, cloud deployment, or production-grade security is included.

## 7. Acceptance criteria
- Faculty can add a student and duplicate roll numbers are rejected.
- Three or more valid samples can be enrolled.
- A trained model can return a match/no-match response for a camera image.
- A recognized student is recorded as present, with duplicates prevented for the same date.
- The date-specific register is visible and can be exported to CSV.
- Removing a student removes their local face sample folder and related attendance records.

## 8. Privacy and ethical considerations
Only enroll consenting participants. Explain what is captured and why, limit access to the local machine, delete samples when no longer needed, and do not use this educational prototype as the sole basis for consequential decisions. Face matching may produce false accepts and false rejects.
