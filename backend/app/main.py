import time
import random
import json

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from fastapi.responses import HTMLResponse
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models import init_db
from app.db import get_connection


app = FastAPI(title="Google Sheets MySQL Sync")


# --------------------
# Startup
# --------------------

@app.on_event("startup")
def startup():
    init_db()


# --------------------
# Health
# --------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------
# Retry with exponential backoff
# --------------------

def retry_with_backoff(fn, max_retries=5, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return fn()
        except HttpError as e:
            status = e.resp.status
            if status in (429, 500, 502, 503, 504):
                sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(sleep_time)
            else:
                raise
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))


# --------------------
# Sheet to MySQL
# --------------------

@app.post("/webhook/sheet")
async def sheet_webhook(request: Request):
    payload = await request.json()
    data = payload.get("data", {})

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (id, name, email)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            email = VALUES(email)
        """,
        (
            data.get("id"),
            data.get("name"),
            data.get("email"),
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "ok"}


# --------------------
# Google Sheets helpers
# --------------------

def get_sheets_service():
    creds = Credentials.from_service_account_file(
        "app/service_account.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)


def update_sheet_row(service, spreadsheet_id, sheet_name, row_id, values):
    result = retry_with_backoff(lambda: service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A2:C"
    ).execute())

    rows = result.get("values", [])

    for index, row in enumerate(rows, start=2):
        if str(row[0]) == str(row_id):
            retry_with_backoff(lambda: service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A{index}:C{index}",
                valueInputOption="RAW",
                body={"values": [values]}
            ).execute())
            return True

    return False


# --------------------
# MySQL to Sheet
# --------------------

@app.api_route("/sync/mysql-to-sheet", methods=["GET", "POST"])
def mysql_to_sheet():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM mysql_change_log
        WHERE processed = FALSE
        ORDER BY created_at ASC
        """
    )
    changes = cursor.fetchall()

    if not changes:
        cursor.close()
        conn.close()
        return {"status": "no changes"}

    service = get_sheets_service()

    SPREADSHEET_ID = "1S40HEgxsbiA0o3_1Lg3cY7T1VHvYSa0-Fv37m7rdmxc"
    SHEET_NAME = "users"

    for change in changes:
        payload = json.loads(change["payload"])

        updated = update_sheet_row(
            service=service,
            spreadsheet_id=SPREADSHEET_ID,
            sheet_name=SHEET_NAME,
            row_id=payload["id"],
            values=[
                payload["id"],
                payload["name"],
                payload["email"]
            ]
        )

        if updated:
            cursor.execute(
                "UPDATE mysql_change_log SET processed = TRUE WHERE id = %s",
                (change["id"],)
            )

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "synced"}


# --------------------
# API for frontend
# --------------------

@app.get("/api/users")
def get_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, name, email FROM users ORDER BY id")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"users": rows}


# --------------------
# Frontend
# --------------------



@app.get("/", response_class=HTMLResponse)
def frontend():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Google Sheets ↔ MySQL Sync Playground</title>
  <style>
    body {
      margin: 0;
      font-family: Inter, Arial, sans-serif;
      background: linear-gradient(180deg, #f8f9fa, #eef1f4);
    }

    .container {
      max-width: 1100px;
      margin: 40px auto;
      padding: 30px;
    }

    h1 {
      text-align: center;
      margin-bottom: 8px;
    }

    .subtitle {
      text-align: center;
      color: #555;
      margin-bottom: 30px;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 30px;
    }

    .card {
      background: white;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 10px 20px rgba(0,0,0,0.06);
    }

    .card h3 {
      margin-top: 0;
    }

    .steps p {
      margin: 8px 0;
      color: #333;
    }

    .btn {
      display: inline-block;
      padding: 10px 16px;
      border-radius: 6px;
      background: #1a73e8;
      color: white;
      text-decoration: none;
      font-size: 14px;
      border: none;
      cursor: pointer;
    }

    .btn.secondary {
      background: #34a853;
    }

    .btn.gray {
      background: #6c757d;
    }

    .btn + .btn {
      margin-left: 10px;
    }

    .table-container {
      background: white;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 10px 20px rgba(0,0,0,0.06);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }

    th, td {
      padding: 10px;
      border-bottom: 1px solid #ddd;
      text-align: left;
    }

    th {
      background: #f1f3f4;
      font-weight: 600;
    }

    .status {
      margin-top: 10px;
      font-size: 13px;
      color: #666;
    }

    .footer {
      text-align: center;
      margin-top: 40px;
      color: #777;
      font-size: 13px;
    }
  </style>
</head>
<body>

<div class="container">
  <h1>Google Sheets ↔ MySQL Sync</h1>
  <div class="subtitle">
    Live two way data synchronization playground
  </div>

  <div class="grid">
    <div class="card steps">
      <h3>How to test</h3>
      <p>1. Open the Google Sheet</p>
      <p>2. Edit or add rows</p>
      <p>3. Changes auto sync to MySQL</p>
      <p>4. Update MySQL to sync back</p>

      <br />

      <a class="btn" target="_blank"
         href="https://docs.google.com/spreadsheets/d/1S40HEgxsbiA0o3_1Lg3cY7T1VHvYSa0-Fv37m7rdmxc">
        Open Google Sheet
      </a>
    </div>

    <div class="card">
      <h3>Controls</h3>
      <p>Manual actions for demo</p>
      <br />
      <button class="btn secondary" onclick="sync()">Sync MySQL → Sheet</button>
      <button class="btn gray" onclick="loadUsers()">Refresh DB</button>
      <div class="status" id="syncStatus">Idle</div>
    </div>
  </div>

  <div class="table-container">
    <h3>Live MySQL View</h3>
    <p class="subtitle">Auto refreshes every 2 seconds</p>

    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Email</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </div>

  <div class="footer">
    Demo system built for real time bi directional sync testing
  </div>
</div>

<script>
async function loadUsers() {
  const res = await fetch("/api/users");
  const data = await res.json();

  const tbody = document.getElementById("rows");
  tbody.innerHTML = "";

  data.users.forEach(u => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${u.id}</td><td>${u.name}</td><td>${u.email}</td>`;
    tbody.appendChild(tr);
  });
}

async function sync() {
  document.getElementById("syncStatus").innerText = "Syncing...";
  const res = await fetch("/sync/mysql-to-sheet");
  const data = await res.json();
  document.getElementById("syncStatus").innerText =
    "Last sync: " + new Date().toLocaleTimeString();
}

loadUsers();
setInterval(loadUsers, 2000);
</script>

</body>
</html>
"""
