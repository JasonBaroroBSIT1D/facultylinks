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

## Android — physical device (same Wi‑Fi as your PC)

`127.0.0.1` on the phone points at the phone, not your PC. Start the API so it listens on the LAN (`python run.py` in `backend/` — binds `0.0.0.0:5000` by default).

Copy `config/dart_defines.local.example.json` to `config/dart_defines.local.json`, set your PC’s Wi‑Fi IPv4 (`ipconfig`, e.g. `192.168.1.27`), then **full reinstall**:

```powershell
flutter run --dart-define-from-file=config/dart_defines.local.json
```

Or inline:

```powershell
flutter run --dart-define=FACULTYLINK_DEV_LAN_HOST=192.168.1.27
```

Or pass the full URL:

```powershell
flutter run --dart-define=FACULTYLINK_API_BASE=http://192.168.1.23:5000
```

Allow port **5000** through Windows Firewall if needed. Debug builds permit cleartext HTTP to your LAN API.

## Android emulator

```powershell
flutter run --dart-define=FACULTYLINK_API_BASE=http://10.0.2.2:5000
```

## Release build

```powershell
flutter build apk --dart-define=FACULTYLINK_API_BASE=https://your-api.example.com
```

See also [docs/BACKEND_SETUP_WINDOWS.md](../docs/BACKEND_SETUP_WINDOWS.md).
