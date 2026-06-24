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

### 12. 強制結束遊戲並清空大廳玩家功能
- **解決問題**：當玩家手機網頁異常退出時（如直接關閉瀏覽器），因為 TCP 半開連線，伺服器可能無法即時偵測到斷線，導致該「幽靈玩家」依然留在遊戲狀態中，阻礙了主持人重設或開始新遊戲。
- **實作邏輯**：
  - 在主持人端右上角標頭（Header）控制區新增了紅色的 **「💥 強制結束遊戲」** 按鈕。
  - 當主持人點擊並確認後，會發送 `force_reset` 訊息給後端。
  - 後端會立即中斷並關閉所有目前連線玩家的 WebSocket 連線，徹底清空 `self.players = {}` 字典，並刪除暫存的 `game_state.json` 檔案。
  - 玩家端會因為連線關閉，自動被引導至暱稱輸入畫面（登入頁面），可重新輸入加入大廳，確保不殘留任何幽靈玩家。

4. **Verify Force Reset Game Feature**:
    - Open Host page `/host` and join with multiple Player pages `/player`.
    - Click "💥 強制結束遊戲" on the top right of the Host page and confirm.
    - Verify that Host page immediately returns to the Lobby with player count reset to `0`, and all Player pages redirect to the nickname join screen.

### 13. 自訂複數題目組別與多資料庫管理功能
- **解決問題**：原本系統只能編輯與使用單一的 `questions.json`，無法設定複數類型的自訂題目組別。
- **實作邏輯**：
  - **資料庫升級**：在後端新增了 `question_sets/` 目錄，每一套題目組別皆儲存為一個獨立的 JSON 檔案（例如 `預設題目.json`）。系統會在啟動時自動將原有的舊 `questions.json` 遷移至 `question_sets/預設題目.json`，確保資料無縫升級且不遺失。
  - **編輯器端 (Creator)**：
    - 右上角新增「目前組別」下拉選單，並附帶 **「📁 新增組別」** 與 **「🗑️ 刪除組別」** 按鈕。
    - 點擊「新增組別」可透過對話視窗輸入名稱並立即建立新的空白組別；點擊「刪除組別」則可永久刪除該組別（限制至少保留一個組別）。
    - 編輯題目與儲存時，皆會自動關聯並更新當前選定的組別檔案。
  - **主持人投影端 (Host)**：
    - 右上角標頭新增了「遊戲題目」下拉選單。在大廳時，主持人可隨時切換題目組別，切換時會即時重新載入題目並重設大廳狀態與題目總數。
    - 當遊戲開始後，該選單會自動停用，以防止遊戲中途誤切換。

5. **Verify Question Sets Feature**:
    - Open Creator page `/creator`, switch sets using the top-right dropdown, create a new set, add questions to it and save.
    - Open Host page `/host`, switch sets in lobby, and verify the questions update instantly. Check that starting the game disables the dropdown.

### 14. 遊戲大廳標頭排版優化與寶礦力主題化
- **解決問題**：在較窄的螢幕上，右上角控制列的按鈕文字因空間不足而換行擠壓成第二排；且左側主題文字需替換為專屬名稱與寶礦力品牌色。
- **實作邏輯**：
  - **排版優化**：
    - 將所有標頭按鈕（包含「題目設定」、「強制結束遊戲」與動態控制按鈕）與狀態標籤的字型大小縮減至 `13px` / `12px`，並調整內距（padding）與間距（gap），節省橫向排版空間。
    - 為按鈕、下拉選單、狀態標籤和標題加入 `white-space: nowrap;` CSS 樣式，**強制禁止文字換行**，徹底解決文字擠壓成兩排的問題。
  - **寶礦力品牌化**：
    - 左上角的主題文字修改為 **「寶礦力知識大挑戰」**。
    - 字型顏色採用經典的寶礦力品牌藍色 (`#0066ff`)，並加上白色的細邊框文字陰影效果 (`text-shadow`)，確保在深綠色的黑板背景上擁有極佳的對比度與質感。

6. **Verify Header Layout & Pocari Theme**:
    - Access `/host` and confirm the top-left title is "寶礦力知識大挑戰" and shows in bright blue with a clean outline.
    - Confirm all top-right controls and status badges fit cleanly on a single row without any text wrapping or line breaks.

### 15. 手機端加入遊戲與大廳同步異常修正 (Websocket Concurrency Fix)
- **問題現象**：手機端掃描 QRcode 後，顯示「您已成功加入遊戲」，但遊戲大廳（Host）卻沒看到該玩家，且無法開始遊戲。
- **根本原因**：在舊程式碼的 `broadcast_to_players` 中，後端透過非同步迴圈直接迭代 `self.players.items()`，並在迴圈內呼叫 `await data["ws"].send_json(message)`。由於 `await` 會讓出執行權，在此期間若有其他玩家連線或狀態變更（例如新玩家連線寫入 `self.players`），會造成字典大小在迭代過程中改變，進而拋出 `RuntimeError: dictionary changed size during iteration` 異常。
- 此異常會傳播到該玩家的 WebSocket 處理程序中，觸發 Exception 區塊，導致伺服器從 `self.players` 中將該玩家刪除（`del game_manager.players[client_name]`）並關閉 WebSocket 連線。但因為手機端在此之前已成功接收到 `join_success` 訊息，畫面已顯示「您已成功加入遊戲」，造成手機端卡在成功畫面，但後端大廳查無此人的不同步現象。
- **解決方案**：在 `server.py` 的 `broadcast_to_players` 函數中，使用 `list(self.players.items())` 建立靜態清單快照進行安全迭代，徹底避免併發修改導致 `RuntimeError` 的錯誤。
- **已部署至 Render**：此修復已推送至 GitHub，並已由 Render 自動重新部署生效。
