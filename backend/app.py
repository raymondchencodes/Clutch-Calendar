from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__) 
CORS(app)  # allow all routes and origins

@app.route("/", methods= ['GET']) 
def home(): 
    return "Flask server is up and running"

@app.route("/preview", methods= ['POST']) 
def preview_schedule():
    textData = request.json.get("data") # one big string from Workday 

    listOfDictionaries = [] # result for API to read
    parseBlock = [] # holds the chunk of relevant information for each class
    collecting = False # tells the loop whether we're inside the chunk of information

    lines = textData.splitlines()

    def processChunk(chunk):
        splitUpDateAndLocation = []
        for part in chunk[4].split("|"):
            singlePart = part.strip()
            splitUpDateAndLocation.append(singlePart)

        return {
            "class": chunk[0],
            "days": splitUpDateAndLocation[0], 
            "time": splitUpDateAndLocation[1],
            "location": splitUpDateAndLocation[2],
            "startDate": chunk[-2],
            "endDate": chunk[-1]
        }
    
    for line in lines:
        line = line.strip()
        if not line: # skip blank lines
            continue
    
        if line == "Quality Graded Credit": # start block
            collecting = True
            parseBlock = [] # reset for next class
            continue
    
        if line == "Opens in new window" and collecting: # end block
            listOfDictionaries.append(processChunk(parseBlock))
            collecting = False
            parseBlock = [] 
            continue

        if collecting: 
            parseBlock.append(line)
    
    if collecting and parseBlock: 
        listOfDictionaries.append(processChunk(parseBlock))

    return jsonify(listOfDictionaries)

if __name__ == "__main__": # ensures that block only runs when script is executed directly
    app.run(debug=True, port=5008)
