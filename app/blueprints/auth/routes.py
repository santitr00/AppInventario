from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, AuditLog
from app.audit import log_event
from app import db

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inventory.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, activo=True).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            log_event(AuditLog.LOGIN_OK, actor=user)
            next_page = request.args.get("next")
            flash(f"Bienvenido, {user.nombre_completo or user.username}.", "success")
            return redirect(next_page or url_for("inventory.index"))

        log_event(
            AuditLog.LOGIN_FAIL,
            nivel=AuditLog.ALERTA,
            actor=username or "(vacío)",
            detalle="Contraseña incorrecta o usuario inactivo/inexistente",
        )
        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_event(AuditLog.LOGOUT)
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))
