from flask import Flask, request, render_template, session,redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask_pymongo import PyMongo

app = Flask(__name__,template_folder="template")
app.config["MONGO_URI"] = "mongodb://localhost:27017/GroupTalk"
mongo = PyMongo(app)
app.config['SECRET_KEY'] = 'ga@kdh'
socketio = SocketIO(app)

#createdRooms ={}

@app.route('/')
def index():
    return render_template('index.html',message="")



#Route to create room
@app.route('/create', methods=['POST','GET'])
def create():
    if request.method == 'POST':
        #session['roomid'] = request.form.get('roomid')
        #session['username'] = request.form.get('username')
        #createdRooms[session.get('roomid')] = request.form.get('password')
        roomid = request.form.get('roomid')
        password = request.form.get('password')
        #createdRooms[request.form.get('roomid')] = request.form.get('password')
        room = findRoom(roomid)
        #print(room)
        if room:
            return render_template('alert.html',message = "Room already exixts. Please choose other roomid!")
        else:
            mongo.db.RoomsList.insert_one({'Roomid':roomid,'password':password,'no_of_clients':0})
            return render_template('alert.html',message = "Room has been created")
    
    return render_template('createRoom.html')


#Route to login
@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':
        roomid = request.form.get('roomid')
        password = request.form.get('password')
        username = request.form.get('username')
        room = findRoom(roomid)
        if room and room.get('password') == password:
            session['roomid'] = roomid
            session['username'] = username
            return render_template('chat.html', roomid = session.get('roomid'), username = session.get('username'))
        else:
            return render_template('alert.html',message = "Incorrect Roomid or password")
    else:
        if 'username' in session and 'roomid' in session:
            return render_template('chat.html', roomid = session.get('roomid'), username = session.get('username'))
        else:
            return redirect('/')


#Event for joining room
@socketio.on('joined')
def on_join(data):
    #print("Joining Room",session.get('roomid'),data)
    join_room(session.get('roomid'))

    mongo.db.ClientsList.insert_one({'roomid':session.get('roomid'),'username':data['username'],'socketId':data['socketId']})
    clientsInfo = getClients(session.get('roomid'))
    clients =  getClientsList(clientsInfo)
    #print(clients)
    emit('update_members',clients,room=session.get('roomid'))

    no_of_clients = findRoom(session.get('roomid'))['no_of_clients']
    mongo.db.RoomsList.update_one({'Roomid':session.get('roomid')},{"$set":{'no_of_clients':no_of_clients+1}})


#Event for leaving room
@socketio.on('leaving')
def on_leave(data):
    #print('leaving')

    mongo.db.ClientsList.delete_one({'socketId':data['socketId']})
    clientsInfo = getClients(data['roomid'])
    clients = getClientsList(clientsInfo)
    emit('update_members',clients,room=data['roomid'])


    no_of_clients = findRoom(data['roomid'])['no_of_clients']
    #print(no_of_clients)
    if no_of_clients == 1:
        mongo.db.RoomsList.delete_one({'Roomid':data['roomid']})
    else:
        mongo.db.RoomsList.update_one({'Roomid':data['roomid']},{"$set":{'no_of_clients':no_of_clients-1}})
    
    leave_room(data['roomid'])



#Event for recieving message
@socketio.on('message')
def handle_message(message):
    emit('response',{"message":message,"username":session.get('username')},room=session.get('roomid'))

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


#logout route
@app.route('/logout')
def logout():
    session.pop('username')
    session.pop('roomid')
    
    return redirect('/')


#Find Room usign roomid
def findRoom(roomid):
    return mongo.db.RoomsList.find_one({'Roomid':roomid})


#find all clients with same roomid
def getClients(roomid):
    return mongo.db.ClientsList.find({'roomid':roomid})


#Get username and save it in a list from output of getClients() function
def getClientsList(clientsInfo):
    return [client.get('username') for client in clientsInfo]

if __name__=='__main__':
    socketio.run(app,debug=True)