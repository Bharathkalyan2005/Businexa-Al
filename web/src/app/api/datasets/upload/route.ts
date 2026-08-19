/**
 * API Route: POST /api/datasets/upload
 *
 * Accepts a file upload (CSV/XLSX), stores it in Vercel Blob (or local storage fallback),
 * creates a dataset row in Postgres, and triggers profiling & analysis via the Python service.
 */

import { put } from "@vercel/blob";
import { NextRequest, NextResponse } from "next/server";
import { and, eq } from "drizzle-orm";

import { getCurrentUser } from "@/lib/auth/get-current-user";
import { db } from "@/lib/db";
import { businesses, datasets } from "@/lib/db/schema";
import { analyzeDataset, profileDataset } from "@/lib/api/python-client";

const ALLOWED_EXTENSIONS = new Set([".csv", ".xlsx"]);
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const formData = await request.formData();
    const file = formData.get("file") as File | null;
    const businessId = formData.get("businessId") as string | null;

    if (!file || !businessId) {
      return NextResponse.json(
        { error: "File and businessId are required." },
        { status: 400 },
      );
    }

    const business = await db.query.businesses.findFirst({
      where: and(eq(businesses.id, businessId), eq(businesses.userId, user.id)),
    });

    if (!business) {
      return NextResponse.json(
        { error: "Business not found." },
        { status: 404 },
      );
    }

    const fileName = file.name.toLowerCase();
    const extension = fileName.substring(fileName.lastIndexOf("."));

    if (!ALLOWED_EXTENSIONS.has(extension)) {
      return NextResponse.json(
        { error: "Only .csv and .xlsx files are supported." },
        { status: 400 },
      );
    }

    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: "File size exceeds the 10 MB limit." },
        { status: 400 },
      );
    }

    // Upload to Vercel Blob or create simulated data URL if token is missing in local dev
    let fileUrl = "";
    try {
      if (process.env.BLOB_READ_WRITE_TOKEN && !process.env.BLOB_READ_WRITE_TOKEN.includes("dummy")) {
        const blob = await put(`datasets/${businessId}/${file.name}`, file, {
          access: "public",
        });
        fileUrl = blob.url;
      } else {
        // Local dev data URL encoding for direct transmission to python
        const buffer = await file.arrayBuffer();
        const base64 = Buffer.from(buffer).toString("base64");
        fileUrl = `data:${file.type || "text/csv"};base64,${base64}`;
      }
    } catch {
      const buffer = await file.arrayBuffer();
      const base64 = Buffer.from(buffer).toString("base64");
      fileUrl = `data:${file.type || "text/csv"};base64,${base64}`;
    }

    // Create dataset row in Postgres with initial status "uploaded"
    console.log(`[Upload Flow] Storing file record for businessId=${businessId}, filename=${file.name}`);
    const [dataset] = await db
      .insert(datasets)
      .values({
        businessId,
        filename: file.name,
        storageUrl: fileUrl,
        status: "uploaded",
      })
      .returning();

    console.log(`[Upload Flow] Created dataset row id=${dataset.id}. Triggering profiling...`);

    // Trigger profiling and analysis via Python service
    let profilingResult = null;
    let analysisResult = null;

    try {
      // Step 1: Profile dataset
      console.log(`[Upload Flow] Calling POST /datasets/${dataset.id}/profile...`);
      profilingResult = await profileDataset(
        dataset.id,
        fileUrl,
        business.businessType,
      );
      console.log(
        `[Upload Flow] Profiling completed for ${dataset.id}: quality_score=${profilingResult.quality_score}, columns=${profilingResult.columns.length}`,
      );

      // Step 2: Analyze dataset
      console.log(`[Upload Flow] Calling POST /datasets/${dataset.id}/analyze...`);
      analysisResult = await analyzeDataset(
        dataset.id,
        fileUrl,
        business.businessType,
      );
      console.log(
        `[Upload Flow] Analysis completed for ${dataset.id}: snapshot_id=${analysisResult.snapshot_id}, revenue=${analysisResult.metrics?.revenue}`,
      );

      // Ensure dataset status is updated to analyzed in DB
      await db
        .update(datasets)
        .set({ status: "analyzed" })
        .where(eq(datasets.id, dataset.id));

      return NextResponse.json({
        dataset: {
          id: dataset.id,
          filename: dataset.filename,
          storageUrl: dataset.storageUrl,
          status: "analyzed",
        },
        profiling: profilingResult,
        analysis: analysisResult,
      });
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Processing failed";
      console.error(`[Upload Flow] Pipeline error for dataset ${dataset.id}:`, error);

      // Mark dataset status as failed in database
      await db
        .update(datasets)
        .set({ status: "failed" })
        .where(eq(datasets.id, dataset.id));

      return NextResponse.json(
        {
          error: `Processing failed: ${errorMsg}`,
          dataset: {
            id: dataset.id,
            filename: dataset.filename,
            storageUrl: dataset.storageUrl,
            status: "failed",
          },
          profiling: profilingResult,
          analysis: null,
        },
        { status: 422 },
      );
    }
  } catch (error) {
    console.error("[Upload Flow] Upload error:", error);
    return NextResponse.json(
      { error: "An unexpected error occurred during upload." },
      { status: 500 },
    );
  }
}
