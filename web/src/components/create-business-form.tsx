"use client";

import { useActionState, useState } from "react";

import { createBusiness } from "@/actions/business";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BUSINESS_TYPE_OPTIONS } from "@/lib/constants";
import type { BusinessType } from "@/lib/db/schema";

const initialState: { error?: string } = {};

export function CreateBusinessForm() {
  const [businessType, setBusinessType] = useState<BusinessType | "">("");
  const [state, formAction, isPending] = useActionState(
    async (_prevState: { error?: string }, formData: FormData) => {
      return createBusiness(formData);
    },
    initialState,
  );

  return (
    <Card className="w-full max-w-lg">
      <CardHeader>
        <CardTitle>Create your business</CardTitle>
        <CardDescription>
          Tell us about your business so Businexa can tailor insights to your industry.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name">Business name</Label>
            <Input
              id="name"
              name="name"
              placeholder="Acme Coffee Shop"
              required
              disabled={isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="businessType">Business type</Label>
            <Select
              value={businessType}
              onValueChange={(value) => setBusinessType(value as BusinessType)}
              disabled={isPending}
            >
              <SelectTrigger id="businessType" className="w-full">
                <SelectValue placeholder="Select a business type" />
              </SelectTrigger>
              <SelectContent>
                {BUSINESS_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <input type="hidden" name="businessType" value={businessType} />
          </div>

          {state.error ? (
            <p className="text-sm text-destructive">{state.error}</p>
          ) : null}

          <Button
            type="submit"
            className="w-full"
            disabled={isPending || businessType === ""}
          >
            {isPending ? "Creating..." : "Create business"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
