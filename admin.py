"""
Admin routes: dashboard, transaction management, analytics, CSV export.
"""

import csv
import io
import json
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, Response, make_response)
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta

from database.models import db, Transaction, User, AuthenticationLog, FraudLog

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to restrict access to admin users only."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_txns = Transaction.query.count()
    total_users = User.query.filter_by(role='user').count()

    # Risk distribution
    high_risk = Transaction.query.filter_by(risk_level='High').count()
    medium_risk = Transaction.query.filter_by(risk_level='Medium').count()
    low_risk = Transaction.query.filter_by(risk_level='Low').count()

    # Status counts
    approved = Transaction.query.filter_by(status='Approved').count()
    blocked = Transaction.query.filter_by(status='Blocked').count()
    pending = Transaction.query.filter(
        Transaction.status.in_(['Pending OTP', 'Pending MFA', 'Under Review'])
    ).count()

    # Recent suspicious transactions
    suspicious = Transaction.query.filter(
        Transaction.fraud_probability >= 50
    ).order_by(Transaction.timestamp.desc()).limit(20).all()

    # Fraud trend data (last 7 days)
    fraud_trend = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_total = Transaction.query.filter(
            Transaction.timestamp >= day_start,
            Transaction.timestamp < day_end
        ).count()
        day_fraud = Transaction.query.filter(
            Transaction.timestamp >= day_start,
            Transaction.timestamp < day_end,
            Transaction.risk_level == 'High'
        ).count()

        fraud_trend.append({
            'date': day_start.strftime('%b %d'),
            'total': day_total,
            'fraud': day_fraud
        })

    return render_template('admin_dashboard.html',
                           total_txns=total_txns,
                           total_users=total_users,
                           high_risk=high_risk,
                           medium_risk=medium_risk,
                           low_risk=low_risk,
                           approved=approved,
                           blocked=blocked,
                           pending=pending,
                           suspicious=suspicious,
                           fraud_trend=json.dumps(fraud_trend))


@admin_bp.route('/transactions')
@admin_required
def transactions():
    page = request.args.get('page', 1, type=int)
    risk_filter = request.args.get('risk', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    min_amount = request.args.get('min_amount', '', type=str)
    max_amount = request.args.get('max_amount', '', type=str)

    query = Transaction.query

    if risk_filter:
        query = query.filter_by(risk_level=risk_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_from:
        try:
            query = query.filter(Transaction.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Transaction.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            pass
    if min_amount:
        try:
            query = query.filter(Transaction.amount >= float(min_amount))
        except ValueError:
            pass
    if max_amount:
        try:
            query = query.filter(Transaction.amount <= float(max_amount))
        except ValueError:
            pass

    txns = query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=25)

    return render_template('admin_transactions.html', txns=txns,
                           risk_filter=risk_filter, status_filter=status_filter,
                           date_from=date_from, date_to=date_to,
                           min_amount=min_amount, max_amount=max_amount)


@admin_bp.route('/action/<int:txn_id>/<action>')
@admin_required
def transaction_action(txn_id, action):
    txn = Transaction.query.get_or_404(txn_id)

    if action == 'approve':
        txn.status = 'Approved'
        flash(f'Transaction #{txn_id} approved.', 'success')
    elif action == 'block':
        txn.status = 'Blocked'
        flash(f'Transaction #{txn_id} blocked.', 'warning')
    elif action == 'review':
        txn.status = 'Under Review'
        flash(f'Transaction #{txn_id} marked for review.', 'info')
    else:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin.transactions'))

    db.session.commit()
    return redirect(url_for('admin.transactions'))


@admin_bp.route('/export')
@admin_required
def export_csv():
    """Export all transactions as CSV."""
    transactions = Transaction.query.order_by(Transaction.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Transaction ID', 'User ID', 'Amount', 'Location', 'Type',
        'Fraud Probability', 'Risk Level', 'Status', 'Timestamp'
    ])

    for txn in transactions:
        writer.writerow([
            txn.transaction_id, txn.user_id, txn.amount, txn.location,
            txn.type, txn.fraud_probability, txn.risk_level,
            txn.status, txn.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        ])

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=fraud_report.csv'
    return response


@admin_bp.route('/analytics')
@admin_required
def analytics():
    """Detailed fraud analytics page."""
    total_txns = Transaction.query.count()
    total_amount = db.session.query(db.func.sum(Transaction.amount)).scalar() or 0
    avg_fraud_prob = db.session.query(
        db.func.avg(Transaction.fraud_probability)
    ).scalar() or 0

    # Risk distribution
    high = Transaction.query.filter_by(risk_level='High').count()
    medium = Transaction.query.filter_by(risk_level='Medium').count()
    low = Transaction.query.filter_by(risk_level='Low').count()

    # Top locations by fraud
    from sqlalchemy import func
    location_stats = db.session.query(
        Transaction.location,
        func.count(Transaction.transaction_id).label('count'),
        func.avg(Transaction.fraud_probability).label('avg_prob')
    ).group_by(Transaction.location).order_by(
        func.avg(Transaction.fraud_probability).desc()
    ).limit(10).all()

    return render_template('analytics.html',
                           total_txns=total_txns,
                           total_amount=round(total_amount, 2),
                           avg_fraud_prob=round(avg_fraud_prob, 2),
                           high=high, medium=medium, low=low,
                           location_stats=location_stats)
