# EV Digital Twin Simulator & Dashboard

This repository contains a simple Flask-based dashboard and a device simulator that posts battery telemetry to the API. It's suited for demo, prototyping, and small deployments.

## Prepare for deployment

You'll find a ready-to-deploy configuration for common PaaS providers (Render, Heroku, Railway):

- `Procfile` — runs `gunicorn app:app`.
- `requirements.txt` — lists Python dependencies.
- `app.py` — updated to bind to `0.0.0.0` and use the `PORT` environment variable.

## Quick local run

1. Create a virtual environment and install requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Start the Flask app (development):

```powershell
$env:FLASK_DEBUG = "1"
python app.py
```

3. In another terminal start the device simulator:

```powershell
python device_simulator.py
```

4. Open the dashboard at `http://127.0.0.1:5000` (you must register/login first).

## Deploy to Render (example)

1. Commit and push this repository to GitHub.
2. Create a new Web Service on Render and connect your GitHub repo.
3. For the start/command, Render will detect `Procfile` or you can use:

   `gunicorn app:app --bind 0.0.0.0:$PORT`

4. Set environment variables if needed:
   - `FLASK_DEBUG=0` (for production)

5. Deploy — Render will build using `requirements.txt` and run the service.

## Deploy to Heroku (example)

1. Install the Heroku CLI and log in.
2. Create an app: `heroku create your-app-name`.
3. Push your repository: `git push heroku main`.
4. Heroku will use `Procfile` and `requirements.txt` to build.

## Notes & next steps

- `users.json` and `mode.txt` are ignored by `.gitignore`. If you want persistent storage, replace them with a managed DB.
- Consider adding TLS/HTTPS, authentication hardening, and secrets management (use environment variables).

If you want, I can:
- Create a Git commit with these files and push to a GitHub repo (you'll need to provide the repo or let me create one), or
- Walk you through connecting your GitHub repo to Render/Heroku and completing deployment steps.
