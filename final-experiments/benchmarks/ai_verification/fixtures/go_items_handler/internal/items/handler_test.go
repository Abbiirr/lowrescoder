package items_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ai-verification/go-items-handler/internal/items"
)

func TestListItemsEmpty(t *testing.T) {
	items.ResetStore()
	req := httptest.NewRequest(http.MethodGet, "/items", nil)
	w := httptest.NewRecorder()
	items.ListItems(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 got %d", w.Code)
	}
}

func TestCreateItem(t *testing.T) {
	items.ResetStore()
	body, _ := json.Marshal(map[string]interface{}{"name": "widget", "price": 9.99})
	req := httptest.NewRequest(http.MethodPost, "/items", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	items.CreateItem(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201 got %d", w.Code)
	}
}

func TestGetItemFound(t *testing.T) {
	items.ResetStore()
	body, _ := json.Marshal(map[string]interface{}{"name": "widget", "price": 9.99})
	req := httptest.NewRequest(http.MethodPost, "/items", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	items.CreateItem(httptest.NewRecorder(), req)

	req2 := httptest.NewRequest(http.MethodGet, "/items/1", nil)
	w2 := httptest.NewRecorder()
	items.GetItem(w2, req2)
	if w2.Code != http.StatusOK {
		t.Fatalf("expected 200 got %d", w2.Code)
	}
}

func TestGetItemNotFound(t *testing.T) {
	items.ResetStore()
	req := httptest.NewRequest(http.MethodGet, "/items/999", nil)
	w := httptest.NewRecorder()
	items.GetItem(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404 got %d", w.Code)
	}
}
