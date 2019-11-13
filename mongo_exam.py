from flask import Flask, render_template,url_for,request,session,redirect, make_response
import pymongo
from datetime import datetime
import time
from hashlib import sha256
import json
import pandas as pd
import xlrd
import smtplib
from email.mime.text import MIMEText

app=Flask(__name__)
app.config['SECRET_KEY'] = b'N\x83Y\x99\x04\xc9\xcfI\xb7\xfc\xce\xd1\xcf\x01\xa8\xccr\xbb&\x1b\x11\xac\xc7V'
app.config['MAX_CONTENT_PATH'] = 1024

client = pymongo.MongoClient("127.0.0.1", 27017)
db = client.mongo_exam

s = smtplib.SMTP_SSL('smtp.gmail.com')
s.set_debuglevel(1)
sender = 'nitte.examinations@gmail.com'
s.login("nitte.examinations@gmail.com", "Nitte@123")

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if request.cookies.get('loggedin') == "True":
        n = len(list(db.question.find()))
        m = len(list(db.student.find()))
        return render_template('teacher.html', loggedin=True,no=str(n),sno=str(m),qno = list(range(n)))
    if request.method == 'POST':
        email = request.form['email']
        pw = sha256(request.form['password'].encode()).hexdigest()
        print(pw)
        a = list(db.teacher.find({"email":email}))
        if len(a) == 0:
            return render_template('teacher.html', msg="Wrong username or password")
        if a[0]['password']:
            n = len(list(db.question.find()))
            m = len(list(db.student.find()))
            resp = make_response(render_template('teacher.html', loggedin=True, no=str(n), sno=str(m), qno=list(range(n))))
            resp.set_cookie('loggedin','True')
            return resp
        else:
            return render_template('teacher.html',stir="Invalid Credentials")
    return render_template('teacher.html')

all_usn = []
@app.route('/student', methods=['GET','POST'])
def student():
    if request.method == 'POST' :
        name = request.form['name']
        usn = request.form['usn']
        print(all_usn)
        students_usn = list(db.student.find({}))
        s_usn = [i['usn'] for i in students_usn]
        print(s_usn)
        if usn in all_usn or usn not in s_usn:
            return render_template('student.html', msg="Invalid Credentials")
        all_usn.append(usn)
        #  db.student.insert({"name":name, "usn":usn})
        resp = make_response(redirect('/test'))
        resp.set_cookie('usn',usn)
        resp.set_cookie('stest','started')
        return resp
    return render_template('student.html')

@app.route('/questions', methods=['GET','POST'])
def questions():
    if request.cookies.get('stest') == "started":
        qu = [list(i.values()) for i in list(db.question.find())]
        return render_template('questions.html', questions=qu, test=True, time=25)
    return redirect('/index')

@app.route('/logout', methods=['GET','POST'])
def logout():
    resp = make_response(redirect('/teacher'))
    resp.set_cookie('loggedin','False')
    return resp

@app.route('/addquestion', methods=['GET','POST'])
def addquestion():
    if request.method == 'POST':
        q = request.form['qname']
        a = request.form['a']
        b = request.form['b']
        c = request.form['c']
        d = request.form['d']
        ans = request.form['answer']
        db.question.insert_one({'q':q,'a':a,'b':b,'c':c,'d':d,'ans':ans})
        return redirect('/teacher')

@app.route('/delq', methods=['GET','POST'])
def delq():
    db.question.remove({})
    return redirect('/teacher')

@app.route('/submit', methods=['GET','POST'])
def submit():
    if request.method == 'POST':
        qu = list(db.question.find())
        answers = [ i['ans'] for i in qu]
        given_answer = []
        for i in range(len(qu)):
            given_answer.append(request.form["answer" + str(i+1)])
        ans = [int(answers[i]==given_answer[i]) for i in range(len(answers))]
        p = (sum(ans)/len(ans))*100
        usn = request.cookies.get('usn')
        db.student.update_one({'usn':usn},{'$set':{'p':str(p)}},upsert=False)
        resp = make_response(render_template('submit.html',percentage=p))
        resp.set_cookie('stest','ended')
        return resp

@app.route('/test',methods = ['GET','POST'])
def test():
    # global START_TIME
    # s1 = START_TIME
    # s2 = time.strftime('%H:%M:%S')
    # FMT = '%H:%M:%S'
    # tdelta = datetime.strptime(s1, FMT) - datetime.strptime(s2, FMT)
    qu = len(list(db.student.find({})))
    return render_template('test.html', n=qu)

@app.route('/dels')
def dels():
    db.student.remove({})
    return redirect('/teacher')

@app.route('/modq', methods= ['GET', 'POST'])
def modq():
    if request.method == "POST":
        quno = request.form['quno']
        return redirect('/modify?no={}'.format(str(quno)))

@app.route('/modify', methods= ['GET', 'POST'])
def modify():
    if request.method == "POST":
        qno = request.form['qno']
        q = request.form['qname']
        a = request.form['a']
        b = request.form['b']
        c = request.form['c']
        d = request.form['d']
        ans = request.form['answer']
        q_id = list(db.question.find({}))[int(qno) - 1]['_id']
        db.question.update_one({'_id':q_id},{'$set':{'q':q,'a':a,'b':b,'c':c,'d':d,'ans':ans}}, upsert=False)
        return redirect('/teacher')
    qu = request.args.get('no')
    c = list(db.question.find({}))
    question=c[int(qu)-1]
    return render_template('modq.html',q=question['q'],a = question['a'],b = question['b'],c = question['a'],d = question['d'],qno=qu)

@app.route('/mite', methods=['GET', 'POST'])
def mite():
    global START_TIME
    if request.method == "POST":
        START_TIME = request.form['tim']
        print(START_TIME)
        return redirect('/teacher')
    return ""


@app.route('/results')
def results():
    data = []
    data_old = [i for i in list(db.student.find({}))]
    for i in data_old:
        del i['_id']
        if i['p'] == None:
            continue
        data.append(i)
    data.sort(key = (lambda x: x['p']))
    return render_template('results.html',sdata=json.dumps(data), loggedin=True)

@app.route('/sendmails', methods=['POST'])
def sendmails():

    students = list(db.student.find({}))

    for student in students:
        #  print(student)
        if student['p']:
            msg = MIMEText("""your ward,{} of usn: {}
                           has secured {}%""".format(student['name'], student['usn'], student['p']))
        else:
            msg = MIMEText("""your ward, {} of usn: {} was absent""".format(student['name'], student['usn']))
        recipients = student['email']
        msg['Subject'] = "Marks"
        msg['From'] = sender
        msg['To'] = recipients
        s.sendmail(sender, recipients, msg.as_string())

    if request.cookies.get('loggedin') == "True":
        n = len(list(db.question.find()))
        m = len(list(db.student.find()))
        return render_template('teacher.html', loggedin=True,no=str(n),sno=str(m),qno = list(range(n)))
    return render_template('teacher.html', loggedin=False,no=str(n),sno=str(m),qno = list(range(n)))


@app.route('/upload', methods = ['POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        filename = f.filename
        checker = filename.endswith(".csv") or filename.endswith(".xlsx")
        if (checker):
            db.student.delete_many({})
            result_list = list()
            f.save(filename)
            if filename.endswith(".csv"):
                df = pd.read_csv(filename)
            if filename.endswith(".xlsx"):
                df = pd.read_excel(filename)
            name, _, _ = filename.partition(".")
            json_filename = name + ".json"
            df.to_json(json_filename)
            jdf = open(json_filename).read()
            data = json.loads(jdf)
            for key in data.keys():
                for data_key in data[key].keys():
                    try:
                        result_list[int(data_key)][key] = data[key][data_key]
                    except IndexError:
                        result_list.append({})
                        result_list[int(data_key)][key] = data[key][data_key]
            for result in result_list:
                db.student.insert(result)

            return render_template("/teacher.html", loggedin=True, uploaded=True)
        return render_template("/teacher.html", loggedin=True, uploaded=False)


@app.errorhandler(404)
def not_found(e):
    return redirect("/index")

if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0')
