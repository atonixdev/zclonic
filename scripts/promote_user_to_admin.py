#!/usr/bin/env python3
"""Promote a user to admin by email.

Usage:
    ./scripts/promote_user_to_admin.py user@example.com

This script directly updates the SQLite DB. Run from the project root and ensure the DB is not in use.
"""
import sys
from dbkamp.db import get_connection

if len(sys.argv) < 2:
    print('Usage: promote_user_to_admin.py user@example.com')
    sys.exit(2)

email = sys.argv[1]
conn = get_connection()
cur = conn.cursor()
cur.execute('SELECT id, email, full_name, is_admin FROM users WHERE email = ?', (email,))
row = cur.fetchone()
if not row:
    print('User not found:', email)
    sys.exit(1)
if row['is_admin']:
    print('User is already an admin:', email)
    sys.exit(0)
cur.execute('UPDATE users SET is_admin = 1 WHERE id = ?', (row['id'],))
conn.commit()
conn.close()
print('Promoted to admin:', email)
