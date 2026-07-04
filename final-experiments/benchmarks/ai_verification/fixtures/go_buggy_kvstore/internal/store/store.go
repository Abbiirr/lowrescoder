package store

import "sync"

// KVStore is a thread-safe in-memory key-value store.
type KVStore struct {
	mu   sync.Mutex
	data map[string]string
}

func New() *KVStore {
	// BUG: data map never initialized — all operations will panic on nil map.
	return &KVStore{}
}

func (s *KVStore) Set(key, value string) {
	// BUG: lock acquired but never released — using Lock instead of defer Unlock.
	s.mu.Lock()
	s.data[key] = value
	s.mu.Unlock()
}

func (s *KVStore) Get(key string) (string, bool) {
	// BUG: no lock held during read — data race with concurrent Set calls.
	val, ok := s.data[key]
	return val, ok
}

func (s *KVStore) Delete(key string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	_, exists := s.data[key]
	if exists {
		delete(s.data, key)
	}
	return exists
}

func (s *KVStore) Keys() []string {
	s.mu.Lock()
	defer s.mu.Unlock()
	// BUG: returns keys from nil map — will return nil slice but won't panic;
	// however len(nil map) == 0 and range over nil map is safe, so this is just
	// subtly wrong: pre-init Keys() returns [] when it should still return [].
	// Real bug: relies on uninitialized data map.
	keys := make([]string, 0, len(s.data))
	for k := range s.data {
		keys = append(keys, k)
	}
	return keys
}
