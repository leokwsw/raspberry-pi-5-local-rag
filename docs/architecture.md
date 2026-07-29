# Architecture

The appliance uses an in-process FastAPI application, SQLite storage and single-worker
background execution. Heavy local models are reached through narrow adapters and remain optional.
