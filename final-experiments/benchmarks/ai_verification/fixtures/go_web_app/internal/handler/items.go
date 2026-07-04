package handler

import (
	"encoding/json"
	"html/template"
	"net/http"
	"path/filepath"
	"runtime"
	"strings"
)

type Item struct {
	ID    int     `json:"id"`
	Name  string  `json:"name"`
	Price float64 `json:"price"`
}

var Store = []Item{
	{ID: 1, Name: "Widget A", Price: 9.99},
	{ID: 2, Name: "Gadget B", Price: 24.99},
	{ID: 3, Name: "Tool C", Price: 14.99},
}

func ResetStore() {
	Store = []Item{
		{ID: 1, Name: "Widget A", Price: 9.99},
		{ID: 2, Name: "Gadget B", Price: 24.99},
		{ID: 3, Name: "Tool C", Price: 14.99},
	}
}

func templateDir() string {
	_, filename, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(filename), "..", "..", "templates")
}

func Index(w http.ResponseWriter, r *http.Request) {
	tmpl := template.Must(template.ParseFiles(filepath.Join(templateDir(), "index.html")))
	w.Header().Set("Content-Type", "text/html")
	tmpl.Execute(w, Store)
}

func APIItems(w http.ResponseWriter, r *http.Request) {
	q := strings.ToLower(r.URL.Query().Get("q"))
	result := Store
	if q != "" {
		result = nil
		for _, item := range Store {
			if strings.Contains(strings.ToLower(item.Name), q) {
				result = append(result, item)
			}
		}
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}
