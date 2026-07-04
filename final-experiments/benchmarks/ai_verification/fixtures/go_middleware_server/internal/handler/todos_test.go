package handler_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ai-verification/go-middleware-server/internal/handler"
)

func TestListTodosEmpty(t *testing.T) {
	handler.ResetTodos()
	req := httptest.NewRequest(http.MethodGet, "/todos", nil)
	w := httptest.NewRecorder()
	handler.ListTodos(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 got %d", w.Code)
	}
}

func TestCreateTodo(t *testing.T) {
	handler.ResetTodos()
	body, _ := json.Marshal(map[string]string{"title": "buy milk"})
	req := httptest.NewRequest(http.MethodPost, "/todos", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handler.CreateTodo(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201 got %d", w.Code)
	}
}

func TestCreateTodoBadRequest(t *testing.T) {
	handler.ResetTodos()
	req := httptest.NewRequest(http.MethodPost, "/todos", bytes.NewReader([]byte(`{}`)))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	handler.CreateTodo(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 got %d", w.Code)
	}
}
