package handler

import (
	"encoding/json"
	"net/http"
	"sync"
)

type Todo struct {
	ID    int    `json:"id"`
	Title string `json:"title"`
	Done  bool   `json:"done"`
}

var (
	mu     sync.Mutex
	todos  []Todo
	nextID = 1
)

func ListTodos(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(todos)
}

func CreateTodo(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		Title string `json:"title"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Title == "" {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	t := Todo{ID: nextID, Title: body.Title, Done: false}
	nextID++
	todos = append(todos, t)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(t)
}

func ResetTodos() {
	mu.Lock()
	defer mu.Unlock()
	todos = nil
	nextID = 1
}
