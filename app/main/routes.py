# -*- coding: utf-8 -*-
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, \
    MessageForm
from app.models import User, Post, Message, Notification
from app.translate import translate
from app.main import bp
from langdetect import detect #language detection
#from textblob import TextBlob #analogue to google`s langdetect

@bp.before_app_request
def before_request():
    '''to do before executing user request'''
    if current_user.is_authenticated:
        current_user.last_seen =  datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())

@bp.route('/', methods = ['GET', 'POST'])
@bp.route('/index', methods = ['GET', 'POST'])
@login_required #blocks page from unauthorized user 
def index():
    form = PostForm()

    if form.validate_on_submit(): #add new posts
        try:
            language = detect(form.post.data)
            #language = TextBlob(form.post.data).detect_language()
        except: #except TranslatorError:
            language = ''

        post = Post(body = form.post.data, author = current_user, 
            language = language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post has been uploaded.'))
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type = int) #paginate messages to show

    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False )

    next_url = url_for('main.index', page = posts.next_num) if posts.has_next \
        else None
    prev_url = url_for('main.index', page = posts.prev_num) if posts.has_prev \
        else None

    return render_template('index.html', title = _('Home'), form = form, 
        posts = posts.items, next_url = next_url, prev_url = prev_url)

@bp.route('/explore')
@login_required
def explore():
    '''Shows posts of every user in blog'''
    page = request.args.get('page', 1, type = int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate( page, 
        current_app.config['POSTS_PER_PAGE'], False )

    next_url = url_for('main.explore', page = posts.next_num) if posts.has_next \
        else None
    prev_url = url_for('main.explore', page = posts.prev_num) if posts.has_prev \
        else None

    return render_template('index.html', title = _('Explore'), 
        posts = posts.items, next_url = next_url, prev_url = prev_url)

@bp.route('/user/<username>') # <..> has dynamic content inside
@login_required
def user(username):
    '''profile page'''
    user = User.query.filter_by(username = username).first_or_404()
    page = request.args.get('page', 1, type = int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page,
        current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.user', username = user.username, page = posts.next_num) \
        if posts.has_next else None
    
    prev_url = url_for('main.user', username = user.username, page = posts.prev_num) \
        if posts.has_prev else None

    form = EmptyForm()

    return render_template('user.html', user = user, posts = posts.items,
        next_url = next_url, prev_url = prev_url, form = form)

@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username = username).first_or_404()
    form = EmptyForm()
    return render_template('user_popup.html', user = user, form = form)

@bp.route('/edit_profile', methods = ['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Changes have been saved'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title = _('Edit Profile'),
        form = form)

@bp.route('/follow/<username>', methods = ['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username = username).first()
        if user is None:
            flash(_('User %(username)s not found.', username = username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username = username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username = username))
        return redirect(url_for('main.user', username = username))
    else:
        return redirect(url_for('main.index'))

@bp.route('/unfollow/<username>', methods = ['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username = username).first()
        if user is None:
            flash(_('User %(username)s not found.', username = username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username = username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s anymore.', 
            username = username))
        return redirect(url_for('main.user', username = username))
    else:
        return redirect(url_for('main.index'))

@bp.route('/translate', methods = ['POST'])
@login_required
def translate_text():
    '''Translates the selected text to the right language. 
    Arguments for translate() are gotten right from the request'''
    return jsonify({'text': translate(request.form['text'], 
                                      request.form['source_language'], 
                                      request.form['dest_language'])})

@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    try:
        page = request.args.get('page', 1, type = int)
        posts, total = Post.search(g.search_form.q.data, page,
            current_app.config['POSTS_PER_PAGE'])
        if total == 0:
            raise
    except: # in case no search results
        flash(_('Unfortunately, no search results for %(q)s.', 
            q = g.search_form.q.data))
        return redirect(url_for('main.explore'))

    if type(total) != int: #then 'dict': {'value': N, 'relation': 'eq'}
        total = total['value']

    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
        next_url=next_url, prev_url=prev_url)

@bp.route('/send_message/<recipient>', methods = ['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author = current_user, recipient = user,
            body = form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username = recipient))
    return render_template('send_message.html', title = _('Send Message'), 
        recipient = recipient, form = form)

@bp.route('/messages')
@login_required
def messages():
    '''show and paginate private messages'''
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type = int)
    messages = current_user.messages_received.order_by( 
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page = messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page = messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages = messages.items, 
        next_url = next_url, prev_url = prev_url)

@bp.route('/notifications')
@login_required
def notifications():
    '''show new notiifcations since the defined moment of time'''
    since = request.args.get('since', 0.0, type = float)
    notifications = current_user.notifications.filter( Notification.timestamp \
        > since).order_by(Notification.timestamp.asc())
    return jsonify([{
            'name': n.name,
            'data': n.get_data(),
            'timestamp': n.timestamp
            } for n in notifications])

@bp.route('/export_posts')
@login_required
def export_posts():
    '''export all posts into local file'''
    if current_user.get_task_in_progress('export_posts'):
        flash(_('An export task is currently in progress'))
    else:
        current_user.launch_task('export_posts', _('Exporting posts...'))
        db.session.commit()
    return redirect(url_for('main.user', username = current_user.username))
