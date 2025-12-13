# ERPNext Lebanese

A custom ERPNext application tailored for the **Lebanese accounting system**, providing a standardized Chart of Accounts and a fully localized, multilingual experience.

## Overview

**ERPNext Lebanese** is a custom ERPNext app that enables Lebanese-compliant accounting by automatically configuring companies with a standardized Lebanese Chart of Accounts (CoA). It supports **Arabic, French, and English**, including full **RTL support** for Arabic, ensuring consistency, compliance, and usability for Lebanese businesses.

## Summary

* Automatic provisioning of Lebanese companies with default CoA, currency, and fiscal settings
* Customized setup wizard focused on Lebanese company requirements
* Multilingual Chart of Accounts (Arabic, French, English) with runtime language switching
* RTL-aware Chart of Accounts UI for Arabic
* Company creation overrides to ensure consistent configuration
* Server APIs and client scripts for dynamic account label localization

## Sponsorship & Support

This project was **sponsored and supported by Elissa**.
Special thanks to **Elissa** for supporting the development and maintenance of this application.

🌐 Website: **[https://www.elissaco.com](https://www.elissaco.com)**

## Features

### 1. Lebanese Standard Chart of Accounts

* **8 Root Accounts**, aligned with the Lebanese accounting structure:

  * `1000` – Equity & Long-Term Debts (رأس المال)
  * `2000` – Fixed Assets (حسابات الأصول الثابتة)
  * `3000` – Inventory & Goods in Process (المخزون وقيد الصنع)
  * `4000` – Receivables & Payables (حسابات الذمم)
  * `5000` – Financial Accounts (الحسابات المالية)
  * `6000` – Costs & Expenses (حسابات الأعباء)
  * `7000` – Income (حسابات الإيرادات)
  * `8000` – Extra-Balance Sheet Contingency Accounts (حسابات الالتزامات خارج الميزانية)

* **Automatic Installation**:

  * During the ERPNext Setup Wizard
  * During manual Company creation after app installation

### 2. Multilingual Support

* Full support for **Arabic, French, and English**
* Dynamic language switching from the Chart of Accounts tree view
* Account names stored with multilingual labels in the chart JSON
* Automatically detects user language from system settings

### 3. Right-to-Left (RTL) Support

* Full RTL layout when Arabic is selected
* Right-aligned text and proper padding
* Icons and balance values repositioned for RTL
* Seamless switching between LTR and RTL modes

### 4. Company Creation Overrides

* Automatically configures Lebanese companies with:

  * Lebanese Standard Chart of Accounts
  * Unverified charts enabled
  * Default Receivable and Payable accounts
* Ensures CoA consistency across setup wizard and manual creation flows

## Installation

Install the app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/lijsamuael/erpnext_lebanese
bench --site site-name install-app erpnext_lebanese
```

Restart bench and clear cache:

```bash
bench restart
bench clear-cache
```