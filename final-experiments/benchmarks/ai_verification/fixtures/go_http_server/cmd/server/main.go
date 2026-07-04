package main

import (
	"net/http"

	"github.com/ai-verification/go-http-server/internal/handler"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/items", handler.ListItems)
	http.ListenAndServe(":8080", mux)
}
