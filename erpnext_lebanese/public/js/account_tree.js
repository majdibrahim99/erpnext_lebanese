console.log("[erpnext_lebanese] account_tree.js loading...");
(function () {
	const settings = frappe.treeview_settings?.Account;
	if (!settings) {
		console.log("[erpnext_lebanese] Account tree settings not found; skipping language controls.");
		return;
	}

	console.log("[erpnext_lebanese] Account tree language controls initialising.");

	const LANGUAGE_OPTIONS = [
		{ label: __("English"), value: "en" },
		{ label: __("Arabic"), value: "ar" },
		{ label: __("French"), value: "fr" },
	];

	const originalOnload = settings.onload;
	const originalOnrender = settings.onrender;
	const originalPostRender = settings.post_render;
	const originalGetLabel = settings.get_label;

	settings.onload = function (treeview) {
		console.log("[erpnext_lebanese] Account tree onload hook triggered.");
		originalOnload && originalOnload(treeview);
		setupLanguageSelector(treeview);
	};

	settings.onrender = function (node) {
		originalOnrender && originalOnrender(node);
		updateNodeLabel(node);
	};

	settings.post_render = function (treeview) {
		originalPostRender && originalPostRender(treeview);
		initializeLanguage(treeview);
	};

	settings.get_label = function (node) {
		const treeview = frappe.treeview_settings?.Account?.treeview;
		const labels = treeview?.__lebanese_labels;

		const docname = node?.data?.value;
		const info = docname ? labels?.[docname] : null;

		if (treeview && info && info.label) {
			const currentLang = treeview.__lebanese_language || "en";
			const labelText = info.label;
			const english = info.english || "";
			const showHint =
				treeview.__lebanese_enabled &&
				currentLang !== "en" &&
				english &&
				english !== labelText;

			if (settings._lebanese_state?.debug) {
				console.log("[erpnext_lebanese] get_label", docname, treeview.__lebanese_language, labelText);
			}

			return frappe.utils.escape_html(labelText);
		}

		if (originalGetLabel) {
			return originalGetLabel(node);
		}

		const title = node?.title;
		const label = node?.label;
		if (title && title !== label) {
			return `${frappe.utils.escape_html(title)} <span class="text-muted">(${frappe.utils.escape_html(label)})</span>`;
		}
		return frappe.utils.escape_html(title || label || "");
	};

	function getState() {
		if (!settings._lebanese_state) {
			settings._lebanese_state = { cache: {}, debug: true };
		}
		return settings._lebanese_state;
	}

	function setupLanguageSelector(treeview) {
		console.log("[erpnext_lebanese] Setting up language selector.");
		if (treeview.page.account_language_select) {
			return;
		}

		const select = treeview.page.add_select(__("Account Language"), LANGUAGE_OPTIONS);
		treeview.page.account_language_select = select;
		select.addClass("account-language-select");

		const defaultLang = resolveDefaultLanguage();
		select.val(defaultLang);

		select.on("change", () => {
			const lang = select.val() || "en";
			treeview.__lebanese_language = lang;
			fetchLabels(treeview, lang, { force: true });
		});

		const companyField = treeview.page.fields_dict?.company;
		if (companyField && !companyField.$input.data("lebanese-language-bound")) {
			companyField.$input.data("lebanese-language-bound", true);
			companyField.$input.on("change", () => {
				const lang = select.val() || "en";
				const state = getState();
				state.cache = {};
				fetchLabels(treeview, lang, { force: true });
			});
		}
	}

	function resolveDefaultLanguage() {
		const lang = (frappe.boot.user.language || "").toLowerCase();
		if (lang.startsWith("ar")) return "ar";
		if (lang.startsWith("fr")) return "fr";
		return "en";
	}

	function initializeLanguage(treeview) {
		const select = treeview.page.account_language_select;
		if (!select) return;

		const lang = select.val() || resolveDefaultLanguage();
		treeview.__lebanese_language = lang;
		fetchLabels(treeview, lang);
	}

	function fetchLabels(treeview, lang, opts = {}) {
		console.log("[erpnext_lebanese] Fetching labels for language:", lang);
		const state = getState();

		const companyField = treeview.page.fields_dict?.company;
		const company = companyField ? companyField.get_value() : null;
		if (!company) {
			return;
		}

		const cacheKey = `${company}::${lang}`;
		if (!opts.force && state.cache[cacheKey]) {
			const payload = state.cache[cacheKey];
			applyLanguagePayload(treeview, payload, lang);
			return;
		}

		frappe.call({
			method: "erpnext_lebanese.api.get_account_language_labels",
			args: { company, language: lang },
		}).then((r) => {
			const payload = r.message || { enabled: false, labels: {} };
			state.cache[cacheKey] = payload;
			applyLanguagePayload(treeview, payload, lang);
		});
	}

	function applyLanguagePayload(treeview, payload, lang) {
		console.log("[erpnext_lebanese] Applying language payload:", payload.enabled, lang);
		treeview.__lebanese_labels = payload.labels || {};
		treeview.__lebanese_enabled = Boolean(payload.enabled);
		treeview.__lebanese_language = lang || payload.language || "en";

		const shared = frappe.treeview_settings?.Account?.treeview;
		if (shared && shared !== treeview) {
			shared.__lebanese_labels = treeview.__lebanese_labels;
			shared.__lebanese_enabled = treeview.__lebanese_enabled;
			shared.__lebanese_language = treeview.__lebanese_language;
		}

		if (treeview.tree) {
			treeview.tree.get_label = (node) => settings.get_label(node);
		}

		updateLanguageSelector(treeview, payload.enabled);
		refreshTree(treeview);
	}

	function updateLanguageSelector(treeview, enabled) {
		const select = treeview.page.account_language_select;
		if (!select) return;

		if (enabled) {
			select.prop("disabled", false);
			select.parent().show();
		} else {
			select.prop("disabled", true);
			select.parent().hide();
		}
	}

	function refreshTree(treeview) {
		const tree = treeview.tree;
		if (!tree || !tree.root_node) return;

		tree
			.load_children(tree.root_node, false)
			.then(() => refreshVisibleNodes(treeview))
			.catch(() => refreshVisibleNodes(treeview));
	}

	function refreshVisibleNodes(treeview) {
		const tree = treeview.tree;
		if (!tree) return;

		Object.keys(tree.nodes || {}).forEach((key) => {
			const node = tree.nodes[key];
			if (node) {
				updateNodeLabel(node);
			}
		});
	}

	function updateNodeLabel(node) {
		const treeview = frappe.treeview_settings?.Account?.treeview;
		if (!treeview || !treeview.tree || !node) {
			return;
		}

		const labelHtml = treeview.tree.get_node_label(node);
		const $label = node.$tree_link?.find(".tree-label");
		if ($label && $label.length && labelHtml !== undefined) {
			$label.html(` ${labelHtml}`);
		}
	}
})();

