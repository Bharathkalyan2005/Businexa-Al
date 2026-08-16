import { neon } from "@neondatabase/serverless";
import { drizzle, type NeonHttpDatabase } from "drizzle-orm/neon-http";

import * as schema from "./schema";

type Database = NeonHttpDatabase<typeof schema>;

let dbInstance: Database | null = null;

function createDb(): Database {
  const url = process.env.DATABASE_URL;
  if (!url) {
    throw new Error("DATABASE_URL environment variable is not set");
  }

  const sql = neon(url);
  return drizzle(sql, { schema });
}

function getDb(): Database {
  if (!dbInstance) {
    dbInstance = createDb();
  }
  return dbInstance;
}

export const db = new Proxy({} as Database, {
  get(_target, prop, receiver) {
    return Reflect.get(getDb(), prop, receiver);
  },
});
