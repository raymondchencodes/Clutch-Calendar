from flask import Flask, jsonify, request
from flask_cors import CORS
import re

app = Flask(__name__) 
CORS(app)

@app.route("/", methods= ['GET']) 
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

        return {
            "class": chunk[0],
            "days": splitUpDayAndLocation[0], 
            "time": splitUpDayAndLocation[1],
            "location": splitUpDayAndLocation[2],
            "startDate": chunk[-2],
            "endDate": chunk[-1]
        }
    
    def splitSections(chunkClass): # scan through the chunk of course(s) and break up the lectures with subsections
        sections = [] # list to hold all subsections (lectures, labs, recitation, etc)
        current_section = [] # stores lines for one subsection
        section_pattern = re.compile(r'^[A-Z0-9\- ]+\s\d{3,4}-[A-Z0-9]+\s-\s.*') # regex for course name

        for line in chunkClass: 
            if re.match(section_pattern, line):
                if current_section: # if we already collected one, save it first
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
    
        if line.startswith("My Dropped/Withdrawn Courses"): # stopping point for the last class
            if collecting and chunkOfClass: 
                listOfDictionaries.extend(splitSections(chunkOfClass))
            break

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

    return jsonify(listOfDictionaries)

if __name__ == "__main__":
    app.run(debug=True, port=5008)
