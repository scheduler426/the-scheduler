class Group:

    groupId: int
    groupName: str
    description: str
    groupRoster: list[User]
    scheduledMeetings: list[Schedule]
    files: list[File]

    def addMember(member: User):
        if member in groupRoster:
            print(f"{member} is already in the group.")
        else:
            groupRoster.append(member)

    def removeMember(member: User):
        if member in groupRoster:
            groupRoster.remove(member)
        else:
            print(f"{member} is not in the group.")

    def editGroupDetails(newName: str, newDescription: str):
        groupName = newName
        description = newDescription

    def deleteGroup():
        groupId = None
        groupName = None
        description = None
        groupRoster.clear()
        scheduledMeetings.clear()
        files.clear()

    def leaveGroup():
        # Logic for a member to leave the group
        pass


    def retrieveRoster():
        return groupRoster

    def createMeeting(): 
        #adding another meeting through schedule?
        #use a schedule parameter?
        scheduledMeetings.append(Schedule())

    def attachFile(file: File):
        files.append(file)

    def retrieveFile(file: File):
        if file in files:
            return file
        else:
            print(f"{file} is not attached to the group.")

    def removeFile(file: File):
        if file in files:
            files.remove(file)
        else:
            print(f"{file} is not attached to the group.")

    def exportMeetingToICS(meetingId: int): 
        #supposed to use meetingID?
        #further details for next deliverable
        pass

    def notifySchedulingConflict(meetingId: int):
        pass

    def cancelMeeting(meetingId: int):
        # Logic to cancel a meeting based on meetingId
        pass

    def setNotification(meetingId: int):
        # Logic to set a notification for a meeting based on meetingId
        pass





    