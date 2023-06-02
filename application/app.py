import random
import string

from flask import Flask, render_template, g, request, redirect, url_for
import sqlite3

# on initialise l'application Flask (grâce à un constructeur)
app = Flask(__name__)
# on déclare des constantes (une pour le nom de la db, et l'autre pour éviter les variables magiques)
# variables magiques = variables dont la valeur est toujours même qu'on est obligé de réecrire à chaque occurernce
DATABASE = 'short_urls.db'
SHORTCODE_LENGTH = 5


# on déclare la première route qui sera affichée comme /status dans l'url
# c'est une méthode get, on peut donc juste afficher des valeurs (voir post + tard)
# ici la route permet juste d'afficher sur la page, une phrase
@app.route('/status', methods=['GET'])
def get_status():
    return 'Up and running !'


# cette fonction n'est pas une route, elle permet de se connecter à la bd et de récupérer l'objet bd
# cette fonction sera utilisée lorsque l'on devra effecturer des requêtes sur la base (insert, select, delete...)
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


# autre méthode mais cette fois pour fermer la bd
# à la fermeture de l'application, on si on a l'objet bd, on la ferme (la bd)
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# retour aux routes
# même principe que celle du dessus
# sauf que cette fois elle s'appelle /display
@app.route('/display', methods=['GET'])
def display():
    # on se connecte à la bd (grâce à la méthode ci-dessus)
    conn = get_db().cursor()
    # on va executer une requête select
    # le fetchall permet de 'formater les données récupérer'
    data = conn.execute('SELECT * FROM url').fetchall()
    conn.close()
    # on passe le résultat de la requête à la vue (c'est à dire au template)
    # à ne pas confondre le nom de la variable dans la vue et le nom de la variable locale contenant le résultat ici
    # on simplifier, mettre le même --> évite les confusions
    return render_template('display.html', data=data)


# cette route /add, en plus de la méthode get, possède la méthode post
# cad qu'elle va être appelée à la fois pour afficher des données/une page
# mais également pour récupérer des données utilisateur
@app.route('/add', methods=['GET', 'POST'])
def add():
    conn = get_db().cursor()
    data = conn.execute('SELECT * FROM url').fetchall()

    # dans le cas où on a récupérer une méthode post (pour récupérer une méthode post,
    # ca se passe dans la vue, cad des template, cad le html)
    if request.method == 'POST':
        # on récupère la valeur de chaque champ du formulaire du fichier html
        target_url = str(request.form.get('target_url'))
        short_code = str(request.form.get('short_code'))

        # si ils sont vides
        if target_url == '' or short_code == '':
            # on réaffiche le template avec un message d'erreur
            return render_template('add_form.html', data=data, message='Failed! Les champs sont vides')

        # sinon, on se connecte à la bd et on regarde si on trouve un nom identique
        # le % permet de passer des paramètres issus du python à la bse
        id = conn.execute("SELECT id FROM url WHERE name = '%s'" % short_code).fetchall()
        # si on a au moins 1 resultat, on indique de l'on a deja dans la bd un shortcode similaire
        if len(id) != 0:
            return render_template('add_form.html', data=data, message='Failed! Le short code existe déjà')

        # sinon on insert la valeur dans la bd
        # on retrouve le % pour les paramètres
        conn.execute("INSERT INTO url(url, name, visits) VALUES ('%s', '%s', 0)" % (target_url, short_code))
        # on commit le resultat (on enregiste les données) !!!!!!!!!!!!!! très important
        get_db().commit()

        # on récupère les nouvelles données
        data = conn.execute('SELECT * FROM url').fetchall()

    # on n'oublie pas de fermer le bd
    conn.close()

    # dans tous les cas, on affiche le template
    # si maintenant on va voir dans le fichier add_form.html, présent dans le répertoire templates
    return render_template('add_form.html', data=data, message='')


@app.route('/shorten', methods=['GET', 'POST'])
def shorten():
    conn = get_db().cursor()
    data = conn.execute('SELECT * FROM url').fetchall()
    if request.method == 'POST':
        target_url = str(request.form.get('target_url'))

        alphabet = string.ascii_letters + string.digits
        short_code = ''.join(random.choice(alphabet) for i in range(SHORTCODE_LENGTH))

        if target_url == '' or short_code == '':
            return render_template('add_form.html', data=data, message='Failed! Les champs sont vides')

        id = conn.execute("SELECT id FROM url WHERE name = '%s'" % short_code).fetchall()
        if len(id) != 0:
            return render_template('add_form.html', data=data, message='Failed! Le short code existe déjà')

        conn.execute("INSERT INTO url(url, name, visits) VALUES ('%s', '%s', 0)" % (target_url, short_code))
        get_db().commit()
        data = conn.execute('SELECT * FROM url').fetchall()

    conn.close()
    return render_template('shorten_form.html', data=data, message='')


@app.route('/r/<string:short_code>')
def raccourci(short_code):
    conn = get_db().cursor()
    url = conn.execute("SELECT url FROM url WHERE name = '%s'" % short_code).fetchall()[0][0]
    conn.execute("UPDATE url SET visits = visits + 1 WHERE name = '%s'" % short_code)
    get_db().commit()
    return redirect(url)


@app.route('/delete/<string:short_code>')
def delete(short_code):
    conn = get_db().cursor()
    conn.execute("DELETE FROM url WHERE name = '%s'" % short_code)
    get_db().commit()
    # redirect combiné à url_for permet (comme url_for dans le html) de faire des liens entre les routes
    # ici on se redirige vers la route add
    return redirect(url_for('add'))


# pour la redéfinition des pages d'erreur
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
