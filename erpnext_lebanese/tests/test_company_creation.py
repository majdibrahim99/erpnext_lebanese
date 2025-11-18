import random

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string

from erpnext_lebanese.overrides.setup_wizard_override import (
	setup_company as wizard_setup_company,
)

LEBANESE_CHART = "Lebanese Standard Chart of Accounts"


class TestLebaneseCompanyCreation(FrappeTestCase):
	def setUp(self):
		self.created_companies = []

	def tearDown(self):
		for company in self.created_companies:
			if frappe.db.exists("Company", company):
				frappe.delete_doc("Company", company, force=1, ignore_permissions=True)
		frappe.db.commit()

	def _unique_company(self, prefix):
		random_suffix = random_string(5).upper()
		name = f"{prefix} {random_suffix}"
		abbr = f"{prefix[:2]}{random_suffix}".upper()[:5]
		return name, abbr

	def _fiscal_year_window(self):
		year = 2100 + random.randint(0, 200)
		return f"{year}-01-01", f"{year}-12-31"

	def _assert_chart_created(self, company_name):
		company = frappe.get_doc("Company", company_name)
		self.assertEqual(company.chart_of_accounts, LEBANESE_CHART)
		account_count = frappe.db.count("Account", {"company": company.name})
		self.assertGreater(account_count, 0)

	def _account_fingerprint(self, company_name):
		rows = frappe.db.get_all(
			"Account",
			filters={"company": company_name},
			fields=["account_number", "account_name", "is_group", "root_type"],
		)
		fingerprint = set()
		for row in rows:
			key = row.account_number or row.account_name
			fingerprint.add((key, row.is_group, row.root_type))
		return fingerprint

	def test_manual_company_creation_installs_lebanese_chart(self):
		company_name, abbr = self._unique_company("Manual Test Co")
		self.created_companies.append(company_name)

		company_doc = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbr,
				"country": "Lebanon",
				"default_currency": "LBP",
			}
		)
		company_doc.insert()
		self._assert_chart_created(company_name)

	def test_setup_wizard_company_creation_matches_manual_flow(self):
		manual_company, manual_abbr = self._unique_company("Manual Baseline Co")
		wizard_company, wizard_abbr = self._unique_company("Wizard Test Co")

		self.created_companies.extend([manual_company, wizard_company])

		manual_doc = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": manual_company,
				"abbr": manual_abbr,
				"country": "Lebanon",
				"default_currency": "LBP",
			}
		)
		manual_doc.insert()
		self._assert_chart_created(manual_company)

		fy_start, fy_end = self._fiscal_year_window()

		wizard_setup_company(
			{
				"company_name": wizard_company,
				"company_abbr": wizard_abbr,
				"fy_start_date": fy_start,
				"fy_end_date": fy_end,
				"chart_of_accounts": LEBANESE_CHART,
			}
		)

		self._assert_chart_created(wizard_company)

		self.assertEqual(
			self._account_fingerprint(manual_company),
			self._account_fingerprint(wizard_company),
		)

