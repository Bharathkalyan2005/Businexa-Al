import { relations } from "drizzle-orm";
import {
  jsonb,
  numeric,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uuid,
} from "drizzle-orm/pg-core";

export const businessTypeEnum = pgEnum("business_type", [
  "retail",
  "restaurant",
  "salon",
  "cleaning_service",
  "ecommerce",
  "other",
]);

export const datasetStatusEnum = pgEnum("dataset_status", [
  "uploaded",
  "profiling",
  "profiled",
  "cleaning",
  "cleaned",
  "analyzing",
  "analyzed",
  "failed",
]);

export const columnTypeEnum = pgEnum("column_type", [
  "date",
  "numeric",
  "categorical",
  "currency",
  "text",
  "unknown",
]);

export const insightCategoryEnum = pgEnum("insight_category", [
  "growth",
  "profitability",
  "anomaly",
  "product",
]);

export const chatRoleEnum = pgEnum("chat_role", ["user", "assistant"]);

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  clerkId: text("clerk_id").notNull().unique(),
  email: text("email").notNull(),
  name: text("name"),
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const businesses = pgTable("businesses", {
  id: uuid("id").primaryKey().defaultRandom(),
  userId: uuid("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  businessType: businessTypeEnum("business_type").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const datasets = pgTable("datasets", {
  id: uuid("id").primaryKey().defaultRandom(),
  businessId: uuid("business_id")
    .notNull()
    .references(() => businesses.id, { onDelete: "cascade" }),
  filename: text("filename").notNull(),
  storageUrl: text("storage_url").notNull(),
  status: datasetStatusEnum("status").notNull().default("uploaded"),
  uploadedAt: timestamp("uploaded_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const datasetColumns = pgTable("dataset_columns", {
  id: uuid("id").primaryKey().defaultRandom(),
  datasetId: uuid("dataset_id")
    .notNull()
    .references(() => datasets.id, { onDelete: "cascade" }),
  columnName: text("column_name").notNull(),
  detectedType: columnTypeEnum("detected_type").notNull(),
  missingCount: numeric("missing_count"),
  missingPct: numeric("missing_pct"),
});

export const metricsSnapshots = pgTable("metrics_snapshots", {
  id: uuid("id").primaryKey().defaultRandom(),
  datasetId: uuid("dataset_id")
    .notNull()
    .references(() => datasets.id, { onDelete: "cascade" }),
  revenue: numeric("revenue"),
  profit: numeric("profit"),
  orders: numeric("orders"),
  growthPct: numeric("growth_pct"),
  topProduct: text("top_product"),
  computedAt: timestamp("computed_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
  rawJson: jsonb("raw_json").notNull(),
});

export const insights = pgTable("insights", {
  id: uuid("id").primaryKey().defaultRandom(),
  datasetId: uuid("dataset_id")
    .notNull()
    .references(() => datasets.id, { onDelete: "cascade" }),
  insightText: text("insight_text").notNull(),
  category: insightCategoryEnum("category").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const chatMessages = pgTable("chat_messages", {
  id: uuid("id").primaryKey().defaultRandom(),
  businessId: uuid("business_id")
    .notNull()
    .references(() => businesses.id, { onDelete: "cascade" }),
  role: chatRoleEnum("role").notNull(),
  content: text("content").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

export const reports = pgTable("reports", {
  id: uuid("id").primaryKey().defaultRandom(),
  businessId: uuid("business_id")
    .notNull()
    .references(() => businesses.id, { onDelete: "cascade" }),
  datasetId: uuid("dataset_id")
    .notNull()
    .references(() => datasets.id, { onDelete: "cascade" }),
  pdfUrl: text("pdf_url").notNull(),
  generatedAt: timestamp("generated_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
});

// Relations (for typed Drizzle queries)
export const usersRelations = relations(users, ({ many }) => ({
  businesses: many(businesses),
}));

export const businessesRelations = relations(businesses, ({ one, many }) => ({
  user: one(users, { fields: [businesses.userId], references: [users.id] }),
  datasets: many(datasets),
  chatMessages: many(chatMessages),
  reports: many(reports),
}));

export const datasetsRelations = relations(datasets, ({ one, many }) => ({
  business: one(businesses, {
    fields: [datasets.businessId],
    references: [businesses.id],
  }),
  columns: many(datasetColumns),
  metricsSnapshots: many(metricsSnapshots),
  insights: many(insights),
  reports: many(reports),
}));

export const datasetColumnsRelations = relations(datasetColumns, ({ one }) => ({
  dataset: one(datasets, {
    fields: [datasetColumns.datasetId],
    references: [datasets.id],
  }),
}));

export const metricsSnapshotsRelations = relations(metricsSnapshots, ({ one }) => ({
  dataset: one(datasets, {
    fields: [metricsSnapshots.datasetId],
    references: [datasets.id],
  }),
}));

export const insightsRelations = relations(insights, ({ one }) => ({
  dataset: one(datasets, {
    fields: [insights.datasetId],
    references: [datasets.id],
  }),
}));

export const chatMessagesRelations = relations(chatMessages, ({ one }) => ({
  business: one(businesses, {
    fields: [chatMessages.businessId],
    references: [businesses.id],
  }),
}));

export const reportsRelations = relations(reports, ({ one }) => ({
  business: one(businesses, {
    fields: [reports.businessId],
    references: [businesses.id],
  }),
  dataset: one(datasets, {
    fields: [reports.datasetId],
    references: [datasets.id],
  }),
}));

export type User = typeof users.$inferSelect;
export type Business = typeof businesses.$inferSelect;
export type BusinessType = Business["businessType"];
