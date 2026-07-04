import express, { Request, Response } from "express";
import * as store from "./store";

export const app = express();
app.use(express.json());

app.get("/todos", (_req: Request, res: Response) => {
  res.json(store.getAll());
});

app.post("/todos", (req: Request, res: Response) => {
  const { title } = req.body as { title?: string };
  if (!title || typeof title !== "string") {
    res.status(400).json({ error: "title required" });
    return;
  }
  res.status(201).json(store.create(title));
});

// GET /todos/:id — NOT YET IMPLEMENTED
// DELETE /todos/:id — NOT YET IMPLEMENTED
