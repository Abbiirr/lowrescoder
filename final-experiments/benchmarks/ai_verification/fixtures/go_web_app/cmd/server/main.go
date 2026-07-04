package main

import (
	"net/http"

	"github.com/ai-verification/go-web-app/internal/handler"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/", handler.Index)
	mux.HandleFunc("/api/items", handler.APIItems)
	http.ListenAndServe(":8080", mux)
}
