from flask import Blueprint, request, redirect, url_for, flash, render_template
from models import User
from database import db
from flask_login import login_user, logout_user, login_required
from flask_bcrypt import Bcrypt

auth = Blueprint("auth", __name__)
bcrypt = Bcrypt()

@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        institution = request.form["institution"]
        license_number = request.form["license_number"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("auth.signup"))
        
        user = User(
            name=name,
            email=email,
            password=password,
            institution=institution,
            license_number=license_number,
            is_verified=False
        )

        db.session.add(user)
        db.session.commit()
        flash("Signup successful! Awaiting verification.", "success")
        return redirect(url_for("auth.login"))
    return render_template("signup.html")

@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('index'))
        flash("Invalid credentials.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("login.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
