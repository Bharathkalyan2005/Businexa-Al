import { Calendar, Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ReportItem {
  id: string;
  pdfUrl: string;
  generatedAt: Date | string;
  dataset?: {
    filename: string;
  } | null;
}

interface ReportListProps {
  reports: ReportItem[];
}

export function ReportList({ reports }: ReportListProps) {
  if (!reports || reports.length === 0) {
    return (
      <Card className="border-border/80 bg-card/60 backdrop-blur-sm">
        <CardContent className="flex flex-col items-center justify-center py-16 text-center text-sm text-muted-foreground">
          <FileText className="mb-3 size-10 text-primary/40" />
          <p className="font-medium text-foreground">No reports generated yet</p>
          <p className="mt-1 text-xs">
            Click &quot;Generate New Report&quot; to build an executive performance summary PDF.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {reports.map((report) => (
        <Card key={report.id} className="border-border/80 bg-card/60 backdrop-blur-sm transition-colors hover:bg-card/80">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2 text-primary">
                <FileText className="size-5" />
              </div>
              <div>
                <p className="text-sm font-semibold">Executive Performance Report</p>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="size-3" />
                    {new Date(report.generatedAt).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  {report.dataset && (
                    <span>• Source: {report.dataset.filename}</span>
                  )}
                </div>
              </div>
            </div>

            <a href={report.pdfUrl} download={`Businexa_Report_${report.id.substring(0, 8)}.pdf`} target="_blank" rel="noreferrer">
              <Button variant="outline" size="sm" className="gap-1.5">
                <Download className="size-4" />
                Download PDF
              </Button>
            </a>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
