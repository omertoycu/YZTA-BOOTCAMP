export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value);
}

// "Caferağa, Kadıköy / İstanbul" — eski kayıtlarda city/neighborhood boş
// olabilir, dolu olanlar birleştirilir.
export function formatLocation(listing: {
  city?: string | null;
  district: string;
  neighborhood?: string | null;
}): string {
  const head = [listing.neighborhood, listing.district].filter(Boolean).join(", ");
  return listing.city ? `${head} / ${listing.city}` : head;
}
