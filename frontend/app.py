import os
import time
import hashlib
import requests
from io import BytesIO
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for, flash, abort,
    make_response, send_file, send_from_directory
)
from flask_login import (
    LoginManager, login_required, current_user
)
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from database import db
from models import User, Prediction, Feedback, Notification, Log
from auth import auth

from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from flask_login import user_logged_in, user_logged_out



# Load environment variables
load_dotenv()




BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)


UPLOAD_FOLDER = os.path.join(UPLOADS_DIR, "images")
GRADCAM_FOLDER = os.path.join(UPLOADS_DIR, "gradcams")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GRADCAM_FOLDER, exist_ok=True)

# CONFIGURATION
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", "587"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GRADCAM_FOLDER'] = GRADCAM_FOLDER

mail = Mail(app)



# DB & Auth Setup
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)

bcrypt = Bcrypt(app)

FASTAPI_URL = os.getenv("FASTAPI_URL",)

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
from admin.routes import admin_bp
app.register_blueprint(admin_bp)


app.register_blueprint(auth)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if not current_user.is_verified:
        flash("Only verified clinicians can use the prediction tool.", "danger")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        try:
            file = request.files["image"]
            if not file:
                return render_template("predict.html", error="No file selected", show_result=True)

            # Generate anonymized SHA-256 filename
            ext = os.path.splitext(file.filename)[1]
            raw = f"{current_user.id}{time.time()}".encode('utf-8')
            hashname = hashlib.sha256(raw).hexdigest()

            filename = secure_filename(f"{hashname}{ext}")
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(image_path)

            # Send image to FastAPI for prediction
            with open(image_path, "rb") as f:
                files = {"file": (filename, f, file.content_type)}
                res = requests.post(FASTAPI_URL, files=files)

            if res.status_code != 200:
                return render_template("predict.html", error="Prediction failed", show_result=True)

            data = res.json()

            # Rename/move Grad-CAM from temp to persistent
            gradcam_ext = os.path.splitext(data["gradcam_path"])[1]

            gradcam_filename = f"{hashname}_gradcam.jpg"
            new_gradcam_path = os.path.join(GRADCAM_FOLDER, gradcam_filename)
            # os.rename(data["gradcam_path"], new_gradcam_path)
            gradcam_url = f"{FASTAPI_URL.replace('/predict/', '')}/gradcams/{os.path.basename(data['gradcam_path'])}"
            response = requests.get(gradcam_url)
            if response.status_code == 200:
                with open(new_gradcam_path, "wb") as f:
                    f.write(response.content)
            else:
                return render_template("predict.html", error="Failed to download Grad-CAM image from backend", show_result=True)
        

            image_filename = filename
            gradcam_filename = gradcam_filename

            # Save prediction to DB
            prediction = Prediction(
                user_id=current_user.id,
                image_path=image_filename,
                gradcam_path=gradcam_filename,
                label=data["label"],
                confidence=data["confidence"]
            )
            db.session.add(prediction)
            db.session.commit()

            # Prepare data for frontend rendering
            result = {
                "label": data["label"],
                "confidence": data["confidence"],
                "image_filename": filename,
                "gradcam_filename": gradcam_filename,
                "prediction_id": prediction.id
            }

            return render_template("predict.html", result=result, show_result=True)

        except Exception as e:
            return render_template("predict.html", error=str(e), show_result=True)

    return render_template("predict.html", show_result=False)

def log_action(user_id, action, metadata=None):
    log = Log(user_id=user_id, action=action, metadata=metadata)
    db.session.add(log)
    db.session.commit()

# When a user logs in
@user_logged_in.connect_via(app)
def log_user_login(sender, user):
    log_action(user.id, "User Logged In")

# When a user logs out
@user_logged_out.connect_via(app)
def log_user_logout(sender, user):
    log_action(user.id, "User Logged Out")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        user = current_user
        user.name = request.form["name"]

        if not user.is_verified:
            user.email = request.form["email"]
            user.institution = request.form["institution"]
            user.license_number = request.form["license_number"]

        # Optional password update
        new_password = request.form.get("password")
        if new_password:
            from auth import bcrypt
            user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")

        db.session.commit()
        notif = Notification(
            user_id=current_user.id,
            message="You updated your profile information."
        )
        db.session.add(notif)
        db.session.commit()
        flash("Profile updated successfully", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html")



@app.route("/quiz")
@login_required
def quiz():
    return render_template("quiz.html")


@app.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)

    predictions = Prediction.query \
        .filter_by(user_id=current_user.id) \
        .order_by(Prediction.timestamp.desc()) \
        .paginate(page=page, per_page=10)

    # Attach the first feedback to each prediction for easy access
    for p in predictions.items:
        p.feedback = p.feedbacks[0] if p.feedbacks else None

    return render_template("history.html", predictions=predictions)


@app.route("/history/<int:prediction_id>", methods=["GET", "POST"])
@login_required
def view_prediction(prediction_id):
    prediction = Prediction.query.get_or_404(prediction_id)

    if prediction.user_id != current_user.id:
        abort(403)

    feedback = Feedback.query.filter_by(prediction_id=prediction_id, user_id=current_user.id).first()

    if request.method == "POST":
        is_correct = request.form.get("is_correct")
        true_label = request.form.get("true_label") if is_correct == "no" else None

        if feedback:
            feedback.is_correct = (is_correct == "yes")
            feedback.true_label = true_label
            feedback.timestamp = datetime.utcnow()
        else:
            feedback = Feedback(
                user_id=current_user.id,
                prediction_id=prediction_id,
                is_correct=(is_correct == "yes"),
                true_label=true_label
            )
            db.session.add(feedback)

        db.session.commit()
        flash("Feedback saved.", "success")
        return redirect(url_for("view_prediction", prediction_id=prediction_id))

    return render_template("view_prediction.html", prediction=prediction, feedback=feedback)


@app.route('/download/history.pdf')
@login_required
def download_history_pdf():
    from io import BytesIO
    buffer = BytesIO()

    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.timestamp.desc()).all()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Prediction History", styles['Title']))
    elements.append(Spacer(1, 12))

    for p in predictions:
        # Feedback info
        feedback = p.feedbacks[0] if p.feedbacks else None
        feedback_text = "✔️ Agreed" if feedback and feedback.is_correct else f"❌ Disagreed ({feedback.true_label or 'Unspecified'})" if feedback else "No feedback"

        # Core info
        elements.append(Paragraph(f"<b>Date:</b> {p.timestamp.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Paragraph(f"<b>Label:</b> {p.label}", styles['Normal']))
        elements.append(Paragraph(f"<b>Confidence:</b> {round(p.confidence, 3)}", styles['Normal']))
        elements.append(Paragraph(f"<b>Feedback:</b> {feedback_text}", styles['Normal']))
        elements.append(Spacer(1, 6))

        # Image path
        #image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', p.image_path)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], p.image_path)

        if os.path.exists(image_path):
            elements.append(Image(image_path, width=3.5*inch, height=2.5*inch))
            elements.append(Spacer(1, 12))
        else:
            elements.append(Paragraph("<i>Image not available</i>", styles['Normal']))
            elements.append(Spacer(1, 12))

        elements.append(Spacer(1, 6))
        elements.append(Paragraph("<hr/>", styles['Normal']))
        elements.append(Spacer(1, 12))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=prediction-history.pdf'
    return response


@app.route('/download/prediction/<int:prediction_id>.pdf')
@login_required
def download_prediction_pdf(prediction_id):
    from io import BytesIO
    buffer = BytesIO()

    prediction = Prediction.query.get_or_404(prediction_id)
    if prediction.user_id != current_user.id:
        abort(403)
    feedback = prediction.feedbacks[0] if prediction.feedbacks else None

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Prediction Report", styles['Title']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Date: {prediction.timestamp.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Label: {prediction.label}", styles['Normal']))
    elements.append(Paragraph(f"Confidence: {round(prediction.confidence, 3)}", styles['Normal']))
    elements.append(Spacer(1, 12))

    if feedback:
        feedback_text = "✔️ Agreed" if feedback.is_correct else f"❌ Disagreed ({feedback.true_label or 'Unspecified'})"
    else:
        feedback_text = "No feedback provided"
    elements.append(Paragraph(f"Feedback: {feedback_text}", styles['Normal']))
    elements.append(Spacer(1, 16))

    # Add Input Image
    input_image_path = os.path.join(app.config['UPLOAD_FOLDER'], prediction.image_path)
    gradcam_image_path = os.path.join(app.config['GRADCAM_FOLDER'], prediction.gradcam_path)


    if os.path.exists(input_image_path):
        elements.append(Paragraph("Input Image:", styles['Heading3']))
        elements.append(Image(input_image_path, width=4*inch, height=3*inch))
        elements.append(Spacer(1, 12))

    if os.path.exists(gradcam_image_path):
        elements.append(Paragraph("Grad-CAM Visualization:", styles['Heading3']))
        elements.append(Image(gradcam_image_path, width=4*inch, height=3*inch))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=prediction-{prediction.id}.pdf'
    return response




@app.route('/submit_feedback/<int:prediction_id>', methods=['POST'])
@login_required
def submit_feedback(prediction_id):
    # ✅ Ensure the user is a verified clinician
    if not current_user.is_authenticated or not current_user.is_verified:
        flash("Only verified clinicians can submit feedback.", "error")
        return redirect(url_for("predict"))

    # ✅ Retrieve form data
    is_correct_str = request.form.get("is_correct")
    true_label = request.form.get("true_label", "").strip()

    if is_correct_str not in ["yes", "no"]:
        flash("Invalid feedback submission.", "error")
        return redirect(url_for("predict"))

    is_correct = is_correct_str == "yes"

    # ✅ Validate prediction exists
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        flash("Prediction not found.", "error")
        return redirect(url_for("predict"))

    # ✅ Store feedback
    feedback = Feedback(
        user_id=current_user.id,
        prediction_id=prediction_id,
        is_correct=is_correct,
        true_label=true_label if not is_correct else None
    )
    db.session.add(feedback)
    db.session.commit()

    flash("Thank you for your feedback!", "success")
    return redirect(url_for("history"))



@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOADS_DIR, filename)


@app.route("/admin/verify")
@login_required
def verify_users():
    if current_user.role != "admin":
        flash("Unauthorized access", "danger")
        return redirect(url_for("index"))

    unverified_users = User.query.filter_by(is_verified=False).all()
    return render_template("admin_verify.html", users=unverified_users)


@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter(
        (Notification.user_id == current_user.id) | (Notification.user_id == None)
    ).order_by(Notification.timestamp.desc()).all()
    return render_template("notifications.html", notifications=notifs)


@app.route('/notification/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notif = Notification.query.get_or_404(notification_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return '', 204




@app.route("/admin/approve/<int:user_id>")
@login_required
def approve_user(user_id):
    if current_user.role != "admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("index"))

    user = User.query.get(user_id)
    if user:
        user.is_verified = True
        db.session.commit()
        flash(f"User {user.name} has been verified.", "success")
    
    # Send verification email
    # Send email
        try:
            msg = Message("Your Account Has Been Verified",
                          recipients=[user.email])
            msg.body = f"""
Hi {user.name},

Your account has been verified. You can now access the prediction tools on GastroDetect AI.

Thank you for your patience!

– GastroDetect AI Team
"""
            mail.send(msg)
            flash("User verified and email sent.", "success")
        except Exception as e:
            flash(f"Verified but failed to send email: {str(e)}", "warning")

    return redirect(url_for("verify_users"))

    return redirect(url_for("verify_users"))

@app.route("/admin/reject/<int:user_id>")
@login_required
def reject_user(user_id):
    if current_user.role != "admin":
        flash("Unauthorized", "danger")
        return redirect(url_for("index"))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.name} has been deleted.", "success")
    return redirect(url_for("verify_users"))




login_manager.login_message = "Please log in to access this page."




# DB Create
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
