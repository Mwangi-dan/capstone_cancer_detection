from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import User, Feedback, Prediction, Notification
from database import db
import pandas as pd
from collections import Counter
from flask import make_response


admin_bp = Blueprint('admin', __name__, template_folder='templates')

def admin_required(view):
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admins only!", "error")
            return redirect(url_for('predict'))
        return view(*args, **kwargs)
    wrapped_view.__name__ = view.__name__
    return login_required(wrapped_view)


@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard():
    from models import User, Prediction, Feedback
    import os
    from datetime import datetime, timedelta

    uploads_path = current_app.config['UPLOAD_FOLDER']
    gradcam_path = current_app.config['GRADCAM_FOLDER']

    # File counts
    num_uploaded_images = len(os.listdir(uploads_path))
    num_gradcam_images = len(os.listdir(gradcam_path))

    # File size stats
    total_upload_size = sum(os.path.getsize(os.path.join(uploads_path, f)) for f in os.listdir(uploads_path))
    total_gradcam_size = sum(os.path.getsize(os.path.join(gradcam_path, f)) for f in os.listdir(gradcam_path))
    total_size_mb = round((total_upload_size + total_gradcam_size) / (1024 * 1024), 2)

    # File types
    file_extensions = [os.path.splitext(f)[1] for f in os.listdir(uploads_path)]
    ext_counts = dict(Counter(file_extensions))

    # Uploads over time (last 7 days)
    past_week = datetime.utcnow() - timedelta(days=7)
    recent_uploads = Prediction.query.filter(Prediction.timestamp >= past_week).all()
    uploads_by_day = Counter([p.timestamp.strftime("%Y-%m-%d") for p in recent_uploads])

    total_users = User.query.count()
    verified_users = User.query.filter_by(is_verified=True).count()
    total_predictions = Prediction.query.count()
    total_feedback = Feedback.query.count()

    retrain_time = None
    retrain_file = os.path.join("last_retrain.txt")
    if os.path.exists(retrain_file):
        with open(retrain_file, "r") as f:
            retrain_time = f.read()

    return render_template(
        'admin/dashboard.html',
        stats={
            "users": total_users,
            "verified": verified_users,
            "predictions": total_predictions,
            "feedback": total_feedback,
            "retrain_time": retrain_time,
            "num_uploaded_images": num_uploaded_images,
            "num_gradcam_images": num_gradcam_images,
            "total_size_mb": total_size_mb,
            "ext_counts": ext_counts,
            "uploads_by_day": uploads_by_day
        }
    )

# -----------------------------
# 2. View & Manage Users
# -----------------------------
@admin_bp.route('/admin/users')
@admin_required
def view_users():
    pending_users = User.query.filter_by(role='clinician', is_verified=False).all()
    verified_users = User.query.filter_by(role='clinician', is_verified=True).all()
    return render_template('admin/users.html', pending_users=pending_users, verified_users=verified_users)

@admin_bp.route('/admin/users/verify/<int:user_id>', methods=['POST'])
@admin_required
def verify_user(user_id):
    user = User.query.get(user_id)
    if user and user.role == 'clinician':
        user.is_verified = True
        notification = Notification(
            user_id=user.id,
            message="Your account has been verified. You can now access the prediction tool."
        )
        db.session.add(notification)

        db.session.commit()
        log_action(current_user.id, "Verified User", f"Verified user ID {user.id} - {user.name}")
        flash(f"Clinician {user.name} has been verified.", "success")
    return redirect(url_for('admin.view_users'))

@admin_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        if user.role == 'admin':
            flash("Cannot delete admin accounts.", "error")
        else:
            db.session.delete(user)
            db.session.commit()
            flash(f"User {user.name} deleted.", "warning")
    return redirect(url_for('admin.view_users'))


@admin_bp.route("/admin/users/<int:user_id>")
@admin_required
def view_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    predictions = Prediction.query.filter_by(user_id=user_id).order_by(Prediction.timestamp.desc()).all()
    feedbacks = Feedback.query.filter_by(user_id=user_id).order_by(Feedback.timestamp.desc()).all()

    correct = sum(1 for f in feedbacks if f.is_correct)
    incorrect = len(feedbacks) - correct

    return render_template("admin/user_detail.html", user=user, predictions=predictions, feedbacks=feedbacks, correct=correct, incorrect=incorrect)



@admin_bp.route('/admin/export/users')
@admin_required
def export_users():
    users = User.query.all()
    data = [{
        "ID": u.id,
        "Name": u.name,
        "Email": u.email,
        "Verified": u.is_verified,
        "Institution": u.institution,
        "License": u.license_number,
        "Role": u.role
    } for u in users]

    df = pd.DataFrame(data)
    csv = df.to_csv(index=False)
    response = make_response(csv)
    response.headers["Content-Disposition"] = "attachment; filename=users.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# -----------------------------
# 3. View Prediction Feedback
# -----------------------------
@admin_bp.route('/admin/feedback')
@admin_required
def view_feedback():
    feedback_list = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    return render_template('admin/feedback.html', feedback_list=feedback_list)


@admin_bp.route('/admin/export/predictions')
@admin_required
def export_predictions():
    predictions = Prediction.query.all()
    data = [{
        "ID": p.id,
        "User": p.user.name,
        "Label": p.label,
        "Confidence": p.confidence,
        "Date": p.timestamp
    } for p in predictions]

    df = pd.DataFrame(data)
    csv = df.to_csv(index=False)
    response = make_response(csv)
    response.headers["Content-Disposition"] = "attachment; filename=predictions.csv"
    response.headers["Content-Type"] = "text/csv"
    return response



@admin_bp.route('/admin/export/feedback')
@admin_required
def export_feedback():
    feedbacks = Feedback.query.all()
    data = [{
        "ID": f.id,
        "User": f.user.name,
        "Prediction ID": f.prediction_id,
        "Correct": f.is_correct,
        "True Label": f.true_label,
        "Submitted": f.timestamp
    } for f in feedbacks]

    df = pd.DataFrame(data)
    csv = df.to_csv(index=False)
    response = make_response(csv)
    response.headers["Content-Disposition"] = "attachment; filename=feedback.csv"
    response.headers["Content-Type"] = "text/csv"
    return response



# -----------------------------
# 4. Filter Incorrect Predictions (for Retraining)
# -----------------------------
@admin_bp.route('/admin/feedback/incorrect')
@admin_required
def view_incorrect_feedback():
    incorrect = Feedback.query.filter_by(is_correct=False).all()
    return render_template('admin/incorrect_feedback.html', feedback_list=incorrect)

# -----------------------------
# 5. Trigger Model Retraining
# -----------------------------
@admin_bp.route('/admin/model/retrain', methods=['GET', 'POST'])
@admin_required
def retrain():
    if request.method == 'POST':
        # Trigger retraining via FastAPI endpoint (example)
        try:
            import requests
            retrain_url = "http://localhost:8000/retrain"  # Update if hosted elsewhere
            res = requests.post(retrain_url)
            if res.status_code == 200:
                log_action(current_user.id, "Triggered Model Retraining")
                flash("Model retraining initiated successfully.", "success")
            else:
                flash(f"Retraining failed: {res.text}", "error")
        except Exception as e:
            flash(f"Error contacting retrain endpoint: {str(e)}", "error")

        return redirect(url_for('admin.retrain'))

    return render_template('admin/retrain.html')

# -----------------------------
# 6. View Logs (Optional)
# -----------------------------
def log_action(user_id, action, metadata=None):
    from models import Log, db
    log = Log(user_id=user_id, action=action, metadata=metadata)
    db.session.add(log)
    db.session.commit()


@admin_bp.route('/admin/logs')
@admin_required
def logs():
    from models import Log
    logs = Log.query.order_by(Log.timestamp.desc()).limit(100).all()
    return render_template("admin/logs.html", logs=logs)


