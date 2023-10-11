""" This module contains the routes for user authentication. """
import bcrypt
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import os
from app.database import get_db
from app.services.services import is_logged_in, hash_password
from fastapi_sso.sso.google import GoogleSSO
from fastapi_sso.sso.facebook import FacebookSSO
from fastapi.responses import RedirectResponse

from app.models.user_models import (
    User,
    UserResponse,
    UserAuthentication,
    LogoutResponse,
)


from fastapi import(
    Depends, 
    HTTPException,
    status, 
    APIRouter, 
    Request,
)

BASE_URL = "/srce/api"
auth_router = APIRouter(prefix=BASE_URL)

# Load environment variables from .env file
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")

GOOGLE_REDIRECT_URL = "https://cofucan.tech/srce/api/google/login/"
FACEBOOK_REDIRECT_URL = "https://cofucan.tech/srce/api/facebook/login/"

#Ensuring oauthlib allows http protocol for testing
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

google_sso = GoogleSSO(
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URL,
    allow_insecure_http=True
    ) 

facebook_sso = FacebookSSO(
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
    FACEBOOK_REDIRECT_URL,
    allow_insecure_http=True
)

@auth_router.post("/signup/", response_model=UserResponse)
async def signup_user(
    user: UserAuthentication, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Registers a new user.

    Args:
        user (UserAuthentication): The user authentication data.
        db (Session, optional): The db session. Defaults to Depends(get_db).

    Raises:
        HTTPException: If the username is not unique.

    Returns:
        UserResponse: The response object.
    """
    try:
        # converting password to array of bytes
        hashed_password = hash_password(user.password)

        new_user = User(username=user.username, hashed_password=hashed_password)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()

        return UserResponse(
            message="User registered successfully", status_code=201, data=None
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
    Logs in a user.

    Args:
        user (UserAuthentication): The user authentication data.
        request (Request): The request object.
        db (Session, optional): The db session. Defaults to Depends(get_db).

    Returns:
        UserResponse: The response object.
    """
    # checking if the user is currently logged in
    user_is_loggedin = is_logged_in(request)

    if user_is_loggedin:
        return UserResponse(
            status_code=401, message="User Already Logged in", data=None
        )

    needed_user = db.query(User).filter_by(username=user.username).first()

    if not needed_user:
        return UserResponse(status_code=403, message="Invalid User", data=None)

    # converting password to array of bytes
    provided_password = user.password

    hashed_password = provided_password.encode("utf-8")

    actual_user_password = needed_user.hashed_password

    # Validating the entered password
    result = bcrypt.checkpw(hashed_password, actual_user_password)

    if not result:
        return UserResponse(
            status_code=403, message="Invalid Password.", data=None
        )

    # Create Session for User
    request.session["username"] = needed_user.username
    request.session["logged_in"] = True

    db.close()

    return UserResponse(status_code=200, message="Login Successful", data=None)


@auth_router.post("/logout/")
async def logout_user(
    request: Request, _: Session = Depends(get_db)
) -> LogoutResponse:
    """
    Logs out a user.

    Args:
        request (Request): The request object.
        _ (Session, optional): The db session. Defaults to Depends(get_db).

    Returns:
        LogoutResponse: The response object.
    """
    # checking if the user is currently logged in
    user_is_loggedin = is_logged_in(request)

    if not user_is_loggedin:
        # User is not logged in, return an error
        return LogoutResponse(status_code=401, message="User not logged in")

    del request.session["username"]
    del request.session["logged_in"]

    return LogoutResponse(
        status_code=200, message="User Logged out successfully"
    )

@auth_router.get("/google/login/")
async def google_login():
    """ Generate Login URL and redirect """

    with google_sso:
        return await google_sso.get_login_redirect()

@auth_router.get("/google/callback/")
async def google_callback(request: Request, db: Session = Depends(get_db)) -> UserResponse:
    """
    Process Login response from Google and return user info
    
    Args:
    -   request: The HTTPS request object 
        db: The database session object

    Return:
    -   UserResponse: A response containing success or failure message when user tries to login with their google account 
    """

    # checking if the user is currently logged in
    user_is_loggedin = is_logged_in(request)

    if user_is_loggedin:
        return UserResponse(
            status_code=401, message="A User is Already Logged in", data=None
        )
    
    with google_sso:
        user = await google_sso.verify_and_process(request)

    if not user:
        UserResponse(status_code=400, message="Failed to Login from Google", data=None)

    user_email = user.email

    #Check if the user is in the database
    user_in_db = db.query(User).filter_by(username= user_email).first()

    #Adds the user to the db if the user doesn't exist
    if not user_in_db:
        password = hash_password(user_email)
        new_user = User(username=user_email, hashed_password=password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()

    # Create Session for User
    request.session["username"] = user_email
    request.session["logged_in"] = True

    return UserResponse (status_code=200, message="User Logged in Successfuly", data=None)

@auth_router.get("/facebook/login")
async def facebook_login(request: Request):
    """Generate Login for the User"""

    with facebook_sso:
        return  await facebook_sso.get_login_redirect()

@auth_router.get("/facebook/callback/")
async def facebook_callback(request: Request,
                            db: Session=Depends(get_db)
                            )->UserResponse:
    """
        Logs in the user to the site using their facebook account

        Args:
        -   request: The request object
        -   db:      The database object

    """

    user_logged_in = is_logged_in(request)

    if user_logged_in:
             return UserResponse(
            status_code=401, message="User Already Logged in", data=None
        )

    with facebook_sso:
        user = await facebook_sso.verify_and_process(request)
    
    if not user:
        UserResponse(status_code=400, message="Failed to Login from Google", data=None)

    user_mail = user.email

    #Check if user exists in database already
    user_in_db = db.query(User).filter_by(username=user_mail).first()

    if not user_in_db:
        password = hash_password(user_mail)
        new_user = User(usernmae=user_mail, hashed_password=password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()
    
    #Create Session for user
    request.session["username"] = user_mail
    request.session["logged_in"] = True

    return UserResponse (status_code=200, message="User Logged in Successfuly", data=None)