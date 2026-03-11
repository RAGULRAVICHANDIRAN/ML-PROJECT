"""
Transaction routes: predict fraud, transaction history, SHAP explanation, MFA verification.
"""

import random
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime

from database.models import db, Transaction, AuthenticationLog, FraudLog

transaction_bp = Blueprint('transaction', __name__)

# Global predictor (set from app.py)
predictor = None

LOCATION_MAP = {
    '1': 'New York', '2': 'Los Angeles', '3': 'Chicago', '4': 'Houston',
    '5': 'Phoenix', '6': 'Philadelphia', '7': 'San Antonio', '8': 'San Diego',
    '9': 'Dallas', '10': 'San Jose', '11': 'Austin', '12': 'Jacksonville',
    '13': 'Fort Worth', '14': 'Columbus', '15': 'Indianapolis',
    '16': 'Charlotte', '17': 'San Francisco', '18': 'Seattle',
    '19': 'Denver', '20': 'Washington DC', '21': 'Mumbai', '22': 'Delhi',
    '23': 'Bangalore', '24': 'London', '25': 'Tokyo'
}

TX_TYPE_MAP = {'0': 'Online Purchase', '1': 'POS Terminal', '2': 'ATM Withdrawal', '3': 'Wire Transfer'}
DEVICE_MAP = {'0': 'Mobile', '1': 'Desktop', '2': 'Tablet'}


class TransactionForm(FlaskForm):
    amount = FloatField('Transaction Amount ($)', validators=[DataRequired(), NumberRange(min=0.01, max=100000)])
    location = SelectField('Transaction Location', choices=[
        ('1', 'New York'), ('2', 'Los Angeles'), ('3', 'Chicago'),
        ('4', 'Houston'), ('5', 'Phoenix'), ('6', 'Philadelphia'),
        ('7', 'San Antonio'), ('8', 'San Diego'), ('9', 'Dallas'),
        ('10', 'San Jose'), ('11', 'Austin'), ('12', 'Jacksonville'),
        ('13', 'Fort Worth'), ('14', 'Columbus'), ('15', 'Indianapolis'),
        ('16', 'Charlotte'), ('17', 'San Francisco'), ('18', 'Seattle'),
        ('19', 'Denver'), ('20', 'Washington DC'), ('21', 'Mumbai'),
        ('22', 'Delhi'), ('23', 'Bangalore'), ('24', 'London'), ('25', 'Tokyo')
    ], validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', choices=[
        ('0', 'Online Purchase'), ('1', 'POS Terminal'),
        ('2', 'ATM Withdrawal'), ('3', 'Wire Transfer')
    ], validators=[DataRequired()])
    prev_tx_frequency = IntegerField('Previous Transaction Frequency (per month)',
                                     validators=[DataRequired(), NumberRange(min=0, max=100)])
    device_type = SelectField('Device Type', choices=[
        ('0', 'Mobile'), ('1', 'Desktop'), ('2', 'Tablet')
    ], validators=[DataRequired()])
    submit = SubmitField('Predict Fraud')


class OTPForm(FlaskForm):
    otp = StringField('Enter OTP', validators=[DataRequired()])
    submit = SubmitField('Verify OTP')


class MFAForm(FlaskForm):
    otp = StringField('OTP Code', validators=[DataRequired()])
    email_code = StringField('Email Verification Code', validators=[DataRequired()])
    biometric = SelectField('Biometric Verification', choices=[
        ('fingerprint', 'Fingerprint Scan'),
        ('face', 'Face Recognition')
    ], validators=[DataRequired()])
    submit = SubmitField('Verify All Factors')


@transaction_bp.route('/dashboard')
@login_required
def dashboard():
    user_txns = Transaction.query.filter_by(user_id=current_user.user_id).order_by(
        Transaction.timestamp.desc()
    ).all()

    total = len(user_txns)
    fraud_count = sum(1 for t in user_txns if t.risk_level == 'High')
    genuine_count = total - fraud_count

    # Get model comparison for dashboard
    model_metrics = {}
    if predictor:
        model_metrics = predictor.get_model_comparison()

    return render_template('dashboard.html',
                           total=total, fraud_count=fraud_count,
                           genuine_count=genuine_count,
                           recent_txns=user_txns[:10],
                           model_metrics=model_metrics)


@transaction_bp.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    form = TransactionForm()
    result = None

    if form.validate_on_submit():
        now = datetime.utcnow()
        features = {
            'amount': float(form.amount.data),
            'location_code': int(form.location.data),
            'transaction_type': int(form.transaction_type.data),
            'prev_tx_frequency': int(form.prev_tx_frequency.data),
            'device_type': int(form.device_type.data),
            'hour': now.hour,
            'day_of_week': now.weekday()
        }

        if predictor is None:
            flash('Model not loaded. Please contact admin.', 'danger')
            return render_template('predict.html', form=form, result=None)

        # Predict
        prediction = predictor.predict(features)
        explanation = predictor.explain(features)

        # Determine initial status based on risk level
        if prediction['risk_level'] == 'Low':
            status = 'Approved'
            auth_type = 'Auto'
        elif prediction['risk_level'] == 'Medium':
            status = 'Pending OTP'
            auth_type = 'OTP'
        else:
            status = 'Pending MFA'
            auth_type = 'MFA'

        # Save transaction
        txn = Transaction(
            user_id=current_user.user_id,
            amount=features['amount'],
            location=LOCATION_MAP.get(form.location.data, 'Unknown'),
            type=TX_TYPE_MAP.get(form.transaction_type.data, 'Unknown'),
            fraud_probability=prediction['probability'],
            risk_level=prediction['risk_level'],
            status=status,
            timestamp=now
        )
        db.session.add(txn)
        db.session.commit()

        # Save auth log
        auth_log = AuthenticationLog(
            transaction_id=txn.transaction_id,
            auth_type=auth_type,
            status='Success' if auth_type == 'Auto' else 'Pending'
        )
        db.session.add(auth_log)

        # Save fraud log with SHAP summary
        fraud_log = FraudLog(
            transaction_id=txn.transaction_id,
            shap_summary=json.dumps(explanation['feature_importance'])
        )
        db.session.add(fraud_log)
        db.session.commit()

        # Generate simulated OTP for session
        if prediction['risk_level'] in ('Medium', 'High'):
            otp = str(random.randint(100000, 999999))
            session['pending_otp'] = otp
            session['pending_txn_id'] = txn.transaction_id
            session['simulated_email_code'] = str(random.randint(100000, 999999))
            flash(f'Simulated OTP sent: {otp}', 'info')
            if prediction['risk_level'] == 'High':
                flash(f'Simulated Email Code: {session["simulated_email_code"]}', 'info')

        result = {
            'transaction_id': txn.transaction_id,
            'probability': prediction['probability'],
            'risk_level': prediction['risk_level'],
            'status': status,
            'explanation': explanation,
            'auth_required': prediction['risk_level'] != 'Low'
        }

    return render_template('predict.html', form=form, result=result)


@transaction_bp.route('/verify-otp/<int:txn_id>', methods=['GET', 'POST'])
@login_required
def verify_otp(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != current_user.user_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('transaction.dashboard'))

    form = OTPForm()
    if form.validate_on_submit():
        stored_otp = session.get('pending_otp', '')
        if form.otp.data == stored_otp:
            txn.status = 'Approved'
            auth_log = AuthenticationLog.query.filter_by(
                transaction_id=txn_id
            ).first()
            if auth_log:
                auth_log.status = 'Success'
            db.session.commit()
            session.pop('pending_otp', None)
            session.pop('pending_txn_id', None)
            flash('OTP verified! Transaction approved.', 'success')
            return redirect(url_for('transaction.dashboard'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')

    return render_template('verify_otp.html', form=form, txn=txn)


@transaction_bp.route('/verify-mfa/<int:txn_id>', methods=['GET', 'POST'])
@login_required
def verify_mfa(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != current_user.user_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('transaction.dashboard'))

    form = MFAForm()
    if form.validate_on_submit():
        stored_otp = session.get('pending_otp', '')
        stored_email = session.get('simulated_email_code', '')

        otp_ok = form.otp.data == stored_otp
        email_ok = form.email_code.data == stored_email
        bio_ok = form.biometric.data in ('fingerprint', 'face')

        if otp_ok and email_ok and bio_ok:
            txn.status = 'Approved'
            auth_log = AuthenticationLog.query.filter_by(
                transaction_id=txn_id
            ).first()
            if auth_log:
                auth_log.status = 'Success'
            db.session.commit()
            session.pop('pending_otp', None)
            session.pop('pending_txn_id', None)
            session.pop('simulated_email_code', None)
            flash('Multi-Factor Authentication verified! Transaction approved.', 'success')
            return redirect(url_for('transaction.dashboard'))
        else:
            errors = []
            if not otp_ok:
                errors.append('Invalid OTP')
            if not email_ok:
                errors.append('Invalid Email Code')
            flash('. '.join(errors) + '.', 'danger')

    return render_template('verify_mfa.html', form=form, txn=txn)


@transaction_bp.route('/block/<int:txn_id>')
@login_required
def block_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != current_user.user_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('transaction.dashboard'))

    txn.status = 'Blocked'
    auth_log = AuthenticationLog.query.filter_by(transaction_id=txn_id).first()
    if auth_log:
        auth_log.status = 'Blocked'
    db.session.commit()
    session.pop('pending_otp', None)
    session.pop('pending_txn_id', None)
    flash('Transaction blocked.', 'warning')
    return redirect(url_for('transaction.dashboard'))


@transaction_bp.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    txns = Transaction.query.filter_by(
        user_id=current_user.user_id
    ).order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=20)
    return render_template('history.html', txns=txns)


@transaction_bp.route('/explain/<int:txn_id>')
@login_required
def explain(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != current_user.user_id and current_user.role != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('transaction.dashboard'))

    fraud_log = FraudLog.query.filter_by(transaction_id=txn_id).first()
    shap_data = {}
    if fraud_log and fraud_log.shap_summary:
        shap_data = json.loads(fraud_log.shap_summary)

    # Regenerate SHAP plot if predictor available
    force_plot_html = ''
    if predictor:
        features = {
            'amount': txn.amount,
            'location_code': list(LOCATION_MAP.keys())[
                list(LOCATION_MAP.values()).index(txn.location)
            ] if txn.location in LOCATION_MAP.values() else 1,
            'transaction_type': list(TX_TYPE_MAP.keys())[
                list(TX_TYPE_MAP.values()).index(txn.type)
            ] if txn.type in TX_TYPE_MAP.values() else 0,
            'prev_tx_frequency': 5,
            'device_type': 0,
            'hour': txn.timestamp.hour,
            'day_of_week': txn.timestamp.weekday()
        }
        # Ensure numeric types
        for k, v in features.items():
            features[k] = int(v) if k != 'amount' else float(v)

        explanation = predictor.explain(features)
        force_plot_html = explanation.get('force_plot_html', '')

    return render_template('explain.html', txn=txn, shap_data=shap_data,
                           force_plot_html=force_plot_html)


@transaction_bp.route('/model-comparison')
@login_required
def model_comparison():
    model_metrics = {}
    best_model = 'Unknown'
    feature_importance_img = None

    if predictor:
        model_metrics = predictor.get_model_comparison()
        best_model = predictor.get_best_model_name()
        feature_importance_img = predictor.get_feature_importance_chart()

    return render_template('model_comparison.html',
                           model_metrics=model_metrics,
                           best_model=best_model,
                           feature_importance_img=feature_importance_img)
