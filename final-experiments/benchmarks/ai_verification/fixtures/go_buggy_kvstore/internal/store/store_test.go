package store_test

import (
	"testing"

	"github.com/ai-verification/go-buggy-kvstore/internal/store"
)

func TestSetAndGet(t *testing.T) {
	s := store.New()
	s.Set("hello", "world")
	val, ok := s.Get("hello")
	if !ok || val != "world" {
		t.Fatalf("expected world got %q, ok=%v", val, ok)
	}
}

func TestGetMissing(t *testing.T) {
	s := store.New()
	_, ok := s.Get("missing")
	if ok {
		t.Fatal("expected false for missing key")
	}
}

func TestDelete(t *testing.T) {
	s := store.New()
	s.Set("k", "v")
	deleted := s.Delete("k")
	if !deleted {
		t.Fatal("expected Delete to return true")
	}
	_, ok := s.Get("k")
	if ok {
		t.Fatal("expected key to be gone after delete")
	}
}

func TestDeleteMissing(t *testing.T) {
	s := store.New()
	deleted := s.Delete("nope")
	if deleted {
		t.Fatal("expected Delete to return false for missing key")
	}
}

func TestKeys(t *testing.T) {
	s := store.New()
	s.Set("a", "1")
	s.Set("b", "2")
	keys := s.Keys()
	if len(keys) != 2 {
		t.Fatalf("expected 2 keys got %d", len(keys))
	}
}
