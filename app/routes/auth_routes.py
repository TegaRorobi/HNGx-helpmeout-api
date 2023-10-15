""" This module contains the routes for user authentication. """
import random

import bcrypt
from fastapi import (
    Depends,
    HTTPException,
    APIRouter,
    Request,
)
from fastapi_sso.sso.google import GoogleSSO
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_models import (
    User,
    UserResponse,
    UserAuthentication,
    LogoutResponse,
)
from app.services.mail_service import send_otp
from app.services.services import (
    hash_password,
    is_valid_email,
    is_strong_password,
)
from app.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URL,
)

BASE_URL = "/srce/api"

auth_router = APIRouter(prefix=BASE_URL)

google_sso = GoogleSSO(
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URL
)


@auth_router.post("/signup/", response_model=UserResponse)
async def signup_user(
    user: UserAuthentication, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Registers a new user. Registration is not case sensitive.

    Args:
        user (UserAuthentication): The user authentication data.
        db (Session, optional): The db session. Defaults to Depends(get_db).

    Raises:
        HTTPException: If the username is not unique.

    Returns:
        UserResponse: The response object.
    """

    if not user.email:
        raise HTTPException(status_code=400, detail="Email field is empty")

    if not is_valid_email(user.email):
        raise HTTPException(status_code=400, detail="Not a valid email")

    if not is_strong_password(user.password):
        raise HTTPException(status_code=400, detail="Password not strong")

    try:
        # converting password to array of bytes
        hashed_password = hash_password(user.password)

        new_user = User(
            username=user.username.lower(),
            hashed_password=hashed_password,
            email=user.email,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()

        return UserResponse(
            message="User registered successfully",
            status_code=201,
            username=user.username.lower(),
        )

    except IntegrityError as err:
        raise HTTPException(
            status_code=400, detail="Username is not unique"
        ) from err


@auth_router.post("/login/", response_model=UserResponse)
async def login_user(
    user: UserAuthentication, request: Request, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Logs in a user. Login is not case sensitive

    Args:
        user (UserAuthentication): The user authentication data.
        request (Request): The request object.
        db (Session, optional): The db session. Defaults to Depends(get_db).

    Returns:
        UserResponse: The response object.
    """

    needed_user = (
        db.query(User).filter_by(username=user.username.lower()).first()
    )

    db.close()

    if not needed_user:
        raise HTTPException(status_code=401, detail="Invalid Username")

    # converting password to array of bytes
    provided_password = user.password

    hashed_password = provided_password.encode("utf-8")

    actual_user_password = needed_user.hashed_password

    if _ := bcrypt.checkpw(hashed_password, actual_user_password):
        return UserResponse(
            status_code=200,
            message="Login Successful",
            username=user.username.lower(),
        )
    else:
        raise HTTPException(status_code=401, detail="Invalid Password.")


@auth_router.post("/logout/")
async def logout_user(_: Session = Depends(get_db)) -> LogoutResponse:
    """
    Logs out a user.

    Args:
        _ (Session, optional): The db session. Defaults to Depends(get_db).

    Returns:
        LogoutResponse: The response object.
    """

    return LogoutResponse(
        status_code=200, message="User Logged out successfully"
    )


@auth_router.post("/request_otp/")
async def request_otp(username: str, db: Session = Depends(get_db)):
    """
    Sends a 6-digit code to the user's email address.

    Args:
        username (str): The user's username.
        db (Session, optional): The db session. Defaults to Depends(get_db).
    Returns:
        UserResponse: The response object.
    """
    # check if user exists
    user = db.query(User).filter_by(username=username.lower()).first()

    if not user:
        return UserResponse(
            status_code=404, message="User not found", data=None
        )

    # generate otp
    otp = random.randint(100000, 999999)

    # send otp to user's email address
    send_otp("yiradesat@gmail.com", otp)

    db.close()

    return {
        "status_code": 200,
        "message": "OTP sent successfully",
        "username": username.lower(),
        "verification_code": otp,
    }


@auth_router.post("/change_password/")
async def change_password(
    user: UserAuthentication, request: Request, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Changes the password of a user.

    Args:
        user (UserAuthentication): The user authentication data.
        db (Session, optional): The db session. Defaults to Depends(get_db).

    Returns:
        UserResponse: The response object.
    """
    requested_user = (
        db.query(User).filter_by(username=user.username.lower()).first()
    )

    if not requested_user:
        return UserResponse(
            status_code=404, message="User not found", data=None
        )

    new_password = hash_password(user.password)

    requested_user.hashed_password = new_password

    db.commit()
    db.close()

    return UserResponse(
        status_code=200,
        message="Password changed successfully",
        username=user.username.lower(),
    )


@auth_router.get("/google/login/")
async def google_login():
    """Generate Login URL and redirect"""

    with google_sso:
        return await google_sso.get_login_redirect()


@auth_router.get("/google/callback/")
async def google_callback(
    request: Request, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Process Login response from Google and return user info

    Args:
        request: The HTTPS request object
        db: The database session object

    Return:
        UserResponse: A response containing success or failure message
    """

    with google_sso:
        user = await google_sso.verify_and_process(request)

    if not user:
        raise HTTPException(
            status_code=400, detail="Failed to Login to Google"
        )

    user_email = user.email
    user_display_name = user.display_name.lower()

    # Check if the user is in the database
    user_in_db = db.query(User).filter_by(username=user_email).first()

    # Adds the user to the db if the user doesn't exist
    if not user_in_db:
        password = hash_password(user_email)
        new_user = User(
            username=user_email, hashed_password=password, email=user_email
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()

    return UserResponse(
        status_code=200,
        message="User Logged in Successfully!",
        username=user_display_name,
    )
