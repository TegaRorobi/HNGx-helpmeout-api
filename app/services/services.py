import asyncio
import glob
import json
import os
import re
import subprocess
from typing import Match
import random

import bcrypt
import nanoid
from deepgram import Deepgram
from fastapi import HTTPException
from fastapi import Request

from app.database import get_db
from app.models.video_models import Video
from app.settings import (
    VIDEO_DIR,
    DEEPGRAM_API_KEY,
    EMAIL_REGEX,
    PASSWORD_REGEX,
)


def process_video(
    video_id: str,
    file_location: str,
    username: str,
):
    """
    Process a video by compressing it and extracting a thumbnail.

    Args:
        video_id (str): The ID of the video.
        file_location (str): The location of the video file.
        username (str): The name of the user.

    Raises:
        HTTPException: If an error occurs.

    Returns:
        None
    """

    # Get a database connection
    db = next(get_db())

    # Query the video by ID
    video = db.query(Video).filter(Video.id == video_id).first()

    # Generate file paths for audio, transcript, and thumbnail
    audio_filename = f"audio_{video_id}"
    audio_location = os.path.join(
        VIDEO_DIR, username, video_id, audio_filename
    )

    transcript_filename = f"transcript_{video_id}"
    transcript_location = os.path.join(
        VIDEO_DIR, username, video_id, transcript_filename
    )

    thumbnail_filename = f"thumbnail_{video_id}"
    thumbnail_location = os.path.join(
        VIDEO_DIR, username, video_id, thumbnail_filename
    )

    try:
        # Extract audio from the video
        audio_location = extract_audio(file_location, audio_location, "mp3")

        # Get the length of the video
        video_length = get_video_length(file_location)

        # Generate transcript using external API
        transcript_location = asyncio.run(
            generate_transcript(
                audio_location, transcript_location, DEEPGRAM_API_KEY, "json"
            )
        )

        # Extract thumbnail from compressed video
        thumbnail_location = extract_thumbnail(
            file_location, thumbnail_location, "jpg"
        )

    except Exception as err:
        # Update the video status to `failed` if an error occurs
        video.status = "failed"
        raise HTTPException(status_code=500, detail=str(err)) from err

    # Update the video status and save the transcript location
    video.video_length = video_length
    video.transcript_location = transcript_location
    video.thumbnail_location = thumbnail_location
    video.status = "completed"

    # Commit changes to the database and close the connection
    db.commit()
    db.close()


def extract_audio(input_path: str, output_path: str, mimetype: str) -> str:
    """
    Extracts the audio from a video using ffmpeg.

    Args:
        input_path (str): The path to the input video.
        output_path (str): The path to the output audio.
        mimetype (str): The mimetype of the output audio.
    """

    output_path = f"{output_path}.{mimetype}"
    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-vn",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "12k",
        output_path,
    ]
    subprocess.run(command, check=True)

    return output_path


def compress_video(
    input_path: str, output_path: str, extension: str = "mp4"
) -> str:
    """
    Compresses a video using ffmpeg.

    Args:
        input_path: The path to the input video.
        output_path: The path to the output video.
        extension: The extension of the output video.

    Returns:
        None

    """
    output_path = f"{output_path}.{extension}"
    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-vcodec",
        "libx264",
        "-crf",
        "28",  # Lower values will have better quality but larger size.
        output_path,
    ]
    subprocess.run(command, check=True)

    return output_path


def get_video_length(video_path: str) -> float:
    """
    Gets the length of a video in seconds.

    Args:
        video_path: The path to the video.

    Returns:
        float: The length of the video in seconds.
    """
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration"]
    result = subprocess.run(
        command + [video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return float(result.stdout.split("\n")[1].split("=")[1])


def extract_thumbnail(
    video_path: str, thumbnail_path: str, extension: str = "jpg"
) -> str:
    """
    Extracts a thumbnail from a video using ffmpeg.

    Args:
        video_path: The path to the input video.
        thumbnail_path: The path to the output thumbnail.
        extension: The extension of the output thumbnail.

    Returns:
        None

    """
    thumbnail_path = f"{thumbnail_path}.{extension}"
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-ss",
        "00:00:02.000",  # Grab a frame at the 2-second mark
        "-vframes",
        "1",
        thumbnail_path,
    ]
    subprocess.run(command, check=True)

    return thumbnail_path


def is_valid_video(file_location: str) -> bool:
    """
    Check if a video file is valid by inspecting its metadata.

    Args:
        file_location (str): The location of the video file.

    Returns:
        bool: True if the video is valid, False otherwise.
    """
    metadata_command = ["ffmpeg", "-i", file_location]
    result = subprocess.run(
        metadata_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    msg = "Invalid data found when processing input"

    return msg not in result.stderr


def create_directory(*args):
    """
    Create a directory or directories.

    Args:
        *args: Variable length argument list of directory paths.

    Returns:
        None
    """
    for path in args:
        # if not is_valid_path(path):
        #     raise ValueError("Invalid directory path")
        # # Use os.path.abspath to get an absolute path.
        # abs_path = os.path.abspath(path)

        # # Ensure the absolute path is within a safe directory.
        # # Our safe directory here is the media directory.
        # safe_root = os.path.abspath(MEDIA_DIR)
        # if not abs_path.startswith(safe_root):
        #     raise ValueError("Path is not allowed")
        # Create the directory if it doesn't exist.
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)


def save_blob(
    username: str, video_id: str, blob_index: int, blob: bytes
) -> str:
    """
    Saves a video blob/chunk.

    Args:
        username: The user associated with the blob.
        video_id: The ID of the video associated with the blob.
        blob_index: The index of the blob.
        blob: The video blob itself.

    Returns:
        The path to the saved blob.
    """
    # Create the directory structure if it doesn't exist
    user_dir = os.path.join(VIDEO_DIR, username)
    video_dir = os.path.join(user_dir, video_id)
    create_directory(user_dir, video_dir)

    # Save the blob
    blob_filename = f"{blob_index}.mp4"
    blob_path = os.path.join(video_dir, blob_filename)
    with open(blob_path, "wb") as f:
        f.write(blob)

    return blob_path


def merge_blobs(username: str, video_id: str) -> str | None:
    """
    Merges video blobs/chunks to form the complete video.

    Args:
        username: The user associated with the blobs.
        video_id: The ID of the video associated with the blobs.

    Returns:
    - The path to the merged video.
    """
    user_dir = os.path.join(VIDEO_DIR, username)
    user_dir = os.path.abspath(user_dir)
    temp_video_dir = os.path.join(user_dir, video_id)
    temp_video_dir = os.path.abspath(temp_video_dir)

    # List all blob files and sort them by their sequence ID
    blob_files = sorted(
        glob.glob(os.path.join(temp_video_dir, "*.mp4")),
        key=lambda x: int(os.path.splitext(os.path.basename(x))[0]),
    )

    # Check if no blobs were found
    if not blob_files:
        return None

    # Merge the blobs
    merged_video_path = os.path.join(temp_video_dir, f"{video_id}.mp4")
    with open(merged_video_path, "wb") as merged_file:
        for blob_file in blob_files:
            with open(blob_file, "rb") as f:
                merged_file.write(f.read())

    return merged_video_path


def generate_id() -> str:
    """
    Generate a unique ID for a video.

    Returns:
        str: A unique ID for a video.
    """

    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    return str(nanoid.generate(size=15, alphabet=alphabet))


def get_transcript(audio_file: str, output_path: str) -> None:
    """
    Generate a transcript for an audio file using Deepgram's API.

    Args:
        audio_file (str): The path to the audio file.
        output_path (str): The path to the output transcript file.
    """
    # Call the async function
    asyncio.run(generate_transcript(audio_file, output_path, DEEPGRAM_API_KEY))


async def generate_transcript(
    audio_file: str, save_to: str, api_key: str, file_format: str = "json"
) -> str:
    """
    Generate a transcript for an audio file using Deepgram's API.

    Args:
        audio_file (str): The path to the audio file.
        save_to (str): The path to the output transcript file.
        api_key (str): The Deepgram API key.
        file_format (str, optional): The format of the output transcript file.
    """
    deepgram = Deepgram(api_key)

    params = {"punctuate": True, "tier": "enhanced", "utterances": True}
    # params = {'smart_format': True, 'utterances': True}
    with open(audio_file, "rb") as audio:
        source = {"buffer": audio, "mimetype": "audio/mp3"}

        response: dict = deepgram.transcription.sync_prerecorded(
            source, params
        )
        deepgram.extra.to_SRT(response)

        transcript_file = f"{save_to}.{file_format}"

        if file_format not in ("srt", "json"):
            raise HTTPException(
                status_code=400, detail="Unsupported file format"
            )

        if file_format == "srt":
            return convert_to_srt(response, transcript_file)
        elif file_format == "json":
            return convert_to_json(response, transcript_file)


def convert_to_srt(transcript_data: dict, output_path: str) -> str:
    """
    Convert a transcript to SRT format.

    Args:
        transcript_data (dict): The transcript data.
        output_path (str): The path to the output SRT file.

    Returns:
        None
    """
    data = transcript_data

    # Extract transcript and word-level information
    _ = data["results"]["channels"][0]["alternatives"][0]["transcript"]
    words = data["results"]["channels"][0]["alternatives"][0]["words"]

    # Create SRT caption file
    srt_file = []

    for i, word_info in enumerate(words):
        start_time = round(word_info["start"], 3)
        end_time = round(word_info["end"], 3)
        word_text = word_info["punctuated_word"]

        srt_entry = f"{i + 1}\n{start_time} --> {end_time}\n{word_text}\n"
        srt_file.append(srt_entry)

    # Save SRT caption file
    with open(output_path, "w", encoding="utf-8") as file:
        file.writelines(srt_file)

    return output_path


def convert_to_json(transcript_data: dict, output_path: str) -> str:
    """
    Convert a transcript to JSON format.

    Args:
        transcript_data (dict): The transcript data.
        output_path (str): The path to the output JSON file.

    Returns:
        None
    """
    data = transcript_data

    # Extract transcript and word-level information
    transcript = data["results"]["channels"][0]["alternatives"][0][
        "transcript"
    ]
    words = data["results"]["channels"][0]["alternatives"][0]["words"]

    # Create JSON file
    json_file = {
        "transcript": transcript,
        "words": words,
    }

    # Save JSON file
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(json_file, file, indent=4)

    return output_path


def hash_password(password: str) -> str:
    """
    Hashes a password.

    Args:
        password (str): The password to be hashed.

    Returns:
        str: The hashed password.
    """
    pw_bytes = password.encode("utf-8")

    # generating the salt
    salt = bcrypt.gensalt()

    # Hashing the password
    return bcrypt.hashpw(pw_bytes, salt)


def get_current_user(request: Request) -> dict:
    """
    Parameters:
        request: The request object.

    Returns:
        dict: The user session
    """
    return request.session


def is_owner(request: Request, video_owner: str) -> bool:
    """
    Checks if the current user is the owner of a video.

    Parameters:
        request: The request object.
        video_owner (str): The username of the video owner.

    Returns:
        bool: True if the current user is the owner; otherwise, False.
    """
    user = get_current_user(request)

    return user.get("username") == video_owner


def is_valid_email(email: str) -> Match[str] | None:
    """
    Checks if the email is valid.

    Parameters:
        email (str): The email address to be validated.

    Returns:
        bool: True if the email is valid; otherwise, False.
    """
    return re.fullmatch(EMAIL_REGEX, email)


def is_strong_password(password: str) -> Match[str] | None:
    """
    Checks if the password is strong.

    Parameters:
        password (str): The password to be validated.

    Returns:
        bool: True if the password is strong; otherwise, False.
    """
    return re.fullmatch(PASSWORD_REGEX, password)


def is_valid_path(path) -> bool:
    """
    Validate a directory path.

    Args:
        path (str): The directory path to validate.

    Returns:
        bool: True if the path is valid, False otherwise.
    """
    # Define a regex pattern for an allowed directory name
    # (alphanumeric, underscores and a single period).
    allowed_pattern = re.compile(r"^[a-zA-Z0-9_.]+$")

    # Ensure the path is a string and does not contain harmful characters.
    if not isinstance(path, str) or not path:
        return False

    # Split the path into components to check for problematic sequences.
    path_components = path.split(os.sep)

    # Check each component of the path.
    for component in path_components:
        # Check for more than one "." character in a component.
        if component.count(".") > 1:
            return False

        # Check for disallowed directory separators.
        if os.sep in component or (os.altsep and os.altsep in component):
            return False

        # Check against the allowlist pattern.
        if not allowed_pattern.match(component):
            return False

    return True


def get_otp() -> int:
    """
    Generates an OTP

    Returns:
        int: Generated OTP
    """

    return random.randint(100000, 999999)
