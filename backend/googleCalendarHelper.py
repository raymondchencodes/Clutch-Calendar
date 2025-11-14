from googleapiclient.discovery import build

def createEvent(eventData, credentials):
    try:
        service = build("calendar", "v3", credentials=credentials)
        response = service.events().insert(calendarId="primary", body=eventData).execute()
        print(f"Event created: {response.get('summary')}")
        return response
    except Exception as e:
        print(f"Failed to create event - {e}")
        return None
