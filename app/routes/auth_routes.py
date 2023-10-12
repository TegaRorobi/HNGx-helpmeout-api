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

GOOGLE_REDIRECT_URL = "https://cofucan.tech/srce/api/google/callback/"
FACEBOOK_REDIRECT_URL = "https://cofucan.tech/srce/api/facebook/callback/"


#Ensuring oauthlib allows http protocol for testing
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

google_sso = GoogleSSO(
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URL
    ) 

facebook_sso = FacebookSSO(
    FACEBOOK_CLIENT_ID,
    FACEBOOK_CLIENT_SECRET,
    FACEBOOK_REDIRECT_URL
)

@auth_router.post("/signup/", response_model=UserResponse)
async def signup_user(
    user: UserAuthentication, db: Session = Depends(get_db)
) -> UserResponse:
    """
    Registers a new user. Registration is not case sensitive. i.e Asanwa and asanwa are the same username

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

        new_user = User(username=user.username.lower(), hashed_password=hashed_password)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()

        return UserResponse(
            message="User registered successfully", status_code=201, username=user.username.lower()
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
    Logs in a user. Login is not case sensitive i.e Asanwa and asanwa are the same username

    Args:
        user (UserAuthentication): The user authentication data.
        request (Request): The request object.
        db (Session, optional): The db session. Defaults to Depends(get_db).

    Returns:
        UserResponse: The response object.
    """
    # checking if the user is currently logged in
    if is_logged_in(request):

        raise HTTPException(
            status_code=401, detail="A user is currently logged in. Logout the current user and try login again."
        )

    needed_user = db.query(User).filter_by(username=user.username.lower()).first()
    db.close()

    if not needed_user:
        raise HTTPException(
            status_code=401, detail="Invalid Username"
        )

    # converting password to array of bytes
    provided_password = user.password

    hashed_password = provided_password.encode("utf-8")

    actual_user_password = needed_user.hashed_password

    # Validating the entered password
    result = bcrypt.checkpw(hashed_password, actual_user_password)

    if not result:
        raise HTTPException(
            status_code=401, detail="Invalid Password."
        )

    # Create Session for User
    request.session["username"] = needed_user.username
    request.session["logged_in"] = True

    return UserResponse(status_code=200, message="Login Successful", username=user.username.lower())


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
    if not is_logged_in(request):
        # User is not logged in, return an error
        raise HTTPException(
            status_code=401, detail="User not logged in"
        )

    del request.session["username"]
    del request.session["logged_in"]

    return LogoutResponse(
        status_code=200, message="User Logged out successfully"
    )

@auth_router.get("/google/login/")
async def google_login():
    """ Generate Login URL and redirect """

    print(LOCAL_GOOGLE_CLIENT_ID, LOCAL_GOOGLE_CLIENT_SECRET)

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
    if is_logged_in(request):
        raise HTTPException(
            status_code=401, detail="A user is currently logged in. Logout the current user and try login again."
        )
    
    with google_sso:
        user = await google_sso.verify_and_process(request)

    if not user:
        raise HTTPException(
            status_code=400, detail="Failed to Login to Google"
        )
    

    user_email = user.email
    user_display_name = user.display_name.lower()

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
    request.session["username"] = user_display_name
    request.session["logged_in"] = True

    return UserResponse (status_code=200, message="User Logged in Successfuly", username=user_display_name)

@auth_router.get("/facebook/login")
async def facebook_login(request: Request):
    """Generate Login for the User"""

    with facebook_sso:
        return await facebook_sso.get_login_redirect()

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


    if is_logged_in(request):
        raise HTTPException(
            status_code=401, detail="A user is currently logged in. Logout the current user and try login again."
        )

    with facebook_sso:
        user = await facebook_sso.verify_and_process(request)
    
    if not user:
        raise HTTPException(
            status_code=400, detail="Failed to Login to Facebook"
        )

    user_mail = user.email
    user_display_name = user.display_name.lower()

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
    request.session["username"] = user_display_name
    request.session["logged_in"] = True

    return UserResponse (status_code=200, message="User Logged in Successfuly", username=user_display_name)