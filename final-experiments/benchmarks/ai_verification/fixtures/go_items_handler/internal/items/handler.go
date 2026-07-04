package items

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"sync"
)

type Item struct {
	ID    int    `json:"id"`
	Name  string `json:"name"`
	Price float64 `json:"price"`
}

// Global state — package-level vars shared by all handler functions.
var (
	mu     sync.Mutex
	store  []Item
	nextID = 1
)

func ResetStore() {
	mu.Lock()
	defer mu.Unlock()
	store = nil
	nextID = 1
}

func ListItems(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(store)
}

func CreateItem(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		Name  string  `json:"name"`
		Price float64 `json:"price"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Name == "" {
		http.Error(w, "bad request", http.StatusBadRequest)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	item := Item{ID: nextID, Name: body.Name, Price: body.Price}
	nextID++
	store = append(store, item)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(item)
}

func GetItem(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	// URL pattern: /items/{id}
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/items/"), "/")
	id, err := strconv.Atoi(parts[0])
	if err != nil {
		http.Error(w, "bad id", http.StatusBadRequest)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	for _, item := range store {
		if item.ID == id {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(item)
			return
		}
	}
	http.Error(w, "not found", http.StatusNotFound)
}
