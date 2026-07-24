CREATE TABLE IF NOT EXISTS ratings (
  beer_id TEXT NOT NULL,
  author  TEXT NOT NULL,
  value   REAL NOT NULL,
  PRIMARY KEY (beer_id, author)
);
CREATE TABLE IF NOT EXISTS comments (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  beer_id    TEXT NOT NULL,
  author     TEXT NOT NULL,
  text       TEXT NOT NULL,
  date       TEXT,
  created_at INTEGER DEFAULT (unixepoch())
);
CREATE TABLE IF NOT EXISTS new_beers (
  id         TEXT PRIMARY KEY,
  marka      TEXT,
  nazwa      TEXT,
  abv        REAL,
  rodzaj     TEXT,
  added_by   TEXT,
  date       TEXT,
  created_at INTEGER DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_comments_beer ON comments (beer_id);
