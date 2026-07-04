from fastapi import FastAPI

app = FastAPI()

_jobs: dict[int, str] = {}
_next_id = 1


@app.post("/jobs")
async def create_job(body: dict) -> dict:
    global _next_id
    name = body.get("name", "unnamed")
    job_id = _next_id
    _next_id += 1
    _jobs[job_id] = "pending"
    return {"id": job_id, "name": name, "status": "pending"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: int) -> dict:
    if job_id not in _jobs:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="not found")
    return {"id": job_id, "status": _jobs[job_id]}


@app.get("/jobs")
async def list_jobs() -> list[dict]:
    return [{"id": k, "status": v} for k, v in _jobs.items()]


def reset():
    global _next_id
    _jobs.clear()
    _next_id = 1
