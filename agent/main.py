import logging
import asyncio
import re
import io
import os
import time
import json
from datetime import datetime, timezone
import random
import aiohttp
from dotenv import load_dotenv

from livekit import api
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, silero, turn_detector, noise_cancellation, elevenlabs, groq

load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")

# Create LLM and TTS objects (adjust as necessary)
try:
    groq_llm = groq.LLM(
        model="llama-3.3-70b-versatile",
        temperature=0.8,
    )
except Exception:
    groq_llm = None


try:
    eleven_tts = elevenlabs.tts.TTS(
        model="eleven_flash_v2_5",
        voice=elevenlabs.tts.Voice(
            id="21m00Tcm4TlvDq8ikWAM",
            name="Rachel",
            category="premade",
            settings=elevenlabs.tts.VoiceSettings(
                stability=0.8,
                similarity_boost=0.6,
                style=0.3,
                use_speaker_boost=True,
            ),
        ),
        streaming_latency=1,
        enable_ssml_parsing=True,
        chunk_length_schedule=[50, 100, 200, 260],
        language="hi",
    )
except Exception:
    eleven_tts = None

# STT
try:
    deepgram_stt = deepgram.stt.STT(
        model="nova-2-general",
        interim_results=True,
        smart_format=True,
        punctuate=True,
        filler_words=False,
        profanity_filter=False,
        keywords=[("English, Hindi, Holiday Trip", 1.5)],
        language="hi",
    )
except Exception:
    deepgram_stt = None

# Prewarm function
def prewarm(proc: JobProcess):
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        proc.userdata["vad"] = None


# async def dropbox_upload(file_path: str, content: bytes):
#     """Upload bytes to Dropbox at file_path. Uses DROPBOX_ACCESS_TOKEN from env.
#     Returns True on success, False otherwise.
#     """
#     token = os.getenv("DROPBOX_ACCESS_TOKEN")
#     if not token:
#         logger.error("DROPBOX_ACCESS_TOKEN not found in environment; skipping Dropbox upload.")
#         return False

#     try:
#         dbx = dropbox.Dropbox(token)
#         # Overwrite if file exists
#         dbx.files_upload(content, file_path, mode=dropbox.files.WriteMode.overwrite, mute=True)
#         logger.info(f"Uploaded to Dropbox: {file_path}")
#         return True
#     except dropbox.exceptions.AuthError as e:
#         logger.error(f"Dropbox auth error: {e}")
#         return False
#     except Exception as e:
#         logger.exception(f"Dropbox upload failed: {e}")
#         return False


# --- Main entrypoint ---
async def entrypoint(ctx: JobContext):
    system_msg = llm.ChatMessage(
        role="system",
        content=(
            """
                ###PERSIONALITY###
                You are Neha , a friendly and professional HR assistant. You are empathetic, patient, and a good listener. You speak in a warm and engaging tone, making candidates feel comfortable and valued.
                You are fluent in both English and Hindi, and can seamlessly switch between the two languages based on the candidate's preference. You use simple and clear language, avoiding jargon or complex terms.

                For this Prompt You have to take the interview of a candidate for the role of a Excel Commands and Concept .

                ###GOALS###
                Your primary goal is to assess the candidate's skills, experience, and cultural fit for the role. You should ask open-ended questions that encourage the candidate to share detailed responses.
                You should also provide information about the company, the role, and the interview process. You should be prepared to answer any questions the candidate may have.
                You should aim to create a positive and engaging interview experience for the candidate, leaving them with a favorable impression of the company.
                Only Asked the Question , Dont Provide the answers of command of excel just ask question if he's unable to recall you can Hint him/her 

                ###CONSTRAINTS###
                - Keep the interviw concise and focused, avoiding unnecessary small talk or tangents.
                - Avoid asking overly personal or sensitive questions that are not relevant to the role.

                - Do not make any promises or guarantees about the role or the interview process.
                - If the candidate asks a question you cannot answer, politely let them know you will follow up with them later.

                ###Conversational FLow : 

                1. Start with a warm greeting and introduction.
                2. Ask the candidate about their background, experience, and skills.
                3. Dive into role-specific questions, focusing on technical skills and problem-solving abilities.
                4. Explore behavioral and situational questions to assess cultural fit.
                5. Provide information about the company and the role.
                6. Allow time for the candidate to ask questions.
                7. Conclude with next steps and a thank you.

           """
        ),
    )

    initial_ctx = llm.ChatContext()
    initial_ctx.messages.append(system_msg)

    transcripts = {}

    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.kind}")

    transcripts["room_name"] = ctx.room.name
    transcripts["transcript"] = []
    transcripts["duration"] = time.time()
    transcripts["date"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata.get("vad"),
        stt=deepgram_stt,
        llm=groq_llm,
        tts=eleven_tts,
        turn_detector=turn_detector.EOUModel(),
        min_endpointing_delay=0.3,
        max_endpointing_delay=3.0,
        chat_ctx=initial_ctx,
        interrupt_min_words=3,
        noise_cancellation=noise_cancellation.BVC() if hasattr(noise_cancellation, 'BVC') else None,
        allow_interruptions=True,
    )

    FILLERS = [
        "hm...",
        "अच्छा...",
        "Okay...",
        "Got it...",
        "हां...",
        "Alright!",
        "वैसे…",
        "ठीक…",
        "जी...",
    ]

    async def play_filler(filler):
        try:
            await agent.say(filler, allow_interruptions=True, add_to_chat_ctx=False)
        except Exception:
            logger.exception("play_filler failed")

    state = {"filler_task": None}

    async def before_llm_cb(assistant: VoicePipelineAgent, chat_ctx: llm.ChatContext):
        if state["filler_task"] is None or state["filler_task"].done():
            state["filler_task"] = asyncio.create_task(play_filler(filler=random.choice(FILLERS)))
        return assistant.llm.chat(chat_ctx=chat_ctx)

    usage_collector = metrics.UsageCollector()

    @agent.on("agent_speech_interrupted")
    def on_agent_speech_interrupted():
        try:
            agent.interrupt()
        except Exception:
            pass

    @agent.on("metrics_collected")
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        try:
            metrics.log_metrics(agent_metrics)
            usage_collector.collect(agent_metrics)
        except Exception:
            pass

    # transcription queue
    log_queue = asyncio.Queue()

    async def hangup():
        try:
            ctx.shutdown(reason="Session ended, call cut.")
            await api.LiveKitAPI().room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
        except Exception as e:
            logger.info(f"received error while ending call: {e}")

    @ctx.room.on('participant_disconnected')
    def on_participant_disconnected():
        asyncio.create_task(hangup())

    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        content = msg.content
        if isinstance(content, list):
            content = "\n".join("[image]" if isinstance(x, llm.ChatImage) else str(x) for x in content)
        log_queue.put_nowait({"speaker": "user", "message": content, "timestamp": timestamp})

    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        log_queue.put_nowait({"speaker": "agent", "message": msg.content, "timestamp": timestamp})
        try:
            if isinstance(msg.content, str) and any(keyword in msg.content.lower() for keyword in ["travel advisor", "goodbye"]):
                asyncio.create_task(hangup())
        except Exception:
            pass

    async def write_transcription():
        while True:
            msg = await log_queue.get()
            if msg is None:
                call_start_time = transcripts.get("duration", time.time())
                transcripts["duration"] = round(time.time() - call_start_time, 2)
                logger.info(f"final: {transcripts} and duration {transcripts['duration']}")
                break
            transcripts["transcript"].append(msg)

    write_task = asyncio.create_task(write_transcription())

    async def finish_queue():
        # Signal write_transcription to finish and wait for it
        await log_queue.put(None)
        await write_task

        
        try:
            await api.LiveKitAPI().aclose()
        except Exception:
            pass

    ctx.add_shutdown_callback(finish_queue)

    agent.start(ctx.room, participant)

    # Greet
    try:
        await agent.say("Hello! Neha here from Hiring Department. Would you prefer to talk in English or Hindi?", allow_interruptions=True)
    except Exception:
        pass


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="test-agent",
        ),
    )
