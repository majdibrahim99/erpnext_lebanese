import json

import frappe
from frappe import _
from erpnext.setup.setup_wizard.operations import install_fixtures as fixtures
from erpnext.setup.setup_wizard.operations.install_fixtures import (
	install_defaults as install_defaults_op,
)

LEBANESE_CHART_NAME = "Lebanese Standard Chart of Accounts"
LEBANESE_COUNTRY = "Lebanon"
LEBANESE_CURRENCY = "LBP"


def after_install():
	"""Called after app installation"""
	pass


def _coerce_args(args):
	if isinstance(args, str):
		try:
			args = json.loads(args)
		except Exception:
			args = {}
	elif args is None:
		args = {}

	if not isinstance(args, dict):
		args = dict(args) if hasattr(args, "__dict__") else {}

	return frappe._dict(args)


def _ensure_lebanese_defaults(args_dict):
	if not args_dict.get("chart_of_accounts"):
		args_dict.chart_of_accounts = LEBANESE_CHART_NAME

	chart = (args_dict.get("chart_of_accounts") or "").lower()
	if "lebanese" in chart:
		args_dict.country = LEBANESE_COUNTRY
		args_dict.currency = args_dict.get("currency") or LEBANESE_CURRENCY

	if not args_dict.get("country"):
		args_dict.country = LEBANESE_COUNTRY

	if not args_dict.get("currency"):
		args_dict.currency = LEBANESE_CURRENCY

	return args_dict


def _normalized_args(args):
	return _ensure_lebanese_defaults(_coerce_args(args))


def get_setup_stages(args=None):
	"""
	Override ERPNext's get_setup_stages to ensure Lebanese defaults while keeping
	the standard stage order.
	"""
	args = _normalized_args(args)

	if frappe.db.exists("Company"):
		return [
			{
				"status": _("Wrapping up"),
				"fail_msg": _("Failed to login"),
				"tasks": [{"fn": fin, "args": args, "fail_msg": _("Failed to login")}],
			}
		]

	return [
		{
			"status": _("Installing presets"),
			"fail_msg": _("Failed to install presets"),
			"tasks": [{"fn": stage_fixtures, "args": args, "fail_msg": _("Failed to install presets")}],
		},
		{
			"status": _("Setting up company"),
			"fail_msg": _("Failed to setup company"),
			"tasks": [{"fn": setup_company, "args": args, "fail_msg": _("Failed to setup company")}],
		},
		{
			"status": _("Setting defaults"),
			"fail_msg": _("Failed to setup defaults"),
			"tasks": [{"fn": setup_defaults, "args": args, "fail_msg": _("Failed to setup defaults")}],
		},
		{
			"status": _("Wrapping up"),
			"fail_msg": _("Failed to login"),
			"tasks": [{"fn": fin, "args": args, "fail_msg": _("Failed to login")}],
		},
	]


def stage_fixtures(args):
	"""Install fixtures using ERPNext helpers while forcing Lebanese defaults."""
	args = _normalized_args(args)
	country = args.get("country") or LEBANESE_COUNTRY
	fixtures.install(country)


def setup_company(args):
	"""
	Create the company during the setup wizard. The Lebanese Company override
	will ensure our CoA is installed for both wizard and manual creation flows.
	"""
	frappe.local.flags.allow_unverified_charts = True
	args_dict = _normalized_args(args)

	try:
		fixtures.install_company(args_dict)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		raise

	company_name = args_dict.get("company_name")
	if company_name and not frappe.db.exists("Company", company_name):
		raise frappe.ValidationError(_("Company {0} was not created").format(company_name))


def setup_defaults(args):
	"""Setup defaults after company creation."""
	args_dict = _normalized_args(args)
	install_defaults_op(args_dict)


def fin(args):
	"""Final setup tasks."""
	frappe.local.message_log = []
	login_as_first_user(_normalized_args(args))


def setup_demo(args):
	"""Setup demo data if requested."""
	args_dict = _coerce_args(args)
	if args_dict.get("setup_demo"):
		from erpnext.setup.demo import setup_demo_data

		frappe.enqueue(setup_demo_data, enqueue_after_commit=True, at_front=True)


def login_as_first_user(args):
	"""Impersonate the first user so the setup wizard can redirect to the desk."""
	if args.get("email") and hasattr(frappe.local, "login_manager"):
		frappe.local.login_manager.login_as(args.get("email"))


@frappe.whitelist()
def setup_complete(args=None):
	"""
	Programmatic setup complete - override ERPNext's method.
	This is called via API, so args might be a JSON string.
	"""
	args_dict = _normalized_args(args)

	try:
		stage_fixtures(args_dict)
		setup_company(args_dict)
		setup_defaults(args_dict)
		fin(args_dict)

		return {
			"status": "success",
			"message": "Setup Completed",
			"home_page": "/desk",
		}
	except Exception as exc:
		frappe.db.rollback()
		return {
			"status": "error",
			"message": str(exc),
		}