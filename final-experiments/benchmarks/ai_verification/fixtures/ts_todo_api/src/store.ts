import { Todo } from "./types";

let nextId = 1;
const todos: Todo[] = [];

export function getAll(): Todo[] {
  return [...todos];
}

export function getById(id: number): Todo | undefined {
  return todos.find((t) => t.id === id);
}

export function create(title: string): Todo {
  const todo: Todo = {
    id: nextId++,
    title,
    done: false,
    createdAt: new Date().toISOString(),
  };
  todos.push(todo);
  return todo;
}

export function markDone(id: number): Todo | undefined {
  const todo = getById(id);
  if (todo) todo.done = true;
  return todo;
}

export function reset(): void {
  todos.length = 0;
  nextId = 1;
}
