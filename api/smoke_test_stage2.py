"""
End-to-end smoke test: Stage 1 → Stage 2 (Groq) → validated spec.
Prints the resolved dashboard spec for both sample datasets.
"""
import asyncio, warnings, json
warnings.filterwarnings("ignore")

from tests.fixtures.universal_datasets import make_sales_df, make_clinical_df
from app.services.universal.profiler import build_data_profile
from app.services.universal.spec_generator import (
    generate_dashboard_spec,
    resolve_all_kpi_values,
)

async def run(label, df):
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")
    profile = build_data_profile(df)
    print(f"  Profile: {profile['row_count']} rows, target={profile['target_column']}")
    print("  Calling Groq API...")

    spec, used_fallback = await generate_dashboard_spec(profile)
    kpis = resolve_all_kpi_values(spec, profile)

    print(f"  used_fallback = {used_fallback}")
    print(f"  Domain  : {spec.domain}")
    print(f"  Title   : {spec.title}")
    print(f"  Accent  : {spec.accent_color}")
    print(f"\n  KPI Cards ({len(kpis)}):")
    for k in kpis:
        print(f"    [{k['format']:8s}]  {k['title']:<30s}  stat_ref={k['stat_ref']:<30s}  value={k['value']}")
    print(f"\n  Charts ({len(spec.charts)}):")
    for c in spec.charts:
        print(f"    [{c.chart_type:<16s}]  {c.title:<35s}  x={c.x_column}  y={c.y_columns}")

asyncio.run(run("SALES DATASET", make_sales_df()))
asyncio.run(run("CLINICAL DATASET", make_clinical_df()))
