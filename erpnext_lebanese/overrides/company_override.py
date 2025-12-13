# erpnext_lebanese/overrides/company_override.py
import frappe
from frappe import _
from erpnext.setup.doctype.company.company import Company
from erpnext_lebanese.overrides.chart_of_accounts_create_override import (
	create_charts as lebanese_create_charts,
)
from erpnext_lebanese.default_accounts import (
	build_company_structural_defaults,
	build_default_account_map,
)


class LebaneseCompany(Company):
	"""
	Override Company class to install Lebanese chart of accounts
	This intercepts the create_default_accounts method and on_update
	"""
	
	def validate(self):
		"""
		Ensure Lebanese companies default to the Lebanese chart of accounts
		whenever a chart is not explicitly selected. This applies to manual
		company creation after the setup wizard has been completed.
		"""
		# If user is creating a Lebanese company manually and has not selected a chart,
		# default to the Lebanese standard chart that ships with this app.
		if self.country == "Lebanon":
			# Enable loading of charts placed in the unverified folder
			frappe.local.flags.allow_unverified_charts = True

			# Only override when no chart is chosen (or the field is empty/whitespace)
			if not (self.chart_of_accounts or "").strip():
				self.chart_of_accounts = "Lebanese Standard Chart of Accounts"

		# Proceed with the standard validations
		super().validate()

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
			
			# After accounts are created, ensure cost center is set for Lebanese companies
			if is_lebanese and self.name:
				try:
					from erpnext_lebanese.default_accounts import _ensure_cost_center_tree, _get_primary_cost_center
					
					# Ensure cost center exists
					cost_center = _ensure_cost_center_tree(self.name)
					if not cost_center:
						cost_center = _get_primary_cost_center(self.name)
					
					# Set cost center if we have one and it's not already set
					if cost_center:
						current_cost_center = frappe.db.get_value("Company", self.name, "cost_center")
						if not current_cost_center:
							# Use db_set for consistency
							self.db_set("cost_center", cost_center)
							self.db_set("round_off_cost_center", cost_center)
							self.db_set("depreciation_cost_center", cost_center)
							frappe.db.commit()
					
					# Create Sales and Purchase Taxes and Charges Templates
					create_lebanese_sales_tax_template(self.name, cost_center)
					create_lebanese_purchase_tax_template(self.name, cost_center)
				except Exception as e:
					# Don't fail company update if cost center setting fails
					frappe.log_error(f"Error setting cost center in on_update: {str(e)}", "Lebanese Company Setup")
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
			return
		
		# For non-Lebanese companies, use default behavior
		super().create_default_tax_template()
	
	def create_default_accounts(self):
		"""
		Override create_default_accounts - Use custom create_charts that handles arabic_name and french_name
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
		
		# Use our custom create_charts for Lebanese companies, otherwise use default
		if is_lebanese:
			# Use custom create_charts that handles arabic_name and french_name
			frappe.local.flags.ignore_root_company_validation = True
			lebanese_create_charts(self.name, self.chart_of_accounts, self.existing_company)
			
			# Set default accounts - use specific Lebanese account numbers
			receivable_account = frappe.db.get_value(
				"Account", {"company": self.name, "account_number": "4111"}, "name"
			)
			if receivable_account:
				self.db_set("default_receivable_account", receivable_account)
			else:
				# Fallback to any receivable account
				self.db_set(
					"default_receivable_account",
					frappe.db.get_value(
						"Account", {"company": self.name, "account_type": "Receivable", "is_group": 0}
					),
				)
			
			payable_account = frappe.db.get_value(
				"Account", {"company": self.name, "account_number": "4011"}, "name"
			)
			if payable_account:
				self.db_set("default_payable_account", payable_account)
			else:
				# Fallback to any payable account
				self.db_set(
					"default_payable_account",
					frappe.db.get_value("Account", {"company": self.name, "account_type": "Payable", "is_group": 0}),
				)
			
			# Set additional default accounts for Lebanese companies
			try:
				# First ensure cost center tree exists and get the cost center name
				from erpnext_lebanese.default_accounts import _ensure_cost_center_tree, _get_primary_cost_center
				
				# Create cost center tree first - this returns the main cost center name
				cost_center = _ensure_cost_center_tree(self.name)
				
				# If creation didn't return it, try to get it
				if not cost_center:
					cost_center = _get_primary_cost_center(self.name)
				
				# Now set all defaults (this will include cost center if found)
				set_lebanese_default_accounts(self.name)
				
				# Explicitly set cost center using db_set (same method as accounts above)
				# This ensures it's set on the company document
				if cost_center:
					self.db_set("cost_center", cost_center)
					self.db_set("round_off_cost_center", cost_center)
					self.db_set("depreciation_cost_center", cost_center)
				
				# Commit all account and cost center changes first
				frappe.db.commit()
				
				# Create default Sales and Purchase Taxes and Charges Templates (after accounts are committed)
				create_lebanese_sales_tax_template(self.name, cost_center)
				create_lebanese_purchase_tax_template(self.name, cost_center)
				
			except Exception as e:
				# Don't fail - accounts are already created
				frappe.log_error(f"Error setting Lebanese defaults: {str(e)}", "Lebanese Company Setup")
				pass
		else:
			# For non-Lebanese companies, use default behavior
			try:
				super().create_default_accounts()
			except Exception as e:
				raise


# Removed - ERPNext will handle chart installation from the JSON file in unverified folder


def set_lebanese_default_accounts(company):
	"""Ensure all ERPNext default account hooks point to Lebanese chart accounts."""
	account_map = build_default_account_map(company)
	structural_map = build_company_structural_defaults(company)
	updates = {**structural_map, **account_map}
	if updates:
		frappe.db.set_value("Company", company, updates)


def create_lebanese_sales_tax_template(company, cost_center=None):
	"""Create default Sales Taxes and Charges Template for Lebanese companies."""
	if not company:
		return
	
	# Get company abbreviation for dynamic account/cost center names
	company_abbr = frappe.db.get_value("Company", company, "abbr")
	if not company_abbr:
		frappe.log_error(
			f"Company abbreviation not found for {company}. Cannot create tax template.",
			"Lebanese Tax Template Creation"
		)
		return
	
	# Check if template already exists for this company
	existing_template = frappe.db.get_value(
		"Sales Taxes and Charges Template",
		{"title": "VAT 11%", "company": company},
		"name"
	)
	
	if existing_template:
		return
	
	# Get account 4427 (Value Added Tax - Collected on Revenues) for this company
	# Retry a few times in case accounts are still being created
	account_4427 = None
	for attempt in range(3):
		frappe.db.commit()  # Commit any pending transactions first
		account_4427 = frappe.db.get_value(
			"Account",
			{"company": company, "account_number": "4427"},
			"name"
		)
		if account_4427:
			break
	
	if not account_4427:
		# Account not found, log and skip template creation
		frappe.log_error(
			f"Account 4427 (Value Added Tax - Collected on Revenues) not found for company {company} after retries. Cannot create tax template.",
			"Lebanese Tax Template Creation"
		)
		return
	
	# Get cost center if not provided
	if not cost_center:
		from erpnext_lebanese.default_accounts import _get_primary_cost_center
		cost_center = _get_primary_cost_center(company)
	
	if not cost_center:
		frappe.log_error(
			f"Cost center not found for company {company}. Cannot create tax template.",
			"Lebanese Tax Template Creation"
		)
		return
	
	# Get company currency
	company_currency = frappe.db.get_value("Company", company, "default_currency") or "LBP"
	
	try:
		# Create Sales Taxes and Charges Template
		template = frappe.get_doc({
			"doctype": "Sales Taxes and Charges Template",
			"title": "VAT 11%",
			"company": company,
			"taxes": [
				{
					"charge_type": "On Net Total",
					"account_head": account_4427,
					"description": "VAT @ 11%",
					"included_in_print_rate": 0,
					"included_in_paid_amount": 0,
					"cost_center": cost_center,
					"rate": 11.0,
					"account_currency": company_currency
				}
			]
		})
		
		template.flags.ignore_permissions = True
		template.flags.ignore_mandatory = True
		template.insert()
		
		frappe.db.commit()
		
	except Exception as e:
		import traceback
		error_msg = f"Error creating Sales Taxes and Charges Template for company {company}: {str(e)}\n{traceback.format_exc()}"
		frappe.log_error(error_msg, "Lebanese Tax Template Creation")


def create_lebanese_purchase_tax_template(company, cost_center=None):
	"""Create default Purchase Taxes and Charges Template for Lebanese companies."""
	if not company:
		return
	
	# Get company abbreviation for dynamic account/cost center names
	company_abbr = frappe.db.get_value("Company", company, "abbr")
	if not company_abbr:
		frappe.log_error(
			f"Company abbreviation not found for {company}. Cannot create tax template.",
			"Lebanese Tax Template Creation"
		)
		return
	
	# Check if template already exists for this company
	existing_template = frappe.db.get_value(
		"Purchase Taxes and Charges Template",
		{"title": "VAT 11%", "company": company},
		"name"
	)
	
	if existing_template:
		return
	
	# Get account 4426.6 (Value Added Tax - On Purchases & Charges) for this company
	# Retry a few times in case accounts are still being created
	account_4426_6 = None
	for attempt in range(3):
		frappe.db.commit()  # Commit any pending transactions first
		account_4426_6 = frappe.db.get_value(
			"Account",
			{"company": company, "account_number": "4426.6"},
			"name"
		)
		if account_4426_6:
			break
	
	if not account_4426_6:
		# Account not found, log and skip template creation
		frappe.log_error(
			f"Account 4426.6 (Value Added Tax - On Purchases & Charges) not found for company {company} after retries. Cannot create tax template.",
			"Lebanese Tax Template Creation"
		)
		return
	
	# Get cost center if not provided
	if not cost_center:
		from erpnext_lebanese.default_accounts import _get_primary_cost_center
		cost_center = _get_primary_cost_center(company)
	
	if not cost_center:
		frappe.log_error(
			f"Cost center not found for company {company}. Cannot create tax template.",
			"Lebanese Tax Template Creation"
		)
		return
	
	# Get company currency
	company_currency = frappe.db.get_value("Company", company, "default_currency") or "LBP"
	
	try:
		# Create Purchase Taxes and Charges Template
		template = frappe.get_doc({
			"doctype": "Purchase Taxes and Charges Template",
			"title": "VAT 11%",
			"company": company,
			"taxes": [
				{
					"charge_type": "On Net Total",
					"account_head": account_4426_6,
					"description": "VAT @ 11%",
					"add_deduct_tax": "Add",
					"included_in_print_rate": 0,
					"included_in_paid_amount": 0,
					"cost_center": cost_center,
					"rate": 11.0,
					"account_currency": company_currency
				}
			]
		})
		
		template.flags.ignore_permissions = True
		template.flags.ignore_mandatory = True
		template.insert()
		
		frappe.db.commit()
		
	except Exception as e:
		import traceback
		error_msg = f"Error creating Purchase Taxes and Charges Template for company {company}: {str(e)}\n{traceback.format_exc()}"
		frappe.log_error(error_msg, "Lebanese Tax Template Creation")

