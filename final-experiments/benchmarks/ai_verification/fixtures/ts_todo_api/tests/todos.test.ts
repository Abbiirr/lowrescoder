import request from "supertest";
import { app } from "../src/app";
import { reset } from "../src/store";

beforeEach(() => reset());

describe("GET /todos", () => {
  it("returns empty list initially", async () => {
    const res = await request(app).get("/todos");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe("POST /todos", () => {
  it("creates a todo and returns 201", async () => {
    const res = await request(app).post("/todos").send({ title: "buy milk" });
    expect(res.status).toBe(201);
    expect(res.body.title).toBe("buy milk");
    expect(res.body.done).toBe(false);
    expect(typeof res.body.id).toBe("number");
  });

  it("rejects missing title with 400", async () => {
    const res = await request(app).post("/todos").send({});
    expect(res.status).toBe(400);
  });
});

describe("GET /todos/:id", () => {
  it("returns 404 for unknown id", async () => {
    const res = await request(app).get("/todos/999");
    expect(res.status).toBe(404);
  });

  it("returns the todo after creation", async () => {
    const created = await request(app).post("/todos").send({ title: "task" });
    const { id } = created.body as { id: number };
    const res = await request(app).get(`/todos/${id}`);
    expect(res.status).toBe(200);
    expect(res.body.id).toBe(id);
  });
});

describe("DELETE /todos/:id", () => {
  it("deletes an existing todo", async () => {
    const created = await request(app).post("/todos").send({ title: "to delete" });
    const { id } = created.body as { id: number };
    const del = await request(app).delete(`/todos/${id}`);
    expect(del.status).toBe(204);
    const res = await request(app).get(`/todos/${id}`);
    expect(res.status).toBe(404);
  });
});
