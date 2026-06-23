# Walkthrough - Kahoot-like Game (Layout Fixes & New Features)

I have resolved the host dashboard layout overflow issues, fixed the question advancement bug, and implemented the two requested player-end features.

## What's New

### 1. Host Screen Overflow & Next Question Fixes (`host.html`)
- **Reason for layout cut-off**: The height of the graph container (`300px`) and option cards grid (`220px`) on the Host screen combined to exceed the vertical height of standard viewports. Since the page style had `overflow: hidden;`, the Yellow/Green choices and the **"查看排行榜" (Show Leaderboard) / "下一題" (Next Question)** footer buttons were cut off off-screen and couldn't be scrolled into view or clicked.
- **Fixed Layout**:
  - Reduced the graph container height from `300px` to `180px` and minimized margins/padding.
  - Reduced the option cards grid height from `220px` to `150px` during reveals and `110px` during questions.
  - Reduced the countdown timer circle dimensions from `140px` to `80px`.
  - Reduced the center question image container from `320px` to `220px` (with placeholder box scaled down to `240px` x `160px`).
  - Compressed header padding from `15px` to `8px` and container margins to `5px/15px`.
- These changes save **over 360px of vertical space**, ensuring the entire screen (including options and bottom control buttons) stays comfortably within the bounds of standard projector or laptop displays (768p) without any cut-off.

### 2. Auto-generated Player Nicknames (`player.html`)
- When a participant opens the player joining page, the system now **automatically generates a fun, unique random nickname** (e.g., "閃亮的企鵝36" or "勇敢的狐狸59").
- If the player likes it, they can immediately click "加入遊戲" to join.
- If they don't, they can delete the generated text and type their own custom nickname.

### 3. Display Questions and Options on Player Screens (`player.html`)
- Modified the mobile active question layout:
  - Stacks the 4 choice buttons vertically as horizontal bars (Red, Blue, Yellow, Green) for optimal mobile reading.
  - The **question text is displayed at the top** of the player's screen.
  - The **option texts are displayed directly inside the buttons** (Red Triangle has Option A text, etc.).
- This allows players to read both the question and all choices directly on their phones, resolving issues where they might be too far from the host screen.

### 4. Creator Toast Overlay Fix (`creator.html`)
- **Top-Right Position**: Moved the popup message (toast) element from `bottom: 90px; right: 20px;` to `top: 95px; right: 20px;` (just below the sticky header).
- **No More Overlaps**: This ensures that when a user uploads an image, the "圖片上傳成功！" (Image uploaded successfully!) toast floats at the top-right instead of covering the "儲存題目設定" (Save) button in the floating footer.

### 5. Question Image Size Doubled (`host.html`, `player.html`)
- **Host Screen**: Changed the question image container height and image max-height from `160px` to `320px` (exactly double the size). The question placeholder size is also doubled to `360px` x `240px` with double font size.
- **Player/Mobile Screen**: Removed the fixed-height container and set the player question image to occupy **100% width** with `height: auto` and `max-height: 240px`. This allows the image to automatically stretch to the maximum width of the phone screen while maintaining aspect ratio, making text inside question images much easier to read.

### 6. Lobby Reconnection & Stuck State Fix (`server.py`)
- **Fresh Lobby on Startup**: Removed `self.load_state()` from server startup and configured it to delete any stale `game_state.json` file when initialized. This prevents the server from starting in a stuck state (e.g. `REVEAL` or `QUESTION` from a previous session), which caused mobile players to be rejected with "game already in progress" error.
- **Persistent Reconnection**: Player session auto-reconnection is kept fully functional in-memory during an active game session without being affected by startup conflicts.

### 7. Instant QR Code Image Downloader (`host.html`)
- **Download Button**: Added a "💾 下載 QR Code 圖片" button directly underneath the lobby QR Code.
- **Save to Downloads**: When clicked, it programmatically fetches the dynamically generated QR code as a blob and prompts the browser to save it as `遊戲加入QR_Code.png` directly into the user's local "Downloads" folder, allowing easy sharing.

### 8. Background Image Preloader (`server.py`, `player.html`)
- **Preload API**: Added `/api/preloads` endpoint to list all active question image URLs without exposing text or options.
- **Instant Display**: On player page load (while in the nickname lobby), the player client fetches these URLs in the background and preloads them into the browser cache. When questions start, the images load **instantly** without delay.

### 9. Upgraded BGM: Intense Question Theme & Cheerful Lobby Soundtracks (`player.html`, `host.html`)
- **Intense Question Theme BGM**: Developed a full polyphonic synth theme for the question answering phase in A-minor, incorporating a driving main melody, an alternating triangle bassline, ticking clock woodblocks, and tuned heartbeat thumps (which dynamically shift pitch to match the root note of the active chord progression for perfect musical harmony).
- **Cheerful Lobby/Waiting BGM**: Added a lighthearted, bouncy synth soundtrack (synthesized via Web Audio API using a playful C-Major 16-step arpeggio, alternating triangle bassline, and high-frequency shaker clicks) that automatically plays when players are in the lobby, waiting for a question to start, waiting for other players to finish answering, or viewing the scoreboard/leaderboards.
- **Louder Volume Levels**: Upgraded the default feedback tones and BGM volume levels:
  - Mobile default `playTone()` volume increased from `0.30` to `0.45`.
  - Mobile wrong-answer tone volume increased from `0.25` to `0.40`.
  - Host feedback chime volume increased from `0.15` to `0.35`.
  - Host wrong-answer tone volume increased from `0.12` to `0.30`.
  - Host background music volume increased from `0.04` to `0.09`.
- **Chromatic Synth Arpeggio**: Added a retro-style sawtooth arpeggiated lead scale that rises in pitch to add musical urgency.
- **Dynamic Tempo Acceleration**: The music now **gradually speeds up** (tempo increases!) from `420ms` down to `160ms` per beat as the timer counts down.
- **Siren Pitch Sweep**: Triggers a rising pitch sweep (riser) after 20 beats to build maximum suspense for the final seconds.

---

## How to Test & Verify

1. **Open Host Dashboard**:
   - Go to [http://localhost:8000/host](http://localhost:8000/host).
   - Verify that all options (Red, Blue, Yellow, Green) fit nicely on the screen and do not overflow.

2. **Open Player Client**:
   - Go to [http://localhost:8000/player](http://localhost:8000/player).
   - Check that a nickname is pre-filled.
   - Click "加入遊戲" and start the game.
   - Confirm that the question text and options appear directly on the phone, and all 4 color buttons fit on a single phone screen.
   - Click "下一題" on the host screen after the first question to verify advancement works flawlessly.

3. **Verify Creator Toast Placement**:
   - Open `/creator` in browser.
   - Upload any image for a question.
   - Observe that the "圖片上傳成功！" toast floats at the top-right and does NOT cover the "儲存題目設定" button at the bottom-right, allowing you to click "儲存題目設定" immediately.

4. **Verify QR Code Downloader**:
   - Access the Host screen: `http://localhost:8000/host`.
   - Click the "💾 下載 QR Code 圖片" button under the QR code.
   - Verify that your browser automatically downloads a file named `遊戲加入QR_Code.png` into your local downloads folder.

5. **Verify Background Image Preloader**:
   - Open player page `http://localhost:8000/player` in browser, open developer network tab.
   - You should observe requests for the question images happening automatically on page load in the background (before starting the game).
   - Start the game and advance to a question with an image. Verify the image appears instantly without loading lag.

6. **Verify Upgraded BGM & Volume**:
   - Join a game from a phone (unmuted) and open the host screen on a computer (unmuted).
   - Once a question starts, listen to the background music on the phone.
   - Verify the double heartbeat thump is exceptionally deep and heavy (chest-thumping kick drum sound) with a strong bass emphasis.
   - Confirm that all feedback tones (correct/incorrect answer sounds) and background music on both the host and player mobile screen are noticeably louder.

### 10. Player Mobile Client Freezing Fix (`player.html`)
- **Root Cause of Freezing**: On some mobile platforms (especially Safari on iOS or certain mobile WebView engines), standard AudioContext initialization requires explicit user interaction. If `AudioContext` is blocked, fails to initialize, or fails to resume (e.g. returning a rejected Promise), it throws an uncaught JavaScript exception. This crashed the WebSocket message handlers or the `submitAnswer()` execution thread, causing the screen to lock up and freeze on the choice selection grid instead of showing the "Answer Submitted" screen.
- **Fixed Implementations**:
  - Wrapped Web Audio API's `AudioContext` initialization and resumption in safe `try...catch` blocks.
  - Added existence checks (`if (!this.ctx) return;`) across all synth playback routines (`playTone`, `startBgm`) to ensure the page behaves gracefully even if audio is disabled.
  - Wrapped the WebSocket `onmessage` handling and JSON parsing in a `try...catch` block to ensure any unexpected payload or audio state failure does not halt processing.
  - Wrapped `submitAnswer()` steps in independent try-catch blocks (for stopping BGM, sending WebSocket payload, applying CSS styles, and playing the sound effect), ensuring that if any single step fails, the other UI transitions and network requests still succeed.

---

## How to Test & Verify

1. **Open Host Dashboard**:
   - Go to [http://localhost:8000/host](http://localhost:8000/host).
   - Verify that all options (Red, Blue, Yellow, Green) fit nicely on the screen and do not overflow.

2. **Open Player Client**:
   - Go to [http://localhost:8000/player](http://localhost:8000/player).
   - Check that a nickname is pre-filled.
   - Click "加入遊戲" and start the game.
   - Confirm that the question text and options appear directly on the phone, and all 4 color buttons fit on a single phone screen.
   - Click "下一題" on the host screen after the first question to verify advancement works flawlessly.

3. **Verify Creator Toast Placement**:
   - Open `/creator` in browser.
   - Upload any image for a question.
   - Observe that the "圖片上傳成功！" toast floats at the top-right and does NOT cover the "儲存題目設定" button at the bottom-right, allowing you to click "儲存題目設定" immediately.

4. **Verify QR Code Downloader**:
   - Access the Host screen: `http://localhost:8000/host`.
   - Click the "💾 下載 QR Code 圖片" button under the QR code.
   - Verify that your browser automatically downloads a file named `遊戲加入QR_Code.png` into your local downloads folder.

5. **Verify Background Image Preloader**:
   - Open player page `http://localhost:8000/player` in browser, open developer network tab.
   - You should observe requests for the question images happening automatically on page load in the background (before starting the game).
   - Start the game and advance to a question with an image. Verify the image appears instantly without loading lag.

6. **Verify Upgraded BGM & Volume**:
   - Join a game from a phone (unmuted) and open the host screen on a computer (unmuted).
   - Once a question starts, listen to the background music on the phone.
   - Verify the double heartbeat thump is exceptionally deep and heavy (chest-thumping kick drum sound) with a strong bass emphasis.
   - Confirm that all feedback tones (correct/incorrect answer sounds) and background music on both the host and player mobile screen are noticeably louder.

7. **Verify Mobile Submit Freeze Fix**:
   - Join the game from a mobile phone (or simulate a mobile device in Chrome DevTools with simulated audio blocks/limitations).
   - Start the game and select an answer.
   - Verify that the player client immediately highlights the selected answer, dims the others, and transitions smoothly to the "Answer Submitted" (`submitted-screen`) screen without freezing, regardless of whether AudioContext is allowed or blocked by the browser.

### 11. GitHub & Cloud Deployment Preparation
- **Added PIP Dependency List (`requirements.txt`)**: Defined all required python packages (`fastapi`, `uvicorn`, `gunicorn`, `aiofiles`, `qrcode`, `pillow`, `websockets`) for automated dependency installation.
- **Added Procfile (`Procfile`)**: Defined the process start configuration for Render's Python environment, launching with the production-ready `gunicorn` runner and single-threaded `uvicorn` workers.
- **Added Git Ignore (`.gitignore`) & Docker Ignore (`.dockerignore`)**: Configured automatic file exclusion lists to prevent local developer configs (`.gemini/`, `.agents/`), database states (`game_state.json`), and temporary python cache directories (`__pycache__/`) from being committed to public GitHub repositories.
- **Enabled Dynamic Port Binding (`server.py`)**: Modified the FastAPI entry point inside `server.py` to dynamically fetch the assigned network port from the standard `$PORT` environment variable injected by cloud providers, enabling automatic deployment and startup on Render.

---

## How to Test & Verify

1. **Verify Dynamic Port Setup**:
   - Run the game server locally using the command line with custom port:
     ```powershell
     $env:PORT="8080"; python server.py
     ```
   - Confirm in logs that it successfully binds to port `8080` instead of the default `8000`.

2. **Verify Deployment Configuration Files**:
    - Confirm that `requirements.txt`, `Procfile`, `.gitignore`, and `.dockerignore` exist in your project root.

3. **Verify Git Upload Helper**:
    - Confirm that [Git上傳助手.ps1](file:///c:/Users/asd552021/OneDrive%20-%20%E9%87%91%E8%BB%8A%E5%A4%A7%E5%A1%9A%E8%82%A1%E4%BB%BD%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8/%E6%A1%8C%E9%9D%A2/%E6%B8%AC%E8%A9%A6/kahoot_game/Git%E4%B8%8A%E5%82%B3%E5%8A%A9%E6%89%8B.ps1) exists in the project root.
