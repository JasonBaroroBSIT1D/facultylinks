# FacultyLink — faculty mobile app

Flutter client for faculty self-assessment. Talks to the Flask API with `X-Client-Type: faculty_mobile`.

## Development (Flutter web on Chrome)

Use a **fixed web port** so you can add that origin to backend `CORS_ORIGINS` (no wildcard CORS).

```powershell
cd faculty_mobile
flutter pub get
flutter run -d chrome --web-port=49932 --dart-define=FACULTYLINK_API_BASE=http://127.0.0.1:5000
```

In `backend/.env`, include both loopback forms of that origin (comma-separated, no trailing slash):

```env
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:49932,http://localhost:49932
```

Run the API on port 5000 (`python run.py` in `backend/`) before signing in.

## Android / other targets

```powershell
flutter run --dart-define=FACULTYLINK_API_BASE=http://127.0.0.1:5000
```

On a physical device, use your PC LAN IP and add any browser/app origin you need to `CORS_ORIGINS`.

See also [docs/BACKEND_SETUP_WINDOWS.md](../docs/BACKEND_SETUP_WINDOWS.md).
