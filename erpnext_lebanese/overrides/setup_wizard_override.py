import frappe
from frappe import _
from frappe.utils import nowdate
import json

from erpnext.setup.setup_wizard.operations import install_fixtures as fixtures

def after_install():
    """Called after app installation"""
    frappe.log_error("Erpnext Lebanese: after_install called", "App installed successfully")

def get_setup_stages(args=None):
    """
    Override ERPNext's get_setup_stages to include Lebanese setup
    The company creation will automatically trigger chart installation via doc_events hook
    """
    frappe.log_error("Erpnext Lebanese: get_setup_stages called", "Override working!")
    
    # Parse args if it's a string
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            args = {}
    elif args is None:
        args = {}
    
    if frappe.db.sql("select name from tabCompany"):
        # Company already exists, just wrap up
        stages = [
            {
                "status": _("Wrapping up"),
                "fail_msg": _("Failed to login"),
                "tasks": [{"fn": fin, "args": args, "fail_msg": _("Failed to login")}],
            }
        ]
    else:
        # No company exists, run full setup
        # The company creation will automatically install Lebanese chart via doc_events hook
        stages = [
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
                "fail_msg": "Failed to set defaults",
                "tasks": [
                    {"fn": setup_defaults, "args": args, "fail_msg": _("Failed to setup defaults")},
                ],
            },
            {
                "status": _("Wrapping up"),
                "fail_msg": _("Failed to login"),
                "tasks": [{"fn": fin, "args": args, "fail_msg": _("Failed to login")}],
            },
        ]

    return stages

def stage_fixtures(args):
    """Install fixtures - we'll use ERPNext's but can override if needed"""
    from erpnext.setup.setup_wizard.operations import install_fixtures as fixtures
    
    # Parse args if it's a string
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            args = {}
    
    frappe.log_error("Erpnext Lebanese: stage_fixtures called", f"Args type: {type(args)}, Args: {args}")
    
    # Get country from args or use Lebanon as default for Lebanese setup
    country = None
    if isinstance(args, dict):
        country = args.get("country")
        
        # If no country specified but this is a Lebanese setup, default to Lebanon
        if not country:
            chart_of_accounts = args.get('chart_of_accounts', '')
            if 'Lebanon' in chart_of_accounts or 'lebanese' in chart_of_accounts.lower():
                country = "Lebanon"
    
    # If still no country, use a safe default
    if not country:
        country = "United States"  # ERPNext's default
    
    frappe.log_error("Erpnext Lebanese: Installing fixtures for country", country)
    fixtures.install(country)

def setup_company(args):
	"""
	Setup company - ERPNext will automatically find and install the Lebanese chart
	from the JSON file in the unverified folder. We just ensure country is set correctly.
	"""
	# CRITICAL: Enable unverified charts FIRST, before any company creation
	# This must be set at the start so it's available when make_records creates the company
	frappe.local.flags.allow_unverified_charts = True
	
	# Parse args if it's a string
	if isinstance(args, str):
		try:
			args = json.loads(args)
		except:
			args = {}
	elif args is None:
		args = {}
	
	# Convert to dict if not already
	if not isinstance(args, dict):
		args = dict(args) if hasattr(args, '__dict__') else {}
	
	# Convert to frappe._dict for consistent access
	args_dict = frappe._dict(args)
	
	# Ensure country is set to Lebanon for Lebanese chart
	chart_of_accounts = args_dict.get('chart_of_accounts', '')
	is_lebanese = chart_of_accounts and ('Lebanese' in chart_of_accounts or 'lebanese' in chart_of_accounts.lower())
	
	# ALWAYS set country to Lebanon if Lebanese chart is selected
	if is_lebanese:
		args_dict['country'] = 'Lebanon'
		if not args_dict.get('currency'):
			args_dict['currency'] = 'LBP'
		frappe.log_error(f"Erpnext Lebanese: Lebanese chart detected: {chart_of_accounts}, setting country to Lebanon", "Info")
	
	# Also ensure country is set even if chart name doesn't match exactly
	if not args_dict.get('country'):
		args_dict['country'] = 'Lebanon'
		frappe.log_error("Erpnext Lebanese: No country set, defaulting to Lebanon", "Info")
	
	# Log what we're about to do
	frappe.log_error(f"Erpnext Lebanese: Calling install_company with args: {dict(args_dict)}, allow_unverified_charts={frappe.local.flags.allow_unverified_charts}", "Debug")
	
	# Use ERPNext's standard install_company - it will find the chart automatically
	# The LebaneseCompany override will handle tax template skipping
	try:
		fixtures.install_company(args_dict)
		frappe.db.commit()
		frappe.log_error("Erpnext Lebanese: install_company completed successfully", "Success")
	except Exception as e:
		frappe.log_error(f"Erpnext Lebanese: install_company failed: {str(e)}\n{frappe.get_traceback()}", "Error")
		frappe.db.rollback()
		raise
	
	# Verify company was created
	try:
		company_name = args_dict.get('company_name')
		if company_name:
			company_exists = frappe.db.exists("Company", company_name)
			if company_exists:
				frappe.log_error(f"Erpnext Lebanese: Verified company exists: {company_name}", "Success")
				
				# Check if accounts were created
				account_count = frappe.db.sql("select count(*) from tabAccount where company=%s", company_name)[0][0]
				frappe.log_error(f"Erpnext Lebanese: Account count for {company_name}: {account_count}", "Info")
			else:
				frappe.log_error(f"Erpnext Lebanese: WARNING - Company not found after creation: {company_name}", "Warning")
				# List all companies
				all_companies = frappe.db.sql("select name from tabCompany")
				frappe.log_error(f"Erpnext Lebanese: All companies in DB: {all_companies}", "Info")
		else:
			frappe.log_error("Erpnext Lebanese: WARNING - No company_name in args", "Warning")
	except Exception as e:
		frappe.log_error(f"Erpnext Lebanese: Company creation failed: {str(e)}\n{frappe.get_traceback()}", "Error")
		frappe.db.rollback()
		raise

def setup_defaults(args):
	"""Setup defaults - this runs after company creation"""
	# Ensure args is a dict
	if isinstance(args, str):
		try:
			args = json.loads(args)
		except:
			args = {}
	elif args is None:
		args = {}
	
	fixtures.install_defaults(frappe._dict(args))
 
def fin(args):
    """Final setup tasks"""
    frappe.local.message_log = []
    
    # Parse args if it's a string
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            args = {}
    elif args is None:
        args = {}
    
    login_as_first_user(args)

def setup_demo(args):
    """Setup demo data if requested"""
    # Parse args if it's a string
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            args = {}
    elif args is None:
        args = {}
    
    if isinstance(args, dict) and args.get("setup_demo"):
        from erpnext.setup.demo import setup_demo_data
        frappe.enqueue(setup_demo_data, enqueue_after_commit=True, at_front=True)

def login_as_first_user(args):
    """Login as first user"""
    if isinstance(args, dict) and args.get("email") and hasattr(frappe.local, "login_manager"):
        frappe.local.login_manager.login_as(args.get("email"))

@frappe.whitelist()
def setup_complete(args=None):
    """
    Programmatic setup complete - override ERPNext's method
    This is called via API, so args might be a JSON string
    """
    frappe.log_error("Erpnext Lebanese: setup_complete called", f"Args type: {type(args)}, Args: {args}")
    
    # Parse args if it's a string and convert to dict
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except:
            args = {}
    elif args is None:
        args = {}
    
    # Ensure default_currency is set for Lebanese setup
    if isinstance(args, dict):
        chart_of_accounts = args.get('chart_of_accounts', '')
        if 'Lebanese' in chart_of_accounts or 'lebanese' in chart_of_accounts.lower():
            if not args.get('currency'):
                args['currency'] = 'LBP'  # Set Lebanese Pound as default
            if not args.get('country'):
                args['country'] = 'Lebanon'
    
    frappe.log_error("Erpnext Lebanese: Converted args", f"Args type: {type(args)}, Keys: {list(args.keys()) if args else 'None'}")
    
    try:
        # Run setup stages - company creation will trigger chart installation via hook
        stage_fixtures(args)
        setup_company(args)
        setup_defaults(args)
        fin(args)
        
        # Return exactly what the frontend expects
        return {
            "status": "success",
            "message": "Setup Completed",
            "home_page": "/desk"
        }
            
    except Exception as e:
        frappe.log_error(f"Setup failed: {str(e)}", "Error")
        frappe.db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
    





