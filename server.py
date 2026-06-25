import os
import json
import socket
import asyncio
import time
import io
import uuid
import subprocess
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import aiofiles
import qrcode

app = FastAPI(title="Kahoot-like Interactive Game")

# Path Configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
QUESTIONS_FILE = os.path.join(BASE_DIR, "questions.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
STATE_FILE = os.path.join(BASE_DIR, "game_state.json")
SETS_DIR = os.path.join(BASE_DIR, "question_sets")

# Ensure directories exist
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SETS_DIR, exist_ok=True)

# Migration: if questions.json exists in root, move it to question_sets/預設題目.json
DEFAULT_SET_FILE = os.path.join(SETS_DIR, "預設題目.json")
if os.path.exists(QUESTIONS_FILE):
    try:
        import shutil
        shutil.move(QUESTIONS_FILE, DEFAULT_SET_FILE)
        print(f"Migrated questions.json to {DEFAULT_SET_FILE}")
    except Exception as e:
        print(f"Error migrating questions.json: {e}")

# If DEFAULT_SET_FILE still doesn't exist, create an empty one
if not os.path.exists(DEFAULT_SET_FILE):
    try:
        with open(DEFAULT_SET_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error creating default set file: {e}")

# Mount Static Files (for uploaded images)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Helper function to get local IP address
def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a public DNS server (doesn't send actual packets)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = '127.0.0.1'
    finally:
        s.close()
    
    # If we got a loopback address, try to resolve via hostname list
    if ip.startswith('127.'):
        try:
            host_info = socket.gethostbyname_ex(socket.gethostname())
            ips = [i for i in host_info[2] if not i.startswith("127.")]
            if ips:
                ip = ips[0]
        except Exception:
            pass
    return ip

def git_push_background():
    # Check if we are running in Render environment
    if "RENDER" in os.environ:
        print("[Git Auto-Push] Detected Render cloud environment. Skipping auto-push to GitHub.")
        return

    # Check if .git directory exists
    git_dir = os.path.join(BASE_DIR, ".git")
    if not os.path.exists(git_dir):
        print(f"[Git Auto-Push] No .git folder found at {git_dir}. Skipping auto-push to GitHub.")
        return

    try:
        print("[Git Auto-Push] Starting git commit and push...")

        # 1. Add all changes in the project directory
        # This stages updated JSON files in question_sets/ and uploaded files in static/uploads/
        subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=True, capture_output=True, text=True)

        # 2. Check if there are changes staged for commit
        status_proc = subprocess.run(["git", "status", "--porcelain"], cwd=BASE_DIR, check=True, capture_output=True, text=True)
        if not status_proc.stdout.strip():
            print("[Git Auto-Push] No changes to commit. Skipping push.")
            return

        # 3. Commit changes
        commit_msg = f"Auto-save question sets & uploads at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=BASE_DIR, check=True, capture_output=True, text=True)

        # 4. Push to GitHub main branch
        # 30-second timeout to prevent hanging due to networking issues
        push_proc = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True, timeout=30, capture_output=True, text=True)
        print(f"[Git Auto-Push] Successfully pushed changes to GitHub.\n{push_proc.stdout}")

    except subprocess.TimeoutExpired as te:
        print(f"[Git Auto-Push] Timeout expired during git push: {te}")
    except subprocess.CalledProcessError as cpe:
        print(f"[Git Auto-Push] Git command failed: {cpe.cmd}")
        print(f"Stdout: {cpe.stdout}")
        print(f"Stderr: {cpe.stderr}")
    except Exception as e:
        print(f"[Git Auto-Push] Unexpected error during git push: {e}")

# Global Game Manager
class GameManager:
    def __init__(self):
        self.host_ws: Optional[WebSocket] = None
        # players structure: { nickname: { "ws": ws_connection, "score": int, "streak": int, "answered": bool, "time_taken": float, "is_correct": bool, "points_earned": int, "connected": bool } }
        self.players: Dict[str, Dict[str, Any]] = {}
        # game_state can be: "LOBBY", "QUESTION", "REVEAL", "LEADERBOARD", "FINISHED"
        self.game_state: str = "LOBBY"
        self.questions: List[Dict[str, Any]] = []
        self.current_question_index: int = 0
        self.current_set_name: str = "預設題目"
        self.timer_seconds: int = 0
        self.timer_task: Optional[asyncio.Task] = None
        # Delete old state file on startup to ensure a fresh lobby and prevent stuck states
        if os.path.exists(STATE_FILE):
            try:
                os.remove(STATE_FILE)
            except Exception:
                pass
        self.load_questions()

    def save_state(self):
        try:
            players_save = {}
            for name, data in self.players.items():
                players_save[name] = {
                    "score": data.get("score", 0),
                    "streak": data.get("streak", 0),
                    "answered": data.get("answered", False),
                    "time_taken": data.get("time_taken", 0.0),
                    "is_correct": data.get("is_correct", False),
                    "points_earned": data.get("points_earned", 0),
                    "selected_index": data.get("selected_index", -1),
                    "connected": False
                }
            state_data = {
                "game_state": self.game_state,
                "current_question_index": self.current_question_index,
                "current_set_name": self.current_set_name,
                "players": players_save
            }
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving game state: {e}")

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                self.game_state = state_data.get("game_state", "LOBBY")
                self.current_question_index = state_data.get("current_question_index", 0)
                self.current_set_name = state_data.get("current_set_name", "預設題目")
                players_load = state_data.get("players", {})
                for name, data in players_load.items():
                    self.players[name] = {
                        "ws": None,
                        "score": data.get("score", 0),
                        "streak": data.get("streak", 0),
                        "answered": data.get("answered", False),
                        "time_taken": data.get("time_taken", 0.0),
                        "is_correct": data.get("is_correct", False),
                        "points_earned": data.get("points_earned", 0),
                        "selected_index": data.get("selected_index", -1),
                        "connected": False
                    }
                print("Game state loaded successfully.")
            except Exception as e:
                print(f"Error loading game state: {e}")

    def load_questions(self):
        set_file = os.path.join(SETS_DIR, f"{self.current_set_name}.json")
        if os.path.exists(set_file):
            try:
                with open(set_file, 'r', encoding='utf-8') as f:
                    self.questions = json.load(f)
            except Exception as e:
                print(f"Error loading questions from {set_file}: {e}")
                self.questions = []
        else:
            self.questions = []

    def change_question_set(self, set_name: str):
        self.current_set_name = set_name
        self.load_questions()
        self.reset_game()

    def get_current_question(self) -> Optional[Dict[str, Any]]:
        if 0 <= self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None

    def reset_game(self):
        self.game_state = "LOBBY"
        self.current_question_index = 0
        self.timer_seconds = 0
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None
        # Keep players but reset their scores for a new game
        for name in list(self.players.keys()):
            if not self.players[name]["connected"]:
                del self.players[name]
            else:
                self.players[name]["score"] = 0
                self.players[name]["streak"] = 0
                self.players[name]["answered"] = False
                self.players[name]["time_taken"] = 0.0
                self.players[name]["is_correct"] = False
                self.players[name]["points_earned"] = 0
        self.save_state()

    async def force_reset_game(self):
        self.game_state = "LOBBY"
        self.current_question_index = 0
        self.timer_seconds = 0
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None
        
        # Close all player WebSocket connections to kick them to the login screen
        for name, data in list(self.players.items()):
            ws = data.get("ws")
            if ws:
                try:
                    await ws.send_json({"type": "reset_to_lobby"})
                    await ws.close()
                except Exception:
                    pass
        
        # Completely clear players
        self.players = {}
        
        # Delete state file to ensure fresh start
        if os.path.exists(STATE_FILE):
            try:
                os.remove(STATE_FILE)
            except Exception:
                pass

    async def broadcast_to_players(self, message: Dict[str, Any]):
        disconnected_players = []
        for name, data in list(self.players.items()):
            if data["connected"] and data["ws"]:
                try:
                    await data["ws"].send_json(message)
                except Exception:
                    disconnected_players.append(name)
        
        for name in disconnected_players:
            self.players[name]["connected"] = False
            self.players[name]["ws"] = None
            print(f"Player {name} disconnected during broadcast.")
        if disconnected_players:
            await self.send_lobby_update()

    async def send_to_host(self, message: Dict[str, Any]):
        if self.host_ws:
            try:
                await self.host_ws.send_json(message)
            except Exception:
                self.host_ws = None
                print("Host connection lost.")

    async def send_lobby_update(self):
        player_list = [
            {"nickname": name, "connected": data["connected"], "score": data["score"]}
            for name, data in self.players.items()
        ]
        await self.send_to_host({
            "type": "lobby_update",
            "players": player_list
        })
        # Notify players of their lobby status
        await self.broadcast_to_players({
            "type": "lobby_status",
            "player_count": len(self.players)
        })

    async def start_question(self):
        question = self.get_current_question()
        if not question:
            await self.end_game()
            return

        self.game_state = "QUESTION"
        # Reset player answer status for this question
        for name in self.players.keys():
            self.players[name]["answered"] = False
            self.players[name]["time_taken"] = 0.0
            self.players[name]["is_correct"] = False
            self.players[name]["points_earned"] = 0

        # Send question to Host (includes correct index, time, options, and image_url if present)
        await self.send_to_host({
            "type": "question_start",
            "question_index": self.current_question_index,
            "total_questions": len(self.questions),
            "question": question["question"],
            "options": question["options"],
            "correct_index": question["correct_index"],
            "time_limit": question["time_limit"],
            "image_url": question.get("image_url")
        })

        # Send question to Players (exclude correct_index)
        await self.broadcast_to_players({
            "type": "question_start",
            "question_index": self.current_question_index,
            "total_questions": len(self.questions),
            "question": question["question"],
            "options": question["options"],
            "time_limit": question["time_limit"],
            "image_url": question.get("image_url")
        })

        self.question_start_time = time.time()
        self.timer_seconds = question["time_limit"]
        
        if self.timer_task:
            self.timer_task.cancel()
        
        self.timer_task = asyncio.create_task(self.countdown_timer())
        self.save_state()

    async def countdown_timer(self):
        try:
            while self.timer_seconds > 0:
                await asyncio.sleep(1)
                self.timer_seconds -= 1
                
                # Broadcast timer tick
                tick_msg = {"type": "timer_tick", "seconds_left": self.timer_seconds}
                await self.send_to_host(tick_msg)
                await self.broadcast_to_players(tick_msg)
                
            # Timer expired
            await self.reveal_answers()
        except asyncio.CancelledError:
            pass

    async def reveal_answers(self):
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None
            
        self.game_state = "REVEAL"
        question = self.get_current_question()
        if not question:
            return

        correct_idx = question["correct_index"]
        
        # Calculate statistics
        stats = [0, 0, 0, 0] # counts for options 0, 1, 2, 3
        for name, data in self.players.items():
            if data["answered"]:
                sel_idx = data.get("selected_index", -1)
                if 0 <= sel_idx < 4:
                    stats[sel_idx] += 1

        # Calculate rankings for leaderboard
        sorted_players = sorted(
            self.players.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        leaderboard_data = []
        for rank, (name, data) in enumerate(sorted_players, 1):
            leaderboard_data.append({
                "rank": rank,
                "nickname": name,
                "score": data["score"],
                "streak": data["streak"],
                "connected": data["connected"]
            })

        # Send reveal to host
        await self.send_to_host({
            "type": "reveal_answers",
            "correct_index": correct_idx,
            "stats": stats,
            "leaderboard": leaderboard_data[:5]
        })

        # Send individual feedback to players
        for rank, (name, data) in enumerate(sorted_players, 1):
            if data["connected"] and data["ws"]:
                try:
                    await data["ws"].send_json({
                        "type": "reveal_player_result",
                        "is_correct": data["is_correct"],
                        "points_earned": data["points_earned"],
                        "total_score": data["score"],
                        "streak": data["streak"],
                        "correct_index": correct_idx,
                        "selected_index": data.get("selected_index", -1),
                        "rank": rank,
                        "total_players": len(self.players)
                    })
                except Exception:
                    pass
        self.save_state()

    async def show_leaderboard(self):
        self.game_state = "LEADERBOARD"
        
        # Rank players
        sorted_players = sorted(
            self.players.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        leaderboard_data = []
        for rank, (name, data) in enumerate(sorted_players, 1):
            leaderboard_data.append({
                "rank": rank,
                "nickname": name,
                "score": data["score"],
                "streak": data["streak"],
                "connected": data["connected"]
            })

        # Host receives top 5
        await self.send_to_host({
            "type": "leaderboard",
            "leaderboard": leaderboard_data[:5]
        })

        # Players receive their own rank
        for rank, (name, data) in enumerate(sorted_players, 1):
            if data["connected"] and data["ws"]:
                try:
                    await data["ws"].send_json({
                        "type": "leaderboard_player",
                        "rank": rank,
                        "total_players": len(self.players),
                        "score": data["score"],
                        "streak": data["streak"]
                    })
                except Exception:
                    pass
        self.save_state()

    async def end_game(self):
        self.game_state = "FINISHED"
        
        sorted_players = sorted(
            self.players.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        podium = []
        for rank, (name, data) in enumerate(sorted_players[:5], 1):
            podium.append({
                "rank": rank,
                "nickname": name,
                "score": data["score"]
            })

        # Send final podium to host
        await self.send_to_host({
            "type": "podium",
            "podium": podium
        })

        # Send final result to players
        for rank, (name, data) in enumerate(sorted_players, 1):
            if data["connected"] and data["ws"]:
                try:
                    await data["ws"].send_json({
                        "type": "game_finished",
                        "rank": rank,
                        "total_players": len(self.players),
                        "score": data["score"]
                    })
                except Exception:
                    pass
        self.save_state()

    async def handle_player_answer(self, name: str, answer_index: int):
        if self.game_state != "QUESTION":
            return
            
        data = self.players.get(name)
        if not data or data["answered"]:
            return

        data["answered"] = True
        data["selected_index"] = answer_index
        
        time_taken = time.time() - self.question_start_time
        data["time_taken"] = time_taken
        
        question = self.get_current_question()
        if not question:
            return
            
        correct_index = question["correct_index"]
        time_limit = question["time_limit"]
        
        if answer_index == correct_index:
            data["is_correct"] = True
            # Scoring algorithm: Max 1000 points. Decays linearly.
            speed_ratio = min(time_taken / time_limit, 1.0)
            base_points = 1000
            points = int(base_points * (1.0 - speed_ratio * 0.5))
            
            # Streak bonus
            data["streak"] += 1
            streak_bonus = min((data["streak"] - 1) * 100, 500)
            points += streak_bonus
            
            data["points_earned"] = points
            data["score"] += points
        else:
            data["is_correct"] = False
            data["streak"] = 0
            data["points_earned"] = 0

        # Send answer acknowledgement to the player
        if data["connected"] and data["ws"]:
            try:
                await data["ws"].send_json({
                    "type": "answer_acknowledged",
                    "nickname": name
                })
            except Exception:
                pass

        # Update host with answer count
        answered_count = sum(1 for p in self.players.values() if p["answered"])
        total_active_players = sum(1 for p in self.players.values() if p["connected"])
        
        await self.send_to_host({
            "type": "answer_received",
            "answered_count": answered_count,
            "total_players": total_active_players
        })
        self.save_state()

        # If all active connected players answered, transition to reveal immediately
        if answered_count >= total_active_players and total_active_players > 0:
            await self.reveal_answers()


game_manager = GameManager()

# HTML Endpoint Handlers
async def get_template(filename: str) -> HTMLResponse:
    filepath = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Template {filename} not found")
    async with aiofiles.open(filepath, mode='r', encoding='utf-8') as f:
        content = await f.read()
    return HTMLResponse(content=content)

@app.get("/")
async def root():
    return await get_template("player.html")

@app.get("/host")
async def host_page():
    return await get_template("host.html")

@app.get("/player")
async def player_page():
    return await get_template("player.html")

@app.get("/creator")
async def creator_page():
    return await get_template("creator.html")

# API Endpoints
@app.get("/api/question_sets")
async def get_question_sets():
    try:
        sets = []
        for filename in os.listdir(SETS_DIR):
            if filename.endswith(".json"):
                name = os.path.splitext(filename)[0]
                filepath = os.path.join(SETS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        count = len(data) if isinstance(data, list) else 0
                except Exception:
                    count = 0
                sets.append({"name": name, "count": count})
        sets.sort(key=lambda x: x["name"])
        return {
            "current_set": game_manager.current_set_name,
            "sets": sets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/question_sets/new")
async def create_question_set(name: str, background_tasks: BackgroundTasks):
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Set name cannot be empty")
    
    # Allow alphanumeric, Chinese, spaces, underscores, dashes
    safe_name = "".join([c for c in name if c.isalnum() or c in " _-"]).strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid set name")
    
    set_file = os.path.join(SETS_DIR, f"{safe_name}.json")
    if os.path.exists(set_file):
        raise HTTPException(status_code=400, detail="Question set already exists")
    
    try:
        async with aiofiles.open(set_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps([], ensure_ascii=False, indent=2))
        background_tasks.add_task(git_push_background)
        return {"status": "success", "name": safe_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/question_sets")
async def delete_question_set(name: str, background_tasks: BackgroundTasks):
    name = name.strip()
    set_file = os.path.join(SETS_DIR, f"{name}.json")
    if not os.path.exists(set_file):
        raise HTTPException(status_code=404, detail="Question set not found")
    
    json_files = [f for f in os.listdir(SETS_DIR) if f.endswith(".json")]
    if len(json_files) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last question set")
    
    try:
        os.remove(set_file)
        if name == game_manager.current_set_name:
            remaining_files = [f for f in os.listdir(SETS_DIR) if f.endswith(".json")]
            new_set = os.path.splitext(remaining_files[0])[0]
            game_manager.change_question_set(new_set)
        background_tasks.add_task(git_push_background)
        return {"status": "success", "message": f"Question set {name} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/questions")
async def get_questions(set: Optional[str] = None):
    set_name = set or game_manager.current_set_name
    set_file = os.path.join(SETS_DIR, f"{set_name}.json")
    if not os.path.exists(set_file):
        raise HTTPException(status_code=404, detail=f"Question set {set_name} not found")
    try:
        async with aiofiles.open(set_file, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/preloads")
async def get_preloads():
    game_manager.load_questions()
    urls = [q.get("image_url") for q in game_manager.questions if q.get("image_url")]
    return {"urls": urls}

@app.post("/api/questions")
async def save_questions(request: Request, background_tasks: BackgroundTasks, set: Optional[str] = None):
    set_name = set or game_manager.current_set_name
    set_file = os.path.join(SETS_DIR, f"{set_name}.json")
    try:
        new_questions = await request.json()
        for q in new_questions:
            if not isinstance(q.get("question"), str):
                raise HTTPException(status_code=400, detail="Invalid question text")
            if not isinstance(q.get("options"), list) or len(q["options"]) != 4:
                raise HTTPException(status_code=400, detail="Options must be a list of 4 items")
            if not isinstance(q.get("correct_index"), int) or not (0 <= q["correct_index"] < 4):
                raise HTTPException(status_code=400, detail="Invalid correct index")
            if not isinstance(q.get("time_limit"), int) or q["time_limit"] <= 0:
                raise HTTPException(status_code=400, detail="Invalid time limit")
            if "image_url" in q and q["image_url"] is not None and not isinstance(q["image_url"], str):
                raise HTTPException(status_code=400, detail="Invalid image URL")
        
        async with aiofiles.open(set_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(new_questions, ensure_ascii=False, indent=2))
        
        if set_name == game_manager.current_set_name:
            game_manager.load_questions()
            
        background_tasks.add_task(git_push_background)
        return {"status": "success", "message": "Questions updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ip")
async def get_server_ip():
    return {"ip": get_local_ip()}

# Image Upload API
@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, JPEG, GIF, and WEBP images are allowed.")
    
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOADS_DIR, unique_filename)
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(content)
        
        return {"url": f"/static/uploads/{unique_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

# Server-side QR Code Generator API
@app.get("/api/qrcode")
def get_qrcode(text: str):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_role = None
    client_name = None
    
    try:
        # First message must be registration
        reg_data = await websocket.receive_json()
        client_role = reg_data.get("role")
        
        if client_role == "host":
            # Set host connection
            game_manager.host_ws = websocket
            print("Host connected via WebSocket.")
            
            # Send initial IP and questions info
            await game_manager.send_to_host({
                "type": "init",
                "game_state": game_manager.game_state,
                "question_count": len(game_manager.questions),
                "current_set_name": game_manager.current_set_name,
                "local_ip": get_local_ip()
            })
            # Send current lobby list if players exist
            await game_manager.send_lobby_update()
            
        elif client_role == "player":
            client_name = reg_data.get("nickname", "").strip()
            if not client_name:
                await websocket.send_json({"type": "error", "message": "暱稱不能為空！"})
                await websocket.close()
                return
                
            # If game is in progress and player was NOT registered, reject
            if game_manager.game_state != "LOBBY" and client_name not in game_manager.players:
                await websocket.send_json({"type": "error", "message": "遊戲已經開始，無法加入！"})
                await websocket.close()
                return

            # Reconnection or brand new connection
            if client_name in game_manager.players:
                existing = game_manager.players[client_name]
                if existing["connected"]:
                    await websocket.send_json({"type": "error", "message": "此暱稱已被使用中！"})
                    await websocket.close()
                    return
                else:
                    # Reconnect
                    print(f"Player {client_name} reconnected.")
                    existing["connected"] = True
                    existing["ws"] = websocket
            else:
                # New registration
                print(f"Player {client_name} joined.")
                game_manager.players[client_name] = {
                    "ws": websocket,
                    "score": 0,
                    "streak": 0,
                    "answered": False,
                    "time_taken": 0.0,
                    "is_correct": False,
                    "points_earned": 0,
                    "connected": True
                }
            game_manager.save_state()
            
            # Send join success
            await websocket.send_json({
                "type": "join_success",
                "nickname": client_name,
                "game_state": game_manager.game_state
            })
            
            # Send current question info if game is active
            if game_manager.game_state == "QUESTION":
                question = game_manager.get_current_question()
                if question and not game_manager.players[client_name]["answered"]:
                    time_elapsed = time.time() - game_manager.question_start_time
                    seconds_left = max(0, int(question["time_limit"] - time_elapsed))
                    await websocket.send_json({
                        "type": "question_start",
                        "question_index": game_manager.current_question_index,
                        "total_questions": len(game_manager.questions),
                        "question": question["question"],
                        "options": question["options"],
                        "time_limit": seconds_left,
                        "image_url": question.get("image_url")
                    })
            
            # Update lobby list
            await game_manager.send_lobby_update()
            
        else:
            await websocket.send_json({"type": "error", "message": "未知的角色設定。"})
            await websocket.close()
            return
            
        # Keep listening for messages
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if client_role == "host":
                if msg_type == "start_game":
                    game_manager.reset_game()
                    await game_manager.start_question()
                elif msg_type == "next_question":
                    game_manager.current_question_index += 1
                    await game_manager.start_question()
                elif msg_type == "reveal_answers":
                    await game_manager.reveal_answers()
                elif msg_type == "show_leaderboard":
                    await game_manager.show_leaderboard()
                elif msg_type == "end_game":
                    await game_manager.end_game()
                elif msg_type == "reset":
                    game_manager.reset_game()
                    await game_manager.send_lobby_update()
                    await game_manager.broadcast_to_players({"type": "reset_to_lobby"})
                elif msg_type == "force_reset":
                    await game_manager.force_reset_game()
                    await game_manager.send_lobby_update()
                elif msg_type == "change_set":
                    set_name = data.get("set_name")
                    if set_name:
                        game_manager.change_question_set(set_name)
                        await game_manager.send_to_host({
                            "type": "init",
                            "game_state": game_manager.game_state,
                            "question_count": len(game_manager.questions),
                            "current_set_name": game_manager.current_set_name,
                            "local_ip": get_local_ip()
                        })
                        await game_manager.send_lobby_update()
                    
            elif client_role == "player" and client_name:
                if msg_type == "submit_answer":
                    ans_idx = data.get("answer_index")
                    if isinstance(ans_idx, int):
                        await game_manager.handle_player_answer(client_name, ans_idx)
                        
    except WebSocketDisconnect:
        if client_role == "host":
            print("Host disconnected.")
            game_manager.host_ws = None
        elif client_role == "player" and client_name:
            print(f"Player {client_name} disconnected.")
            if client_name in game_manager.players:
                # If game is in Lobby, delete player. Otherwise, keep data for reconnection.
                if game_manager.game_state == "LOBBY":
                    del game_manager.players[client_name]
                else:
                    game_manager.players[client_name]["connected"] = False
                    game_manager.players[client_name]["ws"] = None
                await game_manager.send_lobby_update()
            game_manager.save_state()
    except Exception as e:
        print(f"WebSocket error: {e}")
        if client_role == "host":
            game_manager.host_ws = None
        elif client_role == "player" and client_name:
            if client_name in game_manager.players:
                if game_manager.game_state == "LOBBY":
                    del game_manager.players[client_name]
                else:
                    game_manager.players[client_name]["connected"] = False
                    game_manager.players[client_name]["ws"] = None
                await game_manager.send_lobby_update()
            game_manager.save_state()

if __name__ == "__main__":
    import uvicorn
    ip = get_local_ip()
    port = int(os.environ.get("PORT", 8000))
    print("\n" + "="*50)
    print(f"Kahoot-like Game Server is running!")
    print(f"Host screen URL: http://{ip}:{port}/host")
    print(f"Player screen URL: http://{ip}:{port}/player")
    print(f"Question creator URL: http://{ip}:{port}/creator")
    print("="*50 + "\n")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
