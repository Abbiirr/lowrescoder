package products

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"sync"
)

type Product struct {
	ID    int     `json:"id"`
	Name  string  `json:"name"`
	Price float64 `json:"price"`
}

var (
	mu     sync.Mutex
	store  []Product
	nextID = 1
)

func ResetStore() {
	mu.Lock()
	defer mu.Unlock()
	store = nil
	nextID = 1
}

// Handler is a single monolithic handler that routes all /products requests.
// All routing is done manually via URL/method inspection.
func Handler(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	switch {
	case path == "/products" && r.Method == http.MethodGet:
		listProducts(w, r)
	case path == "/products" && r.Method == http.MethodPost:
		createProduct(w, r)
	case strings.HasPrefix(path, "/products/") && r.Method == http.MethodGet:
		getProduct(w, r)
	case strings.HasPrefix(path, "/products/") && r.Method == http.MethodDelete:
		deleteProduct(w, r)
	default:
		http.NotFound(w, r)
	}
}

func listProducts(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	defer mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(store)
}

func createProduct(w http.ResponseWriter, r *http.Request) {
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
	p := Product{ID: nextID, Name: body.Name, Price: body.Price}
	nextID++
	store = append(store, p)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(p)
}

func getProduct(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/products/"))
	if err != nil {
		http.Error(w, "bad id", http.StatusBadRequest)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	for _, p := range store {
		if p.ID == id {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(p)
			return
		}
	}
	http.Error(w, "not found", http.StatusNotFound)
}

func deleteProduct(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(strings.TrimPrefix(r.URL.Path, "/products/"))
	if err != nil {
		http.Error(w, "bad id", http.StatusBadRequest)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	for i, p := range store {
		if p.ID == id {
			store = append(store[:i], store[i+1:]...)
			w.WriteHeader(http.StatusNoContent)
			return
		}
	}
	http.Error(w, "not found", http.StatusNotFound)
}
