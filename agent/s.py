from livekit import api
import os

LIVEKIT_API_KEY="APIbreSJW3MaTqx"
LIVEKIT_API_SECRET="uO9AkPkxyDKWdkf12aSet6XwvHcJy3fZD2IzkoO7n1lB"

token = api.AccessToken(LIVEKIT_API_KEY ,
                        LIVEKIT_API_SECRET) \
    .with_identity("identity") \
    .with_name("name") \
    .with_grants(api.VideoGrants(
        room_join=True,
        room="my-room-01")) \
        .with_room_config(
            api.RoomConfiguration(
                agents=[
                    api.RoomAgentDispatch(
                        agent_name="test-agent", metadata="test-metadata"
                    )
                ],
            ),
        ).to_jwt()


print(token)