import os
from typing import Optional, List, Any, Dict

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import motor.motor_asyncio
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict

load_dotenv()

app = FastAPI(title="Event Management API")

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI is missing in .env")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["event_management_db"]  # must match Atlas DB name


# Helpers
def to_object_id(id_str: str) -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")
    return ObjectId(id_str)


def serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc

    out = dict(doc)
    out["id"] = str(out.pop("_id"))

    # Convert any ObjectId fields to strings (venue_id, event_id, attendee_id, etc.)
    for k, v in list(out.items()):
        if isinstance(v, ObjectId):
            out[k] = str(v)

    return out


# Models
class VenueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=300)
    capacity: int = Field(ge=1)


class VenueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, min_length=1, max_length=300)
    capacity: Optional[int] = Field(default=None, ge=1)


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    date: str = Field(min_length=4, max_length=40)
    max_attendees: int = Field(ge=1)
    venue_id: str


class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    date: Optional[str] = Field(default=None, min_length=4, max_length=40)
    max_attendees: Optional[int] = Field(default=None, ge=1)
    venue_id: Optional[str] = None


class AttendeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(min_length=3, max_length=30)


class AttendeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    email: Optional[str] = Field(default=None, min_length=3, max_length=254)
    phone: Optional[str] = Field(default=None, min_length=3, max_length=30)


class BookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_type: str = Field(min_length=1, max_length=50)
    quantity: int = Field(ge=1)
    event_id: str
    attendee_id: str


class BookingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket_type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    quantity: Optional[int] = Field(default=None, ge=1)
    event_id: Optional[str] = None
    attendee_id: Optional[str] = None


#Test
@app.get("/health")
async def health():
    return {"status": "ok"}


# VENUES CRUD
@app.post("/venues")
async def create_venue(payload: VenueCreate):
    result = await db["venues"].insert_one(payload.model_dump())
    created = await db["venues"].find_one({"_id": result.inserted_id})
    return serialize(created)

@app.get("/venues")
async def list_venues(limit: int = 50, skip: int = 0):
    cursor = db["venues"].find().skip(skip).limit(limit)
    venues = []
    async for doc in cursor:
        venues.append(serialize(doc))
    return venues

@app.get("/venues/{venue_id}")
async def get_venue(venue_id: str):
    oid = to_object_id(venue_id)
    doc = await db["venues"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Venue not found")
    return serialize(doc)

@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, payload: VenueUpdate):
    oid = to_object_id(venue_id)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")

    result = await db["venues"].update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")

    doc = await db["venues"].find_one({"_id": oid})
    return serialize(doc)

@app.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str):
    oid = to_object_id(venue_id)
    result = await db["venues"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    return {"deleted": True, "id": venue_id}


# EVENTS CRUD 
@app.post("/events")
async def create_event(payload: EventCreate):
    venue_oid = to_object_id(payload.venue_id)

    venue = await db["venues"].find_one({"_id": venue_oid})
    if not venue:
        raise HTTPException(status_code=400, detail="Venue not found")

    doc = payload.model_dump()
    doc["venue_id"] = venue_oid

    result = await db["events"].insert_one(doc)
    created = await db["events"].find_one({"_id": result.inserted_id})
    return serialize(created)

@app.get("/events")
async def list_events(limit: int = 50, skip: int = 0):
    cursor = db["events"].find().skip(skip).limit(limit)
    events = []
    async for doc in cursor:
        events.append(serialize(doc))
    return events

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    oid = to_object_id(event_id)
    doc = await db["events"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return serialize(doc)

@app.put("/events/{event_id}")
async def update_event(event_id: str, payload: EventUpdate):
    oid = to_object_id(event_id)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")

    if "venue_id" in updates:
        venue_oid = to_object_id(updates["venue_id"])
        venue = await db["venues"].find_one({"_id": venue_oid})
        if not venue:
            raise HTTPException(status_code=400, detail="Venue not found")
        updates["venue_id"] = venue_oid

    result = await db["events"].update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")

    doc = await db["events"].find_one({"_id": oid})
    return serialize(doc)

@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    oid = to_object_id(event_id)
    result = await db["events"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": True, "id": event_id}


#ATTENDEES CRUD
@app.post("/attendees")
async def create_attendee(payload: AttendeeCreate):
    result = await db["attendees"].insert_one(payload.model_dump())
    created = await db["attendees"].find_one({"_id": result.inserted_id})
    return serialize(created)

@app.get("/attendees")
async def list_attendees(limit: int = 50, skip: int = 0):
    cursor = db["attendees"].find().skip(skip).limit(limit)
    attendees = []
    async for doc in cursor:
        attendees.append(serialize(doc))
    return attendees

@app.get("/attendees/{attendee_id}")
async def get_attendee(attendee_id: str):
    oid = to_object_id(attendee_id)
    doc = await db["attendees"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return serialize(doc)

@app.put("/attendees/{attendee_id}")
async def update_attendee(attendee_id: str, payload: AttendeeUpdate):
    oid = to_object_id(attendee_id)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")

    result = await db["attendees"].update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")

    doc = await db["attendees"].find_one({"_id": oid})
    return serialize(doc)

@app.delete("/attendees/{attendee_id}")
async def delete_attendee(attendee_id: str):
    oid = to_object_id(attendee_id)
    result = await db["attendees"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return {"deleted": True, "id": attendee_id}


#BOOKINGS CRUD 
@app.post("/bookings")
async def create_booking(payload: BookingCreate):
    event_oid = to_object_id(payload.event_id)
    attendee_oid = to_object_id(payload.attendee_id)

    event = await db["events"].find_one({"_id": event_oid})
    if not event:
        raise HTTPException(status_code=400, detail="Event not found")

    attendee = await db["attendees"].find_one({"_id": attendee_oid})
    if not attendee:
        raise HTTPException(status_code=400, detail="Attendee not found")

    doc = payload.model_dump()
    doc["event_id"] = event_oid
    doc["attendee_id"] = attendee_oid

    result = await db["bookings"].insert_one(doc)
    created = await db["bookings"].find_one({"_id": result.inserted_id})
    return serialize(created)

@app.get("/bookings")
async def list_bookings(limit: int = 50, skip: int = 0):
    cursor = db["bookings"].find().skip(skip).limit(limit)
    bookings = []
    async for doc in cursor:
        bookings.append(serialize(doc))
    return bookings

@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    oid = to_object_id(booking_id)
    doc = await db["bookings"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return serialize(doc)

@app.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, payload: BookingUpdate):
    oid = to_object_id(booking_id)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")

    if "event_id" in updates:
        event_oid = to_object_id(updates["event_id"])
        event = await db["events"].find_one({"_id": event_oid})
        if not event:
            raise HTTPException(status_code=400, detail="Event not found")
        updates["event_id"] = event_oid

    if "attendee_id" in updates:
        attendee_oid = to_object_id(updates["attendee_id"])
        attendee = await db["attendees"].find_one({"_id": attendee_oid})
        if not attendee:
            raise HTTPException(status_code=400, detail="Attendee not found")
        updates["attendee_id"] = attendee_oid

    result = await db["bookings"].update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")

    doc = await db["bookings"].find_one({"_id": oid})
    return serialize(doc)

@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str):
    oid = to_object_id(booking_id)
    result = await db["bookings"].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"deleted": True, "id": booking_id}
