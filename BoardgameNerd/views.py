import json
import requests
import xmltodict
import time

from .helper.db import create_account, insert_in_collection, delete_from_collection, update_collection
from .helper.form import check_user_login, change_user_password, change_user_mail
from .api.api import enrich_thumbnail, random_games, wrangle_game
from . import app, HOT_API, SEARCH_API, THING_API, DB
from flask import flash, redirect, render_template, request, session, url_for


@app.route('/')
def index():
    """Main access to the application
    Returns:
        rendering landing page

    """

    user = session.get('user')
    r = requests.get(HOT_API)
    doc = xmltodict.parse(r.content)
    docs=doc["items"]["item"]

    random_games_list = random_games()

    return render_template("pages/index.html", 
                            docs=docs,
                            random_games=random_games_list,
                            title="Home",
                            user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login Page
    Returns:
        rendering login page

    """
    user = session.get('user')

    if user is not None:
        flash("you are already logged on!")
        return redirect(url_for('collection'))

    if request.method == 'POST':
        post_form = request.form
        response = check_user_login(DB, post_form)
        if response['passwordCorrect']:
            flash({"content": "succesful logon!", })         
            return redirect(url_for('collection'))
        else:
            flash({"content": "wrong user or password!", "background": "bg-danger"})         

    return render_template(
        "pages/login.html",
        user=user
    )

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    """Registration Page
    Returns:
        rendering registration page

    """
    user = session.get('user')

    if user is not None:
        flash({"content": " you are already logged on!", "background": "bg-warning"})         
        return redirect(url_for('collection'))

    if request.method == 'POST':
        post_form = request.form
        response = create_account(DB, post_form)
        if response['user_created']:
            flash({"content": "You were successfully signed up", })         
            return redirect(url_for('login'))
        else:
            flash({"content": "user or mail already exists!", "background": "bg-warning"})         

    return render_template(
        'pages/registration.html', 
         user=user
    )

@app.route('/search', methods=['GET', 'POST'])
@app.route('/search/<query>', methods=['GET', 'POST'])
def search(query=None):
    """Search page
    Args:
        query: word to search for, accept multiple words joined with '+'
    Returns:
        rendering search page results

    """
    from_menu = False
    empty_search = False
    user = session.get('user')

    if query is None and not request.form:
        from_menu = True
        return render_template("pages/search-results.html",  
                        search_results=None, 
                        user=user,
                        empty_search=empty_search,
                        from_menu=from_menu)

    if request.method == 'POST':
        post_request = request.form
        query = post_request.get('query')    

    r = requests.get(SEARCH_API+query)
    search_results = xmltodict.parse(r.content)
    if search_results["items"].get("item") is None:
        empty_search = True
        return render_template("pages/search-results.html",  
                        search_results=None, 
                        user=user,
                        empty_search=empty_search,
                        from_menu=from_menu)       
    else:    
        search_results=search_results["items"]["item"]
        if isinstance(search_results, list):
            search_ids_to_enrich = [search['@id'] for search in search_results]
        else:
            search_ids_to_enrich = [search_results['@id']]
        search_results = enrich_thumbnail(search_ids_to_enrich)

    return render_template("pages/search-results.html",  
                            search_results=search_results, 
                            user=user,
                            from_menu=from_menu)

@app.route('/game/<id>', methods=['GET', 'POST'])
def game(id):
    """game detail page
    Args:
        id: id of the game
    Returns:
        rendering detail page

    """
    user = session.get('user')

    if request.method == 'POST':
        if user is None:
            flash({"content": "please login first to add to you collection!", "background": "bg-danger"})                     
            return redirect(url_for('login'))

        post_form = request.form
        response = insert_in_collection(DB, post_form)
        if response["inserted"]:
            flash({"content": "game added to the collection!", })         
            return redirect(url_for('index'))
        else:
            flash({"content": "this game is already part of your collection!", "background": "bg-warning"})         

    r = requests.get(THING_API+str(id))
    detail = xmltodict.parse(r.content)
    detail = wrangle_game(detail)
    return render_template("pages/detail.html", 
                            detail=detail, 
                            user=user,
                            id=id)

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    """game in collection id page
    Args:
        id: id of the game
    Returns:
        rendering game in collection page

    """
    user = session.get('user')

    if user is None:   
        flash({"content": "please login first to edit your collection!", "background": "bg-danger"})         
        return redirect(url_for('login'))

    if request.method == 'POST':
        post_form = request.form
        if post_form['type'] == 'delete':
            response = delete_from_collection(DB, post_form)
            if response['deleted']:
                flash({"content": "game successfully removed from the collection", })         
                return redirect(url_for('collection'))
        elif post_form['type'] == 'update':
            response = update_collection(DB, post_form)
            if response['updated']:
                flash({"content": "game successfully updated", })         
                return redirect(url_for('collection'))
  
    detail  = DB.collection.find_one({"username": user, "id":id}) 
    return render_template("pages/edit.html", 
                            detail=detail , 
                            user=user,
                            id=id)

@app.route('/collection', methods=['GET', 'POST'])
def collection():
    """user collection page
    Returns:
        collection for logged user

    """
    empty_search = False
    user = session.get('user')

    if user is None:            
        flash({"content": "please login first to see your collection!", "background": "bg-danger"})
        return redirect(url_for('login'))

    if request.method == 'POST':
        post_form = request.form
        response = delete_from_collection(DB, post_form)
        if response['deleted']:
            flash({"content": "game successfully removed from the collection", })
            return redirect(url_for('collection'))
    else:
        collections=DB.collection.find({"username":user})
        if collections.count() == 0:
            empty_search = True
        return render_template("pages/collection.html", 
                                user=user,
                                collections=collections,
                                empty_search = empty_search)


@app.route('/logout')
def logout():
    """logout function
    Returns:
        redirect to index cleaning the session.

    """
    session.clear()
    flash({"content": "successful log-out", })
    return redirect(url_for('index'))



@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """setting pages
    Returns:
        render setting page for logged user

    """
    user = session.get('user')

    if user is None:
        flash({"content": "please login first to see your settings!", "background": "bg-danger"})            
        return redirect(url_for('login'))

    if request.method == 'POST':
        post_request = request.form
        if post_request.get('oldemail') != post_request.get('newemail'):
                response = change_user_mail(DB, post_request)
                if response['updated']:
                    flash({"content": "mail successfully updated", })            
                else:
                    flash({"content": "old mail wrong", "background": "bg-danger"})            
        
        if post_request.get('oldpassword') != post_request.get('newpassword'):
                response = change_user_password(DB, post_request)
                if response['updated']:
                    flash({"content": "password successfully updated", })            
                else:
                    flash({"content": "old password wrong", "background": "bg-danger"})            

    return render_template(
        "pages/settings.html", 
        user=user
    )

@app.errorhandler(404)
def page_not_found(e):
    """not found page
    Args:
        e: exception causing the page to be shown
    Returns:
        render not found page

    """
    return render_template('pages/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """error pages
    Args:
        e: exception causing the page to be shown
    Returns:
        render error page

    """
    return render_template('pages/500.html'), 500

@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    user = session.get('user')

    return render_template(
        "pages/contact.html", 
        active="contact",
        user=user,

    )


