frappe.provide("erpnext.setup");

(function () {
	const slides = erpnext?.setup?.slides_settings;
	if (!Array.isArray(slides) || !slides.length) {
		return;
	}

	const organizationSlideIndex = slides.findIndex((slide) => slide.name === "organization");

	const organizationSlide = {
		name: "organization",
		title: __("Setup your organization"),
		icon: "fa fa-building",
		fields: [
			{ fieldtype: "Section Break", label: __("Company Setup") },
			{
				fieldname: "company_name",
				label: __("Company Name"),
				fieldtype: "Data",
				reqd: 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "company_abbr",
				label: __("Company Abbreviation"),
				fieldtype: "Data",
				reqd: 1,
			},
			{ fieldtype: "Section Break", label: __("Account Settings") },
			{
				fieldname: "chart_of_accounts",
				label: __("Chart of Accounts"),
				options: "",
				fieldtype: "Select",
				reqd: 1,
			},
			{ fieldtype: "Column Break" },
			{ fieldname: "view_coa", label: __("View Chart of Accounts"), fieldtype: "Button" },
			{ fieldtype: "Section Break" },
			{ fieldname: "fy_start_date", label: __("Financial Year Begins On"), fieldtype: "Date", reqd: 1 },
			{ fieldname: "fy_end_date", label: __("End Date"), fieldtype: "Date", reqd: 1, hidden: 1 },
			{ fieldtype: "Section Break" },
			{
				fieldname: "setup_demo",
				label: __("Generate Demo Data for Exploration"),
				fieldtype: "Check",
				description: __(
					"If checked, we will create demo data for you to explore the system. This demo data can be erased later."
				),
			},
		],

		onload(slide) {
			this.bind_events(slide);
			if (!frappe.wizard.values.country) {
				frappe.wizard.values.country = "Lebanon";
			}
		},

		before_show() {
			if (!frappe.wizard.values.country) {
				frappe.wizard.values.country = "Lebanon";
			}

			this.load_chart_of_accounts(this);
			this.set_fy_dates(this);
		},

		validate() {
			if (!this.validate_fy_dates()) {
				return false;
			}

			if ((this.values.company_name || "").toLowerCase() === "company") {
				frappe.msgprint(__("Company Name cannot be Company"));
				return false;
			}

			if (!this.values.company_abbr || this.values.company_abbr.length > 10) {
				return false;
			}

			return true;
		},

		validate_fy_dates() {
			const invalid =
				this.values.fy_start_date === "Invalid date" || this.values.fy_end_date === "Invalid date";
			const start_greater_than_end = this.values.fy_start_date > this.values.fy_end_date;

			if (invalid || start_greater_than_end) {
				frappe.msgprint(__("Please enter valid Financial Year Start and End Dates"));
				return false;
			}

			return true;
		},

		set_fy_dates(slide) {
			let country = frappe.wizard.values.country || frappe.defaults.get_default("country");

			if (country) {
				let fy = erpnext.setup.fiscal_years[country];
				let current_year = moment(new Date()).year();
				let next_year = current_year + 1;
				if (!fy) {
					fy = ["01-01", "12-31"];
					next_year = current_year;
				}

				let year_start_date = `${current_year}-${fy[0]}`;
				if (year_start_date > frappe.datetime.get_today()) {
					next_year = current_year;
					current_year -= 1;
				}

				slide.get_field("fy_start_date").set_value(`${current_year}-${fy[0]}`);
				slide.get_field("fy_end_date").set_value(`${next_year}-${fy[1]}`);
			}
		},

		load_chart_of_accounts(slide) {
			const country = "Lebanon";
			frappe.wizard.values.country = country;

			frappe.call({
				method: "erpnext_lebanese.overrides.chart_of_accounts_override.get_lebanese_charts",
				args: { country },
				callback(r) {
					if (r.message && r.message.length > 0) {
						slide.get_input("chart_of_accounts").empty().add_options(r.message);

						const lebaneseChart = r.message.find((chart) =>
							chart.includes("Lebanese Standard Chart of Accounts")
						);
						if (lebaneseChart) {
							slide.get_field("chart_of_accounts").set_value(lebaneseChart);
						}
					}
				},
			});
		},

		bind_events(slide) {
			const me = this;
			slide.get_input("fy_start_date").on("change", function () {
				const start_date = slide.form.fields_dict.fy_start_date.get_value();
				const year_end_date = frappe.datetime.add_days(frappe.datetime.add_months(start_date, 12), -1);
				slide.form.fields_dict.fy_end_date.set_value(year_end_date);
			});

			slide.get_input("view_coa").on("click", function () {
				const chart_template = slide.form.fields_dict.chart_of_accounts.get_value();
				if (!chart_template) {
					return;
				}

				me.charts_modal(slide, chart_template);
			});

			slide
				.get_input("company_name")
				.on("input", function () {
					const parts = slide.get_input("company_name").val().split(" ");
					const abbr = $.map(parts, (p) => (p ? p.substr(0, 1) : null)).join("");
					slide.get_field("company_abbr").set_value(abbr.slice(0, 10).toUpperCase());
				})
				.val(frappe.boot.sysdefaults.company_name || "")
				.trigger("change");

			slide
				.get_input("company_abbr")
				.on("change", function () {
					let abbr = slide.get_input("company_abbr").val();
					if (abbr.length > 10) {
						frappe.msgprint(__("Company Abbreviation cannot have more than 10 characters"));
						abbr = abbr.slice(0, 10);
					}
					slide.get_field("company_abbr").set_value(abbr);
				})
				.val(frappe.boot.sysdefaults.company_abbr || "")
				.trigger("change");
		},

		charts_modal(slide, chart_template) {
			let parent = __("All Accounts");

			const dialog = new frappe.ui.Dialog({
				title: chart_template,
				fields: [
					{
						fieldname: "expand_all",
						label: __("Expand All"),
						fieldtype: "Button",
						click() {
							coa_tree.load_children(coa_tree.root_node, true);
						},
					},
					{
						fieldname: "collapse_all",
						label: __("Collapse All"),
						fieldtype: "Button",
						click() {
							coa_tree
								.get_all_nodes(coa_tree.root_node.data.value, coa_tree.root_node.is_root)
								.then((data_list) => {
									data_list.forEach((d) => {
										coa_tree.toggle_node(coa_tree.nodes[d.parent]);
									});
								});
						},
					},
				],
			});

			const coa_tree = new frappe.ui.Tree({
				parent: $(dialog.body),
				label: parent,
				expandable: true,
				method: "erpnext_lebanese.overrides.chart_of_accounts_override.get_lebanese_coa",
				args: {
					chart: chart_template,
					parent,
					doctype: "Account",
				},
				onclick(node) {
					parent = node.value;
				},
			});

			const form_container = $(dialog.body).find("form");
			const buttons = $(form_container).find(".frappe-control");
			form_container.addClass("flex");
			buttons.each((index, button) => {
				$(button).css({ "margin-right": "1em" });
			});

			dialog.show();
			coa_tree.load_children(coa_tree.root_node, true);
		},
	};

	if (organizationSlideIndex === -1) {
		slides.unshift(organizationSlide);
	} else {
		slides.splice(organizationSlideIndex, 1, organizationSlide);
	}
})();
