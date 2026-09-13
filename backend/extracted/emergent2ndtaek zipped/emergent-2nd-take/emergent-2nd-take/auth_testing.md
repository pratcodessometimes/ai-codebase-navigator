# Outclip Auth Testing Notes

Auth: Emergent Google OAuth (via Emergent Auth service).
Sessions are stored in MongoDB collection `user_sessions` and cookie `session_token`.

For tests where a real browser sign-in isn't desired, seed a session via mongosh:

```
use('test_database');
var uid = 'user_test'+Date.now();
db.users.insertOne({user_id: uid, email: 'test@outclip.io', name: 'Test User', username: 'test_'+Date.now(),
  role: 'EDITOR', avatar_url: '', bio:'', lifetime_points: 0, total_earnings: 0,
  active_platforms: [], is_earnings_public: false, payout_upi:'',
  created_at: new Date().toISOString()});
var tok = 'tok_test_'+Date.now();
db.user_sessions.insertOne({user_id: uid, session_token: tok,
  expires_at: new Date(Date.now()+7*86400000).toISOString(), created_at: new Date().toISOString()});
print(tok);
```

Use `Cookie: session_token=<tok>` or `Authorization: Bearer <tok>` against `/api/auth/me`.
