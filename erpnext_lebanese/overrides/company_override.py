# erpnext_lebanese/overrides/company_override.py
import frappe
from frappe import _
from erpnext.setup.doctype.company.company import Company


class LebaneseCompany(Company):
	"""
	Override Company class to install Lebanese chart of accounts
	This intercepts the create_default_accounts method and on_update
	"""
	
	def on_update(self):
		"""
		Override on_update to handle Lebanese companies properly
		Skip tax template creation for Lebanese companies as they have different tax structure
		CRITICAL: Set allow_unverified_charts BEFORE calling super().on_update() so get_chart() can find our chart
		"""
		# Check if this is a Lebanese company - check both instance and database
		country = getattr(self, 'country', None)
		chart_of_accounts = getattr(self, 'chart_of_accounts', None)
		
		# If not available on instance, check database
		if not country and self.name:
			try:
				country = frappe.db.get_value("Company", self.name, "country")
				chart_of_accounts = frappe.db.get_value("Company", self.name, "chart_of_accounts")
			except:
				pass
		
		is_lebanese = (country == "Lebanon" and chart_of_accounts and 
		              ("Lebanese" in chart_of_accounts or "lebanese" in chart_of_accounts.lower()))
		
		if is_lebanese:
			# Use print instead of log_error to avoid savepoint issues during insert
			print(f"Lebanese CoA: Processing Lebanese company {self.name}")
			# CRITICAL: Enable unverified charts BEFORE calling super().on_update()
			# This ensures get_chart() can find our Lebanese chart in the unverified folder
			frappe.local.flags.allow_unverified_charts = True
			
			# Set flag to skip tax template creation - set it on the instance too for safety
			frappe.flags.skip_tax_template_for_lebanese = True
			if not hasattr(self, 'flags'):
				self.flags = frappe._dict()
			self.flags.skip_tax_template_for_lebanese = True
		
		try:
			# Call parent on_update - this will call create_default_accounts() which calls get_chart()
			super().on_update()
		finally:
			# Clear the flags
			if is_lebanese:
				frappe.flags.skip_tax_template_for_lebanese = False
				if hasattr(self, 'flags'):
					self.flags.skip_tax_template_for_lebanese = False
				# Don't clear allow_unverified_charts - it might be needed elsewhere
	
	def create_default_tax_template(self):
		"""
		Override to skip tax template creation for Lebanese companies
		Lebanon has different tax structure, so we skip the default ERPNext tax setup
		"""
		# ALWAYS check if this is a Lebanese company first
		# Check instance attributes
		country = getattr(self, 'country', None)
		chart_of_accounts = getattr(self, 'chart_of_accounts', None)
		
		# If not available, check database
		if not country and self.name:
			try:
				country = frappe.db.get_value("Company", self.name, "country")
				chart_of_accounts = frappe.db.get_value("Company", self.name, "chart_of_accounts")
			except:
				pass
		
		is_lebanese_company = (country == "Lebanon" and chart_of_accounts and 
		                      ("Lebanese" in chart_of_accounts or "lebanese" in chart_of_accounts.lower()))
		
		# Also check flags
		is_lebanese_flag = getattr(frappe.flags, 'skip_tax_template_for_lebanese', False)
		is_lebanese_instance = getattr(self.flags, 'skip_tax_template_for_lebanese', False) if hasattr(self, 'flags') else False
		
		if is_lebanese_flag or is_lebanese_instance or is_lebanese_company:
			frappe.log_error(f"Skipping tax template creation for Lebanese company: {self.name} (flag={is_lebanese_flag}, instance={is_lebanese_instance}, company={is_lebanese_company}, country={country}, chart={chart_of_accounts})", "Info")
			return
		
		# For non-Lebanese companies, use default behavior
		frappe.log_error(f"Creating tax template for non-Lebanese company: {self.name} (country={country}, chart={chart_of_accounts})", "Debug")
		super().create_default_tax_template()
	
	def create_default_accounts(self):
		"""
		Override create_default_accounts - ERPNext will handle chart installation naturally
		from the JSON file we copied to the unverified folder
		We just need to ensure default accounts are set after installation
		"""
		# CRITICAL: Enable unverified charts FIRST - this must be set before create_charts is called
		frappe.local.flags.allow_unverified_charts = True
		
		# Check if this is a Lebanese company
		country = getattr(self, 'country', None)
		chart_of_accounts = getattr(self, 'chart_of_accounts', None)
		
		# If not available on instance, check database
		if not country and self.name:
			try:
				country = frappe.db.get_value("Company", self.name, "country")
				chart_of_accounts = frappe.db.get_value("Company", self.name, "chart_of_accounts")
			except:
				pass
		
		is_lebanese = (country == "Lebanon" and chart_of_accounts and 
		              ("Lebanese" in chart_of_accounts or "lebanese" in chart_of_accounts.lower()))
		
		# Test if chart can be found BEFORE calling super()
		# Use print instead of log_error to avoid savepoint issues during insert
		if is_lebanese and chart_of_accounts:
			from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import get_chart
			test_chart = get_chart(chart_of_accounts)
			if test_chart:
				root_count = len(test_chart.keys())
				print(f"Lebanese CoA: Chart FOUND ({root_count} roots)")
			else:
				print(f"Lebanese CoA: Chart NOT FOUND!")
		
		print(f"Lebanese CoA: Creating accounts for {self.name}")
		
		# Let ERPNext handle chart installation normally
		# It will find our Lebanese chart in the unverified folder
		# IMPORTANT: Don't use try/except with log_error here as it can break savepoint handling
		# Just let exceptions propagate naturally - make_records will handle rollback
		super().create_default_accounts()
		
		# Verify accounts were created (only log if successful to avoid savepoint issues)
		try:
			account_count = frappe.db.sql("select count(*) from tabAccount where company=%s", self.name)[0][0]
			if account_count > 0:
				# Use print instead of log_error to avoid savepoint issues during insert
				print(f"Lebanese CoA: Created {account_count} accounts for {self.name}")
		except:
			pass  # Don't fail if we can't verify
		
		# After chart installation, set default accounts for Lebanese companies
		# IMPORTANT: Don't commit here - we're inside on_update() during company creation
		# The parent transaction (make_records) will handle commits/rollbacks
		if self.country == "Lebanon" and self.chart_of_accounts:
			chart_name = self.chart_of_accounts or ""
			if "Lebanese" in chart_name or "lebanese" in chart_name.lower():
				try:
					# Set default accounts after chart installation
					# Use db_set instead of commit to avoid breaking savepoint handling
					set_lebanese_default_accounts(self.name)
					# Don't commit - let the parent transaction handle it
				except Exception as e:
					# Don't log errors here as it can break savepoint handling
					# Don't fail - accounts are already created
					pass


# Removed - ERPNext will handle chart installation from the JSON file in unverified folder


def set_lebanese_default_accounts(company):
	"""Set default accounts for Lebanese company after chart installation"""
	company_doc = frappe.get_doc("Company", company)
	
	# Set basic default accounts
	defaults = {
		"default_receivable_account": frappe.db.get_value(
			"Account", 
			{"company": company, "account_type": "Receivable", "is_group": 0},
			order_by="creation asc"
		),
		"default_payable_account": frappe.db.get_value(
			"Account", 
			{"company": company, "account_type": "Payable", "is_group": 0},
			order_by="creation asc"
		),
	}
	
	# Set cash account if exists
	cash_account = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Cash", "is_group": 0},
		order_by="creation asc"
	)
	if cash_account:
		defaults["default_cash_account"] = cash_account
	
	# Set bank account if exists
	bank_account = frappe.db.get_value(
		"Account",
		{"company": company, "account_type": "Bank", "is_group": 0},
		order_by="creation asc"
	)
	if bank_account:
		defaults["default_bank_account"] = bank_account
	
	# Update company with defaults
	for field, value in defaults.items():
		if value:
			company_doc.db_set(field, value)
	
	frappe.log_error(f"Set default accounts for company: {company}", "Default Accounts")

