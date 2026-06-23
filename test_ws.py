import asyncio
import json
import websockets

async def run_test():
    uri = "ws://localhost:8000/ws"
    
    print("Connecting host...")
    async with websockets.connect(uri) as host_ws:
        await host_ws.send(json.dumps({"role": "host"}))
        host_resp = await host_ws.recv()
        print(f"Host received join success: {host_resp}")
        
        print("Connecting player...")
        async with websockets.connect(uri) as player_ws:
            await player_ws.send(json.dumps({"role": "player", "nickname": "TestPlayer"}))
            player_resp = await player_ws.recv()
            print(f"Player received join success: {player_resp}")
            
            # Start game
            print("Host starting game...")
            await host_ws.send(json.dumps({"type": "start_game"}))
            
            # Host next question
            print("Host moving to next question...")
            await host_ws.send(json.dumps({"type": "next_question"}))
            
            # Loop player messages until we get 'question_start'
            while True:
                player_msg_str = await player_ws.recv()
                player_msg = json.loads(player_msg_str)
                print(f"Player received message: {player_msg.get('type')}")
                if player_msg.get('type') == 'question_start':
                    break
            
            # Player submits answer
            print("Player submitting answer...")
            await player_ws.send(json.dumps({"type": "submit_answer", "answer_index": 0}))
            
            # Loop player messages until we get 'answer_acknowledged'
            while True:
                player_msg_str = await player_ws.recv()
                player_msg = json.loads(player_msg_str)
                print(f"Player received after submission: {player_msg.get('type')} - {player_msg_str}")
                if player_msg.get('type') == 'answer_acknowledged':
                    break
            
            # Let's wait a bit to see if anything else happens
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_test())
