#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint, g, request, session, render_template, flash, redirect, url_for
from flaskext.openid import OpenID
from brain.couchviews import *
from brain.helpers import *

auth = Blueprint('auth', __name__)

oid = OpenID()

@auth.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    """ Does the login via OpenID. Has ro call into 'oid.try_login'
        to start the OpenID machinery
    """
    # redirect if already logged in
    if g.user is not None:
        return redirect(oid.get_next_url())
    if request.method == 'GET':
        openid = request.args.get('openid')
        if openid:
            return oid.try_login(openid, ask_for=['email', 'fullname',
                                                  'nickname'])
    return render_template('login.html', next=oid.get_next_url(),
            error=oid.fetch_error())

@oid.after_login
def create_or_login(resp):
    """ Called when OpenID succeeded
    """
    session['openid'] = resp.identity_url
    doc = all_users_view[session['openid']]
    if doc.total_rows > 0:
        user = doc.rows[0]
        session['nickname'] = user['id']
        flash(u'Successfully signed in')
        return redirect(oid.get_next_url())
    return redirect(url_for('.create_profile', next=oid.get_next_url(),
                            name=resp.fullname, nickname=resp.nickname,
                            email=resp.email))

@auth.route('/create-profile', methods=['GET', 'POST'])
def create_profile():
    # if already logged in or no openid url in session
    if g.user is not None or 'openid' not in session:
        return redirect(url_for('.index'))
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        nickname = request.form['nickname']
        if not name:
            flash(u'Error: you have to provide a name')
        elif not nickname:
            flash(u'Error: you have to provide a nickname')
        elif '@' not in email:
            flash(u'Error: you have to provide a valid email address')
        else:
            flash(u'Profil successfully created')
            document = dict(openid=session['openid'], type='user',
                            name=name, email=email, date=get_date(),
                            active='true')
            g.couch[nickname] = document
            return redirect(oid.get_next_url())
    return render_template('create_profile.html', next_url=oid.get_next_url())

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """ Update the profile """
    user = g.couch.get(g.user['nickname'])
    form = dict(name=user['name'], email=user['email'], nickname=user['nickname'])
    if request.method == 'POST':
        if 'delete' in request.form:
            g.couch.delete(g.user)
            session.pop('openid', None)
            flash(u'Profile deleted')
            return redirect(url_for('.index'))
        form['name'] = request.form['name']
        form['email'] = request.form['email']
        form['nickname'] = request.form['nickname']
        if not form['name']:
            flash(u'Error: you have to provide a name')
        elif not form['nickname']:
            flash(u'Error: you have to provide a nickname')
        elif '@' not in form['email']:
            flash(u'Error: you have to provide a valid email address')
        else:
            flash(u'Profile successfully changed')
            user['name'] = form['name']
            user['email'] = form['email'] 
            user['nickname'] = form['nickname']
            g.couch.save(user)
            return redirect(url_for('.edit_profile'))
    return render_template('edit_profile.html', form=form)

@auth.route('/logout')
def logout():
    """ Logout, deletes Session """
    session.pop('openid', None)
    session.pop('nickname', None)
    flash(u'You were signed out')
    return redirect(oid.get_next_url())
