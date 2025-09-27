import frappe

from rockettradeline.api.auth import jwt_required,get_authenticated_user
@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_notifications(limit=20):
	notifications = frappe.db.get_list(
		"Notification Log", fields=["*"], filters={"read": 0, "for_user": get_authenticated_user()}, limit=limit, order_by="modified desc"
	)

	return dict(notifications=notifications or [])


@frappe.whitelist(allow_guest=True)
@jwt_required()
def mark_all_as_read():
	unread_docs_list = frappe.get_all(
		"Notification Log", filters={"read": 0, "for_user": get_authenticated_user()}
	)
	unread_docnames = [doc.name for doc in unread_docs_list]
	if unread_docnames:
		filters = {"name": ["in", unread_docnames]}
		frappe.db.set_value("Notification Log", filters, "read", 1, update_modified=False)

@frappe.whitelist(allow_guest=True)
@jwt_required()
def mark_as_read(docname: str):
	if frappe.flags.read_only:
		return

	if docname:
		frappe.db.set_value("Notification Log", str(docname), "read", 1, update_modified=False)

@frappe.whitelist(allow_guest=True)
@jwt_required()
def trigger_indicator_hide():
	frappe.publish_realtime("indicator_hide", user=frappe.session.user)


def set_notifications_as_unseen(user):
	try:
		frappe.db.set_value("Notification Settings", user, "seen", 0, update_modified=False)
	except frappe.DoesNotExistError:
		return
