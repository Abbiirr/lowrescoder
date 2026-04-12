#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Validation script passes
VALIDATE_RESULT=$(python validate_models.py 2>&1)
VALIDATE_EXIT=$?

if [ "$VALIDATE_EXIT" -eq 0 ]; then
    echo "PASS: validate_models.py passes"
else
    echo "FAIL: validate_models.py failed"
    echo "$VALIDATE_RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Users table has correct columns
USERS_CHECK=$(python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('sqlite:///app.db')
inspector = inspect(engine)
cols = {c['name'] for c in inspector.get_columns('users')}
expected = {'id', 'username', 'email', 'created_at'}
if cols == expected:
    print('ok')
else:
    print(f'WRONG: has={cols}, want={expected}')
" 2>&1)

if [ "$USERS_CHECK" = "ok" ]; then
    echo "PASS: Users table has correct columns"
else
    echo "FAIL: Users table columns wrong: $USERS_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Posts table has correct columns
POSTS_CHECK=$(python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('sqlite:///app.db')
inspector = inspect(engine)
cols = {c['name'] for c in inspector.get_columns('posts')}
expected = {'id', 'title', 'content', 'created_at', 'updated_at', 'author_id'}
if cols == expected:
    print('ok')
else:
    print(f'WRONG: has={cols}, want={expected}')
" 2>&1)

if [ "$POSTS_CHECK" = "ok" ]; then
    echo "PASS: Posts table has correct columns"
else
    echo "FAIL: Posts table columns wrong: $POSTS_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Data preserved
DATA_CHECK=$(python -c "
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///app.db')
with engine.connect() as conn:
    users = conn.execute(text('SELECT COUNT(*) FROM users')).scalar()
    posts = conn.execute(text('SELECT COUNT(*) FROM posts')).scalar()
    alice = conn.execute(text(\"SELECT username FROM users WHERE id=1\")).scalar()
    title1 = conn.execute(text(\"SELECT title FROM posts WHERE id=1\")).scalar()
    if users >= 3 and posts >= 4 and alice == 'alice' and title1 == 'Hello World':
        print('ok')
    else:
        print(f'WRONG: users={users}, posts={posts}, alice={alice}, title1={title1}')
" 2>&1)

if [ "$DATA_CHECK" = "ok" ]; then
    echo "PASS: Existing data preserved"
else
    echo "FAIL: Data not preserved: $DATA_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: models.py was NOT modified
MODELS_HASH_CHECK=$(python -c "
# Verify models.py still has the expected content (key lines)
with open('models.py') as f:
    content = f.read()
checks = [
    'email = Column(String(120)',
    'updated_at = Column(DateTime',
    'class User(Base):',
    'class Post(Base):',
]
ok = all(c in content for c in checks)
print('ok' if ok else 'MODIFIED')
" 2>&1)

if [ "$MODELS_HASH_CHECK" = "ok" ]; then
    echo "PASS: models.py was not modified"
else
    echo "FAIL: models.py was modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
