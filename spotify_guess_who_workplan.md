# Spotify Guess Who (2–8 Players) — Detailed Workplan (Django)

## Overview

Build a **Jackbox-style multiplayer Spotify social game** for **2–8 players**:

- Players log in with Spotify
- One player creates a room (VIP/host)
- Other players join via a short room code
- VIP starts the game
- The game runs in real time
- Each round plays a **~15-second audio clip** and shows **song title + artist + cover art**
- Players guess **which player(s)** have listened to it
- **Multi-select answers are allowed**
- **Points awarded for correct selections**
- **Penalties for incorrect selections** (to prevent “select all”)

This plan prioritizes:

- **Mobile-first gameplay UX** (primary target)
- **Fast gameplay**
- **Low-latency multiplayer**
- **Efficient Spotify data fetching**
- **Server-authoritative game logic**
- **Scalable architecture without overengineering V1**

---

## Product Goal (V1)

A polished, replayable party game for friends where the fun comes from:
- recognizing taste patterns,
- bluff-proof scoring,
- fast rounds,
- social surprise.

### V1 Success Criteria
A room of 4–6 players can:
1. Join in under 60 seconds
2. Sync Spotify data without confusion
3. Start game smoothly (only when all players are synced)
4. Play 10 rounds smoothly
5. See live scoring after each round
6. Finish in under ~15 minutes
7. Start a rematch quickly

---

## Mobile-First Product Direction (V1)

This game should be designed **mobile-first** (primary target), with desktop as a secondary/fallback experience.

### What this means in practice
- **Portrait-first layouts** for gameplay screens
- **Large tap targets** (player selection buttons/cards)
- **Minimal typing** (room code only)
- **Sticky bottom action area** for submit/update answer actions
- **Fast reconnect/resume behavior** (phones frequently background apps)
- **Low-bandwidth, low-jank real-time updates**

This affects UI layout, websocket behavior, and testing priorities, but does **not** change the core gameplay rules.

## Core Gameplay Spec (V1)

## Player Flow
1. Visit site
2. Log in with Spotify
3. Create room or join room by code
4. Wait in lobby (VIP can start when **2–8 players** and **everyone is synced**)
5. VIP starts game
6. Round loop:
   - show song + artist + cover art
   - players select one or more people
   - players can change selections until timer ends
   - timer ends or all players submit/lock
   - reveal correct players + score changes
7. Final leaderboard
8. Rematch / new room

## Round Concept (Guess Who)
Each round presents a **track clue**:
- **~15-second audio clip** (sourced from YouTube)
- **Song title**
- **Artist**
- **Cover art**

Players answer:
> “Who in this room has listened to this?”

Correct answer can be:
- **one person**, or
- **multiple people** (if the track appears in multiple players’ Spotify-derived evidence)

This directly supports your multi-select scoring rule.

---

## Scoring System (Finalized V1 Rules)

Your scoring design is excellent because it discourages “select all” while still allowing smart single guesses.

### Definitions
- `T` = set of true players for this track
- `G` = set of guessed players selected by the user
- `correct = |G ∩ T|`
- `incorrect = |G - T|`

### V1 Scoring Rules
- **+100** for each correct selected player
- **Incorrect guess handling:**
  - If the player selected **only one option** and it is wrong → **0 penalty**
  - If the player selected **more than one option**, each incorrect selected player = **-75**
- **Negative scores are allowed**
- Players can change answers until timer ends

### Scoring Formula (V1)
Let `n = |G|`.

- `base_positive = 100 * correct`
- `base_negative = 0` if `n <= 1`, else `75 * incorrect`
- `score_delta = base_positive - base_negative`

### Examples
#### Example A — single bold guess, wrong
- True = `{A}`
- Guess = `{B}`
- Correct = 0
- Incorrect = 1
- Since only one option chosen → penalty = 0
- **Score delta = 0**

#### Example B — hedge with two guesses, one right one wrong
- True = `{A}`
- Guess = `{A, B}`
- Correct = 1 → +100
- Incorrect = 1 and selected >1 → -75
- **Score delta = +25**

#### Example C — spam all in 6-player room, 2 are correct
- Correct = 2 → +200
- Incorrect = 4 → -300
- **Score delta = -100**
- “Select all” loses.

### Why this is good
- Encourages strategic hedging
- Preserves fun of guessing multiple people
- Prevents obvious abuse
- Makes precision valuable

---

## Round Generation Rules (Important for Fun)

The quality of rounds determines whether the game feels amazing or repetitive.

### Good round properties
A track should be:
- Recognizable enough (or at least interesting)
- Informative (ties strongly to specific players)
- Sometimes shared by multiple players
- Not repeated too often
- Not too generic (e.g., a song everyone has)

### Round Types (V1 = one type)
- **Track Ownership Round**: “Who has listened to this track?”

Future modes can be added later, but V1 should be one polished mode.

### Track Source Strategy (V1)
Use Spotify data from:
- Top tracks (short_term)
- Top tracks (medium_term)
- Top tracks (long_term)
- Recently played tracks

Build a candidate pool and sample with a mix:
- ~50% tracks tied to 1 player
- ~30% tracks tied to 2 players
- ~15% tied to 3+ players
- ~5% “chaos” picks (optional)

This keeps rounds varied and replayable.

---

## Architecture (High-Level)

## Tech Stack (Recommended)
- **Django** (main web app)
- **PostgreSQL** (primary database)
- **Redis** (cache + Channels layer + Celery broker)
- **Django Channels** (real-time multiplayer via WebSockets)
- **Celery** (background Spotify sync + precompute jobs)
- **yt-dlp** (YouTube audio stream URL extraction)
- **HTMX + Alpine.js** *or* lightweight JS frontend (recommended for speed)
- **Docker Compose** (local development)

### Why this stack
- Django keeps auth/admin/data modeling productive
- Channels gives smooth real-time rooms and game state
- Celery prevents blocking on Spotify syncs and YouTube audio resolution
- Redis supports both websocket fanout and cache/state
- yt-dlp reliably extracts direct audio stream URLs from YouTube without needing an API key
- You can build a polished V1 fast without React complexity

---

## System Design Priorities (Efficiency)

You explicitly want this to be efficient — correct instinct.

### Golden Rule
**No Spotify API calls or YouTube lookups during gameplay.**

Everything needed for a match should be:
- pre-synced,
- precomputed,
- audio URLs resolved,
- and ready before the first round starts.

### Efficiency Strategy
1. Each player syncs Spotify data in the lobby
2. VIP can only start when **everyone is synced**
3. When game starts:
   - build track→players ownership mapping
   - generate all 10 rounds at once
   - resolve YouTube audio URLs for all 10 tracks (parallel Celery tasks)
   - cache round payloads (including audio URLs) and match state in Redis
4. Gameplay runs from precomputed data only (audio streams directly from YouTube CDN)
5. Client prefetches next round's audio during reveal/scoreboard phase
6. Persist results asynchronously / minimally

### Performance Targets (V1)
- Lobby updates: sub-200ms perceived latency
- Round broadcast to clients: sub-500ms perceived
- Answer submit ack: very fast (sub-150ms server-side target)
- Reveal broadcast: sub-300ms perceived
- Audio pre-resolve (all 10 tracks): under 15s total (parallel)
- Audio prefetch buffer: 7s (4s reveal + 3s scoreboard) before next round

---

## Spotify Integration Plan

## OAuth (Spotify Login)
Use Spotify Authorization Code Flow:
- User clicks “Login with Spotify”
- App requests Spotify scopes
- Store refresh token securely
- Refresh access token server-side during syncs

### Spotify Scopes (V1)
Use:
- `user-top-read`
- `user-read-recently-played`

These are enough for a strong V1 without increasing scope friction too much.

## What Data to Ingest (V1)
Per player:
- Top tracks (short_term)
- Top tracks (medium_term)
- Top tracks (long_term)
- Recently played tracks (limited sample)

Store normalized metadata:
- Spotify track ID
- Song title
- Artist (primary artist string for V1)
- Album cover art URL
- Preview URL (nullable, for future)
- External Spotify URL (optional)
- Duration (optional)
- YouTube video ID (nullable, cached from search)

### Important Design Choice
V1 does **not** use Spotify's preview URLs for audio (these are unreliable and region-locked).
Instead, audio is sourced from YouTube: the server searches YouTube by track name + artist,
caches the video ID, and resolves a direct audio stream URL via `yt-dlp` at match start time.
This keeps audio reliable across regions while keeping gameplay focused on ownership guessing.

---

## YouTube Audio Integration Plan

### Why YouTube (Not Spotify Previews or Deezer)
Spotify's `preview_url` field is unreliable — many tracks return `null`, and availability is region-dependent. Deezer's API is geo-blocked in several countries (including India). YouTube has the widest global catalog and no region restrictions for audio access.

### How It Works
1. **Search:** For each track, search YouTube with `"{track name}" "{artist}" official audio`
2. **Cache:** Store the `youtube_video_id` on `SpotifyTrack` (persistent — video IDs don't change)
3. **Resolve:** At match start, use `yt-dlp` to extract a direct audio stream URL from the cached video ID
4. **Serve:** Send the audio URL to clients in the `round.started` payload; browser `<audio>` element plays it directly from YouTube's CDN

### When Resolution Happens
- **YouTube search + video ID caching:** during match generation (after VIP clicks Start)
- **Audio stream URL extraction:** same step, in parallel via Celery
- **Client prefetching:** during reveal/scoreboard phase, client preloads the next round's audio

### Audio Clip Strategy
- Clip duration: **~15 seconds**
- Start offset: configurable (default: 30s into the track, or 0 if track is shorter)
- The client handles clipping via `<audio>` element `currentTime` + a JavaScript timer
- No server-side audio processing or file storage needed

### Stream URL Expiry
YouTube CDN URLs are valid for ~6 hours. A match lasts ~15 minutes. No refresh logic needed.

### Fallback
If audio resolution fails for a track (rare), the round plays without audio — just song title + artist + cover art. The game still works; audio is an enhancement, not a hard dependency.

---

## Data Model (Django Apps + Models)

## Suggested Django Apps
- `accounts` — users + Spotify linkage
- `rooms` — room codes, lobby membership, host controls
- `game` — matches, rounds, answers, scoring
- `spotify_sync` — Spotify ingestion + normalized tracks/evidence
- `realtime` — Channels consumers/events (or combine into `rooms/game`)
- `core` — utilities/shared code

## Core Models (V1)

### `User` (Django auth user)
Standard auth user.

### `SpotifyAccount`
Links app user to Spotify identity.
- `user` (OneToOne)
- `spotify_user_id`
- `display_name`
- `access_token` (encrypted/short-lived)
- `refresh_token` (encrypted)
- `token_expires_at`
- `last_synced_at`
- `sync_status` (`not_synced`, `syncing`, `synced`, `failed`)
- `scopes_granted`
- `is_active`

### `SpotifyTrack`
Normalized track catalog.
- `spotify_track_id` (unique)
- `name`
- `artist_name`
- `album_image_url` (nullable)
- `preview_url` (nullable)
- `external_url` (nullable)
- `duration_ms` (nullable)
- `youtube_video_id` (nullable; cached YouTube search result, persistent)
- timestamps

### `UserTrackEvidence`
Proof that a player has “listened to” a track based on Spotify endpoints.
- `user`
- `track`
- `source_type` (`top_short`, `top_medium`, `top_long`, `recent`)
- `source_rank` (nullable)
- `seen_at` (nullable; for recent playback)
- unique constraints to avoid duplicate evidence rows

This powers truth sets for rounds.

### `Room`
Jackbox-style lobby.
- `code` (short unique room code)
- `host_user` (VIP)
- `status` (`lobby`, `starting`, `in_game`, `finished`, `closed`)
- `min_players` (default 2)
- `max_players` (default 8)
- `created_at`
- `expires_at`
- `current_match` (nullable FK)

### `RoomPlayer`
Player membership in a room.
- `room`
- `user`
- `display_name_snapshot`
- `is_host`
- `is_ready` (optional)
- `sync_ready` (derived or persisted flag)
- `joined_at`
- `connection_state` (`connected`, `disconnected`, `reconnecting`)
- `seat_index`

### `Match`
One game session (10 rounds) in a room.
- `room`
- `status` (`draft`, `generating`, `active`, `revealing`, `finished`, `cancelled`)
- `round_count` (default 10)
- `current_round_index`
- `started_at`
- `ended_at`
- `seed` (for reproducibility/debugging)
- `config_json` (timer/scoring settings snapshot)

### `MatchPlayer`
Per-player match stats and score.
- `match`
- `user`
- `room_player_snapshot_name`
- `score`
- `correct_selections_total`
- `incorrect_selections_total`
- `avg_response_ms`
- `position_final` (nullable)

### `Round`
- `match`
- `round_index`
- `status` (`pending`, `active`, `revealed`, `closed`)
- `prompt_type` (`track_ownership`)
- `track` (FK to `SpotifyTrack`)
- `truth_players_json` (list of match_player IDs)
- `audio_url` (nullable; resolved YouTube stream URL, transient per match)
- `audio_start_offset_s` (default 30; where in the track to start the clip)
- `started_at`
- `deadline_at`
- `revealed_at`
- `metadata_json` (e.g., evidence summary, ambiguity level)

### `RoundAnswer`
- `round`
- `match_player`
- `selected_players_json` (multi-select)
- `submitted_at`
- `response_ms`
- `score_delta`
- `correct_count`
- `incorrect_count`
- `selection_count`

### `MatchEvent` (Optional but highly useful)
Append-only event log for debugging/replay.
- `match`
- `event_type`
- `payload_json`
- `created_at`

---

## Real-Time Multiplayer Design (Channels)

## Why WebSockets
You need real-time:
- lobby updates
- sync status updates
- countdown timers
- answer lock-ins
- reveal sync
- live scoreboard updates

Polling will feel noticeably worse.

## Consumer Responsibilities
A room/match websocket consumer should handle:
- player join/leave presence
- host actions (start game)
- answer submission / answer updates until deadline
- state broadcasts
- reconnect sync snapshots

### Suggested Channel Groups
- `room_{code}` → lobby events
- `match_{id}` → gameplay events

## Server Authority (Important)
All game logic is **server-authoritative**:
- Server decides rounds
- Server decides deadlines
- Server stores latest valid answer before deadline
- Server scores everything
- Clients send only selections and UI intents

This prevents cheating and desync.

## Reconnect Strategy (V1)
If player refreshes/disconnects briefly:
- reconnect to websocket
- server sends current state snapshot
- if round is active and deadline not passed:
  - player can continue editing/submitting
- if already expired:
  - client sees waiting/reveal state

This is especially important on **mobile**, where users may briefly background the app, lock their phone, or switch networks.

---

## Room Code / Lobby Mechanic (Jackbox-Style)

## Room Code Requirements
- Easy to say/type
- Case-insensitive
- Low collision chance for active rooms
- Auto-expire

### Recommendation
- 5-character uppercase code
- Letters + digits excluding confusing chars (`O/0`, `I/1`, etc.)
- Example: `K7MZQ`

### Room Lifecycle
- `lobby`
- `starting` (host pressed start; rounds being generated)
- `in_game`
- `finished`
- `closed`

### Host (VIP) Controls
Host can:
- Start game (only if everyone synced and player count 2–8)
- Rematch
- Close room
- (Later) Kick disconnected players / tune settings

### Host Disconnect Handling
V1 recommendation:
- Immediate host transfer to next connected player by join order
- Broadcast “VIP transferred” event

Simpler and less brittle than pause windows in V1.

---

## Game State Machine (Server-Side)

Define explicit states/transitions to keep the system sane.

## Match States
1. `LOBBY`
2. `GENERATING_ROUNDS`
3. `ROUND_ACTIVE`
4. `ROUND_REVEAL`
5. `SCOREBOARD_INTERIM`
6. `FINAL_RESULTS`
7. `REMATCH_LOBBY`
8. `ENDED`

## Timing Defaults (V1)
- **10 rounds**
- **12s answer timer per round**
- Reveal phase: **4s**
- Inter-round scoreboard: **3s**
- Transition buffer: **1s** (optional)

This lands in a nice party-game length.

### Important Timing Implementation Detail
Use **server deadline timestamps**, not constant timer tick messages.
Clients compute countdown locally from the deadline for smoothness and efficiency.

---

## Round Generation Engine (Key Backend Logic)

When VIP presses Start:
1. Validate room has 2–8 players
2. Validate **all players are synced**
3. Build `player -> track set` mappings from evidence
4. Build inverse `track -> players` mapping
5. Filter and score candidate tracks
6. Select 10 rounds with diversity constraints
7. Persist rounds + truth sets
8. Cache active match state in Redis
9. Transition match to active and broadcast round 1

## Core Inverse Mapping
This is the heart of the game:
- For each track, compute set of players with evidence for it
- That set becomes the truth set `T` for a round

### Candidate Track Filters (V1)
Reject tracks if:
- Missing song/artist metadata
- Already used in current match
- Appears in all players too often (boring)
- Track pool quality too weak (fallback logic needed)

### Diversity Heuristics (V1)
Aim for a mix:
- Single-owner truth sets
- Two-owner truth sets
- 3+ owner truth sets

Avoid repeating the same truth set shape too many times in a row.

---

## Scoring Engine Implementation Details

## Final Scoring Algorithm (V1)

Given:
- `T` = truth set
- `G` = guessed set

Compute:
- `correct = len(G ∩ T)`
- `incorrect = len(G - T)`
- `selection_count = len(G)`

Then:
- `positive = 100 * correct`
- `negative = 0 if selection_count <= 1 else 75 * incorrect`
- `score_delta = positive - negative`

### Notes
- Empty selection is allowed (scores 0)
- A wrong single guess scores 0 (no penalty)
- Multi-guess hedging carries downside
- Negative total match score is allowed

### Reveal Fairness UX
On reveal, show **why** the truth set is valid:
- “Found in X’s top tracks (short term)”
- “Found in Y’s recently played”
This helps players trust the game.

---

## Caching & Data Access Strategy (Efficiency-First)

## What goes in Postgres
- Users, Spotify accounts
- Normalized tracks
- User track evidence
- Rooms, room players
- Matches, rounds, answers, scores
- Match history

## What goes in Redis
- Active room presence
- Current match state snapshot
- Round deadlines / transient state
- Socket session mappings
- Temporary reveal/scoreboard payloads
- Rate limiting counters

## Avoid During Gameplay
- Spotify API requests
- YouTube searches or yt-dlp calls
- Heavy DB joins every second
- Recomputing truth mappings mid-match

### Precompute Once Per Match
Store/calculate up front:
- `track_id -> [match_player_ids]`
- round payloads (including audio URLs)
- YouTube audio stream URLs for all round tracks
- match config snapshot
- player ordering / display names

---

## Security & Abuse Considerations (V1)

## Must-have
- CSRF protection for HTTP endpoints
- Session-authenticated websocket connections
- Host-only action validation (`start`, `rematch`, etc.)
- Validate room membership on every socket action
- Validate selected player IDs belong to current match
- Enforce answer deadline server-side
- Rate-limit room creation/join attempts

## Answer Editing Rules (V1)
- Player may submit/update answer multiple times until deadline
- Server stores latest valid answer state before deadline
- After deadline, answer is locked automatically

---

## Error Handling / Edge Cases

## Critical Cases
1. **Player not synced yet**
   - Show sync status in lobby
   - Start disabled until all synced

2. **Player has too little Spotify data**
   - Set a minimum threshold (e.g., 15 unique tracks)
   - If below threshold:
     - allow them to play, but either:
       - exclude from question generation pool, or
       - include with reduced weight
   - Surface a UI hint (“limited data may reduce round quality”)

3. **Host disconnects**
   - Auto-transfer VIP to next connected player
   - Broadcast host transfer event

4. **Player disconnects mid-round**
   - They can reconnect before deadline and continue editing answer
   - If deadline passes with no answer, treat as empty selection

5. **Spotify token expired**
   - Refresh token in background during sync
   - If refresh fails, mark sync failed and ask re-login

6. **Late websocket answer message**
   - Reject if server time > deadline
   - Send `round.locked` / error event

---

## UX / Frontend Screens (V1)

### Mobile-First UX Requirements (Applies to All Screens)
- **Portrait-first** design; desktop adapts from mobile layout
- Minimum tap target size of ~44px+ for all interactive elements
- Clear selected/unselected states with high contrast
- Sticky bottom action bar for primary round actions (submit/update)
- Safe-area support (iPhone notch / home indicator)
- Reduced-motion friendly animations (optional but recommended)
- Avoid hover-dependent interactions
- Keep room code and timer highly legible on small screens


## 1) Landing / Login
- “Login with Spotify”
- Small explanation of game
- Create room / Join room CTA after login

## 2) Create / Join Screen
- Create Room button
- Join by room code input
- Big readable room code display (Jackbox vibe)

## 3) Lobby
- Player list (2–8)
- Host/VIP badge
- Sync status per player (`syncing`, `synced`, `failed`)
- Start button (host only)
- Disabled start reason if blocked (“Waiting for all players to sync”)

## 4) Round Screen
- **Audio player** (auto-plays ~15s clip; simple play/pause controls, mobile-friendly)
- Song title
- Artist
- Cover art
- Multi-select player grid/buttons
- Countdown timer
- Submit / update answer UI
- Clear selection button (nice UX touch)
- Post-submit state still editable until deadline
- **Mobile-first player grid** (e.g., 2 columns on phones, large tap cards)
- **Sticky bottom submit/update bar** for thumb-friendly interaction

## 5) Reveal Screen
- Correct players highlighted
- Your selected players shown with green/red
- Score delta animation
- Short evidence line explaining truth set

## 6) Scoreboard
- Rankings
- Scores
- Round summary
- Next round countdown

## 7) Final Results
- Winner
- Basic stats (correct picks, overguesses, etc.)
- Rematch / new room

---

## API / WebSocket Contract (Suggested)

## HTTP Endpoints (minimal)
- `GET /` — landing
- `GET /auth/spotify/login`
- `GET /auth/spotify/callback`
- `POST /rooms/create`
- `POST /rooms/join`
- `GET /rooms/<code>/`
- `POST /spotify/sync` (manual re-sync trigger, optional)

(Host start can be HTTP or WebSocket; WebSocket is cleaner for real-time flow.)

## WebSocket Events (JSON)

### Client → Server
- `room.join`
- `room.leave`
- `match.start` (host only)
- `round.update_answer` `{selected_player_ids: [...]}`
- `round.submit_answer` (optional explicit lock intent)
- `ping`

### Server → Client
- `room.state`
- `room.player_joined`
- `room.player_left`
- `room.sync_status`
- `match.generating`
- `round.started` `{track, audio_url, audio_start_offset_s, deadline, ...}`
- `round.locked`
- `round.reveal`
- `scoreboard.update`
- `match.finished`
- `error`

Keep schemas versioned if possible (`"v": 1`).

---

## Development Phases / Workplan

## Phase 0 — Project Setup & Foundations (2–3 days)
### Goals
- Base Django project
- Postgres + Redis + Docker
- Channels + Celery wired in

### Tasks
- Scaffold Django project + apps
- Configure Postgres and Redis
- Configure ASGI + Django Channels
- Configure Celery
- Environment variables / settings split
- Logging setup
- Docker Compose for local services
- Basic healthcheck route

### Deliverables
- Local dev stack running
- Web + websocket + worker processes boot successfully

---

## Phase 1 — Spotify Auth + Sync Pipeline (4–6 days)
### Goals
- Login with Spotify
- Store tokens safely
- Import track evidence for gameplay

### Tasks
- Implement Spotify OAuth flow
- Persist SpotifyAccount + refresh tokens
- Add “Connect / Sync Spotify” UI
- Celery task to sync top tracks (3 terms)
- Celery task to sync recently played
- Normalize/store `SpotifyTrack`
- Upsert `UserTrackEvidence`
- Sync status updates (`syncing/synced/failed`)
- Minimum data threshold checks

### Deliverables
- User can connect Spotify
- User can sync and see imported status/count
- Enough data exists to generate rounds later

### Efficiency Notes
- Deduplicate before writes
- Bulk insert/update where possible
- Avoid one-row-at-a-time DB writes in sync loops

---

## Phase 2 — Room/Lobby System (Jackbox-Style) (4–5 days)
### Goals
- Create/join room by code
- Live lobby updates
- Host start gating based on all-sync rule

### Tasks
- Implement `Room`, `RoomPlayer`
- Room code generator + uniqueness checks
- Create room / join room flows
- Lobby page UI
- Room presence websocket consumer
- Host/VIP badge
- Start button with validation:
  - 2–8 players
  - all players synced
- Sync status broadcast into lobby
- Room expiry cleanup job

### Deliverables
- Multiple users can join and see lobby updates live
- Host can only start when everyone is synced

---

## Phase 3 — Game Engine V1 (Round Generation + Match State Machine + Audio) (6–9 days)
### Goals
- Generate valid 10-round matches from synced evidence
- Resolve YouTube audio for all round tracks
- Implement server state machine
- Persist rounds/truth sets

### Tasks
- Implement `Match`, `MatchPlayer`, `Round`
- Build `track -> players` inverse mapping
- Candidate filtering/scoring
- Diversity-aware round selection (single/shared mix)
- YouTube audio resolution pipeline:
  - Search YouTube by `"{track name}" "{artist}" official audio`
  - Cache `youtube_video_id` on `SpotifyTrack` (persistent, doesn't expire)
  - Resolve direct audio stream URL via `yt-dlp` (transient, per match)
  - Run all 10 resolutions in parallel via Celery
  - Validate duration against `SpotifyTrack.duration_ms` where available
  - Fallback: if resolution fails for a track, round plays without audio
- Match config snapshot (timers + scoring rules)
- Match state transitions
- Cache active match state in Redis (including audio URLs)

### Deliverables
- Pressing Start creates a full playable match with audio
- Rounds support single and multi-player truth sets
- Audio resolves for all 10 rounds before first round begins

### Validation Tests
- Works with 2 players
- Works with 8 players
- No duplicate tracks in same match
- Handles sparse data gracefully
- Audio resolves correctly for known tracks
- Graceful fallback when audio resolution fails

---

## Phase 4 — Real-Time Round Play + Answer Editing + Scoring (5–8 days)
### Goals
- Play rounds live
- Allow answer changes until deadline
- Score with finalized rules
- Reveal and scoreboard updates

### Tasks
- Gameplay websocket consumer/events
- Round start broadcast + deadline timestamp + audio URL
- Audio player UI (auto-play ~15s clip, play/pause controls, mobile-friendly)
- Client-side audio prefetching (silently load next round's audio during reveal/scoreboard)
- Multi-select answer UI + state sync
- `round.update_answer` handling
- Deadline lock logic (server-side)
- Scoring engine implementation:
  - +100 correct
  - -75 incorrect only when >1 option chosen
  - 0 penalty for wrong single guess
- Reveal payloads
- Scoreboard updates
- Final results screen

### Deliverables
- Full end-to-end game playable with your exact rules

### Key Implementation Note
Use server deadlines and local client countdowns to avoid noisy timer broadcasts.

---

## Phase 5 — Polish, Reliability, and Performance (4–6 days)
### Goals
- Make it smooth and resilient
- Handle edge cases cleanly
- Improve player trust/fairness UX

### Tasks
- Reconnect sync/resume flow
- Host auto-transfer
- Empty-answer handling on timeout
- Reveal “evidence source” line
- Better lobby and round feedback states
- Query/index optimization
- Rate limiting
- Logging and basic observability
- Rematch flow polish

### Deliverables
- Beta-quality experience you can test with friends reliably

---

## Phase 6 — Deployment & Playtesting (2–4 days)
### Goals
- Ship a playable beta
- Tune scoring/timers from real usage

### Tasks
- Deploy ASGI Django app (Render/Fly/Railway/VPS)
- Production Postgres + Redis
- HTTPS, secure cookies, secrets
- Static files setup
- Production logging
- Playtest with 4–8 players
- Tune round generation mix and timer UX

### Deliverables
- Public beta URL
- Iteration list from playtests

---

## Suggested Timeline (Realistic)
- **Week 1:** Setup + Spotify auth/sync
- **Week 2:** Room/lobby + round generation
- **Week 3:** Real-time gameplay + scoring
- **Week 4:** Polish + deploy + playtests

If part-time, expect ~5–8 weeks.

---

## Testing Strategy (Don’t Skip)

## Unit Tests
- Room code generation uniqueness
- Track→players inverse mapping
- Round candidate filters
- Round selection diversity
- Scoring function (especially penalty edge cases)
- Match state transitions

## Integration Tests
- Spotify sync inserts evidence correctly
- Room create/join flow
- Start game requires all synced
- Match generation works for 2–8 players
- Round answer updates lock at deadline
- Reveal scores persist correctly

## Manual Multiplayer Tests

### Mobile-Specific Testing (High Priority)
Test on real devices (not just browser devtools):
- iPhone Safari
- Android Chrome
- Background app during active round, then return
- Lock/unlock phone during lobby and during a round
- Network drop/reconnect mid-round
- Slow/spotty mobile data conditions
- Portrait layout readability and tap accuracy on smaller screens

Minimum manual tests:
- 2-browser local test
- 4-player real network test
- 8-player room stress test
- Host disconnect / VIP transfer
- Player reconnect mid-round
- Late answer rejection
- Weak-data player scenario

---

## Database Indexing / Query Optimizations (V1)

Add indexes early for hot paths.

### `UserTrackEvidence`
- unique `(user_id, track_id, source_type, source_rank)` or a simplified dedupe constraint strategy
- index `(track_id)`
- index `(user_id)`
- index `(user_id, source_type)`

### `Room`
- unique index `(code)`
- index `(status)`
- index `(expires_at)`

### `RoomPlayer`
- unique `(room_id, user_id)`
- index `(room_id, connection_state)`

### `Match`
- index `(room_id, status)`

### `Round`
- unique `(match_id, round_index)`
- index `(match_id, status)`

### `RoundAnswer`
- unique `(round_id, match_player_id)` if storing only latest answer
  - OR use versioned answers table + latest pointer (more complex; not needed V1)

### `MatchPlayer`
- unique `(match_id, user_id)`

Use `select_related` / `prefetch_related` on scoreboard and reveal DB reads if needed.

---

## Metrics to Track (Gameplay Analytics)

Track lightweight metrics so you can tune gameplay:
- Avg lobby wait time
- Avg Spotify sync time
- % rooms abandoned before start
- % starts blocked by unsynced players
- Avg answer submission time
- Avg selected option count per round
- % wrong single guesses (tests your “no penalty single guess” effect)
- % overguessing (2+ selections)
- Score spread per game
- Drop-off round number

These metrics will help tune scoring and pacing.

---

## V1 Configuration Defaults (Locked In)
- Players: **2–8**
- Start condition: **all players synced**
- Rounds: **10**
- Round answer timer: **12s**
- Reveal time: **4s**
- Inter-round scoreboard: **3s**
- Correct selection: **+100**
- Incorrect selection: **-75** (only if more than one option chosen)
- Wrong single guess penalty: **0**
- Negative scores: **allowed**
- Room code length: **5**
- Audio clip duration: **~15s** (sourced from YouTube)
- Audio start offset: **30s** into track (fallback: 0 if shorter)
- Audio prefetch: **during reveal + scoreboard of previous round**
- Room idle expiry: **2 hours**

---

## Future Extensions (After V1)

### Gameplay
- Full-song playback mode (30s+ clips, longer timer)
- “Most likely” prediction mode (not strict evidence-based)
- Confidence betting
- Team mode (2v2 or 3v3)
- Theme packs (gym songs, sad songs, etc.)
- Custom room settings (rounds/timer)

### Social
- Match history / rivalries
- Shareable result cards
- Friend invites

### Analytics / ML (Later)
- Taste similarity vectors
- Compatibility score mode
- “Player archetypes” (precision vs hedge vs chaos)

---

## Risks & Mitigations

## Risk 1: Spotify data quality varies by user
**Mitigation:** require sync completion, set minimum track thresholds, degrade gracefully for low-data users.

## Risk 2: Real-time complexity slows development
**Mitigation:** one game mode only, simple frontend, server-authoritative state machine.

## Risk 3: Overengineering before proving fun
**Mitigation:** prioritize a fast playable V1 and tune from real playtests.

## Risk 4: Gameplay jank due to live external calls
**Mitigation:** zero Spotify or YouTube calls during gameplay; precompute everything (including audio URLs) on start.

## Risk 5: YouTube audio resolution failures
**Mitigation:** cache `youtube_video_id` persistently on `SpotifyTrack` to avoid repeated searches. Resolve stream URLs in parallel during match generation. If a track fails, round plays without audio (text + cover art fallback). YouTube CDN URLs are valid for ~6 hours — well within a 15-minute match.

## Risk 6: yt-dlp rate limiting or breakage
**Mitigation:** 10 requests per match is well under any rate limit. Cache video IDs to avoid redundant searches across matches. Keep `yt-dlp` updated — it tracks YouTube changes actively. For production scale, consider a dedicated audio resolution worker.

---

## Practical Build Order (Shortest Path to Playable)

If you want the fastest path to “friends can play this,” build in this order:

1. Spotify login + sync one user
2. Room create/join flow
3. Real-time lobby (mobile-first UI)
4. Hardcoded test round (fake truth set)
5. Multi-select UI + finalized scoring
6. Real-time reveal + scoreboard
7. Auto-generated rounds from synced Spotify evidence
8. Edge cases + polish

This keeps momentum high and avoids architecture rabbit holes.

---

## Final Notes

Your multi-select scoring rule is a standout mechanic:
- It makes the game more strategic,
- creates tension around hedging,
- and prevents obvious abuse without overcomplicating the UX.

This is exactly the kind of rule that makes a party game feel “designed,” not just built.
