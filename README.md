# Google Sheets and MySQL Two Way Sync System

## Overview

This project implements a live two way data synchronization system between Google Sheets and a MySQL database.  
Any change made in Google Sheets is reflected in MySQL, and any change made in MySQL is reflected back into Google Sheets.

The system is designed with production level principles in mind. The focus is on correctness, reliability, concurrency handling, and failure recovery rather than being a simple script or one off integration.

A lightweight web interface is also included to visualize the MySQL state in real time and to manually trigger synchronization during demos.

---

## Working Demo

A full end to end working demo has been recorded and is available at the link below.

**Demo Video Link**  
https://drive.google.com/file/d/1d-haWa3mySbK0GM-AWn0NZ5GYZmwELBh/view?usp=sharing

The video demonstrates:

1. Google Sheets to MySQL live synchronization
2. MySQL to Google Sheets synchronization using change logs
3. Concurrent edits handling
4. Retry and recovery during failures
5. Live MySQL state visualization via the web interface

---

## High Level Architecture

The system follows an event driven synchronization model.

1. Google Sheets acts as a collaborative client where multiple users can edit data simultaneously.
2. MySQL acts as the durable source of truth.
3. A backend service coordinates synchronization.
4. MySQL triggers generate immutable change events.
5. Google Sheets is updated by consuming these events in order.

This design avoids full table scans, supports retries, and works correctly under concurrent writes.

---

## Why Change Log Based Synchronization Was Used

MySQL does not provide row level change events by default.  
Direct table syncing would require repeated full table scans or snapshot comparisons, which do not scale and break under concurrency.

To solve this, a Change Data Capture style approach was implemented using a dedicated change log table.

Every insert or update in MySQL produces a structured event.  
The backend consumes these events and applies them to Google Sheets.

This enables:

1. Ordered processing of changes
2. Idempotent synchronization
3. Retry with backoff on failure
4. Crash safe recovery
5. Clear audit trail of modifications

This pattern closely mirrors how real production systems handle cross system synchronization.

---

## Data Flow

### Google Sheets to MySQL

1. A user edits or adds a row in Google Sheets.
2. A Google Apps Script trigger fires on edit.
3. The updated row data is sent to a backend webhook.
4. The backend performs an upsert into MySQL.
5. Concurrent edits are handled safely by the database.

### MySQL to Google Sheets

1. Any insert or update in MySQL fires a database trigger.
2. The trigger writes an event into the change log table.
3. The backend reads unprocessed events in order.
4. Each event updates or inserts the corresponding row in Google Sheets.
5. The event is marked processed only after a successful sync.

---

## Features Implemented

1. Two way live synchronization
2. Event based MySQL change capture
3. Idempotent processing using processed flags
4. Retry with exponential backoff for API failures
5. Ordered event consumption
6. Safe handling of concurrent edits
7. Simple web interface for live visualization
8. Manual sync trigger for demos and debugging
9. Fully dockerized local setup

---

## Edge Cases and Nuances Handled

1. Concurrent edits on the same row
2. Concurrent edits by multiple Google Sheets users
3. Network failures during API calls
4. Partial failures during synchronization
5. Duplicate event prevention using processed flags
6. Crash safe behavior with replayable logs
7. Insert versus update differentiation
8. Deterministic ordering of changes
9. Idempotent re execution of sync logic

---

## Edge Cases Not Implemented

The following were intentionally not implemented due to scope and time constraints:

1. Dynamic schema changes such as column addition or removal
2. Automatic schema migration
3. Row deletions and tombstone handling
4. Adaptive batching for API quota limits
5. Authentication token rotation

These can be added as future extensions.

---

## Multi User Handling Strategy

Multi user access is handled at the system level rather than relying on Google Sheets alone.

1. Multiple users can edit the same sheet concurrently.
2. MySQL triggers serialize concurrent writes into ordered events.
3. The backend processes events sequentially.
4. No user change can silently overwrite another without being logged.

This ensures correctness even when multiple users access the same data from different entry points.

---

## Technology Stack

1. Backend implemented using FastAPI with Python
2. MySQL database with triggers for change capture
3. Google Sheets API for spreadsheet updates
4. Docker and Docker Compose for reproducible setup
5. Lightweight HTML and JavaScript frontend served by the backend

The stack was chosen to balance simplicity, reliability, and ease of demonstration.

---

## Running the Project Locally

### Prerequisites

1. Docker and Docker Compose
2. A Google Sheet with Apps Script configured
3. A Google service account with Sheets API access

### Steps

1. Clone the repository
2. Place the service account JSON file inside the backend app directory
3. Run Docker Compose to start services
4. Expose the backend using ngrok
5. Update the Apps Script webhook URL
6. Edit the sheet or database to observe live sync

---

## Demo Interface

The root endpoint serves a simple web UI that shows the current MySQL state.

The interface allows:

1. Viewing live database rows
2. Manually triggering MySQL to Sheet sync
3. Verifying updates in real time

This UI exists purely to make the system easy to test and demonstrate.

---

## Deployment Notes

The system is deployment ready but demonstrated locally to avoid exposing credentials.

In a production setup, this architecture can be extended with:

1. Managed databases
2. Background workers
3. Authentication and authorization
4. Rate limit aware batching
5. Schema migration tooling

---

## Conclusion

This project demonstrates a reliable, event driven approach to two way synchronization between Google Sheets and MySQL.

The design focuses on correctness, concurrency safety, recoverability, and clarity, closely reflecting patterns used in real world production systems.
