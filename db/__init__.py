from db.collections import init_collections

_cols = init_collections()

users_col    = _cols["users"]
posts_col    = _cols["posts"]
keys_col     = _cols["keys"]
tokens_col   = _cols["tokens"]
requests_col = _cols["requests"]
history_col  = _cols["history"]