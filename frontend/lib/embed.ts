// Map an RSMeans row onto the CostSeg form fields.
// `amount` is deliberately absent: that's the take-off quantity the estimator
// enters, not something RSMeans knows.
//
// `description` overrides the row's own text — that's how an abbreviation chosen
// in the dialog travels, since the form caps descriptions at 50 characters.
export function rowToSelection(
  row: Row,
  description?: string
): CostSegSelection {
  // Total incl. O&P is the default the estimate is built on; bare total is the
  // fallback for rows RSMeans publishes without it. Both are sent so CostSeg can
  // let the estimator choose (new construction / improvement -> Bare Total).
  const price = row.total_op ?? row.bare_total;

  return {
    csiNumber: prettyLine(row.line_number),
    description: description?.trim() || row.description,
    unit: normalizeUnit(row.unit, row.is_percent),
    unitCost: price != null ? String(price) : undefined,
    bareTotal: row.bare_total != null ? String(row.bare_total) : undefined,
    totalOp: row.total_op != null ? String(row.total_op) : undefined,
  };
}