from flask import Flask, redirect, request, session, jsonify
from flask_cors import CORS
from datetime import datetime
from googleCalendarHelper import createEvent
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import re
import os
import json

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # tell OAuth library to allow HTTP

app = Flask(__name__) 
app.secret_key = "random_secret_key"

FRONTEND_ORIGINS = [
    "https://clutch-calendar.vercel.app",
    "http://localhost:5174",  
]

app.config.update(
    SESSION_COOKIE_SAMESITE = "None", # allow cookie to be cross-site
    SESSION_COOKIE_SECURE = True  
)

CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": FRONTEND_ORIGINS}},
)

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

@app.route("/") 
def home(): 
    return "Flask server is up and running"

@app.route("/preview", methods= ['POST']) 
def preview_schedule():
    textData = request.json.get("data") # one big string from Workday 
    lines = textData.splitlines()

    listOfDictionaries = [] # result for API to read
    chunkOfClass = [] # holds the chunk of relevant information for each class
    collecting = False # tells the loop whether we're inside the chunk of information

    def processChunk(chunk): # takes each course chunk and extracts the relevant information
        splitUpDayAndLocation = []
        for part in chunk[4].split("|"): # split up the day, time, and location
            singlePart = part.strip()
            splitUpDayAndLocation.append(singlePart)

        datePattern = re.compile(r"\d{2}/\d{2}/\d{4}") # find start and end date 
        listOfDates = []
    
        for line in chunk:
            if re.fullmatch(datePattern, line.strip()):
                listOfDates.append(line.strip())
    
        start_date = listOfDates[0]
        end_date = listOfDates[1]
                
        return {
            "class": chunk[0],
            "days": splitUpDayAndLocation[0], 
            "time": splitUpDayAndLocation[1],
            "location": splitUpDayAndLocation[2],
            "startDate": start_date,
            "endDate": end_date
        }
    
    def splitSections(chunkClass): # scan through the chunk of course(s) and break up the lectures with subsections
        sections = [] # list to hold all subsections (lectures, labs, recitation, etc)
        current_section = [] # stores lines for one subsection
        section_pattern = re.compile(r'^[A-Z0-9\- ]+\s\d{3,4}-[A-Z0-9]+\s-\s.*') # regex for course name

        for line in chunkClass: 
            if re.match(section_pattern, line):
                if current_section: # if we find a new section, save the previous one
                    sections.append(processChunk(current_section))
                    current_section = []
            current_section.append(line)

        if current_section: # add the last section leftover
            sections.append(processChunk(current_section))
        return sections
    
    for line in lines:
        line = line.strip()
        if not line: 
            continue

        if line == "Quality Graded Credit": # start block
            collecting = True
            chunkOfClass = [] # reset for next class
            continue
    
        if line == "Opens in new window" and collecting: # end block
            listOfDictionaries.extend(splitSections(chunkOfClass))
            collecting = False
            chunkOfClass = [] 
            continue

        if collecting: 
            chunkOfClass.append(line) # add the lines to make the class chunk
        
    if collecting and chunkOfClass:
        listOfDictionaries.extend(splitSections(chunkOfClass))

    return jsonify(listOfDictionaries)

def formatForGoogle(classes): # takes a list of classes and converts them into Google Calendar event objets
    formattedList = []

    for c in classes:
        startTime, endTime = splitTimeRange(c.get("time",""))
        startDate = c.get("startDate", "")
        endDate = c.get("endDate", "")

        # convert the list of days into a string for event dictionary
        googleDaysList = getByDays(c.get("days", "")) 
        googleDaysString = ",".join(googleDaysList)

        event = {
            "summary": c.get("class", ""), 
            "location": c.get("location", ""),
            "start": {
                "dateTime": convertToIsoFormat(startTime, startDate),
                "timeZone": "America/Chicago"
            },
            "end": {
                "dateTime": convertToIsoFormat(endTime, startDate), 
                "timeZone": "America/Chicago"
            },
            "recurrence": [
                f"RRULE:FREQ=WEEKLY;BYDAY={googleDaysString};UNTIL={convertDateToIso(endDate).replace('-', '')}T000000Z"
            ],
        }
        
        formattedList.append(event)

    return formattedList

def splitTimeRange(timeString): 
    listForStartAndEndTime = []

    for t in timeString.split("-"):
        listForStartAndEndTime.append(t)
    
    if (len(listForStartAndEndTime) == 2):
        return listForStartAndEndTime[0], listForStartAndEndTime[1]
    else:
        return "", ""

def convertToIsoFormat(timeToConvert, dateToConvert): # convert the user-friendly time and date into ISO format for API to read
    isoTime = convertTimeToIso(timeToConvert)
    isoDate = convertDateToIso(dateToConvert)

    return isoDate + "T" + isoTime + ":00"

def convertTimeToIso(originalTime): # 'HH:MM' format 
    cleanUpTime = originalTime.strip().upper().replace(".", "") 
    try:
        timeObject = datetime.strptime(cleanUpTime, "%I:%M %p") # convert string into datetime object

        convertObjectToString = timeObject.strftime("%H:%M") # convert object back into string in 24 hour format
        return convertObjectToString 
    except ValueError: 
        return ""

def convertDateToIso(originalDate): # 'YYYY-MM-DD' format 
    try:
        dateObject = datetime.strptime(originalDate, "%m/%d/%Y")
        return dateObject.strftime("%Y-%m-%d")
    except ValueError:
        return ""
    
def getByDays(days):
    mapForDays = { # abbreviation map for API
        "Mon": "MO",
        "Tue": "TU",
        "Wed": "WE",
        "Thu": "TH",
        "Fri": "FR",
        "Sat": "SA",
        "Sun": "SU"
    }

    breakSlashes = days.split("/")
    cleanedListForDays = []

    for day in breakSlashes: # loop for days of the class
        cleanUpWhiteSpaces = day.strip()

        if cleanUpWhiteSpaces:
            cleanedListForDays.append(cleanUpWhiteSpaces) 

    listForDaysGoogle = []
    for d in cleanedListForDays: # loop for days of the class in Google API format
        abbreviation = mapForDays.get(d[:3], "") # get abbreviation of the day
        if abbreviation:
            listForDaysGoogle.append(abbreviation)

    return listForDaysGoogle

@app.route("/api/google/createEvent", methods=["POST"])
def create_event():
    if "credentials" not in session:
        return jsonify({"error": "Not authorized"}), 401

    creds = Credentials(**session["credentials"]) # converts dict into Credentials objeect
    service = build("calendar", "v3", credentials=creds) # Creates Google Calendar API client

    rawClasses = request.get_json()
    formattedClasses = formatForGoogle(rawClasses)

    for event in formattedClasses:
        try:
            response = service.events().insert(calendarId="primary", body=event).execute() # create event
        except Exception as e:
            print("Failed to create event:", e)

    return jsonify({"message": "Events successfully added!"})

@app.route("/api/saveSchedule", methods=["POST"]) # save schedule before starting OAuth
def save_schedule():
    schedule_data = request.get_json()
    session["pending_schedule"] = schedule_data # saves schedule to the user session
    session.modified = True
    return jsonify({"status": "saved"})

@app.route("/api/checkAuth") # route to check if user has valid credentials
def check_auth():
    authorized = "credentials" in session
    return jsonify({"authorized": authorized})

@app.route("/authorize") # route for redirecting to OAuth Screen
def authorize():

    schedule_param = request.args.get("schedule")
    if schedule_param:
        try:
            schedule_data = json.loads(schedule_param)
            session["pending_schedule"] = schedule_data
            session.modified = True
            print("Saved pending_schedule from query param, count:",
                  len(schedule_data) if isinstance(schedule_data, list) else "n/a")
        except Exception as e:
            print("Failed to parse schedule from query param:", e)

    # clear existing credentials 
    session.pop("credentials", None)
    session.modified = True

    flow = Flow.from_client_config( # creates an OAuth flow with user's Google credentials
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth", # location to Google's login page
                "token_uri": "https://oauth2.googleapis.com/token", # location to exchange codes for tokens
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )

    flow.redirect_uri = REDIRECT_URI # tells Google where to send users after they authorize 
    
    # generate authorization url
    authorization_url, state = flow.authorization_url(
        access_type = "offline", # get referesh token
        prompt = "select_account consent" # force account selection screen
    )

    session["state"] = state # save state to session to prevent CSRF cyber attacks
    session.modified = True 
    return redirect(authorization_url) # redirect user to google's login page

@app.route("/oauth2callback") # route for redirecting from Oauth Screen to backend to exchange tokens and create events
def oauth2callback():
    state = session.get("state") 
    if not state: # check if state from the session matches with the state in URL
        return jsonify({"error": "missing_state"}), 400
    
    flow = Flow.from_client_config( # create flow object again
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(authorization_response=request.url) # exchange authorization code for token

    credentials = flow.credentials # save user credentials to sesssion
    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    session.modified = True

    # now that we have credentials, create the events if schedule was saved
    if "pending_schedule" in session:
        schedule = session["pending_schedule"]
        
        creds = Credentials(**session["credentials"])
        service = build("calendar", "v3", credentials=creds)
        
        formattedClasses = formatForGoogle(schedule)
        
        for event in formattedClasses:
            try:
                response = service.events().insert(calendarId="primary", body=event).execute()
            except Exception as e:
                print("Failed to create event:", e)
        
        # clear the pending schedule
        session.pop("pending_schedule", None)
        session.modified = True
        
        return redirect("https://calendar.google.com/calendar/u/0/r")

    return redirect("https://clutch-calendar.vercel.app/?auth=success") # redirect back to frontend

if __name__ == "__main__":
    app.run(debug=True, port=5001, host = "localhost")