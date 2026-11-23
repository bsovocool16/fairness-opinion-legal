# House-style differences: filed decks vs. generated books

These differences come from comparing each bank's generated WTS book (PR #7 branch `claude/project-thread-03usvw`, live run, opinion date 2026-11-21) with filed slides from the reference deck named in that profile's `template`. The side-by-side pages are in `<bank>.pdf`. Sizes and distances were estimated by eye from 150-dpi renders, so they are good to about ±2pt.

Each line is written as a profile change: `field: current → proposed`. If the profile has no field for a feature yet, the line is marked **(new)**, and the renderer has to support it before the profile can set it.

## Every bank

- **(new)** `toc.style: "table"` → `"list"`. Every real TOC is a plain text list without a filled header. Goldman, Jefferies and Evercore use one, and J.P. Morgan has an "Agenda" page. We render a filled 3-column table with the section names centred.
- **(new)** `table.row_height`: ~0.35 in → ~0.15–0.18 in. Table text should also go from ~10pt to ~8pt. In every real deck the tables are about twice as dense as ours.
- **(new)** `table.row_rules`: a gray rule under every row → none. The exceptions are Goldman and Jefferies, which do rule every row, in thin gray.
- **(new)** `ff.columns`: real football fields put column headers over the label, bar and commentary areas. They usually add a column of implied multiples on the right, as Goldman, J.P. Morgan, Citi and Evercore do. Ours has no headers, and the gaps between rows are too wide.
- **(new)** `ff.label_tiers: 1 → 2` for Perella and J.P. Morgan: a category block that spans its methods, then one cell per method.
- **(new)** `comps.style: "table"` → `"bars"` for Perella, Jefferies and Citi. Their peer pages are bar charts of the multiples with median lines.
- The demo "ILLUSTRATIVE" stamp (`stamp: top_center`) is on every page, including covers and dividers. Keep it, since it is the demo legend, but take it off dividers so they read like the real ones.

## Goldman Sachs (`goldman`, ref. PowerSchool 2024 (c)(xii))

- **(new)** `header.strip`: reserve a logo-block area at the top left (about 0.45 in square) and put `INVESTMENT BANKING |` in small gray type at the top right. The title then starts about 1.1 in from the left edge instead of sitting flush left. No mark is drawn in the logo area.
- `title.rule`: `"under"` stays. Move the rule up so it sits under the header strip at about 20% of the page height, in gray `#999999` and thin. Ours is darker and thicker, and it carries a drop shadow.
- `table.header`: `"fill"` → `"text"` for comps: bold navy `1F396C` headers, the group labels underlined, a thin rule underneath.
- `table.stat_fill`: `FFFF99` → `E2EBF4`. PowerSchool shades Peer Mean/Median pale blue. `FFFF99` is from Focus 2023.
- **(new)** `table.grid_header`: on sensitivity grids, use an outlined pale-blue box over the column labels, plus a rotated "WACC" cell in a pale-blue box. Drop the midpoint-row highlight.
- **(new)** `ff.row_bands`: give each row a full-width band, pale blue `C5D3EE`/`E3ECF5` for core rows and gray `D9D9D9` for reference rows. Make the label cells the full row height.
- **(new)** `ff.headers`: "Methodology | Implied Equity Value Per Share | Commentary".
- **(new)** `ff.reference_label_rotated: true`, so the "For Reference" label runs vertically at the left of the reference group.
- **(new)** `cover.order`: `["subtitle", "project"]`. Real covers put "Presentation to the Board of Directors" in large black regular type first, with the project name in steel blue `7399C6` under it. After that come the bank name in bold and the date, with a footer disclaimer rule.
- **(new)** `dividers.furniture: true`. Keep the header strip and the footer rule on section dividers.
- `toc`: `true` stays, but use the list style with Roman numerals and "Appendix A:", and leave out the page numbers.

## Perella Weinberg (`perella`, ref. AgroFresh 2022 (c)(7))

- `table.header_fill`: `00639A` → `513C65` for the projections and financial tables. Keep `00639A` for the DCF sub-table banners.
- **(new)** `table.highlight_rows`: key lines (Revenue, Gross Profit, Adj. EBITDA) get cream `FFEED0` or salmon `FDE9E0`. Add a dashed vertical divider between the actual and projected columns.
- **(new)** `section_header`: blue `008BD2` ALL-CAPS headers with a blue rule under them, inside the page (for example "CORE PRODUCTS UNLEVERED FREE CASH FLOWS"). Perella relies on this more than any other device.
- `ff.method_colors.comps`: `00639A` → a purple-family tint such as `977CB1`. AgroFresh keeps every bar purple or lavender.
- **(new)** `ff.label_tiers: 2`, with a middle "Description / Assumptions" column. Move the methodology text out of the right-hand column into it.
- `cover`: shrink the title to ~20pt and put an italic ~18pt subtitle right under it. Put the rule under the subtitle, then the date, with the whole block at about 28% of the page height. Drop the second (top-right) wedge.
- `dividers.color`: `404040` → `513C65`. Divider text should sit flush with the left margin.
- `legend`: AgroFresh has none, and `"Confidential"` gray top-right comes from Baldwin 2026. That is fine if the template is Baldwin-era. Otherwise set it to `null`.

## J.P. Morgan (`jpm`, ref. Clearwater 2025 (c)(vi))

- `title.size`: 26 → 22.
- `toc`: `false` → `true`, as an "Agenda" list: brown `946946` section number and name, a right-hand "Page" column, a thin rule under each row.
- **(new)** `ff.label_tiers: 2`, with numbered circles (1–4) in the left margin.
- **(new)** `ff.commentary_bullets`: square bullets. Also add an "Implied FV / EBITDA multiple" column on the right.
- **(new)** `ff.current_color: "A6192E"`, a dark-red dashed line for the current price.
- **(new)** `ff.price_label_style: "italic_underline"`, placed under the axis.
- **(new)** `table.projection_header_fill: "8E5BA6"`, the purple band over the projection years. Key rows (Adj. EBITDA, NOPAT, UFCF) get a lilac band, `E9DDF0`.
- `table.header`: `"fill"` → `"text"` for comps: bold underlined headers with a year sub-row. Keep `1E7C98` for the peer-group bars and use gray `7F7F7F` for the reference-only group bar.
- `cover`: run the bottom rule full-bleed from the left edge at about 93% of the height. Move the title block down to about 42%.

## Jefferies (`jefferies`, ref. Whole Earth 2024 (c)(xi))

- **(new)** `page.margin`: ~0.4 in → ~0.15 in. The title sits right in the top-left corner.
- **(new)** `cover.rules_full_bleed: true` and `dividers.rules_full_bleed: true`.
- `dividers`: drop the Roman numerals. The divider should read "Situation Overview", not "I. Transaction Overview".
- `toc`: `true` stays, but as a list: ~10pt letterspaced section names with page numbers in a right-hand column, and no fill.
- `font.title` / `font.body`: `"Arial Narrow"` → a regular-width grotesque (for example `"Arial"`). The real face looks like Trade Gothic, which is not as condensed as Arial Narrow comes out in LibreOffice.
- **(new)** `ff.panels: true`: three outlined boxes, Methodology | chart | Metrics, with underlined method headings.
- **(new)** `ff.axis: true`, a $ axis, plus `ff.multiple_strip: true`, the "Implied Enterprise Value / EBITDA" strip under the axis.
- `ff.reference_label`: keep the text, but **(new)** `ff.reference_label_rotated: true` at the far left of the page.
- **(new)** `ff.value_color: "7F7F7F"`.
- **(new)** `terms_page.style: "grid"` for the transaction overview: a two-column gray-ruled grid with a pale-blue `EAF2FA` header strip and bulleted cells, not a filled-header table.
- **(new)** `comps.style: "bars"`, with green `8FB08C` peer bars, gray/steel subject bars and boxed group-median labels.

## Citi (`citi`, ref. Aspen 2025 (c)(10))

- `legend`: Aspen (2025) has none, so set it to `null`. The red italic "Preliminary | Confidential" line comes from Liberty 2024.
- `footer.page_number`: `"right_bar"` prints "4 |". Citi prints "logo | 3", so it needs **(new)** `"bar_right"`, with the bar before the number and the logo area left blank.
- `table.header`: `"fill"` → `"text"`: black column headers over a black rule, blue `255BE2` values on the key row, and light-blue `E3EBFB` bands on the equity and enterprise value rows.
- **(new)** `section_banner`: full-width `255BE2` banners with white centred text ("Unlevered Free Cash Flow Profile", "Illustrative Sensitivity Analysis"), used within a page instead of table header fills.
- **(new)** `table.side_tabs`: rotated vertical colour tabs that group rows by case (blue for management, green for consensus).
- **(new)** `ff.assumptions_column`, placed between the labels and the chart. Add full-width lavender `E6E9F8` row bands and "Implied Multiples" columns on the right.
- `ff.reference_position`: `"bottom"` stays, but drop the dashed separator. Aspen mixes the reference rows in at the bottom without one.
- `cover`: the frame should fill the page, which means moving the demo disclaimer inside it. Add a group-name line at the top left and shrink the title from ~36pt to ~30pt.

## Evercore (`evercore`, ref. EngageSmart 2023 (c)(ix) + Green Plains 2023 (c)(14))

- `title.two_tier`: `true` → skip the upper tier when the section name equals the page name. EngageSmart uses single-tier titles throughout, so consider setting it to `false` for that template.
- `table.header`: `"fill"` → `"text"`: bold navy `254D81` two-line headers, underlined, with blue `0069AA` group labels.
- **(new)** `table.stat_box: "254D81"`, a navy outline around the `F0F0F0` mean/median block. Group labels go in bold italic underline ("Enterprise Peers").
- **(new)** `table.key_row_box`: light-gray outlined boxes on key DCF rows (Implied Enterprise Value, Implied Value per Share).
- **(new)** `ff.metrics_column`: "Key Metrics and Methodologies" text next to the labels, then implied TEV / multiple / premium columns on the right. Halve the row spacing.
- `ff.label_blocks`: `false` → `true`. EngageSmart puts each method in a colour-filled label cell: navy for DCF, blue for trading, teal for precedents, gray for reference.
- `cover`: title ~28pt → ~20pt, with the rule spanning most of the width directly under it. Subtitle and date ~14pt. **(new)** `cover.draft_stamp`: a red boxed "PRELIMINARY DRAFT / Subject to Change / Highly Confidential / timestamp", top right.
- `toc`: `true` stays, but as a list: ~11pt black names, a "Section" column of Roman numerals, lettered appendix sub-items.
- `dividers`: close already. Align the numeral to the left margin (~0.6 in) and run the rule almost the full width.
