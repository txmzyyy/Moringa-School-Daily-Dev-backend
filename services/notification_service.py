from extensions import db
from models.notification import Notification
from models.subscription import Subscription


def create_content_notifications(content):
    subscriptions = Subscription.query.filter_by(category_id=content.category_id).all()
    notifications = []
    for subscription in subscriptions:
        notification = Notification(
            user_id=subscription.user_id,
            content_id=content.id,
            category_id=content.category_id,
            message=f"New content has been posted: {content.title}",
            is_read=False
        )
        db.session.add(notification)
        notifications.append(notification)
    db.session.commit()
    return notifications


def get_user_notifications(user_id):
    return Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()


def mark_notification_as_read(notification_id, user_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not notification:
        return None
    notification.is_read = True
    db.session.commit()
    return notification


def mark_all_notifications_as_read(user_id):
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return notifications