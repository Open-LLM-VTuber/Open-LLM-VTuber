# -*- coding: utf-8 -*-
import asyncio
import http.cookies
import random
import traceback
import websockets
import json
from loguru import logger
import aiohttp
import blivedm.blivedm as blivedm
import blivedm.blivedm.models.web as web_models
from typing import Optional

# 直播间ID的取值看直播间URL | The value of the live room ID is based on the live room URL.
TEST_ROOM_IDS = [
    1991478060,
]

# 这里填一个已登录账号的cookie的SESSDATA字段的值，不填也能运行，只是无法查看发送弹幕的用户名 |
# Fill in the SESSDATA field value of a logged-in account's cookie here. It can still run without it, but the username sending the danmaku cannot be viewed.
SESSDATA = ""

session: Optional[aiohttp.ClientSession] = None
message_queue = (
    asyncio.Queue()
)  # 创建一个队列用于存储弹幕 | Create a queue to store danmaku messages.


async def main():
    init_session()
    try:
        asyncio.create_task(
            run_single_client()
        )  # 非阻塞启动监听直播间任务 | Non-blocking start of the live room listening task.
        await broadcast_client()  # 继续执行 WebSocket 广播任务 | Continue executing the WebSocket broadcasting task.
    finally:
        await session.close()


def init_session():
    """
    初始化 HTTP 会话 | Initialize HTTP session.
    """
    cookies = http.cookies.SimpleCookie()
    cookies["SESSDATA"] = SESSDATA
    cookies["SESSDATA"]["domain"] = "bilibili.com"
    global session
    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)


async def run_single_client():
    """
    监听直播间弹幕 | Listen to danmaku messages from the live room.
    """
    room_id = random.choice(TEST_ROOM_IDS)
    client = blivedm.BLiveClient(room_id, session=session)
    handler = VtuberHandler()
    client.set_handler(handler)
    client.start()
    try:
        await client.join()
    finally:
        await client.stop_and_close()


class VtuberHandler(blivedm.BaseHandler):
    def _on_heartbeat(
        self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage
    ):
        """
        处理心跳包 | Handle heartbeat packets.
        """
        logger.debug(f"[{client.room_id}] 心跳 | Heartbeat")

    def _on_danmaku(
        self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage
    ):
        """
        处理弹幕消息 | Handle danmaku messages.
        """
        logger.debug(f"[{client.room_id}] {message.uname}：{message.msg}")
        asyncio.create_task(
            message_queue.put(message.msg)
        )  # 将弹幕消息加入队列 | Add danmaku message to the queue.


async def broadcast_client():
    """
    监听队列并通过 WebSocket 发送消息 | Listen to the queue and send messages via WebSocket.
    """
    uri = "ws://localhost:12393/add_msg-ws"
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(
                "广播WebSocket连接已建立 | Broadcast WebSocket connection established"
            )
            # while True:
            #     try:
            #         msg = await message_queue.get()  # 从队列获取消息 | Get message from the queue.
            #         message = {
            #             "type": "text-input",
            #             "text": msg
            #         }
            #         await websocket.send(json.dumps(message))
            #         logger.info(f"广播发送消息 | Broadcasting message: {message}")
            #         break
            #     except Exception as e:
            #         logger.info(f"弹幕列表暂时为空: {e} | Danmaku list is temporarily empty: {e}")
            #         await asyncio.sleep(5)
            #         continue

            while True:
                try:
                    response = await websocket.recv()
                    re_msg = json.loads(response)
                    if "audio" in re_msg:
                        # 只保留必要的字段 | Keep only necessary fields.
                        filtered_msg = {
                            "type": re_msg.get("type"),
                            "duration_ms": re_msg.get("duration_ms", 0),
                            "text": re_msg.get("text"),
                            "actions": re_msg.get("actions"),
                            "slice_length": re_msg.get("slice_length"),
                        }
                        re_msg = filtered_msg
                        logger.info(
                            f"收到音频消息 | Received audio message, duration: {re_msg['duration_ms']}ms"
                        )

                    # 处理消息结束信号 | Handle conversation end signal.
                    if (
                        re_msg.get("type") == "control"
                        and re_msg.get("text") == "conversation-chain-end"
                    ):
                        msg = (
                            await message_queue.get()
                        )  # 从队列获取消息 | Get message from the queue.
                        message = {"type": "text-input", "text": msg}
                        await websocket.send(json.dumps(message))
                        logger.info(f"广播发送消息 | Broadcasting message: {message}")
                        # await asyncio.sleep(10)

                    logger.info(f"广播状态 | Broadcast status: {re_msg}")
                except Exception as e:
                    logger.info(
                        f"弹幕列表暂时为空: {e} | Danmaku list is temporarily empty: {e}"
                    )
                    await asyncio.sleep(5)
                    continue

    except Exception as e:
        logger.error(
            f"广播客户端错误 | Broadcast client error: {e}\n{traceback.format_exc()}"
        )


if __name__ == "__main__":
    asyncio.run(main())
