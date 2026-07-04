package products_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ai-verification/go-legacy-products/internal/products"
)

func TestListEmpty(t *testing.T) {
	products.ResetStore()
	req := httptest.NewRequest(http.MethodGet, "/products", nil)
	w := httptest.NewRecorder()
	products.Handler(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 got %d", w.Code)
	}
}

func TestCreateAndGet(t *testing.T) {
	products.ResetStore()
	body, _ := json.Marshal(map[string]interface{}{"name": "Gizmo", "price": 12.5})
	req := httptest.NewRequest(http.MethodPost, "/products", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	products.Handler(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create expected 201 got %d", w.Code)
	}

	req2 := httptest.NewRequest(http.MethodGet, "/products/1", nil)
	w2 := httptest.NewRecorder()
	products.Handler(w2, req2)
	if w2.Code != http.StatusOK {
		t.Fatalf("get expected 200 got %d", w2.Code)
	}
}

func TestGetNotFound(t *testing.T) {
	products.ResetStore()
	req := httptest.NewRequest(http.MethodGet, "/products/999", nil)
	w := httptest.NewRecorder()
	products.Handler(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 got %d", w.Code)
	}
}

func TestDelete(t *testing.T) {
	products.ResetStore()
	body, _ := json.Marshal(map[string]interface{}{"name": "Widget", "price": 5.0})
	req := httptest.NewRequest(http.MethodPost, "/products", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	products.Handler(httptest.NewRecorder(), req)

	req2 := httptest.NewRequest(http.MethodDelete, "/products/1", nil)
	w2 := httptest.NewRecorder()
	products.Handler(w2, req2)
	if w2.Code != http.StatusNoContent {
		t.Fatalf("delete expected 204 got %d", w2.Code)
	}
}
