package handler_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ai-verification/go-web-app/internal/handler"
)

func setup() { handler.ResetStore() }

func TestIndex(t *testing.T) {
	setup()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	w := httptest.NewRecorder()
	handler.Index(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if ct := w.Header().Get("Content-Type"); ct != "text/html" {
		t.Fatalf("expected text/html, got %q", ct)
	}
}

func TestAPIItems(t *testing.T) {
	setup()
	req := httptest.NewRequest(http.MethodGet, "/api/items", nil)
	w := httptest.NewRecorder()
	handler.APIItems(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var items []handler.Item
	if err := json.NewDecoder(w.Body).Decode(&items); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(items) != 3 {
		t.Fatalf("expected 3 items, got %d", len(items))
	}
}

func TestAPIItemsFilter(t *testing.T) {
	setup()
	req := httptest.NewRequest(http.MethodGet, "/api/items?q=widget", nil)
	w := httptest.NewRecorder()
	handler.APIItems(w, req)
	var items []handler.Item
	json.NewDecoder(w.Body).Decode(&items)
	if len(items) != 1 || items[0].Name != "Widget A" {
		t.Fatalf("unexpected filter result: %v", items)
	}
}
