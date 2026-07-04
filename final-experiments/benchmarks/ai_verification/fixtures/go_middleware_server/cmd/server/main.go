package main

import (
	"net/http"

	"github.com/ai-verification/go-middleware-server/internal/handler"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/todos", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			handler.ListTodos(w, r)
		case http.MethodPost:
			handler.CreateTodo(w, r)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})
	http.ListenAndServe(":8080", mux)
}
