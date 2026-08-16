import type { BusinessType } from "@/lib/db/schema";

export const BUSINESS_TYPE_OPTIONS: ReadonlyArray<{
  value: BusinessType;
  label: string;
}> = [
  { value: "retail", label: "Retail" },
  { value: "restaurant", label: "Restaurant" },
  { value: "salon", label: "Salon" },
  { value: "cleaning_service", label: "Cleaning Service" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "other", label: "Other" },
] as const;

export function isBusinessType(value: string): value is BusinessType {
  return BUSINESS_TYPE_OPTIONS.some((option) => option.value === value);
}
