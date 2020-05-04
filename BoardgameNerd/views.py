import json
import requests
import xmltodict
import time

from .helper.db import create_account, insert_in_collection, delete_from_collection, update_collection
from .helper.form import check_user_login, change_user_password, change_user_mail
from .helper.api import enrich_thumbnail, random_games, wrangle_game
from . import app, HOT_API, SEARCH_API, THING_API, DB
from flask import flash, redirect, render_template, request, session, url_for


@app.route('/')
@app.route('/index')
def index():
    user = session.get('user')
    r = requests.get(HOT_API)
    doc = xmltodict.parse(r.content)
    docs=doc["items"]["item"]

    r = requests.get(HOT_API)
    doc = xmltodict.parse(r.content)
    docs=doc["items"]["item"]

    random_games_list = random_games()

    return render_template("pages/index.html", 
                            docs=docs,
                            random_games=random_games_list,
                            title="Home",
                            user=user)

# login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    user = session.get('user')

    if user is not None:
        user_in_db = DB.users.find_one({"username": session["user"]})
        if user_in_db:
            return render_template("pages/account-page.html", 
                            username=user_in_db.get('username'))

    if request.method == 'POST':
        post_form = request.form
        response = check_user_login(DB, post_form)
        if not response['passwordCorrect']:
            flash("wrong password!")
        elif response['passwordCorrect']:
            flash("succesful logon!")
            return redirect(url_for('collection'))
        else:
            flash("wrong password!")



    return render_template(
        "pages/login.html",
        user=user
    )

# new account page
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    logged_in = True if 'user' in session else False
    user = session.get('user')

    if logged_in:
        user_in_db = DB.users.find_one({"username": session['user']})
        if user_in_db:
            return redirect(url_for('my_account_page', username=user_in_db['username']))

    if request.method == 'POST':
        post_form = request.form
        response = create_account(DB, post_form)
        if response['user_created']:
            flash('You were successfully signed up')
            return redirect(url_for('login'))

    return render_template(
        'pages/registration.html', 
         user=user
    )

# search page
@app.route('/search/<query>', methods=['GET'])
def search(query):
    user = session.get('user')

    r = requests.get(SEARCH_API+query)
    search_results = xmltodict.parse(r.content)
    if search_results["items"].get("item") is None:
        flash("search returned no result")
    else:    
        search_results=search_results["items"]["item"]

        search_ids_to_enrich = [search['@id'] for search in search_results]
        search_results = enrich_thumbnail(search_ids_to_enrich)

    return render_template("pages/search-results.html",  
                            search_results=search_results, 
                            user=user)

# detail boardgame page
@app.route('/game/<id>', methods=['GET', 'POST'])
def game(id):
    user = session.get('user')

    if request.method == 'POST':
        post_form = request.form
        response = insert_in_collection(DB, post_form)
        if response["inserted"]:
            flash("game added to the collection!")
            return redirect(url_for('index'))


    r = requests.get(THING_API+str(id))
    detail = xmltodict.parse(r.content)
    detail = wrangle_game(detail)
    return render_template("pages/detail.html", 
                            detail=detail, 
                            user=user,
                            id=id)

# edit page
@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    user = session.get('user')

    if request.method == 'POST':
        post_form = request.form
        if post_form['type'] == 'delete':
            response = delete_from_collection(DB, post_form)
            if response['deleted']:
                flash("game successfully removed from the collection")
                return redirect(url_for('collection'))
        elif post_form['type'] == 'update':
            response = update_collection(DB, post_form)
            if response['updated']:
                flash("game successfully updated")
                return redirect(url_for('collection'))
  
    detail  = DB.collection.find_one({"username": user, "id":id}) 
    return render_template("pages/edit.html", 
                            detail=detail , 
                            user=user,
                            id=id)

@app.route('/collection', methods=['GET', 'POST'])
def collection():
    user = session.get('user')

    if request.method == 'POST':
        post_form = request.form
        response = delete_from_collection(DB, post_form)
        if response['deleted']:
            flash("game successfully removed from the collection")
            return redirect(url_for('collection'))
    else:
        return render_template("pages/collection.html", 
                                user=user,
                                collections=DB.collection.find({"username":user}))


# log out page
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))



# change password and mail
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = session.get('user')

    if request.method == 'POST':
        post_request = request.form
        if post_request.get('oldemail') != post_request.get('newemail'):
                response = change_user_mail(DB, post_request)
                if response['updated']:
                    flash("mail successfully updated")
        
        if post_request.get('oldpassword') != post_request.get('newpassword'):
                response = change_user_password(DB, post_request)
                if response['updated']:
                    flash("password successfully updated")

    return render_template(
        "pages/settings.html", 
        user=user
    )

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('pages/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    # note that we set the 500 status explicitly
    return render_template('pages/500.html'), 500


