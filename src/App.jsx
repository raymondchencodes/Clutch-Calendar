import 'bootstrap/dist/css/bootstrap.min.css';
import {useState} from "react";
import './App.css'
import axios from "axios";

function App() {
  return (
    <div>
      <Hero />
      <div className="pageWrapper">
        <div className="secondPage">
          <MainSection />
          <Footer />
        </div>
      </div>
    </div>
  );
}

function Hero() {
  return (
    <div className = "HeroSection">
      <div>
        <h1 id = "title">Clutch Calendar</h1>
        <h2 id = "headerTwo">Automate your class  duties.</h2>
        <p id="bodyText">
          Syllabus week is already stressful enough. Why make it harder by manually copying 
          your schedule into a calendar? Look no further than Clutch Calendar — a program 
          meant to easily sync your class schedule in a couple of seconds. 
        </p>     
        
        <a href = "#getStarted-nav">
          <button id = "getStartedButton"> Get Started</button>
        </a> 
      </div>

      <div className = "imageRightPanel">
        <img src="/calendar2.png" width="500" height ="400"/>
      </div>
    </div>
  )
}

function MainSection(){
  return (
    <div id = "getStarted-nav" className = "MainSectionComponent">
      <LeftPanel/>
      <RightPanel/>
    </div>    
  );
}

function LeftPanel (){
  return (
    <div className = "leftPanel">
      <h2>Instructions:</h2>
      <p>1. Navigate to your Academics Hub in Workday</p>
      <p>2. Go to Planning & Registration → Current Classes</p>
      <p>3. In the semester you want to import, click the Expand icon 
        (the button with arrows in the upper-right of your enrolled courses)</p>
      <p>4. Press Command + A (Mac) or Ctrl + A (Windows), 
        then Command + C / Ctrl + C to select and copy your schedule</p>
      <p>5. Paste it into the textbox on this page with Command + Shift + V / Ctrl + Shift + V, 
        then click Confirm Schedule!</p>

      <Video />
    </div>
  );
}

function RightPanel (){
  return (
    <div className = "rightPanel"> 
      <h2>Try it out!</h2>
      <p>
        <strong>Note:</strong> If any of your classes do not have a classroom assigned in Workday, 
        the schedule cannot be imported. Please wait until all courses have room locations before using Clutch Calendar.
      </p>

      <Form />
    </div>
  )
}

function Video() {
  return (
    <div className = "videoSection ratio ratio-16x9">
      <iframe 
        src="https://www.loom.com/embed/a00e232d196f4325bdf6f0d239c16f74" 
        title="YouTube video" 
        allowFullScreen></iframe>
    </div>
  )
}

function Form() {

  const [formInput, setFormInput] = useState(""); // stores and updates whatever the user types/pastes into the textarea
  const [schedule, setSchedule] = useState([]); // array of classes that is returned from backend
  const [openPopUp, setOpenPopUp] = useState(false); // if false, pop is hidden (vise versa)

  const handleSubmit = async () => {
    try {
      const response = await axios.post(
        "https://clutch-calendar-backend.onrender.com/preview",
        { data: formInput },
        { withCredentials: false }     
      );

      setSchedule(response.data) 
  
      setOpenPopUp(true); 

    }catch (error) {
      console.error("Error sending schedule: ", error);
    }
  };

  return (
    <div>
      <textarea 
        className = "formBox" 
        placeholder = "Paste your schedule here" 
        onChange = {(event) => setFormInput(event.target.value)}>
      </textarea> {/*event hook updates the form input with whatever is typed/pasted */}
      
      <br></br>
      
      <button id = "formButton" onClick ={handleSubmit}> Confirm Schedule </button>

      {openPopUp && (
        <PopUp schedule={schedule} setOpenPopUp={setOpenPopUp} />
        // give pop up ability to display the schedule and close itself when user clicks X
      )}
    </div>
  )
}

function PopUp({schedule, setOpenPopUp }){ 

  const [isDisabled, setIsDisabled] = useState(false);

  const handleAdd = async () => {
    try {
      setIsDisabled(true); // Disable the button after click
      
      const encodedSchedule = encodeURIComponent(JSON.stringify(schedule));

      window.location.href = `https://clutch-calendar-backend.onrender.com/authorize?schedule=${encodedSchedule}`;

    }catch (error) {
      console.error("Error sending schedule to Google Calendar: ", error);
      setIsDisabled(false);
    }
  };

  let buttonText; // change button text depending on whether or not the button is disabled
  if (isDisabled) {
    buttonText = "Adding...";
  } else {
    buttonText = "Add to Google Calendar";
  }

  return (
    <div className="popUpToConfirm"> 
      <div className="popup-header">
        <h2>Please confirm your schedule.</h2>
        <button id="closeButton" onClick={() => setOpenPopUp(false)}>X</button>
      </div>

      <ul className="popup-list">
        {schedule.map((course, i) => (
          <li key={i}>
            <strong>{course.class}</strong><br /> 
            {course.days} | {course.time}<br />
            {course.location}<br />
            {course.startDate} - {course.endDate}
          </li>
        ))}
      </ul>
      
      <button id="addToCalendarButton" 
        onClick={handleAdd} 
        disabled={isDisabled}
      >
        {buttonText}
      </button>
    </div>
  )
}

function Footer({schedule}){
  return (
    <div className = "footerBox">
      <p>&copy; 2024 Raymond Chen. All Rights Reserved.</p>
        <ul class="footer-links">
          <li><a href="https://clutch-calendar.vercel.app/privacy.html" target="blank" >Privacy Policy</a></li>
          <li><a href="https://clutch-calendar.vercel.app/terms.html" target="blank" >Terms of Service</a></li>
          <li><a href="https://www.linkedin.com/in/raymond-chen-230b16253/" target="blank" >Contact</a></li>
        </ul>
    </div>
  )
}

export default App;
