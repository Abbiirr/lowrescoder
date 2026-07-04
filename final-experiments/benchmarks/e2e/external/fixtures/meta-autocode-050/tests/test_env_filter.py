import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from env_filter import get_client_env_vars

# --- PASS with bug (input contains only VITE_ vars — bug and fix agree) ---

def test_empty_input():
    assert get_client_env_vars({}) == {}

def test_single_vite_var():
    assert get_client_env_vars({'VITE_API_URL': 'http://api.example.com'}) == {'VITE_API_URL': 'http://api.example.com'}

def test_multiple_vite_vars():
    env = {'VITE_APP_NAME': 'myapp', 'VITE_VERSION': '1.0'}
    assert get_client_env_vars(env) == {'VITE_APP_NAME': 'myapp', 'VITE_VERSION': '1.0'}

def test_only_vite_prefix_returns_full_dict():
    env = {'VITE_X': 'x', 'VITE_Y': 'y', 'VITE_Z': 'z'}
    assert get_client_env_vars(env) == env

# --- FAIL with bug (non-VITE_ vars should be excluded) ---

def test_non_vite_excluded():
    env = {'VITE_API': 'http://api', 'DATABASE_URL': 'postgres://...', 'SECRET_KEY': 's3cr3t'}
    result = get_client_env_vars(env)
    assert result == {'VITE_API': 'http://api'}

def test_all_non_vite_returns_empty():
    env = {'DB_HOST': 'localhost', 'DB_PASSWORD': 'pass', 'NODE_ENV': 'production'}
    assert get_client_env_vars(env) == {}

def test_lowercase_vite_prefix_excluded():
    # 'vite_' (lowercase) must NOT be exposed — only exact 'VITE_' prefix
    env = {'vite_secret': 'leaked', 'VITE_OK': 'safe'}
    result = get_client_env_vars(env)
    assert result == {'VITE_OK': 'safe'}
