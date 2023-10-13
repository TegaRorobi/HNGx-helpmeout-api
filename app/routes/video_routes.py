""" Video routes for the FastAPI application. """
import base64
import datetime
import json
import os
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_models import User
from app.models.video_models import Video, VideoBlob
from app.models.user_models import LogoutResponse
from app.services.mail_service import send_video
from app.services.services import (
    save_blob,
    merge_blobs,
    generate_id,
    process_video,
    hash_password,
    is_owner,
)

router = APIRouter(prefix="/srce/api")

@router.get("/")
async def home():
    return {"Message": "NOTHING LIKE 127.0.0.1"}

@router.post("/start-recording/")
def start_recording(
    username: str,
    db: Session = Depends(get_db),
):
    """
    Start the recording process.

    Args:
        username (str): The username of the user.
        db (Session, optional): The database session. Default
            Depends(get_db).

    Returns:
        dict: A dictionary containing the success message and video ID.

    Raises:
        None
    """

    # Check if the user exists
    if not db.query(User).filter(User.username == username).first():
        password = "asdfghjk"
        hashed_password = hash_password(password)
        new_user = User(username=username, hashed_password=hashed_password)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    video_id = generate_id()
    video_data = Video(
        id=video_id,
        username=username,
        title=f"Untitled Video {video_id}",
    )

    db.add(video_data)
    db.commit()

    return {
        "message": "Recording started successfully",
        "video_id": video_data.id,
    }


@router.post("/upload-blob/")
def upload_video_blob(
    background_tasks: BackgroundTasks,
    request: Request,
    video_data: VideoBlob,
    db: Session = Depends(get_db),
):
    """
    Uploads a video blob to the server.

    Args:
        background_tasks (BackgroundTasks): The background tasks object.
        video_data (VideoBlob): The json data containing video information
        Db (Session, optional): The database session.
            Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the success message and video data
            if applicable.

    Raises:
        None
    """
    # Query the database for the video id
    video = db.query(Video).filter(Video.id == video_data.video_id).first()

    # If the user is not found, raise an exception
    user = db.query(User).filter(User.username == video_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # If the video is not found, raise an exception
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    # If the video is already completed, raise an exception
    if video.status == "completed":
        raise HTTPException(status_code=400, detail="Recording already processed.")

    # Decode the blob data
    blob_data = base64.b64decode(video_data.blob_object)

    # Save the blob
    _ = save_blob(
        video_data.username,
        video_data.video_id,
        video_data.blob_index,
        blob_data,
    )

    # If it's the last blob, merge all blobs and process the video
    if video_data.is_last:
        # Merge the blobs
        video.original_location = merge_blobs(
            video_data.username, video_data.video_id
        )
        if not video.original_location:
            db.close()
            raise HTTPException(status_code=404, detail="No blobs found.")

        video.status = "completed"
        db.commit()

        # Process the video in the background
        background_tasks.add_task(
            process_video,
            video_data.video_id,
            video.original_location,
            video_data.username,
        )

        vid_url = request.url_for("stream_video", video_id=video_data.video_id)
        response = {
            "message": "Blobs received successfully, video is being processed",
            "video_id": video_data.video_id,
            "video_url": str(vid_url),
        }
        db.close()
        return json.dumps(response, indent=2)

    db.close()

    return {"msg": "Chunk received successfully!"}


@router.get("/recording/user/{username}")
def get_videos(username: str, request: Request, db: Session = Depends(get_db)):
    """
    Returns a list of videos associated with the given username.

    Parameters:
        request: The request object
        username (str): The username for which to retrieve the videos.
        request (Request): The FastAPI request object.
        db (Session): The database session.

    Returns:
        List[Video]: A list of Video objects associated with the given
            username, with downloadable URLs instead of absolute paths.
    """

    videos = db.query(Video).filter(Video.username == username).all()

    if not videos:
        raise HTTPException(status_code=404, detail="User Videos not found.")
    
    db.close()

    # Replace the absolute paths with downloadable URLs
    for video in videos:
        video_id = video.id
        video.original_location = str(
            request.url_for("stream_video", video_id=video_id)
        )
        video.thumbnail_location = str(
            request.url_for("get_thumbnail", video_id=video_id)
        )
        video.transcript_location = str(
            request.url_for("get_transcript", video_id=video_id)
        )

    return videos


@router.get("/recording/{video_id}")
def get_video(video_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Retrieve a specific video by its video ID.

    Parameters:
        username (str): The username associated with the video.
        video_id (str): The unique identifier of the video to retrieve.
        db (Session): The database session.

    Returns:
        Video: The Video object corresponding to the provided video_id.

    Raises:
        HTTPException(403): If the video with the given video_id is not public.
        HTTPException(404): If the video with the given video_id is not found.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    db.close()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check if the video is public and if the current user is the owner
    if not video.is_public and not is_owner(request, video.username):
        raise HTTPException(status_code=403, detail="Access denied: Private video or expired public access.")

    # Check if public access period to video has expired,
    # make video private if it has
    if video.is_public and video.public_access_expiry_date:
        current_datetime = datetime.datetime.utcnow()
        if current_datetime >= video.public_access_expiry_date:
            video.is_public = False
            db.add(video)
            db.commit()
            db.close()

    # Replace the absolute paths with downloadable URLs
    video.original_location = str(
        request.url_for("stream_video", video_id=video_id)
    )
    video.thumbnail_location = str(
        request.url_for("get_thumbnail", video_id=video_id)
    )
    video.transcript_location = str(
        request.url_for("get_transcript", video_id=video_id)
    )

    return video


@router.get("/video/{video_id}.mp4")
def stream_video(video_id: str, db: Session = Depends(get_db)):
    """
    Stream a video by its video ID.

    Parameters:
        video_id (str): The ID of the video to be streamed.
        db (Session, optional): The database session. Defaults to the
            result of the get_db function.

    Returns:
        FileResponse: The file response containing the video stream.

    Raises:
        HTTPException: If the video is not found.
    """
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    if video.status == "processing":
        video.original_location = merge_blobs(video.username, video_id)
        if not video.original_location:
            db.close()
            raise HTTPException(status_code=404, detail="No blobs found.")
        video.status = "completed"
        db.commit()
        db.close()

    return FileResponse(video.original_location, media_type="video/mp4")

@router.get("/download/{video_id}")
def download_video(video_id: str, db: Session = Depends(get_db)):
    """
    Triggers download of a video by its video ID.

    Parameters:
        video_id (str): The ID of the video to be streamed.
        db (Session, optional): The database session. Defaults to the
            result of the get_db function.

    Returns:
        FileResponse: The file response containing the video file.

    Raises:
        HTTPException: If the video is not found.
    """
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    if video.status == "processing":
        video.original_location = merge_blobs(video.username, video_id)
        if not video.original_location:
            db.close()
            raise HTTPException(status_code=404, detail="No blobs found.")
        video.status = "completed"
        db.commit()
        db.close()

    return FileResponse(video.original_location, media_type="video/mp4", filename=f"{video.title}.mp4")

@router.get("/transcript/{video_id}.json")
def get_transcript(video_id: str, db: Session = Depends(get_db)):
    """
    Get the transcript for a video by its video ID.

    Parameters:
        video_id (str): The ID of the video to be streamed.
        db (Session, optional): The database session. Defaults to the
            result of the get_db function.

    Returns:
        FileResponse: The file response containing the video stream.

    Raises:
        HTTPException: If the video is not found.
    """
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    if video.status == "processing":
        raise HTTPException(status_code=404, detail="Video not processed yet.")

    db.close()
    return FileResponse(video.transcript_location, media_type="text/plain")


@router.get("/thumbnail/{video_id}.jpeg")
def get_thumbnail(video_id: str, db: Session = Depends(get_db)):
    """
    Get the thumbnail for a video by its video ID.

    Parameters:
        video_id (str): The ID of the video to be streamed.
        db (Session, optional): The database session. Defaults to the
            result of the get_db function.

    Returns:
        FileResponse: The file response containing the video stream.

    Raises:
        HTTPException: If the video is not found.
    """
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    if video.status == "processing":
        raise HTTPException(status_code=404, detail="Video not processed yet.")
    db.close()

    return FileResponse(video.thumbnail_location, media_type="image/jpeg")


@router.patch("/video/{video_id}")
def update_title(video_id: str, title: str, db: Session = Depends(get_db)):
    """
    Updates the title of a video.

    Parameters:
        video_id (str): The ID of the video to be updated.
        title (str): The new title of the video.
        db (Session, optional): The database session. Defaults to the
            result of the get_db function.

    Returns:
        dict: A dictionary with a single key "msg" and the value "Video
            updated successfully!"

    Raises:
        HTTPException: If the video with the specified ID is not found
            in the database.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    video.title = title
    db.commit()
    db.close()
    return {"msg": "Title updated successfully!"}


@router.patch("/videos/transfer/")
def transfer_videos(
    username1: str, username2: str, db: Session = Depends(get_db)
):
    """
    Transfers all videos from one user to another.

    Parameters:
        username1 (str): The username of the user to transfer videos from.
        username2 (str): The username of the user to transfer videos to.
        db (Session, optional): The database session. Defaults to the
            result of the get_db function.

    Returns:
        dict: A dictionary with a single key "msg" and the value "Videos
            transferred successfully!"

    Raises:
        HTTPException: If the user with the specified username is not
            found in the database.
    """
    user1 = db.query(User).filter(User.username == username1).first()
    user2 = db.query(User).filter(User.username == username2).first()

    if not user1:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user2:
        raise HTTPException(status_code=404, detail="User not found.")

    videos = db.query(Video).filter(Video.username == username1).all()
    for video in videos:
        video.username = username2

    db.commit()
    db.close()
    return {"msg": "Videos transferred successfully!"}


@router.delete("/video/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)):
    """
    Deletes a video from the database and removes its associated files
    from the file system.

    Parameters:
        video_id (str): The ID of the video to be deleted.
        db (Session, optional): The database session.
            Defaults to the result of the `get_db` function.

    Returns:
        dict: A dictionary with a single key "msg" and the value "Video
            deleted successfully!"

    Raises:
        HTTPException: If the video with the specified ID is not found
            in the database.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if video:
        if os.path.exists(str(video.original_location)):
            os.remove(str(video.original_location))
        if os.path.exists(str(video.thumbnail_location)):
            os.remove(str(video.thumbnail_location))
        if os.path.exists(str(video.compressed_location)):
            os.remove(str(video.compressed_location))

        db.delete(video)
        db.commit()
        db.close()

        return {"msg": "Video deleted successfully!"}

    db.close()
    raise HTTPException(status_code=404, detail="Video not found.")

# An endpoint to send a vudeo to user's email using fastapi-mail
@router.post("/send-email/{video_id}")
def send_email(
    video_id: str,
    receipient: str,
    db: Session = Depends(get_db),
):
    """
    Sends an email to the user with the video embedded in the email.
    
    Parameters:
        video_id (str): The id of the video to be sent to the user.
        email (str): The email address of the user.
    
    Returns:
        message (str): A message indicating whether the email was sent
            successfully.
    """
    if not video_id or not receipient:
        return None

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")

    if video.status == "processing":
        raise HTTPException(status_code=404, detail="Video not processed yet.")


    try:
        send_video(video.username, video_id, receipient)
        db.close()
    except Exception as e:
        print(e)
        return {"message": "Email not sent!"}, 500

    return {"message": "Email sent successfully!"}
