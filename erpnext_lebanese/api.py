import json
import re
from pathlib import Path
from typing import Dict, Optional

import frappe
from frappe.utils import cstr

METADATA_KEYS = {
	"account_name",
	"account_number",
	"account_type",
	"root_type",
	"is_group",
	"tax_rate",
	"account_currency",
	"arabic_name",
	"french_name",
}

SUPPORTED_LANGUAGES = {"en", "ar", "fr"}


@frappe.whitelist()
def get_account_language_labels(company: str, language: Optional[str] = "en") -> Dict[str, Dict[str, str]]:
	"""Return localized account labels for the Chart of Accounts tree view."""
	if not company:
		return {"enabled": False, "labels": {}}

	lang_code = _normalise_language(language)

	company_row = frappe.db.get_value(
		"Company",
		company,
		["chart_of_accounts"],
		as_dict=True,
	)

	if not company_row:
		return {"enabled": False, "labels": {}}

	chart_name = (company_row.chart_of_accounts or "").strip()
	if not chart_name or "lebanese" not in chart_name.lower():
		return {"enabled": False, "labels": {}}

	chart_tree = _get_cached_chart_tree()
	number_to_labels = _build_label_map(chart_tree)

	accounts = frappe.get_all(
		"Account",
		filters={"company": company},
		fields=["name", "account_number", "account_name"],
	)

	labels: Dict[str, Dict[str, str]] = {}

	for account in accounts:
		account_number = _resolve_account_number(account)
		default_label = account.account_name or account.name

		translations = number_to_labels.get(account_number) if account_number else None

		selected_label = None
		english_label = None

		if translations:
			selected_label = translations.get(lang_code) or translations.get("en")
			english_label = translations.get("en")

		selected_label = selected_label or default_label
		english_label = english_label or default_label

		display_text = selected_label or ""
		if account_number and display_text:
			if not display_text.startswith(account_number):
				display_text = f"{account_number} - {display_text}"

		if account_number and english_label:
			if not english_label.startswith(account_number):
				english_label = f"{account_number} - {english_label}"

		labels[account.name] = {
			"label": display_text or english_label or "",
			"english": english_label or default_label or "",
		}

	return {
		"enabled": True,
		"language": lang_code,
		"labels": labels,
	}


def _normalise_language(language: Optional[str]) -> str:
	if not language:
		return "en"

	lower = language.lower()
	if lower.startswith("ar"):
		return "ar"
	if lower.startswith("fr"):
		return "fr"

	return "en"


def _get_cached_chart_tree() -> Dict:
	cache = frappe.cache()
	cached = cache.get_value("lebanese_standard_chart_tree")
	if cached:
		return cached

	chart_path = (
		Path(frappe.get_app_path("erpnext_lebanese")).resolve()
		/ "data"
		/ "chart_of_accounts"
		/ "lebanese_standard.json"
	)

	with chart_path.open(encoding="utf-8") as handle:
		data = json.load(handle)

	tree = data.get("tree") or {}
	cache.set_value("lebanese_standard_chart_tree", tree)
	return tree


def _build_label_map(tree: Dict) -> Dict[str, Dict[str, Optional[str]]]:
	number_to_labels: Dict[str, Dict[str, Optional[str]]] = {}

	def walk(children: Dict):
		for key, child in children.items():
			if key in METADATA_KEYS or not isinstance(child, dict):
				continue

			account_number = cstr(child.get("account_number")).strip()
			if account_number:
				number_to_labels[account_number] = {
					"en": child.get("account_name") or key,
					"ar": child.get("arabic_name"),
					"fr": child.get("french_name"),
				}

			walk(child)

	walk(tree)
	return number_to_labels


def _resolve_account_number(account) -> str:
	account_number = cstr(getattr(account, "account_number", "")).strip()
	if account_number:
		return account_number

	# Attempt to extract from the account name (e.g. "1000 - Equity ...")
	name = cstr(getattr(account, "name", "")).strip()
	match = re.match(r"^([\d\.]+)\s*-", name)
	if match:
		return match.group(1).strip()

	return ""

