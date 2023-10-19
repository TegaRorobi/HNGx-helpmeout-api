""" This module contains the routes for user authentication. """

import bcrypt
from fastapi import (
    Depends,
    HTTPException,
    APIRouter,
    Request,
)
from fastapi_sso.sso.google import GoogleSSO
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_models import (
    User,
    UserResponse,
    UserAuthentication,
    UserRequest,
    OtpResponse,
)
from app.services.mail_service import send_otp
from app.services.services import (
    hash_password,
    get_otp,
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


@auth_router.post("/get_signup_otp/", response_model=OtpResponse)
async def get_signup_otp(
    user: UserRequest, db: Session = Depends(get_db)
) -> OtpResponse:
    """
    Sends OTP to a new user

    Args:
        user (UserAuthentication): The user authentication data.
        db (Session, optional): The db session. Defaults to Depends(get_db).

    Raises:
        HTTPException: If the username is not unique.

    Returns:
        UserResponse: The response object.
    """

    if (
        db.query(User).filter(func.lower(User.username)
                              == func.lower(user.username)).first()
    ):

        raise HTTPException(status_code=409, detail="Username already exists.")

    otp = get_otp()

    send_otp(recipient_address=user.email, otp=otp, subject="SIGNUP OTP")

    return OtpResponse(
        status_code=200,
        message="OTP sent successfully",
        username=user.username.lower(),
        verification_code=otp,
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
    if (
        db.query(User).filter(func.lower(User.username)
                              == func.lower(user.username)).first()
    ):

        raise HTTPException(status_code=409, detail="Username exists already.")

    # converting password to array of bytes
    hashed_password = hash_password(user.password)

    new_user = User(
        username=user.username,
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


@auth_router.post("/login/", response_model=UserResponse)
async def login_user(
    user: UserAuthentication, _: Request, db: Session = Depends(get_db)
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
        db.query(User).filter(func.lower(User.username)
                              == func.lower(user.username)).first()
    )

    db.close()

    if not needed_user:
        raise HTTPException(status_code=404, detail="Invalid Username")

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


@auth_router.post("/request_otp/")
async def request_otp(
    username: str, db: Session = Depends(get_db)
) -> OtpResponse:
    """
    Sends a 6-digit code to the user's email address.

    Args:
        username (str): The user's username.
        db (Session, optional): The db session. Defaults to Depends(get_db).
    Returns:
        UserResponse: The response object.
    """
    # check if user exists
    user = db.query(User).filter(func.lower(User.username)
                                 == func.lower(username)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # generate otp
    otp = get_otp()

    # send otp to user's email address
    send_otp(
        recipient_address=user.email,
        otp=otp,
        subject="Forgotten Helpmeout Password",
    )

    db.close()

    return OtpResponse(
        status_code=200,
        message="OTP sent successfully",
        username=username.lower(),
        verification_code=otp,
    )


@auth_router.post("/change_password/")
async def change_password(
    user: UserAuthentication, _: Request, db: Session = Depends(get_db)
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
        db.query(User).filter(func.lower(User.username)
                              == func.lower(user.username)).first()
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
    """Generate login url and redirect"""
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
    display_name = user.display_name.lower()

    # Check if a user with the given email exists
    existing_user = db.query(User).filter_by(email=user_email).first()

    # Add user to database if user doesn't exist
    if not existing_user:
        # Validate end ensure unique username
        suffix = 1

        while db.query(User).filter_by(username=display_name).first():
            suffix += 1
            display_name = f"{display_name}_{suffix}"

        password = hash_password(user_email)
        new_user = User(
            email=user_email,
            username=display_name,
            hashed_password=password,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()

    return UserResponse(
        status_code=200,
        message="User Logged in Successfully!",
        username=new_user.username,
    )


# An endpoint ti edit a username given the username
@auth_router.put("/username/{username}/")
async def edit_username(
        username: str, new_username: str, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Edits a user's username.

    Args:
        username (str): The user's username.
        new_username (str): The user's new username
        db: The db session. Defaults to Depends(get_db).

    Returns:
        UserResponse: The response object.

    Raises:
        HTTPException: If the username is not unique.
    """

    user = db.query(User).filter(func.lower(User.username)
                                 == func.lower(username)).first()

    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    if (
        db.query(User).filter(func.lower(User.username)
                              == func.lower(new_username)).first()
    ):
        raise HTTPException(status_code=409, detail="username exists already.")

    user.username = new_username

    db.commit()
    db.refresh(user)
    db.close()

    return {
        "username": user.username,
        "status_code": 200,
        "message": "username updated successfully",
    }
