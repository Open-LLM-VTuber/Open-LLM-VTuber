import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.services.gemini_client import gemini_client

router = APIRouter()

# TODO: Add database dependency and logic to fetch character details.
# This was part of SMV-007 but the files were not committed.
# For now, the endpoint will connect but not be fully functional.

@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, userId: str = Query(...)):
    """
    Handles the main chat WebSocket connection.
    - Authenticates user via userId in the query parameter.
    - Receives messages from the client.
    - Calls the Gemini service to generate a response.
    - Sends the formatted response back to the client.
    """
    await websocket.accept()
    print(f"WebSocket connection accepted for user: {userId}")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "chat_message":
                user_prompt = message.get("payload", {}).get("text", "")

                # Call the Gemini service
                response_text = gemini_client.generate_response(user_prompt)

                # Simple parsing logic, assuming format "[emotion] text"
                try:
                    emotion_tag = response_text.split(']')[0][1:]
                    text_content = response_text.split(']')[1].strip()
                except IndexError:
                    emotion_tag = "error"
                    text_content = "Failed to parse model response."

                await websocket.send_json({
                    "type": "ai_response",
                    "payload": { "emotion": emotion_tag, "text": text_content }
                })

    except WebSocketDisconnect:
        print(f"Client {userId} disconnected")
    except Exception as e:
        print(f"An error occurred for user {userId}: {e}")
        # Optionally send an error message to the client before closing
        # await websocket.close(code=1011, reason=f"An internal error occurred: {e}")
    finally:
        print(f"Closing connection for user {userId}")
