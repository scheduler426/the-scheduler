# Following the user class diagram
# Basic frame - add in functionality later
# Last updated by: Kaleb Pheifer - 10/21/26

class User: 

    # Initialize a user
    def __init__ (self, user_id: int, email: str, password_hash: str, first_name: str, last_name: str): 
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.first_name = first_name
        self.last_name = last_name
        self.available_slots = [] # Set it default empty vs. set it default all time slots? Should we have a base availability for all users? eg 9am-5pm M-F
        self.group_list = []

    def retrieveAvailabilitySchedule(self): 
        # Retrieve a user's availability schedule
        return self.available_slots

    def updateAvailability(self, time, date): 
        # Update a user's availability schedule using the selected times
        # Needs to input time/date information from the user's selection
        # Account Manager?
        pass

    def clearAvailability(self): 
        # Clear out a user's availability schedule
        # Set as default empty vs. set it default all time slots? 
        pass

    def retrieveScheduledMeetings(self): 
        # Retrieve a user's scheduled meetings from all groups
        # Account Manager?
        pass

    def shareUserMeetings(self): 
        # Send an email containing all user's scheduled meetings as an .ics
        # Account Manager?
        pass

    def uploadICSFile(self, file): 
        # Upload an existing .ics file into a user's schedule and adjust their availability
        # Account Manager?
        pass

    def allowEmailReminders(self): 
        # Allow email reminders for a user's scheduled meeting
        # Maybe a default variable that's turned on? Pass in a boolean here that toggles the attribute
        pass

    def createAccount(self):
        # Create a user account by taking in the inputs from the GUI boxes
        # Account manager?  
        pass

    def logIn(self): 
        # Log a user into their account
        # Account Manager?
        pass

    def logOut(self): 
        # Log a user out of their account
        # Account Manager?
        pass

    def updateProfile(self): 
        # Update a user's profile - Kaleb note: I am assuming this is for name, email, etc.?
        # Account Manager?
        pass

    def recoverPassword(self):
        # Recover/reset a user's password
        # Account Manager?
        pass

    def deleteAccount(self): 
        # Delete a user's account
        # Account Manager?
        pass

    def createGroup(self):
        # Create a group containing the user
        # Probably group manager?
        pass

    def getGroups(self): 
        # Retrieve a user's groups
        return self.group_list