import csv
import datetime
from datetime import datetime
from wsgiref.util import FileWrapper

import spacy
import os, io
import pymongo as pymongo
from bson import ObjectId
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse, Http404

from .models import Greeting
from .forms import Form1, Form2

# MONGO_DB_URI = "mongodb://heroku_166t21vc:chbme62a0ama4gda9p203bgs0e@ds113935.mlab.com:13935/heroku_166t21vc?retryWrites=false"
MONGO_DB_URI = "mongodb://" + "user" + ":" + "mongoadmin" + "@" + "mongodb" + ":27017"

myclient = pymongo.MongoClient(MONGO_DB_URI)
# mydb = myclient["heroku_166t21vc"]
mydb = myclient["admin"]


# Create your views here.
def index(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = Form1(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            # process file to DB
            request.session['file1'] = request.FILES['file1']
            request.session['file2_query'] = request.FILES['file2_query']
            request.session['separatore'] = '\n'
            uploadToMongoDB(request.FILES['file1'], request.FILES['file2_query'], request)
            # process label
            request.session["label1"] = form.cleaned_data["label1"]
            request.session["label1_start"] = str(form.cleaned_data["label1_interval"]).split("-")[0]
            request.session["label1_finish"] = str(form.cleaned_data["label1_interval"]).split("-")[1]

            request.session["label2"] = form.cleaned_data["label2"]
            request.session["label2_start"] = str(form.cleaned_data["label2_interval"]).split("-")[0]
            request.session["label2_finish"] = str(form.cleaned_data["label2_interval"]).split("-")[1]

            request.session["label3"] = form.cleaned_data["label3"]
            request.session["label3_start"] = str(form.cleaned_data["label3_interval"]).split("-")[0]
            request.session["label3_finish"] = str(form.cleaned_data["label3_interval"]).split("-")[1]

            # redirect to a new URL:
            return HttpResponseRedirect('/calculatesimilarity/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = Form1()

    return render(request, 'index.html', {'form': form})


# Create your views here.
def index_with_textbox(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = Form2(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            # process file to DB
            request.session['file1'] = form.cleaned_data["file1"]
            request.session['file2_query'] = form.cleaned_data["file2_query"]
            request.session['separatore'] = form.cleaned_data["separatore"]
            uploadToMongoDB2(request.session['file1'], request.session['file2_query'], request)
            # process label
            request.session["label1"] = form.cleaned_data["label1"]
            request.session["label1_start"] = str(form.cleaned_data["label1_interval"]).split("-")[0]
            request.session["label1_finish"] = str(form.cleaned_data["label1_interval"]).split("-")[1]

            request.session["label2"] = form.cleaned_data["label2"]
            request.session["label2_start"] = str(form.cleaned_data["label2_interval"]).split("-")[0]
            request.session["label2_finish"] = str(form.cleaned_data["label2_interval"]).split("-")[1]

            request.session["label3"] = form.cleaned_data["label3"]
            request.session["label3_start"] = str(form.cleaned_data["label3_interval"]).split("-")[0]
            request.session["label3_finish"] = str(form.cleaned_data["label3_interval"]).split("-")[1]

            # redirect to a new URL:
            return HttpResponseRedirect('/calculatesimilarity/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = Form2()

    return render(request, 'index_with_textbox.html', {'form': form})


def uploadToMongoDB(file1, file2, request):
    text_file1 = ""
    text_file2 = ""
    for line in file1:
        text_file1 = text_file1 + str(line.decode("UTF-8"))
    for line in file2:
        text_file2 = text_file2 + str(line.decode("UTF-8"))

    text1_json = {'data': text_file1}
    text2_json = {'data': text_file2}

    f1 = mydb["files"].insert_one(text1_json)
    f2 = mydb["files"].insert_one(text2_json)

    request.session['file1'] = str(f1.inserted_id)
    request.session['file2_query'] = str(f2.inserted_id)

    return True

def uploadToMongoDB2(file1, file2, request):
    text_file1 = ""
    text_file2 = ""
    for line in file1:
        text_file1 = text_file1 + str(line)
    for line in file2:
        text_file2 = text_file2 + str(line)

    text1_json = {'data': text_file1}
    text2_json = {'data': text_file2}

    f1 = mydb["files"].insert_one(text1_json)
    f2 = mydb["files"].insert_one(text2_json)

    request.session['file1'] = str(f1.inserted_id)
    request.session['file2_query'] = str(f2.inserted_id)

    return True

def calculatesimilarity(request):
    file1id = request.session['file1']
    file2id = request.session['file2_query']

    file1 = mydb.get_collection("files").find_one_and_delete({'_id': ObjectId(file1id)})["data"]
    file2 = mydb.get_collection("files").find_one_and_delete({'_id': ObjectId(file2id)})["data"]

    start = datetime.now()

    sim_matrix, colth, rowth, percentage1, percentage2, percentage3, size \
        = similarityMatrix(file1, file2, request, separatore=request.session['separatore'])

    finish = datetime.now()

    return render(request, 'calculatesimilarity.html',
                  {'tempo_di_esecuzione': (finish - start), 'sim_matrix': sim_matrix,
                   'percentage1': f"{(percentage1 * 100) :.2f}", 'percentage2': f"{(percentage2 * 100) :.2f}",
                   'percentage3': f"{(percentage3 * 100) :.2f}", 'size': size})


def similarityMatrix(file1, file2, request, separatore='\n'):
    global c_label1, c_label2, c_label3

    nlp = spacy.load("it_core_news_sm")

    buf1 = io.StringIO(file1).getvalue()
    lines1 = buf1.split(separatore)
    row = len(lines1)

    buf2 = io.StringIO(file2).getvalue()
    lines2 = buf2.split(separatore)
    col = len(lines2)

    sim_matrix = [["string" for x in range(col)] for y in range(row)]
    sim_matrix_val = [[1 for x in range(col)] for y in range(row)]
    i = j = 0
    
    for line1 in lines1:
        j = 0
        for line2 in lines2:
            doc1 = nlp(line1)
            doc2 = nlp(line2)
            val = f"{(doc1.similarity(doc2) * 100) :.2f}"  # calcolo la similarità, la trasformo in percentuale e prendo solo 2 cifre decimali
            sim_matrix_val[i][j] = float(val)
            sim_matrix[i][j] = val2Label(val, request)
            sim_matrix[i][j] = sim_matrix[i][j]
            j = j + 1
        i = i + 1

    tot = c_label1 + c_label2 + c_label3
    percentage1 = c_label1 / tot
    percentage2 = c_label2 / tot
    percentage3 = c_label3 / tot

    write_matrix_on_csv(sim_matrix)
    write_matrix_val_on_csv(sim_matrix_val)

    return sim_matrix, lines1, lines2, percentage1, percentage2, percentage3, (col * row)


def write_matrix_on_csv(matrix):
    fp = open('csv_label.csv', 'w+')
    for line in matrix:
        for cell in line:
            fp.write(str(cell) + ";")
        fp.write("\n")
    fp.close()


def write_matrix_val_on_csv(matrix):
    fp = open('csv_val.csv', 'w+')
    for line in matrix:
        for cell in line:
            fp.write(str(cell) + ";")
        fp.write("\n")
    fp.close()


def download_csv_label(req):
    file_path = os.path.join(settings.MEDIA_ROOT, "csv_label.csv")
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404


def download_csv_val(req):
    file_path = os.path.join(settings.MEDIA_ROOT, "csv_val.csv")
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404


c_label1 = 0
c_label2 = 0
c_label3 = 0


def val2Label(val, request):
    global c_label1, c_label2, c_label3

    if float(request.session["label1_start"]) < float(val) <= float(request.session["label1_finish"]):
        c_label1 += 1
        return request.session["label1"]
    if float(request.session["label2_start"]) < float(val) <= float(request.session["label2_finish"]):
        c_label2 += 1
        return request.session["label2"]
    if float(request.session["label3_start"]) < float(val) <= float(request.session["label3_finish"]):
        c_label3 += 1
        return request.session["label3"]

    return val


def db(request):
    greeting = Greeting()
    greeting.save()

    greetings = Greeting.objects.all()

    return render(request, "db.html", {"greetings": greetings})
