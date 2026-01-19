# Event Management API (FastAPI + MongoDB Atlas)

This project is a REST API for managing events and related data (venues, events, attendees, bookings) using **FastAPI** and **MongoDB Atlas**. It also supports uploading and retrieving multimedia (event posters, promo videos, venue photos).


## Tech Stack
- **FastAPI** (API framework)
- **Uvicorn** (ASGI server)
- **MongoDB Atlas** + **Motor** (async MongoDB driver)
- **Pydantic** (validation / schemas)



## Features
### CRUD
- Venues: create, list, get by id, update, delete
- Events: create, list, get by id, update, delete
- Attendees: create, list, get by id, update, delete
- Bookings: create, list, get by id, update, delete

### Multimedia
- Upload / retrieve **event poster** (image)
- Upload / retrieve **promo video** (video)
- Upload / retrieve **venue photo** (image)



## Project Structure
- `main.py` - FastAPI application and endpoints
- `requirements.txt` - Python dependencies
- `.env` - environment variables (not committed)
- `vercel.json` - Vercel deployment config (if deploying)


## Setup (Local)

 Create and activate a virtual environment
**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
